"""Smoke: every admin GET page returns 200 (or expected 404 for missing entity)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from app.admin.pagination import PageResult
from app.admin.services.activity_queries import ActivityFilters
from app.admin.services.ai_queries import AiSummary, GenerationStats
from app.admin.services.feed_queries import BatchStats
from app.admin.services.notifications_queries import NotificationsSummary
from app.admin.services.ratings_queries import RatingsSummary
from app.admin.services.system_queries import EnvFlag, SystemInfo
from tests.conftest import EVENT_ID, USER_ID, auth_cookies

ADMIN_PAGES = [
    "/admin",
    "/admin/dashboard",
    "/admin/funnels",
    "/admin/users",
    "/admin/activity",
    "/admin/events/lifecycle",
    "/admin/events",
    "/admin/ratings",
    "/admin/feed",
    "/admin/ai",
    "/admin/notifications",
    "/admin/export",
    "/admin/system",
]

MISSING_ENTITY_PAGES = [
    f"/admin/users/{USER_ID}",
    f"/admin/events/{EVENT_ID}",
]


@pytest.fixture
def smoke_admin_app_patched(smoke_admin_app, monkeypatch):
    empty_page = PageResult(items=[], page=1, per_page=50, total=0)
    filters = ActivityFilters(
        date_from=__import__("datetime").date(2026, 6, 1),
        date_to=__import__("datetime").date(2026, 6, 10),
    )

    monkeypatch.setattr(
        "app.admin.routes.users.UsersQueries.list_users",
        AsyncMock(return_value=empty_page),
    )
    monkeypatch.setattr(
        "app.admin.routes.users.UsersQueries.get_user",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.admin.routes.events.EventsQueries.list_events",
        AsyncMock(return_value=empty_page),
    )
    monkeypatch.setattr(
        "app.admin.routes.events.EventsQueries.list_categories",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.admin.routes.events.EventsQueries.get_event",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.admin.routes.lifecycle.LifecycleQueries.list_lifecycle",
        AsyncMock(return_value=empty_page),
    )
    monkeypatch.setattr(
        "app.admin.routes.lifecycle.LifecycleQueries.list_categories",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.admin.routes.activity.ActivityQueries.list_activity",
        AsyncMock(return_value=empty_page),
    )
    monkeypatch.setattr(
        "app.admin.routes.activity.ActivityQueries.parse_filters",
        lambda self, q: filters,
    )
    monkeypatch.setattr(
        "app.admin.routes.activity.ActivityQueries.filters_to_dict",
        lambda self, f: {},
    )
    monkeypatch.setattr(
        "app.admin.routes.activity.ActivityQueries.count_hidden_noisy",
        AsyncMock(return_value=0),
    )
    monkeypatch.setattr(
        "app.admin.routes.activity.ActivityQueries.catalog_for_template",
        lambda self: [],
    )
    monkeypatch.setattr(
        "app.admin.routes.ratings.RatingsQueries.fetch_summary",
        AsyncMock(
            return_value=RatingsSummary([], None, None, None, None, None, [], [], [], "[]")
        ),
    )
    monkeypatch.setattr(
        "app.admin.routes.feed.FeedQueries.fetch_batch_stats",
        AsyncMock(return_value=BatchStats(0, 0, None, None, None, None, 0, 0, 0)),
    )
    monkeypatch.setattr(
        "app.admin.routes.feed.FeedQueries.fetch_tier_breakdown",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.admin.routes.feed.FeedQueries.fetch_injection_by_tier",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.admin.routes.ai.AiQueries.fetch_summary",
        AsyncMock(
            return_value=AiSummary(
                [],
                GenerationStats(0, 0, 0, 0, 0, 2),
                [],
                "[]",
            )
        ),
    )
    monkeypatch.setattr(
        "app.admin.routes.notifications.NotificationsQueries.fetch_summary",
        AsyncMock(return_value=NotificationsSummary(0, 0, 0, 0, 0, 0, [], [])),
    )
    monkeypatch.setattr(
        "app.admin.routes.system.SystemQueries.fetch_info",
        AsyncMock(
            return_value=SystemInfo(
                git_commit="test",
                calibration_version=2,
                bot_mode="polling",
                is_webhook=False,
                admin_enabled=True,
                env_flags=[EnvFlag("BOT_MODE", "polling", False)],
                event_log_count=0,
                action_log_count=0,
                migration_count=10,
            )
        ),
    )
    return smoke_admin_app


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ADMIN_PAGES)
async def test_admin_get_pages_smoke(smoke_admin_app_patched, path):
    async with TestClient(TestServer(smoke_admin_app_patched)) as client:
        resp = await client.get(path, cookies=auth_cookies())
        assert resp.status == 200, f"{path} returned {resp.status}"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", MISSING_ENTITY_PAGES)
async def test_admin_missing_entity_returns_404(smoke_admin_app_patched, path):
    async with TestClient(TestServer(smoke_admin_app_patched)) as client:
        resp = await client.get(path, cookies=auth_cookies())
        assert resp.status == 404
