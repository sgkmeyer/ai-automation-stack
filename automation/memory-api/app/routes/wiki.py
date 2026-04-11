"""Wiki read, proposal, and lint endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from ..actor import ActorFields, actor_metadata
from ..auth import verify_token
from ..wiki_service import (
    PAGE_TYPES,
    PROPOSAL_STATUSES,
    create_wiki_proposal,
    get_wiki_page,
    lint_wiki,
    list_wiki_proposals,
    review_wiki_proposal,
    search_wiki_pages,
    wiki_health,
)

router = APIRouter()


class WikiSearchRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    limit: int = Field(default=5, ge=1, le=50)
    page_types: list[str] = Field(default_factory=list)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be empty")
        return stripped

    @field_validator("page_types")
    @classmethod
    def validate_page_types(cls, value: list[str]) -> list[str]:
        invalid = sorted({item for item in value if item not in PAGE_TYPES})
        if invalid:
            raise ValueError(f"page_types must be drawn from: {', '.join(sorted(PAGE_TYPES))}")
        return value


class WikiPageRequest(BaseModel):
    page_ref: str = Field(..., max_length=1000)


class WikiProposalRequest(ActorFields):
    page_type: str = Field(..., max_length=100)
    title: str = Field(..., max_length=500)
    content: str = Field(..., min_length=1, max_length=50000)
    source_refs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    slug: str | None = Field(default=None, max_length=200)
    page_ref: str | None = Field(default=None, max_length=1000)
    confidence: str | None = Field(default=None, max_length=100)

    @field_validator("page_type")
    @classmethod
    def validate_page_type(cls, value: str) -> str:
        if value not in PAGE_TYPES:
            raise ValueError(f"page_type must be one of: {', '.join(sorted(PAGE_TYPES))}")
        return value


class WikiProposalListRequest(BaseModel):
    status: str | None = None
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in PROPOSAL_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(PROPOSAL_STATUSES))}")
        return value


class WikiProposalReviewRequest(ActorFields):
    proposal_id: UUID
    action: str = Field(..., max_length=20)

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        if value not in {"approve", "reject"}:
            raise ValueError("action must be approve or reject")
        return value


class WikiLintRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)


@router.get("/wiki/health", dependencies=[Depends(verify_token)])
async def wiki_health_route():
    return wiki_health()


@router.post("/wiki/search", dependencies=[Depends(verify_token)])
async def wiki_search(req: WikiSearchRequest):
    results, total = search_wiki_pages(query=req.query, limit=req.limit, page_types=req.page_types or None)
    return {"items": results, "total": total, "limit": req.limit}


@router.post("/wiki/page", dependencies=[Depends(verify_token)])
async def wiki_page(req: WikiPageRequest):
    return get_wiki_page(page_ref=req.page_ref)


@router.post("/wiki/proposals", dependencies=[Depends(verify_token)])
async def wiki_proposals(req: WikiProposalRequest):
    proposal = create_wiki_proposal(
        page_type=req.page_type,
        title=req.title,
        content=req.content,
        source_refs=req.source_refs,
        tags=req.tags,
        slug=req.slug,
        page_ref=req.page_ref,
        confidence=req.confidence,
        actor=actor_metadata(req),
    )
    return proposal


@router.post("/wiki/proposals/list", dependencies=[Depends(verify_token)])
async def wiki_proposals_list(req: WikiProposalListRequest):
    return {"items": list_wiki_proposals(status=req.status, limit=req.limit), "limit": req.limit}


@router.post("/wiki/proposals/review", dependencies=[Depends(verify_token)])
async def wiki_proposals_review(req: WikiProposalReviewRequest):
    return review_wiki_proposal(proposal_id=req.proposal_id, action=req.action, actor=actor_metadata(req))


@router.post("/wiki/lint", dependencies=[Depends(verify_token)])
async def wiki_lint(req: WikiLintRequest):
    return lint_wiki(limit=req.limit)
