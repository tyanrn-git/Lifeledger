import logging
from typing import TYPE_CHECKING
from uuid import UUID

from aiogram import Bot

from app.db.repositories.events import EventsRepository
from app.db.repositories.notifications import NotificationsRepository
from app.db.repositories.users import UsersRepository
from app.i18n import resolve_lang, t

logger = logging.getLogger(__name__)

NEW_RATINGS_DEBOUNCE_HOURS = 1

if TYPE_CHECKING:
    from app.services.analytics_service import AnalyticsService


class NotificationService:
    def __init__(
        self,
        notifications_repo: NotificationsRepository,
        users_repo: UsersRepository,
        events_repo: EventsRepository,
        bot: Bot,
        analytics_service: "AnalyticsService | None" = None,
    ) -> None:
        self._notifications = notifications_repo
        self._users = users_repo
        self._events = events_repo
        self._bot = bot
        self._analytics = analytics_service

    async def on_event_rated(self, event_id: UUID) -> None:
        meta = await self._events.get_notification_meta(event_id)
        if not meta or meta.author_user_id is None:
            return

        author = await self._users.get_by_id(meta.author_user_id)
        if not author:
            return

        lang = resolve_lang(author.language_code)
        await self._maybe_notify_new_ratings(meta.author_user_id, event_id, lang)
        if meta.latest_rating_scope == "friend" and meta.friends_ratings_count == 1:
            await self._maybe_notify_first_friend_rating(meta.author_user_id, event_id, lang)

    async def _maybe_notify_new_ratings(
        self,
        user_id: UUID,
        event_id: UUID,
        lang: str,
    ) -> None:
        if await self._notifications.exists_recent(
            event_id, "new_ratings", NEW_RATINGS_DEBOUNCE_HOURS
        ):
            return

        body = t("notify_new_ratings", lang)
        await self._create_and_send(user_id, event_id, "new_ratings", body)

    async def _maybe_notify_first_friend_rating(
        self,
        user_id: UUID,
        event_id: UUID,
        lang: str,
    ) -> None:
        if await self._notifications.exists_for_event(event_id, "first_friend_rating"):
            return

        body = t("notify_first_friend_rating", lang)
        await self._create_and_send(user_id, event_id, "first_friend_rating", body)

    async def _create_and_send(
        self,
        user_id: UUID,
        event_id: UUID,
        notification_type: str,
        body: str,
    ) -> None:
        notification_id = await self._notifications.create(
            user_id, event_id, notification_type, body
        )
        if self._analytics:
            await self._analytics.track(
                "notification_created",
                user_id,
                notification_id=str(notification_id),
                notification_type=notification_type,
                event_id=str(event_id) if event_id else None,
            )
        await self._try_send(user_id, body, notification_id)

    async def _try_send(self, user_id: UUID, body: str, notification_id: UUID) -> None:
        user = await self._users.get_by_id(user_id)
        if not user or not user.notifications_enabled:
            return

        try:
            await self._bot.send_message(user.telegram_id, body)
            await self._notifications.mark_sent(notification_id)
            if self._analytics:
                await self._analytics.track(
                    "notification_sent",
                    user_id,
                    notification_id=str(notification_id),
                )
        except Exception as exc:
            logger.exception(
                "Failed to send notification %s to user %s",
                notification_id,
                user_id,
            )
            if self._analytics:
                await self._analytics.track(
                    "notification_failed",
                    user_id,
                    notification_id=str(notification_id),
                    error=str(exc),
                )
