from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import asyncpg


@dataclass
class EventRatingAggregates:
    total_count: int
    community_count: int
    friends_count: int
    community_user_score: Decimal | None
    friends_score: Decimal | None


class RatingsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def exists(self, event_id: UUID, rater_user_id: UUID) -> bool:
        val = await self._pool.fetchval(
            "select 1 from ratings where event_id = $1 and rater_user_id = $2",
            event_id,
            rater_user_id,
        )
        return val is not None

    async def create(
        self,
        event_id: UUID,
        rater_user_id: UUID,
        score: int,
        rating_scope: str,
    ) -> None:
        await self._pool.execute(
            """
            insert into ratings (event_id, rater_user_id, rating_scope, score)
            values ($1, $2, $3::rating_scope, $4)
            """,
            event_id,
            rater_user_id,
            rating_scope,
            score,
        )

    async def get_event_aggregates(self, event_id: UUID) -> EventRatingAggregates:
        row = await self._pool.fetchrow(
            """
            select
              count(*)::int as total_count,
              count(*) filter (where rating_scope = 'community')::int as community_count,
              count(*) filter (where rating_scope = 'friend')::int as friends_count,
              avg(score)::numeric(5,2) as community_user_score,
              avg(score) filter (where rating_scope = 'friend')::numeric(5,2) as friends_score
            from ratings
            where event_id = $1
            """,
            event_id,
        )
        friends_score = row["friends_score"] if row["friends_count"] else None
        community_user_score = row["community_user_score"] if row["total_count"] else None
        return EventRatingAggregates(
            total_count=row["total_count"],
            community_count=row["community_count"],
            friends_count=row["friends_count"],
            community_user_score=community_user_score,
            friends_score=friends_score,
        )
