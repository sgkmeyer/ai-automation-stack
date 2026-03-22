"""Unified recall router v1."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from ..auth import verify_token
from ..config import settings
from ..recall_service import format_local_time, search_context_entries, search_memory_entries
from ..registry_service import list_registry, query_registry

router = APIRouter()

INTENT_TYPES = {
    "saved_content_lookup",
    "conversation_recall",
    "durable_knowledge_recall",
    "current_context_lookup",
    "task_or_open_loop_recall",
    "broad_synthesis",
}


class UnifiedRecallRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be empty")
        return stripped


def _lower(query: str) -> str:
    return query.strip().lower()


def classify_intent(query: str) -> tuple[str, str]:
    lowered = _lower(query)

    if any(phrase in lowered for phrase in ("open loops", "waiting on", "waiting-on", "blocked", "decisions pending")):
        return "task_or_open_loop_recall", "question asks for operational follow-through state"

    if any(phrase in lowered for phrase in ("what did i save", "saved items", "reading inbox", "saved link", "bookmark", "what did i just save")):
        return "saved_content_lookup", "saved-content wording points to registry-first retrieval"

    if any(token in lowered for token in (" article ", " video ", " post ", " link ", " saved ", " bookmark ", " registry ")):
        return "saved_content_lookup", "content/bookmark wording suggests registry lookup"

    if any(phrase in lowered for phrase in ("what did", "summarize my call", "action items", "follow-up", "what happened in today", "meeting with", "call with")) and (
        "said" in lowered or "meeting" in lowered or "call" in lowered or "transcript" in lowered
    ):
        return "conversation_recall", "question asks about what was said or what happened in a conversation"

    if any(token in lowered for token in ("meeting", "call", "transcript", "said", "discussed", "action items", "follow-up")):
        return "conversation_recall", "meeting/transcript wording suggests transcript-first recall"

    if any(token in lowered for token in ("today", "latest", "just now", "current", "this chat", "this thread")):
        return "current_context_lookup", "recency/current-session wording suggests current-context lookup"

    if any(phrase in lowered for phrase in ("brief me on", "full picture", "what changed this week")):
        return "broad_synthesis", "broad briefing wording suggests a synthesis-oriented lookup"

    if any(phrase in lowered for phrase in ("what do you remember", "what do you know", "remind me what you know", "background", "history", "profile")):
        return "durable_knowledge_recall", "memory-shaped wording suggests durable knowledge recall"

    return "durable_knowledge_recall", "defaulting to durable knowledge recall for a broad memory-shaped question"


def lane_policy(intent_type: str) -> tuple[str, str | None]:
    if intent_type == "saved_content_lookup":
        return "registry", "memory"
    if intent_type == "conversation_recall":
        return "transcripts", "memory"
    if intent_type == "durable_knowledge_recall":
        return "memory", "transcripts"
    if intent_type == "current_context_lookup":
        return "current_context", "memory"
    if intent_type == "task_or_open_loop_recall":
        return "tasks", "memory"
    return "memory", "transcripts"


def derive_lane_query(query: str, intent_type: str) -> tuple[str, str | None]:
    stripped = query.strip()
    lowered = stripped.lower()

    if intent_type == "saved_content_lookup":
        for prefix in (
            "what did i save about ",
            "show my saved items on ",
            "show my saved items about ",
            "what did i just save about ",
        ):
            if lowered.startswith(prefix):
                return stripped[len(prefix) :].strip(), None
        if "reading inbox" in lowered:
            return "", None
        return stripped, None

    if intent_type == "durable_knowledge_recall":
        for prefix in (
            "what do you remember about ",
            "what do you know about ",
            "remind me what you know about ",
        ):
            if lowered.startswith(prefix):
                entity = stripped[len(prefix) :].strip()
                return entity, entity
        return stripped, None

    if intent_type == "conversation_recall":
        match = re.search(r"what did (.+?) say about (.+)", lowered)
        if match:
            entity = stripped[match.start(1) : match.end(1)]
            topic = stripped[match.start(2) : match.end(2)]
            return f"{entity} {topic}".strip(), entity.strip()

        match = re.search(r"(?:summarize|summary of) (?:my )?(?:call|meeting|conversation) with (.+)", lowered)
        if match:
            entity = stripped[match.start(1) : match.end(1)]
            return entity.strip(), entity.strip()
        return stripped, None

    return stripped, None


def compute_confidence(results: list[dict[str, Any]], total_found: int, lane: str, *, inbox_request: bool = False) -> float:
    if lane == "tasks":
        return 0.15
    if not results:
        return 0.10
    if inbox_request and lane == "registry":
        return 0.92

    top_score = float(results[0].get("score", 0.0) or 0.0)
    confidence = 0.55 + min(top_score, 0.40)
    if total_found >= 3:
        confidence += 0.05
    return round(min(confidence, 0.98), 2)


def compute_density(results: list[dict[str, Any]], confidence: float) -> str:
    count = len(results)
    if count == 0:
        return "empty"
    if count == 1 and confidence >= 0.80:
        return "narrow_high_confidence"
    if count == 1:
        return "thin"
    if 2 <= count <= 4:
        return "medium"
    return "rich"


def should_fallback(intent_type: str, primary_confidence: float, primary_density: str, secondary_lane: str | None) -> bool:
    if not secondary_lane or secondary_lane == "tasks":
        return False
    if intent_type == "saved_content_lookup" and primary_confidence >= 0.80 and primary_density != "thin":
        return False
    return primary_confidence < 0.80 or primary_density in {"empty", "thin"}


async def run_lane(lane: str, query: str, entity_name: str | None, limit: int) -> tuple[list[dict[str, Any]], int]:
    if lane == "registry":
        if not query:
            rows, total = await list_registry(
                review_state="inbox",
                source_kind=None,
                topics=[],
                user_tags=[],
                from_ts=None,
                to_ts=None,
                limit=limit,
                page=1,
                sort="oldest",
            )
        else:
            rows, total = await query_registry(
                query=query,
                source_kind=None,
                review_state=None,
                from_ts=None,
                to_ts=None,
                topics=[],
                user_tags=[],
                limit=limit,
                page=1,
            )
        results = [
            {
                "id": str(row["id"]),
                "title": row.get("title") or row.get("canonical_host") or "Registry item",
                "summary": row.get("summary") or row.get("why_it_matters") or "",
                "source_type": "registry_item",
                "source": "registry",
                "source_ref": row.get("canonical_url"),
                "canonical_url": row.get("canonical_url"),
                "occurred_at": row["last_captured_at"].isoformat() if row.get("last_captured_at") else None,
                "occurred_at_local": format_local_time(row["last_captured_at"]) if row.get("last_captured_at") else None,
                "display_timezone": settings.display_timezone,
                "entity_refs": row.get("topics") or [],
                "citation": "registry item",
                "score": float(row.get("rank") or (0.9 if not query else 0.0)),
                "why_it_matters": row.get("why_it_matters"),
                "key_takeaways": row.get("key_takeaways") or [],
                "review_state": row.get("review_state"),
            }
            for row in rows
        ]
        return results, total

    if lane == "transcripts":
        return await search_memory_entries(query=query, entity_name=entity_name, limit=limit, lane="transcripts")

    if lane == "memory":
        return await search_memory_entries(query=query, entity_name=entity_name, limit=limit, lane="memory")

    if lane == "current_context":
        return await search_context_entries(query=query, limit=limit)

    return [], 0


@router.post("/router/recall", dependencies=[Depends(verify_token)])
async def unified_recall(req: UnifiedRecallRequest):
    intent_type, routing_reason = classify_intent(req.query)
    primary_lane, secondary_lane = lane_policy(intent_type)
    lane_query, entity_name = derive_lane_query(req.query, intent_type)

    primary_results, primary_total = await run_lane(primary_lane, lane_query, entity_name, req.limit)
    primary_confidence = compute_confidence(
        primary_results,
        primary_total,
        primary_lane,
        inbox_request=(primary_lane == "registry" and lane_query == ""),
    )
    primary_density = compute_density(primary_results, primary_confidence)
    fallback_recommended = should_fallback(intent_type, primary_confidence, primary_density, secondary_lane)

    lane_attempts: list[dict[str, Any]] = [
        {
            "lane": primary_lane,
            "query": lane_query,
            "confidence": primary_confidence,
            "result_density": primary_density,
            "fallback_recommended": fallback_recommended,
            "results": primary_results,
            "total_found": primary_total,
        }
    ]

    final_results = primary_results
    fallback_used = False
    answer_mode = "direct_answer" if primary_confidence >= 0.80 and primary_density != "thin" else "thin_result_disclosure"

    if fallback_recommended and secondary_lane:
        secondary_results, secondary_total = await run_lane(secondary_lane, lane_query, entity_name, req.limit)
        secondary_confidence = compute_confidence(secondary_results, secondary_total, secondary_lane)
        secondary_density = compute_density(secondary_results, secondary_confidence)
        lane_attempts.append(
            {
                "lane": secondary_lane,
                "query": lane_query,
                "confidence": secondary_confidence,
                "result_density": secondary_density,
                "fallback_recommended": False,
                "results": secondary_results,
                "total_found": secondary_total,
            }
        )
        fallback_used = True
        if secondary_confidence > primary_confidence + 0.05:
            final_results = secondary_results
        elif primary_results and secondary_results:
            final_results = (primary_results[: max(1, req.limit // 2)] + secondary_results[: max(1, req.limit // 2)])[: req.limit]
        elif secondary_results:
            final_results = secondary_results
        answer_mode = "routed_with_fallback" if final_results else "thin_result_disclosure"

    return {
        "query": req.query,
        "intent_type": intent_type,
        "primary_lane": primary_lane,
        "secondary_lane": secondary_lane,
        "routing_reason": routing_reason,
        "fallback_used": fallback_used,
        "answer_mode": answer_mode,
        "results": final_results,
        "lane_attempts": lane_attempts,
    }
