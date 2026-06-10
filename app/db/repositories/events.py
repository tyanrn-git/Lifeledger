from datetime import datetime
from uuid import UUID

import asyncpg

from app.schemas.events import Event, EventForRating
from app.schemas.notifications import EventNotificationMeta


def _row_to_event(row: asyncpg.Record) -> Event:
    return Event(
        id=row["id"],
        author_user_id=row["author_user_id"],
        event_type=row["event_type"],
        original_text=row["original_text"],
        normalized_text=row["normalized_text"] or row["original_text"],
        self_score=row["self_score"],
        friends_score=row["friends_score"],
        final_community_score=row["final_community_score"],
    )


class EventsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        author_id: UUID,
        event_type: str,
        original_text: str,
        original_language: str,
        normalized_text: str,
        self_score: int,
        ai_score: float,
        final_community_score: float,
        event_time: datetime | None = None,
        action_text: str | None = None,
        context_text: str | None = None,
        category: str | None = None,
    ) -> Event:
        row = await self._pool.fetchrow(
            """
            insert into events (
              author_user_id, event_type, original_text, original_language,
              normalized_text, self_score, ai_score, final_community_score,
              event_time, action_text, context_text, category
            )
            values ($1, $2::event_type, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            returning *
            """,
            author_id,
            event_type,
            original_text,
            original_language,
            normalized_text,
            self_score,
            ai_score,
            final_community_score,
            event_time,
            action_text,
            context_text,
            category,
        )
        return _row_to_event(row)

    async def get_for_author(self, event_id: UUID, author_id: UUID) -> Event | None:
        row = await self._pool.fetchrow(
            """
            select * from events
            where id = $1 and author_user_id = $2 and is_deleted = false
            """,
            event_id,
            author_id,
        )
        return _row_to_event(row) if row else None

    async def list_by_author(self, author_id: UUID) -> list[Event]:
        rows = await self._pool.fetch(
            """
            select * from events
            where author_user_id = $1 and is_deleted = false
            order by created_at desc
            """,
            author_id,
        )
        return [_row_to_event(row) for row in rows]

    async def update_scores(
        self,
        event_id: UUID,
        *,
        community_user_score: float | None,
        friends_score: float | None,
        final_community_score: float | None,
        community_ratings_count: int,
        friends_ratings_count: int,
    ) -> None:
        await self._pool.execute(
            """
            update events
            set community_user_score = $2,
                friends_score = $3,
                final_community_score = $4,
                community_ratings_count = $5,
                friends_ratings_count = $6,
                updated_at = now()
            where id = $1
            """,
            event_id,
            community_user_score,
            friends_score,
            final_community_score,
            community_ratings_count,
            friends_ratings_count,
        )

    async def get_ai_score(self, event_id: UUID) -> float | None:
        val = await self._pool.fetchval(
            "select ai_score from events where id = $1",
            event_id,
        )
        return float(val) if val is not None else None

    async def soft_delete(self, event_id: UUID, author_id: UUID) -> bool:
        result = await self._pool.execute(
            """
            update events
            set is_deleted = true,
                deleted_at = now(),
                author_user_id = null,
                anonymized_after_delete = true
            where id = $1 and author_user_id = $2 and is_deleted = false
            """,
            event_id,
            author_id,
        )
        return result.endswith("1")

    async def get_notification_meta(self, event_id: UUID) -> EventNotificationMeta | None:
        row = await self._pool.fetchrow(
            """
            select
              e.author_user_id,
              e.friends_ratings_count,
              r.rating_scope::text as latest_rating_scope
            from events e
            left join lateral (
              select rating_scope
              from ratings
              where event_id = e.id
              order by created_at desc
              limit 1
            ) r on true
            where e.id = $1 and e.is_deleted = false
            """,
            event_id,
        )
        if not row:
            return None
        return EventNotificationMeta(
            author_user_id=row["author_user_id"],
            friends_ratings_count=row["friends_ratings_count"],
            latest_rating_scope=row["latest_rating_scope"],
        )

    async def get_for_rating(self, event_id: UUID) -> EventForRating | None:
        row = await self._pool.fetchrow(
            """
            select id, event_type::text, normalized_text, final_community_score
            from events
            where id = $1 and is_deleted = false
            """,
            event_id,
        )
        if not row:
            return None
        return EventForRating(
            id=row["id"],
            event_type=row["event_type"],
            normalized_text=row["normalized_text"] or "",
            final_community_score=row["final_community_score"],
        )

    async def fetch_available_for_user(
        self,
        user_id: UUID,
        limit: int,
        under_rated_threshold: int,
    ) -> list[UUID]:
        rows = await self._pool.fetch(
            """
            select e.id
            from events e
            where e.is_deleted = false
              and (e.author_user_id is null or e.author_user_id <> $1)
              and not exists (
                select 1 from event_impressions ei
                where ei.event_id = e.id and ei.user_id = $1
              )
            order by
              case
                when e.author_user_id is not null and exists (
                  select 1 from friendships f
                  where f.status = 'accepted'
                    and (
                      (f.requester_user_id = $1 and f.addressee_user_id = e.author_user_id)
                      or (f.addressee_user_id = $1 and f.requester_user_id = e.author_user_id)
                    )
                ) then 0
                else 1
              end,
              case when e.community_ratings_count <= $3 then 0 else 1 end,
              e.created_at desc
            limit $2
            """,
            user_id,
            limit,
            under_rated_threshold,
        )
        return [row["id"] for row in rows]
