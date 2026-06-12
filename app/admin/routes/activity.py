from aiohttp import web

from app.admin.pagination import build_query, parse_page
from app.admin.services.activity_queries import ActivityQueries
from app.admin.templates import render_template
from app.analytics.event_catalog import EVENT_GROUPS


def _html_response(html: str) -> web.Response:
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


async def activity_list(request: web.Request) -> web.Response:
    pool = request.app["pool"]
    queries = ActivityQueries(pool)
    query = {k: v for k, v in request.query.items()}
    filters = queries.parse_filters(query)
    page = parse_page(request.query.get("page"))
    result = await queries.list_activity(filters, page)
    hidden_noisy = await queries.count_hidden_noisy(filters)
    filter_dict = queries.filters_to_dict(filters)

    html = render_template(
        "activity.html",
        show_nav=True,
        active="activity",
        rows=result.items,
        page=result,
        filters=filters,
        filter_dict=filter_dict,
        filter_query=build_query(filter_dict),
        build_query=build_query,
        event_groups=EVENT_GROUPS,
        catalog=queries.catalog_for_template(),
        hidden_noisy=hidden_noisy,
    )
    return _html_response(html)
