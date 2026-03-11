"""Structured retrieval endpoint."""

import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from ..auth import verify_token
from ..config import settings
from ..db import get_conn
from ..memory_types import ENTRY_TYPES
from ..synthesis import synthesize_answer

router = APIRouter()


class RecallRequest(BaseModel):
    query: str = Field(..., max_length=2000, description="Natural language question or search")
    entity_name: str | None = Field(default=None, description="Filter by entity name")
    entry_type: str | None = Field(default=None, description="Filter by entry type")
    after: datetime | None = Field(default=None, description="Entries after this time")
    before: datetime | None = Field(default=None, description="Entries before this time")
    limit: int = Field(default=20, ge=1, le=50)
    synthesize: bool = Field(default=True, description="Generate an LLM-synthesized answer from results")

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be empty")
        return stripped

    @field_validator("entry_type")
    @classmethod
    def validate_entry_type(cls, value: str | None) -> str | None:
        if value is not None and value not in ENTRY_TYPES:
            raise ValueError(f"entry_type must be one of: {', '.join(sorted(ENTRY_TYPES))}")
        return value


class RecallEntry(BaseModel):
    entry_id: UUID
    entry_type: str
    body: str
    source: str
    occurred_at: datetime
    entities: list[dict]


class Citation(BaseModel):
    index: int
    entry_id: UUID
    entry_type: str
    occurred_at: datetime


class RecallResponse(BaseModel):
    entries: list[RecallEntry]
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    total_found: int


def _decode_entities(raw_entities) -> list[dict]:
    if not raw_entities:
        return []
    if isinstance(raw_entities, str):
        return json.loads(raw_entities)
    return raw_entities


@router.post("/recall", response_model=RecallResponse, dependencies=[Depends(verify_token)])
async def recall(req: RecallRequest):
    """Search memory with structured filters plus full-text search."""
    conditions: list[str] = []
    params: list[object] = []
    param_idx = 0

    if req.query:
        param_idx += 1
        conditions.append(f"e.tsv @@ websearch_to_tsquery('english', ${param_idx})")
        params.append(req.query)
        rank_expr = f"ts_rank_cd(e.tsv, websearch_to_tsquery('english', ${param_idx}))"
    else:
        rank_expr = "0"

    if req.entity_name:
        param_idx += 1
        conditions.append(
            f"""
            e.id IN (
                SELECT ee.entry_id FROM memory.entry_entities ee
                JOIN memory.entities ent ON ent.id = ee.entity_id
                WHERE ent.normalized_name = LOWER(${param_idx})
                   OR LOWER(${param_idx}) = ANY(SELECT LOWER(a) FROM unnest(ent.aliases) a)
            )
            """
        )
        params.append(req.entity_name)

    if req.entry_type:
        param_idx += 1
        conditions.append(f"e.entry_type = ${param_idx}")
        params.append(req.entry_type)

    if req.after:
        param_idx += 1
        conditions.append(f"e.occurred_at >= ${param_idx}")
        params.append(req.after)

    if req.before:
        param_idx += 1
        conditions.append(f"e.occurred_at <= ${param_idx}")
        params.append(req.before)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    param_idx += 1
    limit_param = param_idx
    effective_limit = min(req.limit, settings.max_recall_results)

    query = f"""
        SELECT
            e.id, e.entry_type, e.body, e.source, e.occurred_at,
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
        LIMIT ${limit_param}
    """
    params.append(effective_limit)

    async with get_conn() as conn:
        rows = await conn.fetch(query, *params)
        count_query = f"""
            SELECT COUNT(DISTINCT e.id)
            FROM memory.entries e
            LEFT JOIN memory.entry_entities ee ON ee.entry_id = e.id
            LEFT JOIN memory.entities ent ON ent.id = ee.entity_id
            WHERE {where_clause}
        """
        total = await conn.fetchval(count_query, *params[:-1])

    entries = [
        RecallEntry(
            entry_id=row["id"],
            entry_type=row["entry_type"],
            body=row["body"],
            source=row["source"],
            occurred_at=row["occurred_at"],
            entities=_decode_entities(row["entities"]),
        )
        for row in rows
    ]

    answer = None
    if req.synthesize and entries:
        try:
            answer = await synthesize_answer(req.query, entries)
        except Exception:
            answer = None

    citations = [
        Citation(index=index, entry_id=entry.entry_id, entry_type=entry.entry_type, occurred_at=entry.occurred_at)
        for index, entry in enumerate(entries, start=1)
    ]

    return RecallResponse(entries=entries, answer=answer, citations=citations, total_found=total)
