"""Helpers for file-backed memory ingestion flows."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from .extraction import extract_from_log
from .memory_types import normalize_extraction

PERSONAL_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "icloud.com",
    "me.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "proton.me",
    "protonmail.com",
    "yahoo.com",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def compose_entry_body(title: str | None, content: str) -> str:
    """Prefix content with title when it helps retrieval and human scanning."""
    title_text = (title or "").strip()
    content_text = content.strip()
    if title_text and not content_text.startswith(title_text):
        return f"{title_text}\n\n{content_text}"
    return content_text


def _display_name_from_email(email: str) -> str | None:
    local_part, _, domain = email.strip().lower().partition("@")
    if not local_part or not domain:
        return None

    pieces = [piece for piece in re.split(r"[._-]+", local_part) if piece]
    if len(pieces) >= 2:
        return " ".join(piece.capitalize() for piece in pieces)
    return None


def _company_from_domain(domain: str) -> str | None:
    normalized = domain.strip().lower()
    if not normalized or normalized in PERSONAL_EMAIL_DOMAINS:
        return None

    root = normalized.split(".")[0]
    if not root:
        return None
    return " ".join(piece.capitalize() for piece in re.split(r"[-_]+", root) if piece)


def participant_entities(participants: list[str]) -> list[dict[str, Any]]:
    """Derive stable participant and company entities from transcript metadata."""
    entities: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for raw_participant in participants:
        participant = str(raw_participant or "").strip()
        if not participant:
            continue

        person_name = participant
        aliases: list[str] = []
        company_name: str | None = None
        if EMAIL_RE.match(participant):
            aliases = [participant.lower()]
            display_name = _display_name_from_email(participant)
            if display_name:
                person_name = display_name
            _, _, domain = participant.partition("@")
            company_name = _company_from_domain(domain)

        person_key = ("person", person_name.lower(), "participant")
        if person_key not in seen:
            entities.append({"name": person_name, "type": "person", "role": "participant", "aliases": aliases})
            seen.add(person_key)

        if company_name:
            company_key = ("company", company_name.lower(), "mentioned")
            if company_key not in seen:
                entities.append({"name": company_name, "type": "company", "role": "mentioned"})
                seen.add(company_key)

    return entities


def merge_entities(*entity_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge entity lists without duplicating the same type/name/role triple."""
    merged: list[dict[str, Any]] = []
    seen: dict[tuple[str, str, str], dict[str, Any]] = {}

    for entity_list in entity_lists:
        for entity in entity_list:
            name = str(entity.get("name", "")).strip()
            entity_type = str(entity.get("type", "topic")).strip() or "topic"
            role = str(entity.get("role", "mentioned")).strip() or "mentioned"
            if not name:
                continue

            key = (entity_type, name.lower(), role)
            aliases = [str(alias).strip().lower() for alias in entity.get("aliases", []) if str(alias).strip()]
            if key not in seen:
                normalized = dict(entity)
                normalized["name"] = name
                if aliases:
                    normalized["aliases"] = sorted(set(aliases))
                merged.append(normalized)
                seen[key] = normalized
                continue

            if aliases:
                existing_aliases = [str(alias).strip().lower() for alias in seen[key].get("aliases", []) if str(alias).strip()]
                seen[key]["aliases"] = sorted(set(existing_aliases + aliases))

    return merged


