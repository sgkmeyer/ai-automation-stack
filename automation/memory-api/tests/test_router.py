from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


if "pydantic_settings" not in sys.modules:
    pydantic_settings = types.ModuleType("pydantic_settings")

    class BaseSettings:
        def __init__(self, **kwargs):
            for name, value in self.__class__.__dict__.items():
                if name.startswith("_") or callable(value):
                    continue
                setattr(self, name, kwargs.get(name, value))

    pydantic_settings.BaseSettings = BaseSettings
    pydantic_settings.SettingsConfigDict = dict
    sys.modules["pydantic_settings"] = pydantic_settings

if "asyncpg" not in sys.modules:
    asyncpg = types.ModuleType("asyncpg")

    class Pool:
        pass

    async def create_pool(*_args, **_kwargs):
        return Pool()

    asyncpg.Pool = Pool
    asyncpg.create_pool = create_pool
    sys.modules["asyncpg"] = asyncpg

if "fastapi" not in sys.modules:
    fastapi = types.ModuleType("fastapi")

    class APIRouter:
        def post(self, *_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

    def Depends(*_args, **_kwargs):
        return None

    def Header(*_args, **_kwargs):
        return None

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    fastapi.APIRouter = APIRouter
    fastapi.Depends = Depends
    fastapi.Header = Header
    fastapi.HTTPException = HTTPException
    sys.modules["fastapi"] = fastapi

if "pydantic" not in sys.modules:
    pydantic = types.ModuleType("pydantic")

    class BaseModel:
        pass

    def Field(*_args, **_kwargs):
        return None

    def field_validator(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator

    pydantic.BaseModel = BaseModel
    pydantic.Field = Field
    pydantic.field_validator = field_validator
    sys.modules["pydantic"] = pydantic

if "app.registry_service" not in sys.modules:
    registry_service = types.ModuleType("app.registry_service")

    async def list_registry(**_kwargs):
        return [], 0

    async def query_registry(**_kwargs):
        return [], 0

    registry_service.list_registry = list_registry
    registry_service.query_registry = query_registry
    sys.modules["app.registry_service"] = registry_service

if "app.wiki_service" not in sys.modules:
    wiki_service = types.ModuleType("app.wiki_service")

    def search_wiki_pages(**_kwargs):
        return [], 0

    wiki_service.search_wiki_pages = search_wiki_pages
    sys.modules["app.wiki_service"] = wiki_service

from app.routes import router


class RouterIntentTests(unittest.TestCase):
    def test_latest_transcript_summaries_route_to_conversation_recall(self):
        intent_type, reason = router.classify_intent("latest transcript summaries")

        self.assertEqual(intent_type, "conversation_recall")
        self.assertIn("transcript", reason)

    def test_saved_content_queries_still_route_to_registry_first(self):
        primary_lane, secondary_lane = router.lane_policy("saved_content_lookup", "what did i save about ai")

        self.assertEqual(primary_lane, "registry")
        self.assertEqual(secondary_lane, "memory")
