"""Primary capture endpoint."""

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from ..auth import verify_token
from ..config import settings
from ..db import get_conn
from ..extraction import extract_from_log
from ..memory_types import SOURCES, normalize_extraction

router = APIRouter()


class LogRequest(BaseModel):
    text: str = Field(..., max_length=settings.max_body_length, description="Natural language log entry")
    source: str = Field(default="tars", description="Input channel")
    occurred_at: datetime | None = Field(default=None, description="When this happened (defaults to now)")
    source_ref: str | None = Field(default=None, description="Origin reference: filename, message ID, URL, etc.")
    tags: list[str] = Field(default_factory=list, description="Optional tags for filtering")
    structured: dict | None = Field(default=None, description="Optional structured payload")

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if value not in SOURCES:
            raise ValueError(f"source must be one of: {', '.join(sorted(SOURCES))}")
        return value


class LogResponse(BaseModel):
    entry_id: UUID
    entry_type: str
    entities_linked: list[dict]
    ingestion_job_id: UUID


@router.post("/log", response_model=LogResponse, dependencies=[Depends(verify_token)])
async def create_log(req: LogRequest):
    """Log an entry with automatic entity extraction and classification."""
    occurred = req.occurred_at or datetime.now(timezone.utc)
    structured = dict(req.structured or {})
    if req.tags:
        structured["tags"] = req.tags

    try:
        extraction = normalize_extraction(await extract_from_log(req.text))
    except Exception:
        extraction = {
            "entry_type": "observation",
            "entities": [],
            "summary": req.text,
        }

    async with get_conn() as conn:
        async with conn.transaction():
            job_id = await conn.fetchval(
                """
                INSERT INTO memory.ingestion_jobs (source_type, source_ref, status)
                VALUES ($1, $2, 'processing')
                RETURNING id
                """,
                "tars_log" if req.source == "tars" else req.source,
                req.source_ref,
            )

            entry_id = await conn.fetchval(
                """
                INSERT INTO memory.entries (entry_type, body, structured, source, source_ref, occurred_at)
                VALUES ($1, $2, $3::jsonb, $4, $5, $6)
                RETURNING id
                """,
                extraction.get("entry_type", "observation"),
                req.text,
                json.dumps(structured),
                req.source,
                req.source_ref,
                occurred,
            )

            linked = []
            for ent in extraction.get("entities", []):
                entity_name = ent.get("name", "unknown")
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
                        "type": ent.get("type"),
                        "role": ent.get("role", "mentioned"),
                    }
                )

            await conn.execute(
                """
                UPDATE memory.ingestion_jobs
                SET status = 'completed', entries_created = 1, entities_linked = $2, completed_at = NOW()
                WHERE id = $1
                """,
                job_id,
                len(linked),
            )

    return LogResponse(
        entry_id=entry_id,
        entry_type=extraction.get("entry_type", "observation"),
        entities_linked=linked,
        ingestion_job_id=job_id,
    )
