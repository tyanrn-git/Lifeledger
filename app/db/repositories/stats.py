from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import asyncpg


@dataclass
class AuthorEventRow:
    self_score: int
    friends_score: Decimal | None
    final_community_score: Decimal | None
    event_date: datetime


@dataclass
class EvaluatorAggregateRow:
    rated_events_count: int
    user_average: Decimal | None
    community_average: Decimal | None


class StatsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_author_real_events(self, user_id: UUID) -> list[AuthorEventRow]:
        rows = await self._pool.fetch(
            """
            select
              self_score,
              friends_score,
              final_community_score,
              coalesce(event_time, created_at) as event_date
            from events
            where author_user_id = $1
              and is_deleted = false
              and event_type = 'real'
            order by coalesce(event_time, created_at)
            """,
            user_id,
        )
        return [
            AuthorEventRow(
                self_score=row["self_score"],
                friends_score=row["friends_score"],
                final_community_score=row["final_community_score"],
                event_date=row["event_date"],
            )
            for row in rows
        ]

    async def get_evaluator_aggregates(self, user_id: UUID) -> EvaluatorAggregateRow:
        row = await self._pool.fetchrow(
            """
            select
              count(*)::int as rated_events_count,
              avg(r.score)::numeric(5,2) as user_average,
              avg(e.final_community_score)::numeric(5,2) as community_average
            from ratings r
            join events e on e.id = r.event_id
            where r.rater_user_id = $1
              and e.is_deleted = false
            """,
            user_id,
        )
        count = row["rated_events_count"] if row else 0
        if count == 0:
            return EvaluatorAggregateRow(
                rated_events_count=0,
                user_average=None,
                community_average=None,
            )
        return EvaluatorAggregateRow(
            rated_events_count=count,
            user_average=row["user_average"],
            community_average=row["community_average"],
        )
