from aiohttp import web

from app.admin.templates import render_template


async def home(request: web.Request) -> web.Response:
    pool = request.app["pool"]
    event_count = await pool.fetchval("select count(*)::int from admin_event_log")
    html = render_template(
        "home.html",
        show_nav=True,
        active="home",
        event_count=event_count,
    )
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response
