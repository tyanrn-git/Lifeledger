from datetime import date, timedelta

import asyncpg


class DailyAggregatesService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def refresh_date(self, day: date) -> None:
        next_day = day + timedelta(days=1)
        await self._pool.execute(
            """
            insert into analytics_daily (
              date, new_users, active_users, events_created, ratings_count,
              ai_events_generated, feed_empty_count, batches_created, avg_batch_size
            )
            select
              $1::date,
              (select count(*)::int from users
               where created_at >= $1 and created_at < $2),
              (select count(distinct user_id)::int from admin_event_log
               where event_name = 'user_seen'
                 and created_at >= $1 and created_at < $2
                 and user_id is not null),
              (select count(*)::int from events
               where created_at >= $1 and created_at < $2 and is_deleted = false),
              (select count(*)::int from ratings
               where created_at >= $1 and created_at < $2),
              (select count(*)::int from events
               where source = 'ai_generated'::event_source
                 and created_at >= $1 and created_at < $2),
              (select count(*)::int from admin_event_log
               where event_name = 'feed_empty'
                 and created_at >= $1 and created_at < $2),
              (select count(*)::int from admin_event_log
               where event_name = 'batch_created'
                 and created_at >= $1 and created_at < $2),
              (select avg(actual_size)::numeric(6,2) from rating_batches
               where created_at >= $1 and created_at < $2)
            on conflict (date) do update set
              new_users = excluded.new_users,
              active_users = excluded.active_users,
              events_created = excluded.events_created,
              ratings_count = excluded.ratings_count,
              ai_events_generated = excluded.ai_events_generated,
              feed_empty_count = excluded.feed_empty_count,
              batches_created = excluded.batches_created,
              avg_batch_size = excluded.avg_batch_size
            """,
            day,
            next_day,
        )

    async def ensure_range(self, start: date, end: date) -> None:
        day = start
        while day <= end:
            await self.refresh_date(day)
            day += timedelta(days=1)
