"""Mutation journal operator endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import verify_token
from ..mutation_journal import list_mutations, rollback_mutation

router = APIRouter()


class MutationQueryRequest(BaseModel):
    subsystem: str | None = None
    target_id: UUID | None = None
    limit: int = Field(default=20, ge=1, le=100)


class MutationRollbackRequest(BaseModel):
    mutation_id: UUID
    actor_type: str = Field(default="operator", max_length=100)
    actor_id: str | None = Field(default="memory-api", max_length=200)
    reason: str | None = Field(default=None, max_length=2000)


@router.post("/mutations/query", dependencies=[Depends(verify_token)])
async def mutations_query(req: MutationQueryRequest):
    rows = await list_mutations(subsystem=req.subsystem, target_id=req.target_id, limit=req.limit)
    return {
        "mutations": [
            {
                "mutation_id": str(row["id"]),
                "occurred_at": row["occurred_at"].isoformat(),
                "actor_type": row["actor_type"],
                "actor_id": row["actor_id"],
                "subsystem": row["subsystem"],
                "mutation_type": row["mutation_type"],
                "target_id": str(row["target_id"]),
                "reason": row["reason"],
                "before_state": row["before_state"] or {},
                "after_state": row["after_state"] or {},
                "rollback_mode": row["rollback_mode"],
                "rollback_status": row["rollback_status"],
                "rolled_back_by_mutation_id": str(row["rolled_back_by_mutation_id"]) if row["rolled_back_by_mutation_id"] else None,
                "metadata": row["metadata"] or {},
            }
            for row in rows
        ]
    }


@router.post("/mutations/rollback", dependencies=[Depends(verify_token)])
async def mutations_rollback(req: MutationRollbackRequest):
    result = await rollback_mutation(
        req.mutation_id,
        actor_type=req.actor_type,
        actor_id=req.actor_id,
        reason=req.reason,
    )
    return {"ok": True, **result}

