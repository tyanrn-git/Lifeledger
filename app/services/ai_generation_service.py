import logging
from uuid import uuid4

import asyncpg

from app.config import settings
from app.db.repositories.events import EventsRepository
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

_GENERATION_LOCK_KEY = 77341101


class AIGenerationService:
    def __init__(self, pool: asyncpg.Pool, events_repo: EventsRepository, ai_service: AIService) -> None:
        self._pool = pool
        self._events = events_repo
        self._ai = ai_service

    async def ensure_pool_for_user(self, user_id, target: int | None = None) -> int:
        need = target or settings.batch_size
        min_available = settings.ai_generation_min_available
        threshold = max(min_available, need)
        created_total = 0

        for _ in range(3):
            available = await self._events.count_available_for_user(user_id)
            if available >= threshold:
                return created_total

            batch_created = await self._generate_locked_batch(user_id)
            created_total += batch_created
            if batch_created == 0:
                break

        return created_total

    async def _generate_locked_batch(self, user_id) -> int:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "select pg_advisory_xact_lock($1)",
                    _GENERATION_LOCK_KEY,
                )
                avoid = await self._events.list_avoid_texts_for_user(
                    user_id, limit=40
                )
                global_avoid = await conn.fetch(
                    """
                    select normalized_text
                    from events
                    where source = 'ai_generated'::event_source
                      and is_deleted = false
                    order by created_at desc
                    limit 30
                    """
                )
                for row in global_avoid:
                    text = row["normalized_text"]
                    if text and text not in avoid:
                        avoid.append(text)

                batch = await self._ai.generate_event_batch(
                    avoid,
                    settings.ai_generation_batch_size,
                )
                if not batch.events:
                    logger.warning("AI returned empty event batch")
                    return 0

                batch_id = uuid4()
                created_ids = await self._events.create_ai_generated_batch(
                    batch.events,
                    batch_id,
                    conn=conn,
                )
                logger.info(
                    "AI generated %s events in batch %s for user %s",
                    len(created_ids),
                    batch_id,
                    user_id,
                )
                return len(created_ids)
