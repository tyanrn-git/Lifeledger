from uuid import UUID

from aiohttp import web

from app.admin.pagination import build_query, parse_page
from app.admin.services.users_queries import UsersQueries
from app.admin.templates import render_template


def _html_response(html: str) -> web.Response:
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


async def users_list(request: web.Request) -> web.Response:
    pool = request.app["pool"]
    queries = UsersQueries(pool)
    query = {k: v for k, v in request.query.items()}
    filters = queries.parse_filters(query)
    page = parse_page(request.query.get("page"))
    result = await queries.list_users(filters, page)
    filter_dict = queries.filters_to_dict(filters)

    html = render_template(
        "users_list.html",
        show_nav=True,
        active="users",
        users=result.items,
        page=result,
        filters=filters,
        filter_query=build_query(filter_dict),
        build_query=build_query,
        filter_dict=filter_dict,
        display_name=UsersQueries.display_name,
    )
    return _html_response(html)


async def user_detail(request: web.Request) -> web.Response:
    pool = request.app["pool"]
    try:
        user_id = UUID(request.match_info["id"])
    except ValueError:
        raise web.HTTPNotFound()

    user = await UsersQueries(pool).get_user(user_id)
    if not user:
        raise web.HTTPNotFound()

    html = render_template(
        "user_detail.html",
        show_nav=True,
        active="users",
        user=user,
        display_name=UsersQueries.display_name,
    )
    return _html_response(html)
