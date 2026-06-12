from uuid import UUID

import asyncpg


class ImpressionsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_batch_impressions(
        self,
        user_id: UUID,
        batch_id: UUID,
        event_ids: list[UUID],
        source_priorities: list[int] | None = None,
        feed_tiers: list[int] | None = None,
    ) -> None:
        if not event_ids:
            return
        if source_priorities is None:
            source_priorities = list(range(len(event_ids)))
        if feed_tiers is None:
            feed_tiers = [None] * len(event_ids)
        await self._pool.executemany(
            """
            insert into event_impressions (
              event_id, user_id, batch_id, status, source_priority, feed_tier
            )
            values ($1, $2, $3, 'shown', $4, $5)
            on conflict (event_id, user_id) do nothing
            """,
            [
                (event_id, user_id, batch_id, priority, tier)
                for event_id, priority, tier in zip(
                    event_ids, source_priorities, feed_tiers
                )
            ],
        )

    async def inject_into_batch(
        self,
        user_id: UUID,
        batch_id: UUID,
        event_id: UUID,
        source_priority: int,
        feed_tier: int | None = None,
    ) -> bool:
        result = await self._pool.execute(
            """
            insert into event_impressions (
              event_id, user_id, batch_id, status, source_priority, feed_tier
            )
            values ($1, $2, $3, 'shown', $4, $5)
            on conflict (event_id, user_id) do nothing
            """,
            event_id,
            user_id,
            batch_id,
            source_priority,
            feed_tier,
        )
        return result.endswith("1")

    async def get_impression_meta(
        self, user_id: UUID, event_id: UUID
    ) -> tuple[UUID | None, int | None]:
        row = await self._pool.fetchrow(
            """
            select batch_id, feed_tier
            from event_impressions
            where user_id = $1 and event_id = $2
            """,
            user_id,
            event_id,
        )
        if not row:
            return None, None
        return row["batch_id"], row["feed_tier"]

    async def is_in_batch(self, batch_id: UUID, event_id: UUID) -> bool:
        val = await self._pool.fetchval(
            """
            select 1 from event_impressions
            where batch_id = $1 and event_id = $2
            """,
            batch_id,
            event_id,
        )
        return val is not None

    async def get_next_shown(self, user_id: UUID, batch_id: UUID) -> UUID | None:
        return await self._pool.fetchval(
            """
            select event_id
            from event_impressions
            where user_id = $1 and batch_id = $2 and status = 'shown'
            order by source_priority nulls last, shown_at
            limit 1
            """,
            user_id,
            batch_id,
        )

    async def mark_rated(self, user_id: UUID, event_id: UUID) -> None:
        await self._pool.execute(
            """
            update event_impressions
            set status = 'rated', rated_at = now()
            where user_id = $1 and event_id = $2
            """,
            user_id,
            event_id,
        )

    async def mark_skipped(self, user_id: UUID, event_id: UUID) -> None:
        await self._pool.execute(
            """
            update event_impressions
            set status = 'skipped', skipped_at = now()
            where user_id = $1 and event_id = $2
            """,
            user_id,
            event_id,
        )

    async def get_batch_id(self, user_id: UUID, event_id: UUID) -> UUID | None:
        return await self._pool.fetchval(
            "select batch_id from event_impressions where user_id = $1 and event_id = $2",
            user_id,
            event_id,
        )

    async def has_impression(self, user_id: UUID, event_id: UUID) -> bool:
        val = await self._pool.fetchval(
            "select 1 from event_impressions where user_id = $1 and event_id = $2",
            user_id,
            event_id,
        )
        return val is not None
