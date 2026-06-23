import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, ErrorEvent, Message, TelegramObject, Update, User as TgUser

from app.i18n import resolve_lang, t
from app.schemas.users import User
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


_USER_CACHE_TTL_SEC = 45.0
logger = logging.getLogger(__name__)


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
        self._user_cache: dict[int, tuple[User, float]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = _extract_tg_user(event)
        if tg_user:
            is_new = False
            cached = self._user_cache.get(tg_user.id)
            now = time.monotonic()
            if cached and now - cached[1] < _USER_CACHE_TTL_SEC:
                user = cached[0]
            else:
                user, is_new = await self._user_service.get_or_create_user(tg_user)
                self._user_cache[tg_user.id] = (user, now)
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


async def on_dispatcher_error(event: ErrorEvent) -> bool:
    logger.exception("Unhandled bot error: %s", event.exception)
    update = event.update
    lang = "ru"
    if update.callback_query and update.callback_query.from_user:
        lang = resolve_lang(update.callback_query.from_user.language_code)
    elif update.message and update.message.from_user:
        lang = resolve_lang(update.message.from_user.language_code)

    try:
        if update.callback_query:
            if update.callback_query.message:
                await update.callback_query.answer()
                await update.callback_query.message.answer(t("error_generic", lang))
            else:
                await update.callback_query.answer()
        elif update.message:
            await update.message.answer(t("error_generic", lang))
    except Exception:
        logger.exception("Failed to notify user about bot error")
    return True
