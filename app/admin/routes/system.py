from aiohttp import web

from app.admin.services.system_queries import SystemQueries
from app.admin.templates import render_template


async def system_page(request: web.Request) -> web.Response:
    info = await SystemQueries(request.app["pool"]).fetch_info()
    html = render_template(
        "system.html",
        show_nav=True,
        active="system",
        info=info,
    )
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response
