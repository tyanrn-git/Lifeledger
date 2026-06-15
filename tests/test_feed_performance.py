from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import asyncio

import pytest

from app.schemas.feed import FeedEventCandidate
from app.services.ai_generation_service import AIGenerationService
from app.services.feed_service import FeedService

USER_ID = uuid4()
NOW = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)


def _candidate() -> FeedEventCandidate:
    return FeedEventCandidate(
        id=uuid4(),
        feed_tier=0,
        created_at=NOW,
    )


@pytest.mark.asyncio
async def test_fetch_or_generate_blocks_only_when_pool_empty():
    events_repo = MagicMock()
    events_repo.fetch_available_candidates = AsyncMock(
        side_effect=[
            [],
            [_candidate()],
        ]
    )
    ai_generation = MagicMock()
    ai_generation.ensure_pool_for_user = AsyncMock(return_value=1)
    ai_generation.schedule_pool_refill = MagicMock()

    feed_service = FeedService(
        events_repo,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        ai_generation,
    )

    result = await feed_service._fetch_or_generate(USER_ID)

    assert len(result) == 1
    ai_generation.ensure_pool_for_user.assert_awaited_once_with(USER_ID)
    ai_generation.schedule_pool_refill.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_or_generate_schedules_background_refill_when_partial():
    events_repo = MagicMock()
    events_repo.fetch_available_candidates = AsyncMock(return_value=[_candidate()])
    ai_generation = MagicMock()
    ai_generation.ensure_pool_for_user = AsyncMock()
    ai_generation.schedule_pool_refill = MagicMock()

    feed_service = FeedService(
        events_repo,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        ai_generation,
    )

    result = await feed_service._fetch_or_generate(USER_ID)

    assert len(result) == 1
    ai_generation.ensure_pool_for_user.assert_not_awaited()
    ai_generation.schedule_pool_refill.assert_called_once_with(USER_ID)


def test_schedule_pool_refill_deduplicates_inflight_tasks(monkeypatch):
    ai_generation = AIGenerationService(
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    ai_generation.ensure_pool_for_user = AsyncMock()

    def fake_create_task(coro):
        coro.close()
        return MagicMock(done=lambda: False)

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    ai_generation.schedule_pool_refill(USER_ID)
    ai_generation.schedule_pool_refill(USER_ID)

    assert len(ai_generation._refill_tasks) == 1
