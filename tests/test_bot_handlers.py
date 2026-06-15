"""Bot handler tests — key user flows without real Telegram API."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.analytics.event_catalog import EVENT_NAMES
from app.bot.handlers.common import cmd_help
from app.bot.handlers.friends import cmd_friends
from app.bot.handlers.rate import send_feed
from app.bot.handlers.settings import settings_disable, settings_enable
from app.schemas.events import EventForRating
from app.services.feed_service import FeedStart
from tests.conftest import USER_ID

NOW = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)


def _message(text: str = "/help") -> MagicMock:
    message = MagicMock()
    message.text = text
    message.answer = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_cmd_help_ru():
    message = _message("/help")
    await cmd_help(message, lang="ru")
    message.answer.assert_awaited_once()
    text = message.answer.await_args.args[0]
    assert "LifeLedger" in text
    assert "оценивать" in text.lower()


@pytest.mark.asyncio
async def test_cmd_friends_empty_list():
    message = _message("/friends")
    friendship_service = MagicMock()
    friendship_service.list_friends = AsyncMock(return_value=[])
    friendship_service.list_pending_incoming = AsyncMock(return_value=[])
    friendship_service.build_invite_link = MagicMock(return_value="https://t.me/bot?start=invite_x")
    friendship_service.build_invite_share_url = MagicMock(return_value="https://t.me/share/url")

    await cmd_friends(message, USER_ID, "ru", friendship_service)
    message.answer.assert_awaited_once()
    assert "друз" in message.answer.await_args.args[0].lower() or "friend" in message.answer.await_args.args[0].lower()


@pytest.mark.asyncio
async def test_send_feed_empty():
    message = _message()
    feed_service = MagicMock()
    feed_service.start_or_resume = AsyncMock(
        return_value=FeedStart(batch_id=UUID(int=0), batch_size=0, is_new_batch=False, event=None)
    )
    translation_service = MagicMock()

    await send_feed(
        message,
        USER_ID,
        "ru",
        "ru",
        feed_service,
        translation_service,
        show_batch_intro=False,
    )
    message.answer.assert_awaited_once()
    assert message.answer.await_args.kwargs.get("reply_markup") is not None


@pytest.mark.asyncio
async def test_send_feed_with_event():
    event_id = uuid4()
    event = EventForRating(
        id=event_id,
        event_type="real",
        normalized_text="Test event text",
        final_community_score=Decimal("3.5"),
    )
    message = _message()
    feed_service = MagicMock()
    feed_service.start_or_resume = AsyncMock(
        return_value=FeedStart(
            batch_id=uuid4(),
            batch_size=5,
            is_new_batch=True,
            event=event,
        )
    )
    translation_service = MagicMock()
    translation_service.get_display_text = AsyncMock(return_value="Test event text")

    await send_feed(
        message,
        USER_ID,
        "ru",
        "ru",
        feed_service,
        translation_service,
        show_batch_intro=True,
    )
    assert message.answer.await_count == 2
    card_text = message.answer.await_args_list[-1].args[0]
    assert "Test event text" in card_text


@pytest.mark.asyncio
async def test_settings_enable_tracks_analytics():
    callback = MagicMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    user = MagicMock()
    user.notifications_enabled = False
    user.language_code = "ru"
    user_service = MagicMock()
    user_service.get_user = AsyncMock(return_value=user)
    user_service.set_notifications_enabled = AsyncMock()
    analytics = MagicMock()
    analytics.track_background = MagicMock()

    await settings_enable(callback, USER_ID, "ru", user_service, analytics)
    analytics.track_background.assert_called_once()
    assert analytics.track_background.call_args.args[0] == "settings_notifications_changed"


@pytest.mark.asyncio
async def test_settings_disable_tracks_analytics():
    callback = MagicMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    user = MagicMock()
    user.notifications_enabled = True
    user.language_code = "ru"
    user_service = MagicMock()
    user_service.get_user = AsyncMock(return_value=user)
    user_service.set_notifications_enabled = AsyncMock()
    analytics = MagicMock()
    analytics.track_background = MagicMock()

    await settings_disable(callback, USER_ID, "ru", user_service, analytics)
    analytics.track_background.assert_called_once()
    assert analytics.track_background.call_args.kwargs.get("enabled") is False


def test_event_catalog_matches_tracked_events():
    """Every event_name used in code should be in the catalog."""
    required = {
        "user_registered",
        "user_seen",
        "event_created",
        "event_deleted",
        "event_rated",
        "event_skipped",
        "feed_started",
        "feed_empty",
        "batch_created",
        "batch_completed",
        "event_shown",
        "event_injected_into_batch",
        "friend_invite_sent",
        "friendship_accepted",
        "friendship_rejected",
        "notification_created",
        "notification_sent",
        "notification_failed",
        "ai_generation_triggered",
        "ai_generation_completed",
        "ai_generation_failed",
        "settings_notifications_changed",
        "settings_language_changed",
    }
    assert required <= EVENT_NAMES
