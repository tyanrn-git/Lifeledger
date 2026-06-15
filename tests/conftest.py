"""Shared fixtures for admin and bot tests."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from aiohttp import web

from app.admin.app import setup_admin_routes
from app.admin.auth import create_session_payload, set_session_cookie
from app.config import settings

USER_ID = UUID("11111111-1111-4111-8111-111111111111")
EVENT_ID = UUID("22222222-2222-4222-8222-222222222222")
NOW = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)


def auth_cookies() -> dict[str, str]:
    response = web.Response()
    set_session_cookie(response, create_session_payload())
    return {k: m.value for k, m in response.cookies.items()}


def auth_cookies_with_csrf() -> tuple[dict[str, str], str]:
    payload = create_session_payload()
    response = web.Response()
    set_session_cookie(response, payload)
    cookies = {k: m.value for k, m in response.cookies.items()}
    return cookies, payload["csrf"]


def _kpi_row() -> dict:
    return {
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


def _funnel_row() -> dict:
    return {
        "registration": 10,
        "first_feed": 8,
        "first_event_viewed": 7,
        "first_rating": 6,
        "five_ratings": 4,
        "ten_ratings": 2,
        "first_event_created": 3,
        "first_community_rating": 2,
        "friend_invite_sent": 2,
        "friendship_accepted": 1,
        "first_friend_rating": 1,
        "returned_d1": 1,
        "returned_d2_7": 1,
    }


def make_smoke_pool() -> MagicMock:
    pool = MagicMock()
    kpi = _kpi_row()
    funnel = _funnel_row()

    async def fetchrow_side_effect(query, *args):
        q = " ".join(query.lower().split())
        if "as registration" in q and "returned_d2_7" in q:
            return funnel
        if "percentile_cont" in q or "median_hours" in q:
            return {"median_hours": 12.5, "median_skip": 0.25}
        if "users_total" in q:
            return kpi
        return None

    pool.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
    pool.fetchval = AsyncMock(return_value=0)
    pool.fetch = AsyncMock(return_value=[])
    pool.execute = AsyncMock()
    return pool


@pytest.fixture
def smoke_admin_app(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "admin-test-pass")
    monkeypatch.setattr(settings, "telegram_bot_token", "bot-token")
    monkeypatch.setattr(settings, "bot_mode", "polling")

    pool = make_smoke_pool()
    app = web.Application()
    setup_admin_routes(app, pool)
    app["pool"] = pool
    return app
