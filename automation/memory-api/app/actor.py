"""Shared actor metadata for agent-neutral write contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ActorFields(BaseModel):
    actor_type: str = Field(default="agent", max_length=100)
    actor_id: str | None = Field(default=None, max_length=200)
    session_id: str | None = Field(default=None, max_length=200)
    source_client: str | None = Field(default=None, max_length=100)
    reason: str | None = Field(default=None, max_length=2000)


def actor_metadata(actor: ActorFields | Any) -> dict[str, Any]:
    payload = {
        "actor_type": getattr(actor, "actor_type", None),
        "actor_id": getattr(actor, "actor_id", None),
        "session_id": getattr(actor, "session_id", None),
        "source_client": getattr(actor, "source_client", None),
        "reason": getattr(actor, "reason", None),
    }
    return {key: value for key, value in payload.items() if value not in {None, ""}}


def with_actor_metadata(structured: dict[str, Any], actor: ActorFields | Any) -> dict[str, Any]:
    metadata = actor_metadata(actor)
    if not metadata:
        return structured

    enriched = dict(structured)
    enriched["actor"] = metadata
    return enriched
