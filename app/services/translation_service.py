import asyncio
import logging
from uuid import UUID

import asyncpg

from app.db.repositories.translations import TranslationsRepository
from app.services.ai_service import AIService
from app.utils.language import lang_prefix, languages_match

logger = logging.getLogger(__name__)


class TranslationService:
    def __init__(
        self,
        pool: asyncpg.Pool,
        translations_repo: TranslationsRepository,
        ai_service: AIService,
    ) -> None:
        self._pool = pool
        self._translations = translations_repo
        self._ai = ai_service
        self._inflight: set[tuple[UUID, str]] = set()

    async def get_display_text(self, event_id: UUID, target_language: str) -> str:
        row = await self._pool.fetchrow(
            """
            select normalized_text, original_language
            from events
            where id = $1 and is_deleted = false
            """,
            event_id,
        )
        if not row:
            return ""

        normalized_text = row["normalized_text"] or ""
        source_language = row["original_language"] or "en"
        target = lang_prefix(target_language)

        if languages_match(source_language, target) or not normalized_text:
            return normalized_text

        cached = await self._translations.get(event_id, target)
        if cached:
            return cached

        translated = await self._ai.translate_event(
            normalized_text, lang_prefix(source_language), target
        )
        await self._translations.save(event_id, target, translated)
        return translated

    def prefetch_display_text(self, event_id: UUID, target_language: str) -> None:
        target = lang_prefix(target_language)
        key = (event_id, target)
        if key in self._inflight:
            return
        self._inflight.add(key)

        async def _run() -> None:
            try:
                await self.get_display_text(event_id, target_language)
            except Exception:
                logger.exception("Failed to prefetch translation for event %s", event_id)
            finally:
                self._inflight.discard(key)

        asyncio.create_task(_run())
