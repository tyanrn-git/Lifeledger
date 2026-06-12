from aiohttp import web

from app.admin.services.ratings_queries import RatingsQueries
from app.admin.templates import render_template


async def ratings_page(request: web.Request) -> web.Response:
    summary = await RatingsQueries(request.app["pool"]).fetch_summary()
    html = render_template(
        "ratings.html",
        show_nav=True,
        active="ratings",
        summary=summary,
    )
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response
