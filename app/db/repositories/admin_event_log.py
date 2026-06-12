import json
from uuid import UUID

import asyncpg


class AdminEventLogRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def insert(
        self,
        event_name: str,
        user_id: UUID | None = None,
        properties: dict | None = None,
    ) -> None:
        props = properties or {}
        await self._pool.execute(
            """
            insert into admin_event_log (user_id, event_name, properties)
            values ($1, $2, $3::jsonb)
            """,
            user_id,
            event_name,
            json.dumps(props, default=str),
        )
