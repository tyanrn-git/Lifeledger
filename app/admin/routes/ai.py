from aiohttp import web

from app.admin.services.ai_queries import AiQueries
from app.admin.templates import render_template


async def ai_page(request: web.Request) -> web.Response:
    summary = await AiQueries(request.app["pool"]).fetch_summary()
    html = render_template(
        "ai.html",
        show_nav=True,
        active="ai",
        summary=summary,
    )
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response