def checksum_for(*parts: object) -> str:
    """Compute a stable checksum for idempotent re-ingest."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part if part is not None else "").encode("utf-8"))
        digest.update(b"\n\x1f\n")
    return digest.hexdigest()


def ensure_utc(value: datetime | None) -> datetime:
    """Default missing datetimes and normalize aware values to UTC."""
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def classify_text(text: str, default_entry_type: str) -> dict[str, Any]:
    """Reuse log extraction, but preserve route-specific defaults on weak output."""
    try:
        extraction = normalize_extraction(await extract_from_log(text))
    except Exception:
        extraction = {"entry_type": default_entry_type, "entities": []}

    if extraction.get("entry_type") == "observation" and default_entry_type != "observation":
        extraction["entry_type"] = default_entry_type
    extraction.setdefault("entities", [])
    return extraction


async def create_ingestion_job(conn, source_type: str, source_ref: str | None) -> UUID:
    """Create an ingestion job row and return its ID."""
    return await conn.fetchval(
        """
        INSERT INTO memory.ingestion_jobs (source_type, source_ref, status)
        VALUES ($1, $2, 'processing')
        RETURNING id
        """,
        source_type,
        source_ref,
    )


async def complete_ingestion_job(
    conn,
    job_id: UUID,
    *,
    entries_created: int,
    entities_linked: int,
    error_message: str | None = None,
) -> None:
    """Mark an ingestion job as completed or failed."""
    status = "failed" if error_message else "completed"
    await conn.execute(
        """
        UPDATE memory.ingestion_jobs
        SET status = $2,
            entries_created = $3,
            entities_linked = $4,
            error_message = $5,
            completed_at = NOW()
        WHERE id = $1
        """,
        job_id,
        status,
        entries_created,
        entities_linked,
        error_message,
    )


async def link_entities(conn, entry_id: UUID, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Upsert entities and link them to an entry."""
    linked: list[dict[str, Any]] = []
    for ent in entities:
        entity_name = ent.get("name", "").strip()
        if not entity_name:
            continue

        aliases = [str(alias).strip().lower() for alias in ent.get("aliases", []) if str(alias).strip()]

        entity_id = await conn.fetchval(
            """
            INSERT INTO memory.entities (entity_type, name, normalized_name, aliases)
            VALUES ($1, $2, LOWER($2), $3::text[])
            ON CONFLICT (entity_type, normalized_name) DO UPDATE
            SET updated_at = NOW(),
                aliases = (
                    SELECT COALESCE(array_agg(DISTINCT alias), '{}'::text[])
                    FROM unnest(COALESCE(memory.entities.aliases, '{}'::text[]) || EXCLUDED.aliases) AS alias
                )
            RETURNING id
            """,
            ent.get("type", "topic"),
            entity_name,
            aliases,
        )

        await conn.execute(
            """
            INSERT INTO memory.entry_entities (entry_id, entity_id, role)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
            """,
            entry_id,
            entity_id,
            ent.get("role", "mentioned"),
        )
        linked.append(
            {
                "name": entity_name,
                "type": ent.get("type", "topic"),
                "role": ent.get("role", "mentioned"),
                "aliases": aliases,
            }
        )

    return linked


async def upsert_entry_by_source_ref(
    conn,
    *,
    source: str,
    source_ref: str | None,
    entry_type: str,
    body: str,
    occurred_at: datetime,
    structured: dict[str, Any],
) -> tuple[UUID, str]:
    """Create or update a file-backed entry keyed by source/source_ref."""
    checksum = structured.get("checksum")
    existing = None
    if source_ref:
        existing = await conn.fetchrow(
            """
            SELECT id, structured
            FROM memory.entries
            WHERE source = $1 AND source_ref = $2
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
            """,
            source,
            source_ref,
        )

    if existing:
        existing_structured = existing["structured"] or {}
        if isinstance(existing_structured, str):
            try:
                existing_structured = json.loads(existing_structured)
            except json.JSONDecodeError:
                existing_structured = {}
        if existing_structured.get("checksum") == checksum:
            return existing["id"], "unchanged"

        await conn.execute(
            """
            UPDATE memory.entries
            SET entry_type = $2,
                body = $3,
                structured = $4::jsonb,
                occurred_at = $5
            WHERE id = $1
            """,
            existing["id"],
            entry_type,
            body,
            json.dumps(structured),
            occurred_at,
        )
        await conn.execute("DELETE FROM memory.entry_entities WHERE entry_id = $1", existing["id"])
        return existing["id"], "updated"

    entry_id = await conn.fetchval(
        """
        INSERT INTO memory.entries (entry_type, body, structured, source, source_ref, occurred_at)
        VALUES ($1, $2, $3::jsonb, $4, $5, $6)
        RETURNING id
        """,
        entry_type,
        body,
        json.dumps(structured),
        source,
        source_ref,
        occurred_at,
    )
    return entry_id, "created"
