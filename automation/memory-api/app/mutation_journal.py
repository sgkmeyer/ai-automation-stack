"""Mutation journal helpers for reversible user-facing actions."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from .db import get_conn


def _as_json(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {})


def _decode_json(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    if isinstance(value, dict):
        return value
    return {}


async def record_mutation(
    conn,
    *,
    actor_type: str,
    actor_id: str | None,
    subsystem: str,
    mutation_type: str,
    target_id: UUID,
    reason: str | None,
    before_state: dict[str, Any] | None,
    after_state: dict[str, Any] | None,
    rollback_mode: str,
    rollback_status: str = "available",
    metadata: dict[str, Any] | None = None,
    rolled_back_by_mutation_id: UUID | None = None,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO ops.mutation_journal (
            actor_type, actor_id, subsystem, mutation_type, target_id, reason,
            before_state, after_state, rollback_mode, rollback_status, metadata,
            rolled_back_by_mutation_id
        )
        VALUES (
            $1, $2, $3, $4, $5, $6,
            $7::jsonb, $8::jsonb, $9, $10, $11::jsonb, $12
        )
        RETURNING *
        """,
        actor_type,
        actor_id,
        subsystem,
        mutation_type,
        target_id,
        reason,
        _as_json(before_state),
        _as_json(after_state),
        rollback_mode,
        rollback_status,
        _as_json(metadata),
        rolled_back_by_mutation_id,
    )
    return dict(row)


async def list_mutations(
    *,
    subsystem: str | None = None,
    target_id: UUID | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    idx = 0

    if subsystem:
        idx += 1
        conditions.append(f"subsystem = ${idx}")
        params.append(subsystem)

    if target_id:
        idx += 1
        conditions.append(f"target_id = ${idx}")
        params.append(target_id)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    idx += 1
    params.append(limit)

    async with get_conn() as conn:
        rows = await conn.fetch(
            f"""
            SELECT *
            FROM ops.mutation_journal
            WHERE {where_clause}
            ORDER BY occurred_at DESC
            LIMIT ${idx}
            """,
            *params,
        )
    return [dict(row) for row in rows]


async def rollback_mutation(
    mutation_id: UUID,
    *,
    actor_type: str = "operator",
    actor_id: str | None = "memory-api",
    reason: str | None = None,
) -> dict[str, Any]:
    async with get_conn() as conn, conn.transaction():
        mutation = await conn.fetchrow(
            "SELECT * FROM ops.mutation_journal WHERE id = $1 FOR UPDATE",
            mutation_id,
        )
        if not mutation:
            raise ValueError(f"mutation {mutation_id} not found")
        if mutation["rollback_status"] != "available":
            raise ValueError(f"mutation {mutation_id} is not rollbackable")

        mutation_row = dict(mutation)
        if mutation_row["subsystem"] == "registry" and mutation_row["mutation_type"] == "review_state_change":
            current = await conn.fetchrow(
                """
                SELECT id, review_state, title, canonical_url
                FROM registry.items
                WHERE id = $1
                FOR UPDATE
                """,
                mutation_row["target_id"],
            )
            if not current:
                raise ValueError(f"registry item {mutation_row['target_id']} not found")

            before_state = _decode_json(mutation_row.get("before_state"))
            previous_review_state = before_state.get("review_state")
            if not previous_review_state:
                raise ValueError(f"mutation {mutation_id} has no prior review_state")

            await conn.execute(
                """
                UPDATE registry.items
                SET review_state = $2
                WHERE id = $1
                """,
                mutation_row["target_id"],
                previous_review_state,
            )

            rollback_entry = await record_mutation(
                conn,
                actor_type=actor_type,
                actor_id=actor_id,
                subsystem="registry",
                mutation_type="review_state_rollback",
                target_id=mutation_row["target_id"],
                reason=reason or f"rollback of mutation {mutation_id}",
                before_state={"review_state": current["review_state"]},
                after_state={"review_state": previous_review_state},
                rollback_mode="inverse_mutation",
                rollback_status="not_available",
                metadata={"rollback_of_mutation_id": str(mutation_id)},
            )

            await conn.execute(
                """
                UPDATE ops.mutation_journal
                SET rollback_status = 'rolled_back',
                    rolled_back_by_mutation_id = $2
                WHERE id = $1
                """,
                mutation_id,
                rollback_entry["id"],
            )

            return {
                "mutation_id": str(mutation_id),
                "rolled_back_by_mutation_id": str(rollback_entry["id"]),
                "subsystem": "registry",
                "target_id": str(mutation_row["target_id"]),
                "review_state": previous_review_state,
                "title": current["title"],
                "canonical_url": current["canonical_url"],
            }

        raise ValueError(
            f"rollback for {mutation_row['subsystem']}/{mutation_row['mutation_type']} is not implemented"
        )
