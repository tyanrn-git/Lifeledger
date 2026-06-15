from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.analytics_service import AnalyticsService


@pytest.mark.asyncio
async def test_track_inserts_via_repo():
    repo = AsyncMock()
    service = AnalyticsService(repo)
    user_id = uuid4()

    await service.track("user_seen", user_id, source="test")

    repo.insert.assert_awaited_once_with("user_seen", user_id, {"source": "test"})


@pytest.mark.asyncio
async def test_track_many_inserts_batch():
    repo = AsyncMock()
    service = AnalyticsService(repo)
    user_id = uuid4()

    await service.track_many(
        [
            ("event_shown", user_id, {"event_id": "1"}),
            ("event_shown", user_id, {"event_id": "2"}),
        ]
    )

    repo.insert_many.assert_awaited_once()


@pytest.mark.asyncio
async def test_track_swallows_repo_errors():
    repo = AsyncMock()
    repo.insert.side_effect = RuntimeError("db down")
    service = AnalyticsService(repo)

    await service.track("feed_empty", uuid4())
