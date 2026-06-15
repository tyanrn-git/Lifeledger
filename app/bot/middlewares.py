from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update, User as TgUser

from app.i18n import resolve_lang
from app.services.analytics_service import AnalyticsService
from app.services.user_service import UserService
from app.utils.language import lang_prefix


def _extract_tg_user(event: TelegramObject) -> TgUser | None:
    if isinstance(event, Update):
        if event.message:
            return event.message.from_user
        if event.callback_query:
            return event.callback_query.from_user
        if event.edited_message:
            return event.edited_message.from_user
        return None
    if isinstance(event, Message):
        return event.from_user
    if isinstance(event, CallbackQuery):
        return event.from_user
    return None


class ServicesMiddleware(BaseMiddleware):
    def __init__(self, services: dict[str, Any]) -> None:
        self._services = services

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data.update(self._services)
        return await handler(event, data)


class UserContextMiddleware(BaseMiddleware):
    def __init__(
        self,
        user_service: UserService,
        analytics_service: AnalyticsService | None = None,
    ) -> None:
        self._user_service = user_service
        self._analytics = analytics_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = _extract_tg_user(event)
        if tg_user:
            user, is_new = await self._user_service.get_or_create_user(tg_user)
            data["user"] = user
            data["user_id"] = user.id
            data["lang"] = resolve_lang(tg_user.language_code)
            data["content_lang"] = lang_prefix(user.language_code)
            if self._analytics:
                self._analytics.track_background("user_seen", user.id)
                if is_new:
                    self._analytics.track_background(
                        "user_registered",
                        user.id,
                        telegram_id=tg_user.id,
                    )

        return await handler(event, data)
