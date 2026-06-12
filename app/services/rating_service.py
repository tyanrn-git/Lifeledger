from typing import TYPE_CHECKING
from uuid import UUID

import asyncpg

from app.db.repositories.events import EventsRepository
from app.db.repositories.friendships import FriendshipsRepository
from app.db.repositories.impressions import ImpressionsRepository
from app.db.repositories.ratings import RatingsRepository
from app.schemas.events import EventForRating
from app.utils.scoring import build_community_score_breakdown

if TYPE_CHECKING:
    from app.services.analytics_service import AnalyticsService


class RatingService:
    def __init__(
        self,
        pool: asyncpg.Pool,
        ratings_repo: RatingsRepository,
        impressions_repo: ImpressionsRepository,
        events_repo: EventsRepository,
        friendships_repo: FriendshipsRepository,
        analytics_service: "AnalyticsService | None" = None,
    ) -> None:
        self._pool = pool
        self._ratings = ratings_repo
        self._impressions = impressions_repo
        self._events = events_repo
        self._friendships = friendships_repo
        self._analytics = analytics_service

    async def rate_event(self, user_id: UUID, event_id: UUID, score: int) -> EventForRating:
        if not (-10 <= score <= 10):
            raise ValueError("Score out of range")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                author_id = await conn.fetchval(
                    "select author_user_id from events where id = $1 and is_deleted = false",
                    event_id,
                )
                if author_id == user_id:
                    raise PermissionError("own_event")

                already = await conn.fetchval(
                    "select 1 from ratings where event_id = $1 and rater_user_id = $2",
                    event_id,
                    user_id,
                )
                if already:
                    raise ValueError("already_rated")

                rating_scope = "community"
                if author_id is not None:
                    is_friend = await conn.fetchval(
                        """
                        select 1 from friendships
                        where status = 'accepted'
                          and (
                            (requester_user_id = $1 and addressee_user_id = $2)
                            or (requester_user_id = $2 and addressee_user_id = $1)
                          )
                        """,
                        user_id,
                        author_id,
                    )
                    if is_friend:
                        rating_scope = "friend"

                await conn.execute(
                    """
                    insert into ratings (event_id, rater_user_id, rating_scope, score)
                    values ($1, $2, $3::rating_scope, $4)
                    """,
                    event_id,
                    user_id,
                    rating_scope,
                    score,
                )
                await conn.execute(
                    """
                    update event_impressions
                    set status = 'rated', rated_at = now()
                    where user_id = $1 and event_id = $2
                    """,
                    user_id,
                    event_id,
                )
                await self._recalculate_event_scores(event_id, conn)

        if self._analytics:
            await self._analytics.track(
                "event_rated",
                user_id,
                event_id=str(event_id),
                score=score,
                rating_scope=rating_scope,
            )

        event = await self._events.get_for_rating(event_id)
        if not event:
            raise LookupError("event_not_found")
        return event

    async def skip_event(self, user_id: UUID, event_id: UUID) -> None:
        batch_id, feed_tier = await self._impressions.get_impression_meta(user_id, event_id)
        await self._impressions.mark_skipped(user_id, event_id)
        if self._analytics:
            props: dict = {"event_id": str(event_id)}
            if batch_id:
                props["batch_id"] = str(batch_id)
            if feed_tier is not None:
                props["feed_tier"] = feed_tier
            await self._analytics.track("event_skipped", user_id, **props)

    async def _recalculate_event_scores(self, event_id: UUID, conn: asyncpg.Connection) -> None:
        row = await conn.fetchrow(
            """
            select
              count(*)::int as total_count,
              count(*) filter (where rating_scope = 'community')::int as community_count,
              count(*) filter (where rating_scope = 'friend')::int as friends_count,
              avg(score) filter (where rating_scope = 'community')::numeric(5,2)
                as community_user_score,
              avg(score) filter (where rating_scope = 'friend')::numeric(5,2) as friends_score
            from ratings
            where event_id = $1
            """,
            event_id,
        )

        ai_score = await conn.fetchval("select ai_score from events where id = $1", event_id)
        ai_score_f = float(ai_score) if ai_score is not None else None

        community_count = row["community_count"]
        community_user_score = (
            float(row["community_user_score"]) if community_count else None
        )
        friends_score = float(row["friends_score"]) if row["friends_count"] else None

        breakdown = build_community_score_breakdown(
            ai_score_f,
            community_user_score,
            community_count,
        )

        await conn.execute(
            """
            update events
            set community_user_score = $2,
                friends_score = $3,
                final_community_score = $4,
                community_ratings_count = $5,
                friends_ratings_count = $6,
                community_ai_weight = $7,
                community_user_weight = $8,
                updated_at = now()
            where id = $1
            """,
            event_id,
            breakdown.community_user_score,
            friends_score,
            breakdown.final_community_score,
            community_count,
            row["friends_count"],
            breakdown.ai_weight,
            breakdown.user_weight,
        )
