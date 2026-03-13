"""memory-api -- Personal memory service for the Satoic automation stack."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import close_pool, get_pool
from .routes import context, entities, health, ingest, log, recall, registry


@asynccontextmanager
async def lifespan(_: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(
    title="memory-api",
    description="Personal memory layer for the Satoic stack",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(log.router)
app.include_router(recall.router)
app.include_router(context.router)
app.include_router(entities.router)
app.include_router(ingest.router)
app.include_router(registry.router)
