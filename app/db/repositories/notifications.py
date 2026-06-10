from uuid import UUID

import asyncpg


class NotificationsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def exists_for_event(self, event_id: UUID, notification_type: str) -> bool:
        val = await self._pool.fetchval(
            """
            select 1 from notifications
            where event_id = $1 and notification_type = $2::notification_type
            limit 1
            """,
            event_id,
            notification_type,
        )
        return val is not None

    async def exists_recent(
        self,
        event_id: UUID,
        notification_type: str,
        hours: int,
    ) -> bool:
        val = await self._pool.fetchval(
            """
            select 1 from notifications
            where event_id = $1
              and notification_type = $2::notification_type
              and created_at > now() - make_interval(hours => $3)
            limit 1
            """,
            event_id,
            notification_type,
            hours,
        )
        return val is not None

    async def create(
        self,
        user_id: UUID,
        event_id: UUID,
        notification_type: str,
        body: str,
    ) -> UUID:
        return await self._pool.fetchval(
            """
            insert into notifications (user_id, event_id, notification_type, body)
            values ($1, $2, $3::notification_type, $4)
            returning id
            """,
            user_id,
            event_id,
            notification_type,
            body,
        )

    async def mark_sent(self, notification_id: UUID) -> None:
        await self._pool.execute(
            """
            update notifications
            set is_sent = true, sent_at = now()
            where id = $1
            """,
            notification_id,
        )
