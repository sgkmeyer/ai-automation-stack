"""Helpers for file-backed memory ingestion flows."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from .extraction import extract_from_log
from .memory_types import normalize_extraction


def compose_entry_body(title: str | None, content: str) -> str:
    """Prefix content with title when it helps retrieval and human scanning."""
    title_text = (title or "").strip()
    content_text = content.strip()
    if title_text and not content_text.startswith(title_text):
        return f"{title_text}\n\n{content_text}"
    return content_text


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

        entity_id = await conn.fetchval(
            """
            INSERT INTO memory.entities (entity_type, name, normalized_name)
            VALUES ($1, $2, LOWER($2))
            ON CONFLICT (entity_type, normalized_name) DO UPDATE SET updated_at = NOW()
            RETURNING id
            """,
            ent.get("type", "topic"),
            entity_name,
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
