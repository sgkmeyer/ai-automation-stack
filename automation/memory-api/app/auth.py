"""Simple bearer token authentication."""

from fastapi import Header, HTTPException

from .config import settings


async def verify_token(authorization: str | None = Header(default=None)) -> None:
    """Verify bearer token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.removeprefix("Bearer ")
    if token != settings.memory_api_token:
        raise HTTPException(status_code=403, detail="Invalid token")
