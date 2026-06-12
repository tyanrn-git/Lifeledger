from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from app.admin.app import setup_admin_routes
from app.admin.auth import create_session_payload, set_session_cookie
from app.admin.pagination import PageResult
from app.admin.services.activity_queries import ActivityFilters, ActivityRow
from app.config import settings

USER_ID = UUID("11111111-1111-4111-8111-111111111111")
LOG_ID = UUID("33333333-3333-4333-8333-333333333333")
NOW = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)


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


def _auth() -> dict[str, str]:
    payload = create_session_payload()
    response = web.Response()
    set_session_cookie(response, payload)
    return {k: m.value for k, m in response.cookies.items()}


@pytest.mark.asyncio
async def test_activity_page_renders(admin_app, monkeypatch):
    row = ActivityRow(
        id=LOG_ID,
        created_at=NOW,
        event_name="event_rated",
        event_label="Оценка события",
        user_id=USER_ID,
        user_display="@roman",
        properties='{"event_id": "22222222-2222-4222-8222-222222222222", "score": 5}',
        linked_event_id=UUID("22222222-2222-4222-8222-222222222222"),
    )
    page = PageResult(items=[row], page=1, per_page=50, total=1)
    filters = ActivityFilters(
        date_from=date(2026, 6, 1),
        date_to=date(2026, 6, 10),
    )

    monkeypatch.setattr(
        "app.admin.routes.activity.ActivityQueries.list_activity",
        AsyncMock(return_value=page),
    )
    monkeypatch.setattr(
        "app.admin.routes.activity.ActivityQueries.count_hidden_noisy",
        AsyncMock(return_value=3),
    )
    monkeypatch.setattr(
        "app.admin.routes.activity.ActivityQueries.parse_filters",
        lambda self, q: filters,
    )
    monkeypatch.setattr(
        "app.admin.routes.activity.ActivityQueries.filters_to_dict",
        lambda self, f: {"date_from": "2026-06-01", "date_to": "2026-06-10"},
    )
    monkeypatch.setattr(
        "app.admin.routes.activity.ActivityQueries.catalog_for_template",
        lambda self: [{"name": "event_rated", "label": "Оценка", "group": "events", "group_label": "События"}],
    )

    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.get("/admin/activity", cookies=_auth())
        assert resp.status == 200
        text = await resp.text()
        assert "Activity Log" in text
        assert "event_rated" in text
        assert "@roman" in text


@pytest.mark.asyncio
async def test_friendship_accept_tracks_analytics():
    from app.services.friendship_service import FriendshipService

    friendships = MagicMock()
    friendships.get_by_id = AsyncMock(
        return_value=MagicMock(
            requester_user_id=USER_ID,
            addressee_user_id=UUID("44444444-4444-4444-8444-444444444444"),
        )
    )
    friendships.accept = AsyncMock(return_value=True)
    analytics = MagicMock()
    analytics.track = AsyncMock()

    service = FriendshipService(friendships, MagicMock(), "bot", analytics)
    ok = await service.accept_friendship(
        UUID("55555555-5555-4555-8555-555555555555"),
        USER_ID,
    )
    assert ok
    analytics.track.assert_awaited_once()
    assert analytics.track.await_args.args[0] == "friendship_accepted"
