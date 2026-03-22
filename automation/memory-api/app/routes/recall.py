"""Structured retrieval endpoint."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from ..auth import verify_token
from ..config import settings
from ..memory_types import ENTRY_TYPES
from ..recall_service import decode_entities, format_local_time, search_memory_entries
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
    occurred_at_local: str
    display_timezone: str
    entities: list[dict]


class Citation(BaseModel):
    index: int
    entry_id: UUID
    entry_type: str
    occurred_at: datetime
    occurred_at_local: str
    display_timezone: str


class RecallResponse(BaseModel):
    entries: list[RecallEntry]
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    total_found: int

@router.post("/recall", response_model=RecallResponse, dependencies=[Depends(verify_token)])
async def recall(req: RecallRequest):
    """Search memory with structured filters plus full-text search."""
    rows, total = await search_memory_entries(
        query=req.query,
        entity_name=req.entity_name,
        entry_type=req.entry_type,
        after=req.after,
        before=req.before,
        limit=req.limit,
        lane="all",
    )

    entries = [
        RecallEntry(
            entry_id=UUID(row["id"]),
            entry_type=row["source_type"],
            body=row["body"],
            source=row["source"],
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
            occurred_at_local=row["occurred_at_local"],
            display_timezone=settings.display_timezone,
            entities=[{"name": name, "type": "unknown", "role": "mentioned"} for name in row.get("entity_refs", [])],
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
        Citation(
            index=index,
            entry_id=entry.entry_id,
            entry_type=entry.entry_type,
            occurred_at=entry.occurred_at,
            occurred_at_local=entry.occurred_at_local,
            display_timezone=settings.display_timezone,
        )
        for index, entry in enumerate(entries, start=1)
    ]

    return RecallResponse(entries=entries, answer=answer, citations=citations, total_found=total)
