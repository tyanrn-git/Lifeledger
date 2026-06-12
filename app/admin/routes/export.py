from aiohttp import web

from app.admin.csrf import validate_csrf
from app.admin.services.export_service import EXPORT_TYPES, ExportService
from app.admin.templates import render_template


def _csrf(request: web.Request) -> str:
    session = request.get("admin_session") or {}
    return session.get("csrf", "")


def _html_response(html: str) -> web.Response:
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


async def export_page(request: web.Request) -> web.Response:
    date_from, date_to = ExportService.default_date_range()
    html = render_template(
        "export.html",
        show_nav=True,
        active="export",
        export_types=EXPORT_TYPES,
        date_from=date_from,
        date_to=date_to,
        csrf_token=_csrf(request),
        error=None,
    )
    return _html_response(html)


async def export_download(request: web.Request) -> web.Response:
    data = await request.post()
    if not validate_csrf(_csrf(request), data.get("csrf_token")):
        raise web.HTTPForbidden(text="Invalid CSRF token")

    export_type = (data.get("export_type") or "").strip()
    date_from = (data.get("date_from") or "").strip()
    date_to = (data.get("date_to") or "").strip()
    service = ExportService(request.app["pool"])

    try:
        req = service.parse_request(export_type, date_from, date_to)
        result = await service.generate(req)
    except ValueError as exc:
        html = render_template(
            "export.html",
            show_nav=True,
            active="export",
            export_types=EXPORT_TYPES,
            date_from=date_from,
            date_to=date_to,
            csrf_token=_csrf(request),
            error=str(exc),
        )
        return _html_response(html)

    return web.Response(
        body=result.csv_text.encode("utf-8-sig"),
        content_type="text/csv",
        charset="utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-Robots-Tag": "noindex, nofollow",
        },
    )
