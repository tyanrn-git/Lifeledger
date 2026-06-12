from aiohttp import web

from app.admin.services.funnel_service import FunnelService
from app.admin.templates import render_template


async def funnels(request: web.Request) -> web.Response:
    pool = request.app["pool"]
    steps = await FunnelService(pool).compute()
    html = render_template(
        "funnels.html",
        show_nav=True,
        active="funnels",
        steps=steps,
    )
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response
