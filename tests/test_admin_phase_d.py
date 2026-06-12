from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from app.admin.app import setup_admin_routes
from app.admin.auth import create_session_payload, set_session_cookie
from app.admin.services.ai_queries import AiSummary, GenerationStats
from app.admin.services.feed_queries import BatchStats
from app.admin.services.notifications_queries import NotificationsSummary
from app.admin.services.ratings_queries import RatingsSummary
from app.config import settings


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "admin-test-pass")
    monkeypatch.setattr(settings, "telegram_bot_token", "bot-token")
    monkeypatch.setattr(settings, "bot_mode", "polling")
    pool = MagicMock()
    app = web.Application()
    setup_admin_routes(app, pool)
    app["pool"] = pool
    return app


def _session_cookie() -> dict[str, str]:
    response = web.Response()
    set_session_cookie(response, create_session_payload())
    return {k: m.value for k, m in response.cookies.items()}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,mock_target,summary_factory,needle",
    [
        (
            "/admin/ratings",
            "app.admin.routes.ratings.RatingsQueries.fetch_summary",
            lambda: RatingsSummary([], None, None, None, None, None, [], [], [], "[]"),
            "Ratings Analytics",
        ),
        (
            "/admin/feed",
            "app.admin.routes.feed.FeedQueries.fetch_batch_stats",
            lambda: BatchStats(0, 0, None, None, None, None, 0, 0, 0),
            "Feed Analytics",
        ),
        (
            "/admin/ai",
            "app.admin.routes.ai.AiQueries.fetch_summary",
            lambda: AiSummary(
                [],
                GenerationStats(0, 0, 0, 0, 0, 2),
                [],
                "[]",
            ),
            "AI Analytics",
        ),
        (
            "/admin/notifications",
            "app.admin.routes.notifications.NotificationsQueries.fetch_summary",
            lambda: NotificationsSummary(0, 0, 0, 0, 0, 0, [], []),
            "Notifications",
        ),
    ],
)
async def test_phase_d_pages_render(
    admin_app, monkeypatch, path, mock_target, summary_factory, needle
):
    monkeypatch.setattr(mock_target, AsyncMock(return_value=summary_factory()))
    if path == "/admin/feed":
        monkeypatch.setattr(
            "app.admin.routes.feed.FeedQueries.fetch_tier_breakdown",
            AsyncMock(return_value=[]),
        )
        monkeypatch.setattr(
            "app.admin.routes.feed.FeedQueries.fetch_injection_by_tier",
            AsyncMock(return_value=[]),
        )

    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.get(path, cookies=_session_cookie())
        assert resp.status == 200
        assert needle in await resp.text()
