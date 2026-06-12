from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True)
class BatchStats:
    batches_total: int
    batches_completed: int
    avg_batch_size: float | None
    median_batch_size: float | None
    pct_under_requested: float | None
    pct_under_10: float | None
    empty_feed_7d: int
    ai_gen_triggers_7d: int
    injections_total: int


@dataclass(frozen=True)
class TierRow:
    feed_tier: str
    status: str
    count: int


@dataclass(frozen=True)
class InjectionTierRow:
    feed_tier: str
    count: int


class FeedQueries:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def fetch_batch_stats(self) -> BatchStats:
        row = await self._pool.fetchrow(
            """
            select
              count(*)::int as batches_total,
              count(*) filter (where completed_at is not null)::int as batches_completed,
              avg(actual_size)::numeric(6,2) as avg_size,
              percentile_cont(0.5) within group (order by actual_size) as median_size,
              round(
                100.0 * count(*) filter (where actual_size < requested_size)
                / nullif(count(*), 0), 1
              ) as pct_under_requested,
              round(
                100.0 * count(*) filter (where actual_size < 10)
                / nullif(count(*), 0), 1
              ) as pct_under_10
            from rating_batches
            """
        )
        empty_feed = await self._pool.fetchval(
            """
            select count(*)::int from admin_event_log
            where event_name = 'feed_empty'
              and created_at >= current_date - interval '7 days'
            """
        )
        ai_triggers = await self._pool.fetchval(
            """
            select count(*)::int from admin_event_log
            where event_name = 'ai_generation_triggered'
              and created_at >= current_date - interval '7 days'
            """
        )
        injections = await self._pool.fetchval(
            """
            select count(*)::int from admin_event_log
            where event_name = 'event_injected_into_batch'
            """
        )
        return BatchStats(
            batches_total=row["batches_total"],
            batches_completed=row["batches_completed"],
            avg_batch_size=_f(row["avg_size"]),
            median_batch_size=_f(row["median_size"]),
            pct_under_requested=_f(row["pct_under_requested"]),
            pct_under_10=_f(row["pct_under_10"]),
            empty_feed_7d=empty_feed or 0,
            ai_gen_triggers_7d=ai_triggers or 0,
            injections_total=injections or 0,
        )

    async def fetch_tier_breakdown(self) -> list[TierRow]:
        rows = await self._pool.fetch(
            """
            select
              coalesce(feed_tier::text, 'null') as feed_tier,
              status::text as status,
              count(*)::int as cnt
            from event_impressions
            group by feed_tier, status
            order by feed_tier nulls last, status
            """
        )
        return [
            TierRow(feed_tier=r["feed_tier"], status=r["status"], count=r["cnt"])
            for r in rows
        ]

    async def fetch_injection_by_tier(self) -> list[InjectionTierRow]:
        rows = await self._pool.fetch(
            """
            select
              coalesce(properties->>'feed_tier', 'null') as feed_tier,
              count(*)::int as cnt
            from admin_event_log
            where event_name = 'event_injected_into_batch'
            group by 1
            order by cnt desc
            """
        )
        return [
            InjectionTierRow(feed_tier=r["feed_tier"], count=r["cnt"]) for r in rows
        ]


def _f(val) -> float | None:
    if val is None:
        return None
    return float(val)
