from uuid import UUID

import asyncpg


class TranslationsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, event_id: UUID, language_code: str) -> str | None:
        return await self._pool.fetchval(
            """
            select translated_text from event_translations
            where event_id = $1 and language_code = $2
            """,
            event_id,
            language_code,
        )

    async def save(self, event_id: UUID, language_code: str, translated_text: str) -> None:
        await self._pool.execute(
            """
            insert into event_translations (event_id, language_code, translated_text)
            values ($1, $2, $3)
            on conflict (event_id, language_code)
            do update set translated_text = excluded.translated_text, updated_at = now()
            """,
            event_id,
            language_code,
            translated_text,
        )
