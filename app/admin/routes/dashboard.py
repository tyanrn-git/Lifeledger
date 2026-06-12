import json
from datetime import datetime, timezone

from aiohttp import web

from app.admin.services.admin_queries import AdminQueries
from app.admin.services.daily_aggregates import DailyAggregatesService
from app.admin.services.lifecycle_queries import LifecycleQueries
from app.admin.templates import render_template


async def dashboard(request: web.Request) -> web.Response:
    pool = request.app["pool"]
    days = AdminQueries(pool).parse_days(request.query.get("days"))
    end = datetime.now(timezone.utc).date()

    queries = AdminQueries(pool)
    start = await queries.resolve_start_date(days)
    await DailyAggregatesService(pool).ensure_range(start, end)

    kpis = await queries.fetch_kpis()
    charts = await queries.fetch_chart_series(days)
    chart_json = json.dumps(
        {
            key: [{"day": p.day, "value": p.value} for p in points]
            for key, points in charts.items()
        }
    )
    recent_logs = await queries.fetch_recent_logs()
    log_counts = await queries.fetch_log_counts_7d()
    ops = await queries.fetch_ops_failures()
    lifecycle_kpis = await LifecycleQueries(pool).fetch_kpis()

    period = request.query.get("days") or "7"
    html = render_template(
        "dashboard.html",
        show_nav=True,
        active="dashboard",
        kpis=kpis,
        lifecycle_kpis=lifecycle_kpis,
        chart_json=chart_json,
        recent_logs=recent_logs,
        log_counts=log_counts,
        ops=ops,
        period=period,
    )
    response = web.Response(text=html, content_type="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response
