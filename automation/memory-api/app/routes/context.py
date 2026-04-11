"""Context register endpoints."""

from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import Field

from ..actor import ActorFields, actor_metadata
from ..auth import verify_token
from ..db import get_conn
from ..mutation_journal import record_mutation

router = APIRouter()


class ContextUpdateRequest(ActorFields):
    key: str = Field(..., max_length=200)
    value: str = Field(..., max_length=10000)


class ContextDeleteRequest(ActorFields):
    pass


@router.get("/context", dependencies=[Depends(verify_token)])
async def get_all_context():
    """Return the full context register, grouped by domain."""
    async with get_conn() as conn:
        rows = await conn.fetch(
            "SELECT domain, key, value, updated_at FROM memory.context_register ORDER BY domain, key"
        )

    result: dict[str, list[dict]] = {}
    for row in rows:
        domain = row["domain"]
        result.setdefault(domain, []).append(
            {
                "key": row["key"],
                "value": row["value"],
                "updated_at": row["updated_at"].isoformat(),
            }
        )

    return {"context": result}


@router.put("/context/{domain}", dependencies=[Depends(verify_token)])
async def update_context(domain: str, req: ContextUpdateRequest):
    """Upsert a context register entry for a given domain."""
    async with get_conn() as conn:
        async with conn.transaction():
            previous = await conn.fetchrow(
                """
                SELECT value
                FROM memory.context_register
                WHERE domain = $1 AND normalized_key = LOWER($2)
                """,
                domain,
                req.key,
            )
            await conn.execute(
                """
                INSERT INTO memory.context_register (domain, key, normalized_key, value)
                VALUES ($1, $2, LOWER($2), $3)
                ON CONFLICT (domain, normalized_key)
                DO UPDATE SET value = $3, updated_at = NOW()
                """,
                domain,
                req.key,
                req.value,
            )
            mutation = await record_mutation(
                conn,
                actor_type=req.actor_type,
                actor_id=req.actor_id,
                subsystem="context",
                mutation_type="context_upsert",
                target_id=uuid5(NAMESPACE_URL, f"context:{domain}:{req.key.lower()}"),
                reason=req.reason,
                before_state={"domain": domain, "key": req.key, "value": previous["value"] if previous else None},
                after_state={"domain": domain, "key": req.key, "value": req.value},
                rollback_mode="inverse_mutation",
                rollback_status="available",
                metadata=actor_metadata(req),
            )

    return {"status": "updated", "domain": domain, "key": req.key, "mutation_id": str(mutation["id"])}


@router.delete("/context/{domain}/{key}", dependencies=[Depends(verify_token)])
async def delete_context(
    domain: str,
    key: str,
    req: ContextDeleteRequest | None = Body(default=None),
):
    """Remove a context register entry."""
    actor_type = req.actor_type if req else "agent"
    actor_id = req.actor_id if req else None
    session_id = req.session_id if req else None
    source_client = req.source_client if req else None
    reason = req.reason if req else None

    async with get_conn() as conn:
        async with conn.transaction():
            previous = await conn.fetchrow(
                """
                SELECT value
                FROM memory.context_register
                WHERE domain = $1 AND normalized_key = LOWER($2)
                FOR UPDATE
                """,
                domain,
                key,
            )
            result = await conn.execute(
                "DELETE FROM memory.context_register WHERE domain = $1 AND normalized_key = LOWER($2)",
                domain,
                key,
            )
            count = int(result.split(" ")[-1])
            if count == 0:
                raise HTTPException(status_code=404, detail=f"No context entry found for {domain}/{key}")

            mutation = await record_mutation(
                conn,
                actor_type=actor_type,
                actor_id=actor_id,
                subsystem="context",
                mutation_type="context_delete",
                target_id=uuid5(NAMESPACE_URL, f"context:{domain}:{key.lower()}"),
                reason=reason,
                before_state={"domain": domain, "key": key, "value": previous["value"] if previous else None},
                after_state={"domain": domain, "key": key, "value": None},
                rollback_mode="inverse_mutation",
                rollback_status="available",
                metadata={
                    key_name: value
                    for key_name, value in {
                        "actor_type": actor_type,
                        "actor_id": actor_id,
                        "session_id": session_id,
                        "source_client": source_client,
                        "reason": reason,
                    }.items()
                    if value not in {None, ""}
                },
            )

    return {"status": "deleted", "domain": domain, "key": key, "mutation_id": str(mutation["id"])}
