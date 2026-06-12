from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from app.admin.app import setup_admin_routes
from app.admin.auth import create_session_payload, set_session_cookie
from app.admin.services.export_service import ExportResult, ExportService
from app.admin.services.system_queries import EnvFlag, SystemInfo
from app.config import settings

EVENT_ID = UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "admin-test-pass")
    monkeypatch.setattr(settings, "telegram_bot_token", "bot-token")
    monkeypatch.setattr(settings, "bot_mode", "polling")

    pool = MagicMock()
    pool.fetchval = AsyncMock(return_value=0)
    pool.fetch = AsyncMock(return_value=[])
    pool.fetchrow = AsyncMock(return_value={"id": EVENT_ID})
    pool.execute = AsyncMock()

    app = web.Application()
    setup_admin_routes(app, pool)
    app["pool"] = pool
    return app


def _auth() -> tuple[dict[str, str], str]:
    payload = create_session_payload()
    response = web.Response()
    set_session_cookie(response, payload)
    cookies = {k: m.value for k, m in response.cookies.items()}
    return cookies, payload["csrf"]


@pytest.mark.asyncio
async def test_export_page_renders(admin_app):
    cookies, _ = _auth()
    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.get("/admin/export", cookies=cookies)
        assert resp.status == 200
        text = await resp.text()
        assert "CSV Export" in text
        assert "event_lifecycle" in text


@pytest.mark.asyncio
async def test_system_page_renders(admin_app, monkeypatch):
    info = SystemInfo(
        git_commit="abc123",
        calibration_version=2,
        bot_mode="polling",
        is_webhook=False,
        admin_enabled=True,
        env_flags=[EnvFlag("BOT_MODE", "polling", False)],
        event_log_count=10,
        action_log_count=2,
        migration_count=10,
    )
    monkeypatch.setattr(
        "app.admin.routes.system.SystemQueries.fetch_info",
        AsyncMock(return_value=info),
    )
    async with TestClient(TestServer(admin_app)) as client:
        cookies, _ = _auth()
        resp = await client.get("/admin/system", cookies=cookies)
        assert resp.status == 200
        text = await resp.text()
        assert "System" in text
        assert "abc123" in text
        assert "SCORING_CALIBRATION_VERSION" in text


@pytest.mark.asyncio
async def test_export_post_requires_csrf(admin_app):
    cookies, _ = _auth()
    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.post(
            "/admin/export",
            data={"export_type": "users", "date_from": "2026-06-01", "date_to": "2026-06-10"},
            cookies=cookies,
        )
        assert resp.status == 403


@pytest.mark.asyncio
async def test_export_post_downloads_csv(admin_app, monkeypatch):
    result = ExportResult(
        filename="users_2026-06-01_2026-06-10.csv",
        row_count=1,
        csv_text="id,telegram_id\n1,123\n",
    )
    monkeypatch.setattr(
        ExportService,
        "parse_request",
        lambda self, t, f, to: MagicMock(
            export_type="users",
            date_from=date(2026, 6, 1),
            date_to=date(2026, 6, 10),
        ),
    )
    monkeypatch.setattr(
        ExportService,
        "generate",
        AsyncMock(return_value=result),
    )

    cookies, csrf = _auth()
    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.post(
            "/admin/export",
            data={
                "csrf_token": csrf,
                "export_type": "users",
                "date_from": "2026-06-01",
                "date_to": "2026-06-10",
            },
            cookies=cookies,
        )
        assert resp.status == 200
        assert resp.headers["Content-Type"].startswith("text/csv")
        body = await resp.read()
        assert b"telegram_id" in body


@pytest.mark.asyncio
async def test_hide_event_requires_csrf(admin_app):
    cookies, _ = _auth()
    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.post(
            f"/admin/events/{EVENT_ID}/hide",
            data={"comment": "spam"},
            cookies=cookies,
        )
        assert resp.status == 403


@pytest.mark.asyncio
async def test_hide_event_redirects(admin_app, monkeypatch):
    monkeypatch.setattr(
        "app.admin.routes.moderation.ModerationService.set_feed_hidden",
        AsyncMock(return_value=True),
    )
    cookies, csrf = _auth()
    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.post(
            f"/admin/events/{EVENT_ID}/hide",
            data={"csrf_token": csrf, "comment": "spam"},
            cookies=cookies,
            allow_redirects=False,
        )
        assert resp.status == 302
        assert resp.headers["Location"] == f"/admin/events/{EVENT_ID}?msg=hidden"


def test_export_parse_rejects_long_range():
    service = ExportService(MagicMock())
    with pytest.raises(ValueError, match="90"):
        service.parse_request("users", "2026-01-01", "2026-06-10")


def test_export_parse_unknown_type():
    service = ExportService(MagicMock())
    with pytest.raises(ValueError, match="unknown"):
        service.parse_request("reports", "2026-06-01", "2026-06-10")
