from uuid import UUID

from aiohttp import web

from app.admin.csrf import validate_csrf
from app.admin.services.moderation_service import ModerationService


def _csrf(request: web.Request) -> str:
    session = request.get("admin_session") or {}
    return session.get("csrf", "")


async def event_hide(request: web.Request) -> web.Response:
    return await _moderate(request, hidden=True)


async def event_unhide(request: web.Request) -> web.Response:
    return await _moderate(request, hidden=False)


async def _moderate(request: web.Request, *, hidden: bool) -> web.Response:
    try:
        event_id = UUID(request.match_info["id"])
    except ValueError:
        raise web.HTTPNotFound()

    data = await request.post()
    if not validate_csrf(_csrf(request), data.get("csrf_token")):
        raise web.HTTPForbidden(text="Invalid CSRF token")

    comment = (data.get("comment") or "").strip() or None
    ok = await ModerationService(request.app["pool"]).set_feed_hidden(
        event_id, hidden, comment
    )
    if not ok:
        raise web.HTTPNotFound()

    action = "hidden" if hidden else "unhidden"
    raise web.HTTPFound(f"/admin/events/{event_id}?msg={action}")
