from aiohttp import web

from app.admin.services.feed_queries import FeedQueries
from app.admin.templates import render_template


async def feed_page(request: web.Request) -> web.Response:
    queries = FeedQueries(request.app["pool"])
    stats = await queries.fetch_batch_stats()
    tiers = await queries.fetch_tier_breakdown()
    injections = await queries.fetch_injection_by_tier()
    html = render_template(
        "feed.html",
        show_nav=True,
        active="feed",
        stats=stats,
        tiers=tiers,
        injections=injections,
    )
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response
