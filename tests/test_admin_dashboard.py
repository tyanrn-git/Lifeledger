from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from app.admin.app import setup_admin_routes
from app.admin.auth import create_session_payload, encode_session, set_session_cookie
from app.admin.services.admin_queries import AdminQueries
from app.config import settings


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "admin-test-pass")
    monkeypatch.setattr(settings, "telegram_bot_token", "bot-token")
    monkeypatch.setattr(settings, "bot_mode", "polling")

    pool = MagicMock()
    kpi_row = {
        "users_total": 3,
        "new_users_today": 1,
        "new_users_7d": 2,
        "active_users_today": 2,
        "active_users_7d": 3,
        "events_total": 10,
        "events_today": 1,
        "ratings_total": 5,
        "ratings_today": 1,
        "ai_events_total": 4,
        "avg_community_ratings": 1.5,
        "avg_batch_size": 27.0,
        "empty_feed_starts_7d": 0,
        "ai_generation_triggers_7d": 0,
        "pending_ai_rescore": 0,
        "events_no_impressions_24h": 1,
    }

    async def fetchrow_side_effect(query, *args):
        if "percentile_cont" in query:
            return {"median_hours": 12.5, "median_skip": 0.25}
        return kpi_row

    pool.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
    pool.fetchval = AsyncMock(return_value=None)
    pool.fetch = AsyncMock(return_value=[])
    pool.execute = AsyncMock()

    app = web.Application()
    setup_admin_routes(app, pool)
    return app


def _session_cookie() -> dict[str, str]:
    response = web.Response()
    set_session_cookie(response, create_session_payload())
    return {k: m.value for k, m in response.cookies.items()}


@pytest.mark.asyncio
async def test_dashboard_requires_auth(admin_app):
    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.get("/admin/dashboard", allow_redirects=False)
        assert resp.status == 302


@pytest.mark.asyncio
async def test_dashboard_renders(admin_app):
    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.get(
            "/admin/dashboard",
            cookies=_session_cookie(),
        )
        assert resp.status == 200
        text = await resp.text()
        assert "Dashboard" in text
        assert "Журнал событий" in text


def test_parse_days():
    q = AdminQueries(MagicMock())
    assert q.parse_days("7") == 7
    assert q.parse_days("30") == 30
    assert q.parse_days("all") is None
    assert q.parse_days("bad") == 7
