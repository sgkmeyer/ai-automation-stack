from __future__ import annotations

import sys
import types
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

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

from app import recall_service


def _entry_row(
    *,
    entry_id: str,
    body: str,
    source_ref: str,
    occurred_at: datetime,
    entry_type: str = "transcript_summary",
    source: str = "transcript",
    rank: float = 0.0,
) -> dict:
    return {
        "id": entry_id,
        "entry_type": entry_type,
        "body": body,
        "source": source,
        "source_ref": source_ref,
        "occurred_at": occurred_at,
        "rank": rank,
        "entities": [],
    }


class _FakeConnection:
    def __init__(self, rows: list[dict], total: int | None = None):
        self.rows = rows
        self.total = len(rows) if total is None else total

    async def fetch(self, *_args, **_kwargs):
        return self.rows

    async def fetchval(self, *_args, **_kwargs):
        return self.total


class _FakeConnContext:
    def __init__(self, conn: _FakeConnection):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class RecallQueryPlanTests(unittest.TestCase):
    def test_latest_transcript_summaries_use_recency_mode(self):
        plan = recall_service.build_recall_query_plan(
            query="latest transcript summaries",
            lane="all",
            now=datetime(2026, 4, 20, 16, 0, tzinfo=ZoneInfo("America/Toronto")),
        )

        self.assertTrue(plan.use_transcript_recency)
        self.assertEqual(plan.effective_query, "")
        self.assertTrue(plan.is_low_signal)
        self.assertTrue(plan.dedupe_transcript_families)
        self.assertIsNone(plan.after)
        self.assertIsNone(plan.before)

    def test_today_transcript_summaries_use_toronto_day_bounds(self):
        plan = recall_service.build_recall_query_plan(
            query="today transcript summaries",
            lane="all",
            now=datetime(2026, 4, 20, 16, 30, tzinfo=ZoneInfo("America/Toronto")),
        )

        self.assertEqual(plan.after, datetime(2026, 4, 20, 4, 0, tzinfo=UTC))
        self.assertEqual(plan.before, datetime(2026, 4, 21, 4, 0, tzinfo=UTC))

    def test_action_item_queries_do_not_dedupe_summary_families(self):
        plan = recall_service.build_recall_query_plan(
            query="latest transcript action items",
            lane="transcripts",
            now=datetime(2026, 4, 20, 16, 0, tzinfo=ZoneInfo("America/Toronto")),
        )

        self.assertTrue(plan.use_transcript_recency)
        self.assertTrue(plan.wants_action_items)
        self.assertFalse(plan.dedupe_transcript_families)


class SearchMemoryEntriesTests(unittest.IsolatedAsyncioTestCase):
    async def test_latest_transcript_summaries_dedupe_to_recent_family_rows(self):
        rows = [
            _entry_row(
                entry_id="old-key-points",
                body="Older March key points",
                source_ref="krisp:old-meeting#key_points",
                occurred_at=datetime(2026, 3, 16, 14, 54, 21, tzinfo=UTC),
                rank=0.75,
            ),
            _entry_row(
                entry_id="recent-base",
                body="Recent base transcript",
                source_ref="krisp:new-meeting",
                occurred_at=datetime(2026, 4, 20, 19, 55, 39, tzinfo=UTC),
                rank=0.15,
            ),
            _entry_row(
                entry_id="recent-key-points",
                body="Recent key points",
                source_ref="krisp:new-meeting#key_points",
                occurred_at=datetime(2026, 4, 20, 19, 56, 12, tzinfo=UTC),
                rank=0.75,
            ),
            _entry_row(
                entry_id="recent-action-summary",
                body="Recent action item summary",
                source_ref="krisp:new-meeting#action_items",
                occurred_at=datetime(2026, 4, 20, 19, 56, 13, tzinfo=UTC),
                rank=0.85,
            ),
            _entry_row(
                entry_id="recent-explicit-action",
                body="Ship the plan",
                source_ref="krisp:new-meeting#action_item:1",
                occurred_at=datetime(2026, 4, 20, 19, 56, 13, tzinfo=UTC),
                entry_type="action_item",
                rank=0.95,
            ),
        ]

        with patch.object(recall_service, "get_conn", return_value=_FakeConnContext(_FakeConnection(rows))):
            results, total = await recall_service.search_memory_entries(
                query="latest transcript summaries",
                limit=5,
                lane="all",
            )

        self.assertEqual(total, 2)
        self.assertEqual(results[0]["source_ref"], "krisp:new-meeting#key_points")
        self.assertEqual(results[1]["source_ref"], "krisp:old-meeting#key_points")
        self.assertNotIn("krisp:new-meeting#action_item:1", [result["source_ref"] for result in results])

    async def test_latest_transcript_action_items_keep_action_item_rows(self):
        rows = [
            _entry_row(
                entry_id="recent-action-summary",
                body="Recent action item summary",
                source_ref="krisp:new-meeting#action_items",
                occurred_at=datetime(2026, 4, 20, 19, 56, 13, tzinfo=UTC),
                rank=0.85,
            ),
            _entry_row(
                entry_id="recent-explicit-action",
                body="Ship the plan",
                source_ref="krisp:new-meeting#action_item:1",
                occurred_at=datetime(2026, 4, 20, 19, 56, 13, tzinfo=UTC),
                entry_type="action_item",
                rank=0.95,
            ),
        ]

        with patch.object(recall_service, "get_conn", return_value=_FakeConnContext(_FakeConnection(rows))):
            results, total = await recall_service.search_memory_entries(
                query="latest transcript action items",
                limit=5,
                lane="transcripts",
            )

        self.assertEqual(total, 2)
        self.assertEqual(results[0]["source_type"], "transcript_summary")
        self.assertEqual(results[1]["source_type"], "action_item")
