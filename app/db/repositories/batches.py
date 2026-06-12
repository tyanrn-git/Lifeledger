from uuid import UUID

import asyncpg


class BatchesRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_active_batch(self, user_id: UUID) -> UUID | None:
        return await self._pool.fetchval(
            """
            select id from rating_batches
            where user_id = $1 and completed_at is null
            order by created_at desc
            limit 1
            """,
            user_id,
        )

    async def create_batch(self, user_id: UUID, requested_size: int, actual_size: int) -> UUID:
        return await self._pool.fetchval(
            """
            insert into rating_batches (user_id, requested_size, actual_size)
            values ($1, $2, $3)
            returning id
            """,
            user_id,
            requested_size,
            actual_size,
        )

    async def complete_batch(self, batch_id: UUID) -> None:
        await self._pool.execute(
            "update rating_batches set completed_at = now() where id = $1",
            batch_id,
        )

    async def list_users_with_active_batches(self) -> list[UUID]:
        rows = await self._pool.fetch(
            """
            select distinct user_id
            from rating_batches
            where completed_at is null
            """
        )
        return [row["user_id"] for row in rows]

    async def count_remaining(self, user_id: UUID, batch_id: UUID) -> int:
        return await self._pool.fetchval(
            """
            select count(*)::int
            from event_impressions
            where user_id = $1 and batch_id = $2 and status = 'shown'
            """,
            user_id,
            batch_id,
        ) or 0
