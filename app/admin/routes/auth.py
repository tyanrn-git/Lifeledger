from aiohttp import web

from app.admin.auth import (
    clear_session_cookie,
    create_session_payload,
    set_session_cookie,
    verify_password,
)
from app.admin.templates import render_template


async def login_get(request: web.Request) -> web.Response:
    html = render_template("login.html", show_nav=False, error=None)
    return web.Response(text=html, content_type="text/html")


async def login_post(request: web.Request) -> web.Response:
    data = await request.post()
    password = (data.get("password") or "").strip()
    if not verify_password(password):
        html = render_template("login.html", show_nav=False, error="Неверный пароль")
        return web.Response(text=html, content_type="text/html", status=401)

    response = web.Response(status=302, headers={"Location": "/admin"})
    set_session_cookie(response, create_session_payload())
    return response


async def logout(request: web.Request) -> web.Response:
    response = web.Response(status=302, headers={"Location": "/admin/login"})
    clear_session_cookie(response)
    return response
