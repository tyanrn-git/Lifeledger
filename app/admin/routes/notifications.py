from aiohttp import web

from app.admin.services.notifications_queries import NotificationsQueries
from app.admin.templates import render_template


async def notifications_page(request: web.Request) -> web.Response:
    summary = await NotificationsQueries(request.app["pool"]).fetch_summary()
    html = render_template(
        "notifications.html",
        show_nav=True,
        active="notifications",
        summary=summary,
    )
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response
