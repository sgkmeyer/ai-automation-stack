"""Shared search helpers for memory and context lanes."""

from __future__ import annotations

import json
import re
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import settings
from .db import get_conn
from .memory_types import ENTRY_TYPES


def display_zone() -> ZoneInfo:
    try:
        return ZoneInfo(settings.display_timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def format_local_time(value: datetime) -> str:
    return value.astimezone(display_zone()).strftime("%Y-%m-%d %I:%M %p %Z")


def decode_entities(raw_entities) -> list[dict]:
    if not raw_entities:
        return []
    if isinstance(raw_entities, str):
        return json.loads(raw_entities)
    return raw_entities


def ranking_bonus_expr() -> str:
    return """
        CASE
            WHEN e.entry_type = 'action_item' THEN 0.95
            WHEN e.source = 'transcript' AND COALESCE(e.structured->>'source_event_type', '') = 'action_items_generated' THEN 0.85
            WHEN e.source = 'transcript' AND COALESCE(e.structured->>'source_event_type', '') = 'key_points_generated' THEN 0.75
            WHEN e.source = 'transcript' AND COALESCE(e.structured->>'source_event_type', '') = 'transcript_created' THEN 0.15
            ELSE 0
        END
    """


async def search_memory_entries(
    *,
    query: str,
    entity_name: str | None = None,
    entry_type: str | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
    limit: int = 20,
    lane: str = "memory",
) -> tuple[list[dict], int]:
    if entry_type is not None and entry_type not in ENTRY_TYPES:
        raise ValueError(f"entry_type must be one of: {', '.join(sorted(ENTRY_TYPES))}")

    conditions: list[str] = []
    params: list[object] = []
    param_idx = 0
    rank_expr = _memory_rank_expr(query, params, param_idx)
    if query:
        param_idx += 1
        conditions.append(f"e.tsv @@ websearch_to_tsquery('english', ${param_idx}::text)")
        params.append(query)

    if lane == "transcripts":
        conditions.append("(e.source = 'transcript' OR e.entry_type IN ('transcript_summary', 'action_item'))")
    elif lane == "memory":
        conditions.append("NOT (e.source = 'transcript' OR e.entry_type IN ('transcript_summary', 'action_item'))")

    if entity_name:
        param_idx += 1
        conditions.append(
            f"""
            e.id IN (
                SELECT ee.entry_id FROM memory.entry_entities ee
                JOIN memory.entities ent ON ent.id = ee.entity_id
                WHERE ent.normalized_name = LOWER(${param_idx}::text)
                   OR ent.normalized_name LIKE '%' || LOWER(${param_idx}::text) || '%'
                   OR EXISTS (
                        SELECT 1
                        FROM unnest(ent.aliases) AS alias
                        WHERE LOWER(alias) = LOWER(${param_idx}::text)
                           OR LOWER(alias) LIKE '%' || LOWER(${param_idx}::text) || '%'
                   )
            )
            """
        )
        params.append(entity_name)

    if entry_type:
        param_idx += 1
        conditions.append(f"e.entry_type = ${param_idx}")
        params.append(entry_type)

    if after:
        param_idx += 1
        conditions.append(f"e.occurred_at >= ${param_idx}")
        params.append(after)

    if before:
        param_idx += 1
        conditions.append(f"e.occurred_at <= ${param_idx}")
        params.append(before)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    param_idx += 1
    params.append(min(limit, settings.max_recall_results))

    async with get_conn() as conn:
        rows = await conn.fetch(
            f"""
            SELECT
                e.id, e.entry_type, e.body, e.source, e.source_ref, e.occurred_at,
                {rank_expr} AS rank,
                COALESCE(
                    json_agg(
                        json_build_object('name', ent.name, 'type', ent.entity_type, 'role', ee.role)
                    ) FILTER (WHERE ent.id IS NOT NULL),
                    '[]'::json
                ) AS entities
            FROM memory.entries e
            LEFT JOIN memory.entry_entities ee ON ee.entry_id = e.id
            LEFT JOIN memory.entities ent ON ent.id = ee.entity_id
            WHERE {where_clause}
            GROUP BY e.id
            ORDER BY rank DESC, e.occurred_at DESC
            LIMIT ${param_idx}
            """,
            *params,
        )
        total = await conn.fetchval(
            f"""
            SELECT COUNT(DISTINCT e.id)
            FROM memory.entries e
            LEFT JOIN memory.entry_entities ee ON ee.entry_id = e.id
            LEFT JOIN memory.entities ent ON ent.id = ee.entity_id
            WHERE {where_clause}
            """,
            *params[:-1],
        )

    return [
        {
            "id": str(row["id"]),
            "title": _title_from_body(row["body"]),
            "summary": _truncate(row["body"], 400),
            "body": row["body"],
            "source_type": row["entry_type"],
            "source": row["source"],
            "source_ref": row["source_ref"],
            "occurred_at": row["occurred_at"].isoformat(),
            "occurred_at_local": format_local_time(row["occurred_at"]),
            "display_timezone": settings.display_timezone,
            "entity_refs": [entity.get("name") for entity in decode_entities(row["entities"]) if entity.get("name")],
            "citation": f"{row['source']}:{row['entry_type']}",
            "score": float(row["rank"] or 0),
        }
        for row in rows
    ], int(total or 0)


def _memory_rank_expr(query: str, params: list[object], param_idx: int) -> str:
    if query:
        return f"(ts_rank_cd(e.tsv, websearch_to_tsquery('english', ${param_idx + 1}::text)) + {ranking_bonus_expr()})"
    return ranking_bonus_expr()


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


def _title_from_body(body: str) -> str:
    first_line = body.splitlines()[0].strip() if body else ""
    if not first_line:
        return "Memory entry"
    return _truncate(first_line, 120)


def normalize_query_text(query: str) -> str:
    cleaned = re.sub(r"\s+", " ", query.strip())
    return cleaned


async def search_context_entries(*, query: str, limit: int = 10) -> tuple[list[dict], int]:
    normalized = normalize_query_text(query).lower()
    like_value = f"%{normalized}%"

    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT
                domain,
                key,
                value,
                updated_at,
                CASE
                    WHEN LOWER(key) = $1 THEN 0.95
                    WHEN LOWER(domain) = $1 THEN 0.90
                    WHEN LOWER(key) LIKE $2 THEN 0.80
                    WHEN LOWER(value) LIKE $2 THEN 0.65
                    WHEN LOWER(domain) LIKE $2 THEN 0.60
                    ELSE 0.40
                END AS score
            FROM memory.context_register
            WHERE LOWER(domain) LIKE $2
               OR LOWER(key) LIKE $2
               OR LOWER(value) LIKE $2
            ORDER BY score DESC, updated_at DESC
            LIMIT $3
            """,
            normalized,
            like_value,
            limit,
        )
        total = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM memory.context_register
            WHERE LOWER(domain) LIKE $1
               OR LOWER(key) LIKE $1
               OR LOWER(value) LIKE $1
            """,
            like_value,
        )

    return [
        {
            "id": f"{row['domain']}::{row['key']}",
            "title": f"{row['domain']} / {row['key']}",
            "summary": row["value"],
            "source_type": "context_entry",
            "source": "context",
            "source_ref": f"{row['domain']}:{row['key']}",
            "occurred_at": row["updated_at"].isoformat(),
            "occurred_at_local": format_local_time(row["updated_at"]),
            "display_timezone": settings.display_timezone,
            "entity_refs": [],
            "citation": "context register",
            "score": float(row["score"] or 0),
        }
        for row in rows
    ], int(total or 0)
