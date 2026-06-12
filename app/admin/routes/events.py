from uuid import UUID

from aiohttp import web

from app.admin.pagination import build_query, parse_page
from app.admin.services.events_queries import EventsQueries
from app.admin.services.users_queries import UsersQueries
from app.admin.templates import render_template


def _html_response(html: str) -> web.Response:
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


async def events_list(request: web.Request) -> web.Response:
    pool = request.app["pool"]
    queries = EventsQueries(pool)
    query = {k: v for k, v in request.query.items()}
    filters = queries.parse_filters(query)
    page = parse_page(request.query.get("page"))
    result = await queries.list_events(filters, page)
    categories = await queries.list_categories()
    filter_dict = queries.filters_to_dict(filters)

    html = render_template(
        "events_list.html",
        show_nav=True,
        active="events",
        events=result.items,
        page=result,
        filters=filters,
        categories=categories,
        filter_query=build_query(filter_dict),
        build_query=build_query,
        filter_dict=filter_dict,
        display_name=UsersQueries.display_name,
    )
    return _html_response(html)


def _csrf(request: web.Request) -> str:
    session = request.get("admin_session") or {}
    return session.get("csrf", "")


async def event_detail(request: web.Request) -> web.Response:
    pool = request.app["pool"]
    try:
        event_id = UUID(request.match_info["id"])
    except ValueError:
        raise web.HTTPNotFound()

    event = await EventsQueries(pool).get_event(event_id)
    if not event:
        raise web.HTTPNotFound()

    html = render_template(
        "event_detail.html",
        show_nav=True,
        active="events",
        event=event,
        csrf_token=_csrf(request),
        flash_msg=request.query.get("msg"),
    )
    return _html_response(html)
