"""Shared search helpers for memory and context lanes."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import settings
from .db import get_conn
from .memory_types import ENTRY_TYPES

TEMPORAL_OPERATORS = (
    "most recent",
    "this month",
    "this week",
    "yesterday",
    "newest",
    "latest",
    "recent",
    "today",
)
GENERIC_TRANSCRIPT_TERMS = (
    "transcripts",
    "transcript",
    "summaries",
    "summary",
    "meetings",
    "meeting",
    "conversations",
    "conversation",
    "calls",
    "call",
)
TRANSCRIPT_HINT_TERMS = GENERIC_TRANSCRIPT_TERMS + (
    "action items",
    "action item",
    "follow up",
    "follow-up",
    "open loops",
    "open loop",
    "waiting on",
)
ACTION_ITEM_TERMS = (
    "action items",
    "action item",
    "follow ups",
    "follow up",
    "follow-ups",
    "follow-up",
    "open loops",
    "open loop",
    "waiting on",
)
LOW_SIGNAL_TERMS = {
    "a",
    "about",
    "all",
    "for",
    "from",
    "get",
    "i",
    "latest",
    "me",
    "most",
    "my",
    "newest",
    "of",
    "please",
    "recent",
    "show",
    "the",
    "this",
    "today",
    "what",
    "yesterday",
}


@dataclass(slots=True)
class RecallQueryPlan:
    original_query: str
    normalized_query: str
    effective_query: str
    use_transcript_recency: bool
    wants_action_items: bool
    after: datetime | None
    before: datetime | None
    is_low_signal: bool
    dedupe_transcript_families: bool


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


def normalize_query_text(query: str) -> str:
    cleaned = re.sub(r"\s+", " ", query.strip())
    return cleaned


def build_recall_query_plan(
    *,
    query: str,
    lane: str,
    after: datetime | None = None,
    before: datetime | None = None,
    now: datetime | None = None,
) -> RecallQueryPlan:
    normalized_query = normalize_query_text(query)
    lowered = normalized_query.lower()
    temporal_operator = _detect_temporal_operator(lowered)
    wants_action_items = _contains_any_term(lowered, ACTION_ITEM_TERMS)
    transcript_hint = lane == "transcripts" or _contains_any_term(lowered, TRANSCRIPT_HINT_TERMS)
    use_transcript_recency = temporal_operator is not None and transcript_hint

    effective_query = normalized_query
    if use_transcript_recency:
        effective_query = _remove_terms(normalized_query, TEMPORAL_OPERATORS)
        effective_query = _remove_terms(effective_query, GENERIC_TRANSCRIPT_TERMS)
        effective_query = normalize_query_text(effective_query.lower())

    is_low_signal = _is_low_signal_query(effective_query)
    derived_after, derived_before = _derive_temporal_bounds(
        temporal_operator=temporal_operator,
        now=now,
    )

    return RecallQueryPlan(
        original_query=normalized_query,
        normalized_query=normalized_query,
        effective_query=effective_query,
        use_transcript_recency=use_transcript_recency,
        wants_action_items=wants_action_items,
        after=after or derived_after,
        before=before or derived_before,
        is_low_signal=is_low_signal,
        dedupe_transcript_families=use_transcript_recency and not wants_action_items,
    )


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

    plan = build_recall_query_plan(query=query, lane=lane, after=after, before=before)
    effective_lane = "transcripts" if lane == "all" and plan.use_transcript_recency else lane
    search_query = plan.effective_query if not plan.is_low_signal else ""

    conditions: list[str] = []
    params: list[object] = []
    param_idx = 0
    rank_expr = _memory_rank_expr(search_query, param_idx)
    if search_query:
        param_idx += 1
        conditions.append(f"e.tsv @@ websearch_to_tsquery('english', ${param_idx}::text)")
        params.append(search_query)

    if effective_lane == "transcripts":
        conditions.append("(e.source = 'transcript' OR e.entry_type IN ('transcript_summary', 'action_item'))")
    elif effective_lane == "memory":
        conditions.append("NOT (e.source = 'transcript' OR e.entry_type IN ('transcript_summary', 'action_item'))")

    if plan.use_transcript_recency and not plan.wants_action_items:
        conditions.append("e.entry_type <> 'action_item'")

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

    if plan.after:
        param_idx += 1
        conditions.append(f"e.occurred_at >= ${param_idx}")
        params.append(plan.after)

    if plan.before:
        param_idx += 1
        conditions.append(f"e.occurred_at < ${param_idx}")
        params.append(plan.before)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    fetch_limit = min(limit, settings.max_recall_results)
    query_limit = fetch_limit
    if plan.use_transcript_recency:
        query_limit = max(fetch_limit, min(fetch_limit * 10, settings.max_recall_results * 10))

    param_idx += 1
    params.append(query_limit)
    order_clause = "e.occurred_at DESC, rank DESC" if plan.use_transcript_recency else "rank DESC, e.occurred_at DESC"

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
            ORDER BY {order_clause}
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

    results = [
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
    ]

    if plan.dedupe_transcript_families:
        results = dedupe_transcript_results(results, fetch_limit)
        total = len(results)
    else:
        results = results[:fetch_limit]

    return results, int(total or 0)


def dedupe_transcript_results(results: list[dict], limit: int) -> list[dict]:
    best_by_family: dict[str, dict] = {}
    for result in results:
        if result.get("source_type") == "action_item":
            continue
        family_key = transcript_family_base(result.get("source_ref"))
        current = best_by_family.get(family_key)
        if current is None or _transcript_candidate_sort_key(result) > _transcript_candidate_sort_key(current):
            best_by_family[family_key] = result

    deduped = sorted(
        best_by_family.values(),
        key=lambda result: (
            datetime.fromisoformat(result["occurred_at"]),
            transcript_family_priority(result.get("source_ref")),
            float(result.get("score", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return deduped[:limit]


def transcript_family_base(source_ref: str | None) -> str:
    if not source_ref:
        return ""
    if "#action_item:" in source_ref:
        return source_ref.split("#action_item:", 1)[0]
    if "#" in source_ref:
        return source_ref.split("#", 1)[0]
    return source_ref


def transcript_family_priority(source_ref: str | None) -> int:
    if not source_ref:
        return 0
    if source_ref.endswith("#key_points"):
        return 3
    if source_ref.endswith("#action_items"):
        return 1
    if "#action_item:" in source_ref:
        return 0
    if "#" not in source_ref:
        return 2
    return 0


def _memory_rank_expr(query: str, param_idx: int) -> str:
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


def _contains_any_term(query: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", query) for term in terms)


def _detect_temporal_operator(query: str) -> str | None:
    for phrase in TEMPORAL_OPERATORS:
        if re.search(rf"\b{re.escape(phrase)}\b", query):
            return phrase
    return None


def _remove_terms(query: str, terms: tuple[str, ...]) -> str:
    cleaned = query
    for term in sorted(terms, key=len, reverse=True):
        cleaned = re.sub(rf"\b{re.escape(term)}\b", " ", cleaned, flags=re.IGNORECASE)
    return normalize_query_text(cleaned)


def _is_low_signal_query(query: str) -> bool:
    tokens = [token for token in re.findall(r"[a-z0-9]+", query.lower()) if token]
    if not tokens:
        return True
    informative_tokens = [token for token in tokens if token not in LOW_SIGNAL_TERMS and len(token) > 2]
    return not informative_tokens


def _derive_temporal_bounds(
    *,
    temporal_operator: str | None,
    now: datetime | None = None,
) -> tuple[datetime | None, datetime | None]:
    if temporal_operator is None or temporal_operator in {"latest", "newest", "most recent", "recent"}:
        return None, None

    current = now or datetime.now(display_zone())
    if current.tzinfo is None:
        current = current.replace(tzinfo=display_zone())
    local_current = current.astimezone(display_zone())

    if temporal_operator == "today":
        start = local_current.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif temporal_operator == "yesterday":
        end = local_current.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)
    elif temporal_operator == "this week":
        start = local_current.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=local_current.weekday())
        end = local_current + timedelta(seconds=1)
    elif temporal_operator == "this month":
        start = local_current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = local_current + timedelta(seconds=1)
    else:
        return None, None

    return start.astimezone(UTC), end.astimezone(UTC)


def _transcript_candidate_sort_key(result: dict) -> tuple[int, datetime, float]:
    return (
        transcript_family_priority(result.get("source_ref")),
        datetime.fromisoformat(result["occurred_at"]),
        float(result.get("score", 0.0) or 0.0),
    )


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
