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
async def test_track_swallows_repo_errors():
    repo = AsyncMock()
    repo.insert.side_effect = RuntimeError("db down")
    service = AnalyticsService(repo)

    await service.track("feed_empty", uuid4())
