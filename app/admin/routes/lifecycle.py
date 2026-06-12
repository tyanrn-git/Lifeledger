from aiohttp import web

from app.admin.pagination import build_query, parse_page
from app.admin.services.lifecycle_queries import PRESETS, LifecycleQueries
from app.admin.templates import render_template


def _html_response(html: str) -> web.Response:
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


async def lifecycle_list(request: web.Request) -> web.Response:
    pool = request.app["pool"]
    queries = LifecycleQueries(pool)
    query = {k: v for k, v in request.query.items()}
    filters = queries.parse_filters(query)
    page = parse_page(request.query.get("page"))
    result = await queries.list_lifecycle(filters, page)
    categories = await queries.list_categories()
    filter_dict = queries.filters_to_dict(filters)

    html = render_template(
        "lifecycle.html",
        show_nav=True,
        active="lifecycle",
        rows=result.items,
        page=result,
        filters=filters,
        presets=PRESETS,
        categories=categories,
        filter_query=build_query(filter_dict),
        build_query=build_query,
        filter_dict=filter_dict,
        highlight_id=str(filters.event_id) if filters.event_id else None,
    )
    return _html_response(html)
