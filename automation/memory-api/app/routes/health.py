"""Health check endpoint."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..db import get_conn

router = APIRouter()


@router.get("/health")
async def health():
    """Check API and database connectivity."""
    try:
        async with get_conn() as conn:
            await conn.fetchval("SELECT 1")
            memory_schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'memory')"
            )
            registry_schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'registry')"
            )
        return {
            "status": "healthy",
            "db": "connected",
            "schema": {
                "memory": "ready" if memory_schema_exists else "missing",
                "registry": "ready" if registry_schema_exists else "missing",
            },
        }
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "db": "error", "detail": str(exc)},
        )
