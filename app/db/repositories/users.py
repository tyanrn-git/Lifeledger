from datetime import datetime, timezone
from uuid import UUID

import asyncpg
from aiogram.types import User as TelegramUser

from app.schemas.users import User
from app.utils.language import lang_prefix
from app.utils.languages import normalize_content_language


def _row_to_user(row: asyncpg.Record) -> User:
    return User(
        id=row["id"],
        telegram_id=row["telegram_id"],
        username=row["username"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        language_code=row["language_code"],
        notifications_enabled=row["notifications_enabled"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_seen_at=row["last_seen_at"],
    )


class UsersRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        row = await self._pool.fetchrow(
            "select * from users where telegram_id = $1",
            telegram_id,
        )
        return _row_to_user(row) if row else None

    async def get_or_create(self, tg_user: TelegramUser, default_language: str) -> tuple[User, bool]:
        existing = await self.get_by_telegram_id(tg_user.id)
        now = datetime.now(timezone.utc)
        language = normalize_content_language(
            tg_user.language_code or default_language,
            default=lang_prefix(default_language),
        )

        if existing:
            row = await self._pool.fetchrow(
                """
                update users
                set username = $2,
                    first_name = $3,
                    last_name = $4,
                    last_seen_at = $5,
                    updated_at = $5
                where telegram_id = $1
                returning *
                """,
                tg_user.id,
                tg_user.username,
                tg_user.first_name,
                tg_user.last_name,
                now,
            )
            return _row_to_user(row), False

        row = await self._pool.fetchrow(
            """
            insert into users (
              telegram_id, username, first_name, last_name,
              language_code, last_seen_at
            )
            values ($1, $2, $3, $4, $5, $6)
            returning *
            """,
            tg_user.id,
            tg_user.username,
            tg_user.first_name,
            tg_user.last_name,
            language,
            now,
        )
        return _row_to_user(row), True

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._pool.fetchrow("select * from users where id = $1", user_id)
        return _row_to_user(row) if row else None

    async def set_language_code(self, user_id: UUID, language_code: str) -> None:
        await self._pool.execute(
            """
            update users
            set language_code = $2, updated_at = now()
            where id = $1
            """,
            user_id,
            language_code,
        )

    async def set_notifications_enabled(self, user_id: UUID, enabled: bool) -> None:
        await self._pool.execute(
            """
            update users
            set notifications_enabled = $2, updated_at = now()
            where id = $1
            """,
            user_id,
            enabled,
        )
