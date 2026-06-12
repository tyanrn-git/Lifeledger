import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from aiohttp import web

from app.admin.csrf import new_csrf_token
from app.config import settings

COOKIE_NAME = "ll_admin_session"
SESSION_MAX_AGE = 60 * 60 * 24  # default 24h; overridden by settings


def admin_enabled() -> bool:
    return bool(settings.admin_password)


def _session_max_age() -> int:
    return settings.admin_session_ttl_hours * 3600


def _signing_secret() -> bytes:
    material = settings.admin_password or settings.telegram_bot_token
    return hashlib.sha256(material.encode()).digest()


def create_session_payload() -> dict[str, Any]:
    return {
        "auth": True,
        "csrf": new_csrf_token(),
        "exp": int(time.time()) + _session_max_age(),
    }


def encode_session(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    body = base64.urlsafe_b64encode(raw).decode()
    sig = hmac.new(_signing_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def decode_session(value: str | None) -> dict[str, Any] | None:
    if not value or "." not in value:
        return None
    body, sig = value.rsplit(".", 1)
    expected = hmac.new(_signing_secret(), body.encode(), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(expected, sig):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body.encode()))
    except (json.JSONDecodeError, ValueError):
        return None
    if not payload.get("auth"):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def verify_password(password: str) -> bool:
    if not settings.admin_password:
        return False
    return secrets.compare_digest(password, settings.admin_password)


def set_session_cookie(response: web.Response, payload: dict[str, Any]) -> None:
    response.set_cookie(
        COOKIE_NAME,
        encode_session(payload),
        httponly=True,
        secure=settings.is_webhook,
        samesite="Lax",
        max_age=_session_max_age(),
    )


def clear_session_cookie(response: web.Response) -> None:
    response.del_cookie(COOKIE_NAME)


def get_session(request: web.Request) -> dict[str, Any] | None:
    return decode_session(request.cookies.get(COOKIE_NAME))


@web.middleware
async def admin_auth_middleware(request: web.Request, handler):
    path = request.path
    if not path.startswith("/admin"):
        return await handler(request)

    if not admin_enabled():
        raise web.HTTPNotFound()

    if path in ("/admin/login", "/admin/logout"):
        return await handler(request)

    session = get_session(request)
    if not session:
        raise web.HTTPFound("/admin/login")

    request["admin_session"] = session
    return await handler(request)
