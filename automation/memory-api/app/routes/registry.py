"""Registry capture, processing, query, and review endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field, HttpUrl, field_validator

from ..auth import verify_token
from ..registry_service import create_registry_capture, list_registry, process_registry_item, query_registry, review_registry_item

router = APIRouter()

REGISTRY_REVIEW_STATES = {"inbox", "reviewed", "archived"}
REGISTRY_SOURCE_KINDS = {"web", "youtube", "x", "tiktok", "unknown"}
REGISTRY_MODES = {"answer", "list", "summary"}
REGISTRY_REVIEW_ACTIONS = {"mark_reviewed", "archive", "mark_inbox"}


class RegistryCaptureRequest(BaseModel):
    url: HttpUrl
    note: str | None = Field(default=None, max_length=2000)
    tags: list[str] = Field(default_factory=list)
    capture_channel: str = Field(default="ios_shortcut", max_length=100)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [piece.strip() for piece in value.split(",") if piece.strip()]
        return value


class RegistryCaptureResponse(BaseModel):
    ok: bool
    item_id: UUID
    processing_status: str
    review_state: str
    message: str


class RegistryProcessRequest(BaseModel):
    item_id: UUID
    reprocess: bool = False


class RegistryQueryRequest(BaseModel):
    query: str | None = Field(default=None, max_length=2000)
    source_kind: str | None = None
    review_state: str | None = None
    from_ts: datetime | None = Field(default=None, alias="from")
    to_ts: datetime | None = Field(default=None, alias="to")
    topics: list[str] = Field(default_factory=list)
    user_tags: list[str] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=50)
    page: int = Field(default=1, ge=1, le=1000)
    mode: str = Field(default="answer")

    @field_validator("source_kind")
    @classmethod
    def validate_source_kind(cls, value: str | None) -> str | None:
        if value is not None and value not in REGISTRY_SOURCE_KINDS:
            raise ValueError(f"source_kind must be one of: {', '.join(sorted(REGISTRY_SOURCE_KINDS))}")
        return value

    @field_validator("review_state")
    @classmethod
    def validate_review_state(cls, value: str | None) -> str | None:
        if value is not None and value not in REGISTRY_REVIEW_STATES:
            raise ValueError(f"review_state must be one of: {', '.join(sorted(REGISTRY_REVIEW_STATES))}")
        return value

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        if value not in REGISTRY_MODES:
            raise ValueError(f"mode must be one of: {', '.join(sorted(REGISTRY_MODES))}")
        return value


class RegistryListRequest(BaseModel):
    review_state: str | None = None
    source_kind: str | None = None
    topics: list[str] = Field(default_factory=list)
    user_tags: list[str] = Field(default_factory=list)
    from_ts: datetime | None = Field(default=None, alias="from")
    to_ts: datetime | None = Field(default=None, alias="to")
    limit: int = Field(default=10, ge=1, le=50)
    page: int = Field(default=1, ge=1, le=1000)
    sort: str = Field(default="newest")

    @field_validator("source_kind")
    @classmethod
    def validate_source_kind(cls, value: str | None) -> str | None:
        if value is not None and value not in REGISTRY_SOURCE_KINDS:
            raise ValueError(f"source_kind must be one of: {', '.join(sorted(REGISTRY_SOURCE_KINDS))}")
        return value

    @field_validator("review_state")
    @classmethod
    def validate_review_state(cls, value: str | None) -> str | None:
        if value is not None and value not in REGISTRY_REVIEW_STATES:
            raise ValueError(f"review_state must be one of: {', '.join(sorted(REGISTRY_REVIEW_STATES))}")
        return value

    @field_validator("sort")
    @classmethod
    def validate_sort(cls, value: str) -> str:
        if value not in {"newest", "oldest"}:
            raise ValueError("sort must be one of: newest, oldest")
        return value


class RegistryReviewRequest(BaseModel):
    item_id: UUID
    action: str

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        if value not in REGISTRY_REVIEW_ACTIONS:
            raise ValueError(f"action must be one of: {', '.join(sorted(REGISTRY_REVIEW_ACTIONS))}")
        return value


def _format_item(row: dict) -> dict:
    captures = row.get("captures") or []
    metadata = row.get("metadata") or {}
    return {
        "item_id": str(row["id"]),
        "title": row.get("title"),
        "source_kind": row.get("source_kind"),
        "review_state": row.get("review_state"),
        "processing_status": row.get("processing_status"),
        "canonical_url": row.get("canonical_url"),
        "summary": row.get("summary"),
        "why_it_matters": row.get("why_it_matters"),
        "key_takeaways": row.get("key_takeaways") or [],
        "topics": row.get("topics") or [],
        "user_tags": metadata.get("user_tags") or [],
        "capture_count": metadata.get("capture_count"),
        "extraction_mode": metadata.get("extraction_mode"),
        "raw_archive_path": row.get("raw_archive_path"),
        "last_captured_at": row["last_captured_at"].isoformat() if row.get("last_captured_at") else None,
        "processed_at": row["processed_at"].isoformat() if row.get("processed_at") else None,
        "captures": captures,
    }


@router.post("/registry/capture", response_model=RegistryCaptureResponse, dependencies=[Depends(verify_token)])
async def registry_capture(req: RegistryCaptureRequest, background_tasks: BackgroundTasks):
    result = await create_registry_capture(
        url=str(req.url),
        note=req.note,
        tags=req.tags,
        capture_channel=req.capture_channel,
    )
    background_tasks.add_task(process_registry_item, result["item_id"])
    return RegistryCaptureResponse(
        ok=True,
        item_id=result["item_id"],
        processing_status=result["processing_status"],
        review_state=result["review_state"],
        message="Saved to TARS Registry",
    )


@router.post("/registry/process", dependencies=[Depends(verify_token)])
async def registry_process(req: RegistryProcessRequest):
    return await process_registry_item(req.item_id, reprocess=req.reprocess)


@router.post("/registry/query", dependencies=[Depends(verify_token)])
async def registry_query(req: RegistryQueryRequest):
    rows, total = await query_registry(
        query=req.query,
        source_kind=req.source_kind,
        review_state=req.review_state,
        from_ts=req.from_ts,
        to_ts=req.to_ts,
        topics=req.topics,
        user_tags=req.user_tags,
        limit=req.limit,
        page=req.page,
    )
    return {
        "mode": req.mode,
        "items": [_format_item(row) for row in rows],
        "total": total,
        "page": req.page,
        "limit": req.limit,
    }


@router.post("/registry/list", dependencies=[Depends(verify_token)])
async def registry_list(req: RegistryListRequest):
    rows, total = await list_registry(
        review_state=req.review_state,
        source_kind=req.source_kind,
        topics=req.topics,
        user_tags=req.user_tags,
        from_ts=req.from_ts,
        to_ts=req.to_ts,
        limit=req.limit,
        page=req.page,
        sort=req.sort,
    )
    return {
        "items": [_format_item(row) for row in rows],
        "total": total,
        "page": req.page,
        "limit": req.limit,
        "sort": req.sort,
    }


@router.post("/registry/review", dependencies=[Depends(verify_token)])
async def registry_review(req: RegistryReviewRequest):
    row = await review_registry_item(req.item_id, req.action)
    return {
        "ok": True,
        "item_id": str(row["id"]),
        "review_state": row["review_state"],
        "title": row["title"],
        "canonical_url": row["canonical_url"],
    }
