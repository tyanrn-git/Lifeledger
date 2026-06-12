from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

from app.utils.scoring import SCORING_CALIBRATION_VERSION


@dataclass(frozen=True)
class DisputedEvent:
    event_id: UUID
    preview: str
    ai_score: float | None
    community_user_score: float | None
    final_community_score: float | None
    community_ai_weight: float | None
    community_user_weight: float | None
    scoring_calibration_version: int
    community_ratings_count: int
    dispute_delta: float


@dataclass(frozen=True)
class GenerationStats:
    ai_events_total: int
    ai_events_7d: int
    triggers_7d: int
    failed_7d: int
    pending_rescore: int
    calibration_version: int


@dataclass(frozen=True)
class LogRow:
    created_at: datetime
    properties: str


@dataclass(frozen=True)
class AiSummary:
    disputed: list[DisputedEvent]
    stats: GenerationStats
    recent_failures: list[LogRow]
    ai_per_day_json: str


class AiQueries:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def fetch_summary(self) -> AiSummary:
        disputed_rows = await self._pool.fetch(
            """
            select
              id as event_id,
              left(coalesce(normalized_text, original_text), 80) as preview,
              ai_score, community_user_score, final_community_score,
              community_ai_weight, community_user_weight,
              scoring_calibration_version, community_ratings_count,
              abs(ai_score - community_user_score) as dispute_delta
            from events
            where is_deleted = false
              and community_ratings_count >= 5
              and ai_score is not null
              and community_user_score is not null
              and abs(ai_score - community_user_score) >= 3
            order by dispute_delta desc
            limit 30
            """
        )
        stats_row = await self._pool.fetchrow(
            """
            select
              (select count(*)::int from events
               where source = 'ai_generated'::event_source and is_deleted = false)
                as ai_events_total,
              (select count(*)::int from events
               where source = 'ai_generated'::event_source
                 and is_deleted = false
                 and created_at >= current_date - interval '7 days')
                as ai_events_7d,
              (select count(*)::int from admin_event_log
               where event_name = 'ai_generation_triggered'
                 and created_at >= current_date - interval '7 days')
                as triggers_7d,
              (select count(*)::int from admin_event_log
               where event_name = 'ai_generation_failed'
                 and created_at >= current_date - interval '7 days')
                as failed_7d,
              (select count(*)::int from events
               where is_deleted = false
                 and scoring_calibration_version < $1)
                as pending_rescore
            """,
            SCORING_CALIBRATION_VERSION,
        )
        fail_rows = await self._pool.fetch(
            """
            select created_at, properties::text as properties
            from admin_event_log
            where event_name = 'ai_generation_failed'
            order by created_at desc
            limit 10
            """
        )
        day_rows = await self._pool.fetch(
            """
            select date::text as day, ai_events_generated as value
            from analytics_daily
            where date >= current_date - interval '29 days'
            order by date
            """
        )
        import json

        return AiSummary(
            disputed=[
                DisputedEvent(
                    event_id=r["event_id"],
                    preview=r["preview"],
                    ai_score=_f(r["ai_score"]),
                    community_user_score=_f(r["community_user_score"]),
                    final_community_score=_f(r["final_community_score"]),
                    community_ai_weight=_f(r["community_ai_weight"]),
                    community_user_weight=_f(r["community_user_weight"]),
                    scoring_calibration_version=r["scoring_calibration_version"],
                    community_ratings_count=r["community_ratings_count"],
                    dispute_delta=float(r["dispute_delta"]),
                )
                for r in disputed_rows
            ],
            stats=GenerationStats(
                ai_events_total=stats_row["ai_events_total"],
                ai_events_7d=stats_row["ai_events_7d"],
                triggers_7d=stats_row["triggers_7d"],
                failed_7d=stats_row["failed_7d"],
                pending_rescore=stats_row["pending_rescore"],
                calibration_version=SCORING_CALIBRATION_VERSION,
            ),
            recent_failures=[
                LogRow(created_at=r["created_at"], properties=r["properties"][:200])
                for r in fail_rows
            ],
            ai_per_day_json=json.dumps(
                [{"day": r["day"], "value": r["value"] or 0} for r in day_rows]
            ),
        )


def _f(val) -> float | None:
    if val is None:
        return None
    return float(val)
