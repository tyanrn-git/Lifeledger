from datetime import datetime
from uuid import UUID

import asyncpg

from app.schemas.ai import GeneratedEventDraft
from app.schemas.events import Event, EventForRating
from app.schemas.notifications import EventNotificationMeta
from app.utils.content_hash import content_hash as make_content_hash
from app.utils.scoring import SCORING_CALIBRATION_VERSION


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
        text_hash = make_content_hash(normalized_text)
        row = await self._pool.fetchrow(
            """
            insert into events (
              author_user_id, event_type, original_text, original_language,
              normalized_text, self_score, ai_score, final_community_score,
              event_time, action_text, context_text, category,
              source, content_hash,
              community_ai_weight, community_user_weight, scoring_calibration_version
            )
            values (
              $1, $2::event_type, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
              'user'::event_source, $13,
              1.0, 0.0, $14
            )
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
            text_hash,
            SCORING_CALIBRATION_VERSION,
        )
        return _row_to_event(row)

    async def create_ai_generated_batch(
        self,
        drafts: list[GeneratedEventDraft],
        generation_batch_id: UUID,
        *,
        conn: asyncpg.Connection | None = None,
    ) -> list[UUID]:
        if not drafts:
            return []

        executor = conn if conn is not None else self._pool
        created: list[UUID] = []
        for draft in drafts:
            text = draft.normalized_text.strip()
            if not text:
                continue
            text_hash = make_content_hash(text)
            exists = await executor.fetchval(
                "select 1 from events where content_hash = $1 and is_deleted = false limit 1",
                text_hash,
            )
            if exists:
                continue

            ai_score = float(draft.ai_score)
            self_score = int(draft.ai_score)
            row = await executor.fetchrow(
                """
                insert into events (
                  author_user_id, event_type, original_text, original_language,
                  normalized_text, self_score, ai_score, final_community_score,
                  action_text, context_text, category,
                  source, generation_batch_id, content_hash,
                  community_ai_weight, community_user_weight, scoring_calibration_version
                )
                values (
                  null, 'hypothetical'::event_type, $1, 'en', $1, $2, $3, $3,
                  $4, $5, $6,
                  'ai_generated'::event_source, $7, $8,
                  1.0, 0.0, $9
                )
                returning id
                """,
                text,
                self_score,
                ai_score,
                draft.action,
                draft.context,
                draft.category,
                generation_batch_id,
                text_hash,
                SCORING_CALIBRATION_VERSION,
            )
            if row:
                created.append(row["id"])
        return created

    async def count_available_for_user(self, user_id: UUID) -> int:
        val = await self._pool.fetchval(
            """
            select count(*)::int
            from events e
            where e.is_deleted = false
              and (e.author_user_id is null or e.author_user_id <> $1)
              and not exists (
                select 1 from event_impressions ei
                where ei.event_id = e.id and ei.user_id = $1
              )
              and not exists (
                select 1
                from event_impressions ei2
                join events e2 on e2.id = ei2.event_id
                where ei2.user_id = $1
                  and e.content_hash is not null
                  and e2.content_hash = e.content_hash
              )
            """,
            user_id,
        )
        return val or 0

    async def list_avoid_texts_for_user(self, user_id: UUID, limit: int = 40) -> list[str]:
        rows = await self._pool.fetch(
            """
            select e.normalized_text
            from event_impressions ei
            join events e on e.id = ei.event_id
            where ei.user_id = $1
              and e.normalized_text is not null
            group by e.normalized_text
            order by max(ei.shown_at) desc
            limit $2
            """,
            user_id,
            limit,
        )
        return [row["normalized_text"] for row in rows]

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
              and not exists (
                select 1
                from event_impressions ei2
                join events e2 on e2.id = ei2.event_id
                where ei2.user_id = $1
                  and e.content_hash is not null
                  and e2.content_hash = e.content_hash
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
              case
                when e.author_user_id is not null and exists (
                  select 1 from friendships f
                  where f.status = 'accepted'
                    and (
                      (f.requester_user_id = $1 and f.addressee_user_id = e.author_user_id)
                      or (f.addressee_user_id = $1 and f.requester_user_id = e.author_user_id)
                    )
                ) then 0
                when e.community_ratings_count <= $3 then 0
                else 1
              end,
              e.created_at desc
            limit $2
            """,
            user_id,
            limit,
            under_rated_threshold,
        )
        return [row["id"] for row in rows]
