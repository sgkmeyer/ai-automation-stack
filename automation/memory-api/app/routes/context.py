"""Context register endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import verify_token
from ..db import get_conn

router = APIRouter()


class ContextUpdateRequest(BaseModel):
    key: str = Field(..., max_length=200)
    value: str = Field(..., max_length=10000)


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

    return {"status": "updated", "domain": domain, "key": req.key}


@router.delete("/context/{domain}/{key}", dependencies=[Depends(verify_token)])
async def delete_context(domain: str, key: str):
    """Remove a context register entry."""
    async with get_conn() as conn:
        result = await conn.execute(
            "DELETE FROM memory.context_register WHERE domain = $1 AND normalized_key = LOWER($2)",
            domain,
            key,
        )

    count = int(result.split(" ")[-1])
    if count == 0:
        raise HTTPException(status_code=404, detail=f"No context entry found for {domain}/{key}")

    return {"status": "deleted", "domain": domain, "key": key}
