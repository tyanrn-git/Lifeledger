from uuid import UUID

from aiogram.types import User as TelegramUser

from app.config import settings
from app.db.repositories.users import UsersRepository
from app.schemas.users import User
from app.utils.languages import normalize_content_language


class UserService:
    def __init__(self, users_repo: UsersRepository) -> None:
        self._users = users_repo

    async def get_or_create_user(self, tg_user: TelegramUser) -> tuple[User, bool]:
        return await self._users.get_or_create(tg_user, settings.default_language)

    async def get_user(self, user_id: UUID) -> User | None:
        return await self._users.get_by_id(user_id)

    async def set_notifications_enabled(self, user_id: UUID, enabled: bool) -> None:
        await self._users.set_notifications_enabled(user_id, enabled)

    async def set_content_language(self, user_id: UUID, language_code: str) -> None:
        code = normalize_content_language(language_code)
        await self._users.set_language_code(user_id, code)
