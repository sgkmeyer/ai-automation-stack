"""Week 2 ingestion endpoints for file-backed sources."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from ..auth import verify_token
from ..config import settings
from ..db import get_conn
from ..ingestion import (
    checksum_for,
    classify_text,
    complete_ingestion_job,
    compose_entry_body,
    create_ingestion_job,
    ensure_utc,
    link_entities,
    merge_entities,
    participant_entities,
    upsert_entry_by_source_ref,
)
from ..memory_types import ENTRY_TYPES

router = APIRouter()

DOCUMENT_SOURCES = {"obsidian", "manual", "n8n", "system"}


def _compose_transcript_body(title: str | None, content: str, participants: list[str]) -> str:
    participant_line = ", ".join(participant.strip() for participant in participants if participant and participant.strip())
    if not participant_line:
        return compose_entry_body(title, content)

    contextual_content = f"Participants: {participant_line}\n\n{content.strip()}"
    return compose_entry_body(title, contextual_content)


class IngestDocumentRequest(BaseModel):
    source: str = Field(default="obsidian", description="Document source channel")
    source_ref: str = Field(..., min_length=1, max_length=1000, description="Stable file/key identity")
    source_type: str = Field(default="md", min_length=1, max_length=50)
    title: str | None = Field(default=None, max_length=500)
    content: str = Field(..., min_length=1, max_length=settings.max_body_length)
    occurred_at: datetime | None = Field(default=None)
    entry_type: str | None = Field(default=None, description="Optional explicit entry type")
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if value not in DOCUMENT_SOURCES:
            allowed = ", ".join(sorted(DOCUMENT_SOURCES))
            raise ValueError(f"source must be one of: {allowed}")
        return value

    @field_validator("entry_type")
    @classmethod
    def validate_entry_type(cls, value: str | None) -> str | None:
        if value is not None and value not in ENTRY_TYPES:
            raise ValueError(f"entry_type must be one of: {', '.join(sorted(ENTRY_TYPES))}")
        return value

    @field_validator("source_ref", "content")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped


class IngestDocumentResponse(BaseModel):
    ingestion_job_id: UUID
    entry_id: UUID
    operation: str
    entry_type: str
    entities_linked: list[dict]
    checksum: str


class IngestTranscriptRequest(BaseModel):
    source_ref: str = Field(..., min_length=1, max_length=1000, description="Transcript file or meeting identity")
    title: str | None = Field(default=None, max_length=500)
    transcript_text: str = Field(..., min_length=1, max_length=settings.max_body_length)
    summary: str | None = Field(default=None, max_length=settings.max_body_length)
    occurred_at: datetime | None = Field(default=None)
    participants: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list, description="Explicit action items from upstream parsing")
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    source: str = Field(default="transcript")

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if value != "transcript":
            raise ValueError("source must be transcript")
        return value

    @field_validator("source_ref", "transcript_text")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped


class IngestTranscriptResponse(BaseModel):
    ingestion_job_id: UUID
    summary_entry_id: UUID
    summary_operation: str
    summary_checksum: str
    summary_entities_linked: list[dict]
    action_item_entry_ids: list[UUID]
    action_items_processed: int


@router.post("/ingest/document", response_model=IngestDocumentResponse, dependencies=[Depends(verify_token)])
async def ingest_document(req: IngestDocumentRequest):
    """Idempotently ingest a document-like source, keyed by source/source_ref."""
    occurred = ensure_utc(req.occurred_at)
    body = compose_entry_body(req.title, req.content)
    checksum = checksum_for(req.source, req.source_ref, req.source_type, req.title or "", req.content)
    default_entry_type = req.entry_type or ("journal" if req.source == "obsidian" else "observation")
    extraction = await classify_text(body, default_entry_type)

    structured = dict(req.metadata)
    if req.tags:
        structured["tags"] = req.tags
    structured.update(
        {
            "ingest_kind": "document",
            "source_type": req.source_type,
            "title": req.title,
            "checksum": checksum,
        }
    )

    async with get_conn() as conn:
        async with conn.transaction():
            job_id = await create_ingestion_job(conn, f"{req.source}_document", req.source_ref)
            try:
                entry_id, operation = await upsert_entry_by_source_ref(
                    conn,
                    source=req.source,
                    source_ref=req.source_ref,
                    entry_type=extraction["entry_type"],
                    body=body,
                    occurred_at=occurred,
                    structured=structured,
                )
                linked = await link_entities(conn, entry_id, extraction["entities"])
                await complete_ingestion_job(
                    conn,
                    job_id,
                    entries_created=0 if operation == "unchanged" else 1,
                    entities_linked=len(linked),
                )
            except Exception as exc:
                await complete_ingestion_job(conn, job_id, entries_created=0, entities_linked=0, error_message=str(exc))
                raise

    return IngestDocumentResponse(
        ingestion_job_id=job_id,
        entry_id=entry_id,
        operation=operation,
        entry_type=extraction["entry_type"],
        entities_linked=linked,
        checksum=checksum,
    )


@router.post("/ingest/transcript", response_model=IngestTranscriptResponse, dependencies=[Depends(verify_token)])
async def ingest_transcript(req: IngestTranscriptRequest):
    """Ingest a transcript summary plus optional explicit action-item entries."""
    occurred = ensure_utc(req.occurred_at)
    summary_text = (req.summary or "").strip() or req.transcript_text.strip()
    summary_body = _compose_transcript_body(req.title, summary_text, req.participants)
    summary_checksum = checksum_for(
        req.source_ref,
        req.title or "",
        req.transcript_text,
        req.summary or "",
        tuple(req.participants),
        tuple(req.action_items),
    )
    summary_extraction = await classify_text(summary_body, "transcript_summary")
    summary_extraction["entry_type"] = "transcript_summary"
    participant_entity_candidates = participant_entities(req.participants)
    summary_entities = merge_entities(summary_extraction["entities"], participant_entity_candidates)

    summary_structured = dict(req.metadata)
    if req.tags:
        summary_structured["tags"] = req.tags
    summary_structured.update(
        {
            "ingest_kind": "transcript",
            "title": req.title,
            "participants": req.participants,
            "checksum": summary_checksum,
            "transcript_length": len(req.transcript_text),
            "action_items_count": len(req.action_items),
        }
    )

    async with get_conn() as conn:
        async with conn.transaction():
            job_id = await create_ingestion_job(conn, "transcript", req.source_ref)
            try:
                summary_entry_id, summary_operation = await upsert_entry_by_source_ref(
                    conn,
                    source=req.source,
                    source_ref=req.source_ref,
                    entry_type="transcript_summary",
                    body=summary_body,
                    occurred_at=occurred,
                    structured=summary_structured,
                )
                summary_linked = await link_entities(conn, summary_entry_id, summary_entities)

                action_item_entry_ids: list[UUID] = []
                action_item_changes = 0
                total_entities = len(summary_linked)
                for index, item in enumerate(req.action_items, start=1):
                    item_text = item.strip()
                    if not item_text:
                        continue
                    action_checksum = checksum_for(req.source_ref, "action_item", index, item_text, tuple(req.participants))
                    action_structured = {
                        "ingest_kind": "transcript_action_item",
                        "parent_source_ref": req.source_ref,
                        "parent_entry_id": str(summary_entry_id),
                        "checksum": action_checksum,
                    }
                    if req.tags:
                        action_structured["tags"] = req.tags
                    action_extraction = await classify_text(item_text, "action_item")
                    action_extraction["entry_type"] = "action_item"
                    action_entities = merge_entities(action_extraction["entities"], participant_entity_candidates)
                    action_entry_id, action_operation = await upsert_entry_by_source_ref(
                        conn,
                        source=req.source,
                        source_ref=f"{req.source_ref}#action_item:{index}",
                        entry_type="action_item",
                        body=item_text,
                        occurred_at=occurred,
                        structured=action_structured,
                    )
                    action_item_entry_ids.append(action_entry_id)
                    linked = await link_entities(conn, action_entry_id, action_entities)
                    total_entities += len(linked)
                    if action_operation != "unchanged":
                        action_item_changes += 1

                await complete_ingestion_job(
                    conn,
                    job_id,
                    entries_created=(0 if summary_operation == "unchanged" else 1) + action_item_changes,
                    entities_linked=total_entities,
                )
            except Exception as exc:
                await complete_ingestion_job(conn, job_id, entries_created=0, entities_linked=0, error_message=str(exc))
                raise

    return IngestTranscriptResponse(
        ingestion_job_id=job_id,
        summary_entry_id=summary_entry_id,
        summary_operation=summary_operation,
        summary_checksum=summary_checksum,
        summary_entities_linked=summary_linked,
        action_item_entry_ids=action_item_entry_ids,
        action_items_processed=len(action_item_entry_ids),
    )
