from dataclasses import dataclass
from datetime import datetime

import asyncpg


@dataclass(frozen=True)
class TypeCount:
    notification_type: str
    total: int
    sent: int
    pending: int


@dataclass(frozen=True)
class NotificationsSummary:
    created_total: int
    sent_total: int
    failed_total: int
    failed_stale: int
    failed_log_7d: int
    users_disabled: int
    by_type: list[TypeCount]
    recent_failures: list[tuple[datetime, str]]


class NotificationsQueries:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def fetch_summary(self) -> NotificationsSummary:
        totals = await self._pool.fetchrow(
            """
            select
              count(*)::int as created_total,
              count(*) filter (where is_sent = true)::int as sent_total,
              count(*) filter (
                where is_sent = false
                  and created_at < now() - interval '1 hour'
              )::int as failed_stale
            from notifications
            """
        )
        failed_log = await self._pool.fetchval(
            """
            select count(*)::int from admin_event_log
            where event_name = 'notification_failed'
              and created_at >= current_date - interval '7 days'
            """
        )
        disabled = await self._pool.fetchval(
            """
            select count(*)::int from users
            where notifications_enabled = false
            """
        )
        type_rows = await self._pool.fetch(
            """
            select
              notification_type::text as notification_type,
              count(*)::int as total,
              count(*) filter (where is_sent = true)::int as sent,
              count(*) filter (where is_sent = false)::int as pending
            from notifications
            group by notification_type
            order by total desc
            """
        )
        recent = await self._pool.fetch(
            """
            select created_at, properties::text as properties
            from admin_event_log
            where event_name = 'notification_failed'
            order by created_at desc
            limit 10
            """
        )
        created = totals["created_total"]
        sent = totals["sent_total"]
        stale = totals["failed_stale"]
        return NotificationsSummary(
            created_total=created,
            sent_total=sent,
            failed_total=stale + (failed_log or 0),
            failed_stale=stale,
            failed_log_7d=failed_log or 0,
            users_disabled=disabled or 0,
            by_type=[
                TypeCount(
                    notification_type=r["notification_type"],
                    total=r["total"],
                    sent=r["sent"],
                    pending=r["pending"],
                )
                for r in type_rows
            ],
            recent_failures=[
                (r["created_at"], r["properties"][:200]) for r in recent
            ],
        )
