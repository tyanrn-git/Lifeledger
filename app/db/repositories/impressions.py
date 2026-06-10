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
    ) -> None:
        if not event_ids:
            return
        await self._pool.executemany(
            """
            insert into event_impressions (event_id, user_id, batch_id, status, source_priority)
            values ($1, $2, $3, 'shown', $4)
            on conflict (event_id, user_id) do nothing
            """,
            [
                (event_id, user_id, batch_id, position)
                for position, event_id in enumerate(event_ids)
            ],
        )

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
