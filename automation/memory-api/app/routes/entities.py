"""Browse and search entities."""

from fastapi import APIRouter, Depends, Query

from ..auth import verify_token
from ..db import get_conn

router = APIRouter()


@router.get("/entities", dependencies=[Depends(verify_token)])
async def list_entities(
    entity_type: str | None = Query(default=None, description="Filter by type: person, company, project, topic"),
    q: str | None = Query(default=None, description="Search by name (case-insensitive prefix match)"),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List entities with optional type filter and name search."""
    conditions: list[str] = []
    params: list[object] = []
    param_idx = 0

    if entity_type:
        param_idx += 1
        conditions.append(f"e.entity_type = ${param_idx}")
        params.append(entity_type)

    if q:
        param_idx += 1
        conditions.append(f"e.normalized_name LIKE ${param_idx}")
        params.append(f"{q.lower()}%")

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    param_idx += 1
    params.append(limit)

    async with get_conn() as conn:
        rows = await conn.fetch(
            f"""
            SELECT e.id, e.entity_type, e.name, e.aliases, e.notes, e.created_at, e.updated_at,
                   COUNT(ee.entry_id) AS entry_count
            FROM memory.entities e
            LEFT JOIN memory.entry_entities ee ON ee.entity_id = e.id
            WHERE {where_clause}
            GROUP BY e.id
            ORDER BY COUNT(ee.entry_id) DESC, e.name
            LIMIT ${param_idx}
            """,
            *params,
        )

    return {
        "entities": [
            {
                "id": str(row["id"]),
                "entity_type": row["entity_type"],
                "name": row["name"],
                "aliases": row["aliases"],
                "notes": row["notes"],
                "entry_count": row["entry_count"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in rows
        ],
        "total": len(rows),
    }
