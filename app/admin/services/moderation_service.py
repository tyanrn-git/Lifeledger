from uuid import UUID

import asyncpg


class ModerationService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def set_feed_hidden(
        self,
        event_id: UUID,
        hidden: bool,
        comment: str | None = None,
    ) -> bool:
        row = await self._pool.fetchrow(
            """
            update events
            set is_feed_hidden = $2
            where id = $1 and is_deleted = false
            returning id
            """,
            event_id,
            hidden,
        )
        if not row:
            return False

        action = "hide_event" if hidden else "unhide_event"
        await self._pool.execute(
            """
            insert into admin_action_log (action, target_type, target_id, comment)
            values ($1, 'event', $2, $3)
            """,
            action,
            event_id,
            (comment or "").strip() or None,
        )
        return True
