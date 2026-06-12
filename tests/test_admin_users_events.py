from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from app.admin.app import setup_admin_routes
from app.admin.auth import create_session_payload, encode_session, set_session_cookie
from app.admin.pagination import PageResult
from app.admin.services.events_queries import EventListRow
from app.admin.services.users_queries import UserListRow
from app.config import settings

USER_ID = UUID("11111111-1111-4111-8111-111111111111")
EVENT_ID = UUID("22222222-2222-4222-8222-222222222222")
NOW = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "admin-test-pass")
    monkeypatch.setattr(settings, "telegram_bot_token", "bot-token")
    monkeypatch.setattr(settings, "bot_mode", "polling")

    pool = MagicMock()
    pool.fetchval = AsyncMock(return_value=0)
    pool.fetch = AsyncMock(return_value=[])
    pool.fetchrow = AsyncMock(return_value=None)

    app = web.Application()
    setup_admin_routes(app, pool)
    app["pool"] = pool
    return app


def _session_cookie() -> dict[str, str]:
    response = web.Response()
    set_session_cookie(response, create_session_payload())
    return {k: m.value for k, m in response.cookies.items()}


@pytest.mark.asyncio
async def test_users_list_requires_auth(admin_app):
    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.get("/admin/users", allow_redirects=False)
        assert resp.status == 302


@pytest.mark.asyncio
async def test_users_list_renders(admin_app, monkeypatch):
    row = UserListRow(
        id=USER_ID,
        telegram_id=123,
        username="roman",
        first_name="Roman",
        last_name=None,
        language_code="ru",
        created_at=NOW,
        last_seen_at=NOW,
        events_count=2,
        ratings_count=10,
        friends_count=1,
    )
    page = PageResult(items=[row], page=1, per_page=50, total=1)

    async def fake_list(filters, page_num):
        return page

    monkeypatch.setattr(
        "app.admin.routes.users.UsersQueries.list_users",
        AsyncMock(side_effect=fake_list),
    )
    monkeypatch.setattr(
        "app.admin.routes.users.UsersQueries.parse_filters",
        lambda self, q: MagicMock(),
    )
    monkeypatch.setattr(
        "app.admin.routes.users.UsersQueries.filters_to_dict",
        lambda self, f: {},
    )

    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.get("/admin/users", cookies=_session_cookie())
        assert resp.status == 200
        text = await resp.text()
        assert "Users" in text
        assert "roman" in text


@pytest.mark.asyncio
async def test_events_list_renders(admin_app, monkeypatch):
    row = EventListRow(
        id=EVENT_ID,
        preview="Test event",
        source="user",
        event_type="real",
        category="семья",
        original_language="ru",
        author_user_id=USER_ID,
        author_name="roman",
        self_score=5,
        final_community_score=4.5,
        community_ratings_count=3,
        impressions_count=10,
        is_deleted=False,
        is_feed_hidden=False,
        created_at=NOW,
    )
    page = PageResult(items=[row], page=1, per_page=50, total=1)

    monkeypatch.setattr(
        "app.admin.routes.events.EventsQueries.list_events",
        AsyncMock(return_value=page),
    )
    monkeypatch.setattr(
        "app.admin.routes.events.EventsQueries.list_categories",
        AsyncMock(return_value=["семья"]),
    )
    monkeypatch.setattr(
        "app.admin.routes.events.EventsQueries.parse_filters",
        lambda self, q: MagicMock(),
    )
    monkeypatch.setattr(
        "app.admin.routes.events.EventsQueries.filters_to_dict",
        lambda self, f: {},
    )

    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.get("/admin/events", cookies=_session_cookie())
        assert resp.status == 200
        text = await resp.text()
        assert "Events" in text
        assert "Test event" in text


@pytest.mark.asyncio
async def test_lifecycle_list_renders(admin_app, monkeypatch):
    from app.admin.pagination import PageResult

    page = PageResult(items=[], page=1, per_page=50, total=0)
    monkeypatch.setattr(
        "app.admin.routes.lifecycle.LifecycleQueries.list_lifecycle",
        AsyncMock(return_value=page),
    )
    monkeypatch.setattr(
        "app.admin.routes.lifecycle.LifecycleQueries.list_categories",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.admin.routes.lifecycle.LifecycleQueries.parse_filters",
        lambda self, q: __import__(
            "app.admin.services.lifecycle_queries", fromlist=["LifecycleFilters"]
        ).LifecycleFilters(),
    )
    monkeypatch.setattr(
        "app.admin.routes.lifecycle.LifecycleQueries.filters_to_dict",
        lambda self, f: {},
    )

    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.get("/admin/events/lifecycle", cookies=_session_cookie())
        assert resp.status == 200
        text = await resp.text()
        assert "Event Lifecycle" in text
        assert "Без показов" in text
