from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import asyncpg

from app.utils.scoring import SCORING_CALIBRATION_VERSION


@dataclass(frozen=True)
class DashboardKPIs:
    users_total: int
    new_users_today: int
    new_users_7d: int
    active_users_today: int
    active_users_7d: int
    events_total: int
    events_today: int
    ratings_total: int
    ratings_today: int
    ai_events_total: int
    avg_community_ratings: float | None
    avg_batch_size: float | None
    empty_feed_starts_7d: int
    ai_generation_triggers_7d: int
    pending_ai_rescore: int
    events_no_impressions_24h: int


@dataclass(frozen=True)
class ChartDay:
    day: str
    value: float


@dataclass(frozen=True)
class LogRow:
    created_at: datetime
    event_name: str
    user_id: str | None
    properties: str


@dataclass(frozen=True)
class EventNameCount:
    event_name: str
    count: int


class AdminQueries:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    def parse_days(self, raw: str | None) -> int | None:
        if not raw or raw == "all":
            return None
        try:
            value = int(raw)
        except ValueError:
            return 7
        if value in (7, 30, 90):
            return value
        return 7

    async def fetch_kpis(self) -> DashboardKPIs:
        row = await self._pool.fetchrow(
            """
            select
              (select count(*)::int from users) as users_total,
              (select count(*)::int from users
               where created_at >= current_date) as new_users_today,
              (select count(*)::int from users
               where created_at >= current_date - interval '7 days') as new_users_7d,
              (select count(distinct user_id)::int from admin_event_log
               where event_name = 'user_seen'
                 and created_at >= current_date and user_id is not null) as active_users_today,
              (select count(distinct user_id)::int from admin_event_log
               where event_name = 'user_seen'
                 and created_at >= current_date - interval '7 days'
                 and user_id is not null) as active_users_7d,
              (select count(*)::int from events where is_deleted = false) as events_total,
              (select count(*)::int from events
               where is_deleted = false and created_at >= current_date) as events_today,
              (select count(*)::int from ratings) as ratings_total,
              (select count(*)::int from ratings
               where created_at >= current_date) as ratings_today,
              (select count(*)::int from events
               where source = 'ai_generated'::event_source and is_deleted = false) as ai_events_total,
              (select avg(community_ratings_count)::numeric(6,2) from events
               where is_deleted = false) as avg_community_ratings,
              (select avg(actual_size)::numeric(6,2) from rating_batches) as avg_batch_size,
              (select count(*)::int from admin_event_log
               where event_name = 'feed_empty'
                 and created_at >= current_date - interval '7 days') as empty_feed_starts_7d,
              (select count(*)::int from admin_event_log
               where event_name = 'ai_generation_triggered'
                 and created_at >= current_date - interval '7 days') as ai_generation_triggers_7d,
              (select count(*)::int from events
               where is_deleted = false
                 and scoring_calibration_version < $1) as pending_ai_rescore,
              (select count(*)::int from events e
               where e.is_deleted = false
                 and e.created_at < now() - interval '24 hours'
                 and not exists (
                   select 1 from event_impressions ei where ei.event_id = e.id
                 )) as events_no_impressions_24h
            """,
            SCORING_CALIBRATION_VERSION,
        )
        return DashboardKPIs(
            users_total=row["users_total"],
            new_users_today=row["new_users_today"],
            new_users_7d=row["new_users_7d"],
            active_users_today=row["active_users_today"],
            active_users_7d=row["active_users_7d"],
            events_total=row["events_total"],
            events_today=row["events_today"],
            ratings_total=row["ratings_total"],
            ratings_today=row["ratings_today"],
            ai_events_total=row["ai_events_total"],
            avg_community_ratings=float(row["avg_community_ratings"])
            if row["avg_community_ratings"] is not None
            else None,
            avg_batch_size=float(row["avg_batch_size"])
            if row["avg_batch_size"] is not None
            else None,
            empty_feed_starts_7d=row["empty_feed_starts_7d"],
            ai_generation_triggers_7d=row["ai_generation_triggers_7d"],
            pending_ai_rescore=row["pending_ai_rescore"],
            events_no_impressions_24h=row["events_no_impressions_24h"],
        )

    async def fetch_chart_series(self, days: int | None) -> dict[str, list[ChartDay]]:
        if days is None:
            rows = await self._pool.fetch(
                """
                select date::text as day,
                       new_users, active_users, events_created, ratings_count,
                       ai_events_generated, feed_empty_count
                from analytics_daily
                order by date
                """
            )
        else:
            start = date.today() - timedelta(days=days - 1)
            rows = await self._pool.fetch(
                """
                select date::text as day,
                       new_users, active_users, events_created, ratings_count,
                       ai_events_generated, feed_empty_count
                from analytics_daily
                where date >= $1
                order by date
                """,
                start,
            )

        def series(key: str) -> list[ChartDay]:
            return [
                ChartDay(day=r["day"], value=float(r[key] or 0))
                for r in rows
            ]

        return {
            "new_users": series("new_users"),
            "active_users": series("active_users"),
            "events": series("events_created"),
            "ratings": series("ratings_count"),
            "ai_generated": series("ai_events_generated"),
            "feed_empty": series("feed_empty_count"),
        }

    async def fetch_recent_logs(self, limit: int = 20) -> list[LogRow]:
        rows = await self._pool.fetch(
            """
            select created_at, event_name, user_id, properties::text as properties
            from admin_event_log
            order by created_at desc
            limit $1
            """,
            limit,
        )
        return [
            LogRow(
                created_at=r["created_at"],
                event_name=r["event_name"],
                user_id=str(r["user_id"]) if r["user_id"] else None,
                properties=r["properties"][:120],
            )
            for r in rows
        ]

    async def fetch_log_counts_7d(self) -> list[EventNameCount]:
        rows = await self._pool.fetch(
            """
            select event_name, count(*)::int as cnt
            from admin_event_log
            where created_at >= current_date - interval '7 days'
            group by event_name
            order by cnt desc, event_name
            """
        )
        return [EventNameCount(event_name=r["event_name"], count=r["cnt"]) for r in rows]

    async def fetch_ops_failures(self) -> dict[str, list[dict[str, Any]]]:
        ai_rows = await self._pool.fetch(
            """
            select created_at, properties::text as properties
            from admin_event_log
            where event_name = 'ai_generation_failed'
            order by created_at desc
            limit 5
            """
        )
        notif_rows = await self._pool.fetch(
            """
            select created_at, properties::text as properties
            from admin_event_log
            where event_name = 'notification_failed'
            order by created_at desc
            limit 5
            """
        )
        return {
            "ai_generation_failed": [dict(r) for r in ai_rows],
            "notification_failed": [dict(r) for r in notif_rows],
        }

    async def resolve_start_date(self, days: int | None) -> date:
        end = datetime.now(timezone.utc).date()
        if days is None:
            val = await self._pool.fetchval(
                "select min(date) from analytics_daily"
            )
            if val is None:
                val = await self._pool.fetchval(
                    "select min(created_at::date) from users"
                )
            return val or end
        return end - timedelta(days=days - 1)
