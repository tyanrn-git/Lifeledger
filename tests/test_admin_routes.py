from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from app.admin.app import setup_admin_routes
from app.config import settings


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "admin-test-pass")
    monkeypatch.setattr(settings, "telegram_bot_token", "bot-token")
    monkeypatch.setattr(settings, "bot_mode", "polling")

    pool = MagicMock()
    pool.fetchval = AsyncMock(return_value=0)

    app = web.Application()
    setup_admin_routes(app, pool)
    return app


@pytest.mark.asyncio
async def test_admin_disabled_returns_404(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "")
    pool = MagicMock()
    app = web.Application()
    setup_admin_routes(app, pool)
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/admin/login")
        assert resp.status == 404


@pytest.mark.asyncio
async def test_login_page(admin_app):
    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.get("/admin/login")
        assert resp.status == 200
        text = await resp.text()
        assert "Admin login" in text


@pytest.mark.asyncio
async def test_admin_redirects_without_session(admin_app):
    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.get("/admin", allow_redirects=False)
        assert resp.status == 302
        assert resp.headers["Location"] == "/admin/login"


@pytest.mark.asyncio
async def test_login_success(admin_app):
    async with TestClient(TestServer(admin_app)) as client:
        resp = await client.post(
            "/admin/login",
            data={"password": "admin-test-pass"},
            allow_redirects=False,
        )
        assert resp.status == 302
        assert resp.headers["Location"] == "/admin"
        assert "ll_admin_session" in resp.cookies
