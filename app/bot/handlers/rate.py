import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    batch_complete_keyboard,
    empty_feed_keyboard,
    next_event_keyboard,
    rating_keyboard,
)
from app.bot.views import event_card_text, parse_uuid, rating_result_text
from app.config import settings
from app.i18n import t
from app.db.repositories.impressions import ImpressionsRepository
from app.services.feed_service import FeedService
from app.services.notification_service import NotificationService
from app.services.rating_service import RatingService
from app.services.translation_service import TranslationService

logger = logging.getLogger(__name__)
router = Router()


async def _display_text(
    translation_service: TranslationService,
    event_id: UUID,
    content_lang: str,
) -> str:
    return await translation_service.get_display_text(event_id, content_lang)


async def send_feed(
    message: Message,
    user_id: UUID,
    lang: str,
    content_lang: str,
    feed_service: FeedService,
    translation_service: TranslationService,
    *,
    show_batch_intro: bool,
    force_new: bool = False,
) -> None:
    feed = await feed_service.start_or_resume(user_id, force_new=force_new)

    if feed.event is None:
        await message.answer(t("no_events", lang), reply_markup=empty_feed_keyboard(lang))
        return

    if show_batch_intro and feed.is_new_batch:
        await message.answer(t("batch_prepared", lang, count=feed.batch_size))

    display = await _display_text(translation_service, feed.event.id, content_lang)
    await message.answer(
        event_card_text(feed.event, lang, display),
        reply_markup=rating_keyboard(feed.event.id, lang),
    )


async def send_next_event(
    message: Message,
    user_id: UUID,
    batch_id: UUID,
    lang: str,
    content_lang: str,
    feed_service: FeedService,
    translation_service: TranslationService,
) -> None:
    event = await feed_service.get_next_in_batch(user_id, batch_id)
    if event is None:
        await message.answer(
            t("batch_complete", lang, size=settings.batch_size),
            reply_markup=batch_complete_keyboard(lang, settings.batch_size),
        )
        return

    display = await _display_text(translation_service, event.id, content_lang)
    await message.answer(
        event_card_text(event, lang, display),
        reply_markup=rating_keyboard(event.id, lang),
    )


@router.callback_query(F.data.startswith("rate:"))
async def on_rate(
    callback: CallbackQuery,
    rating_service: RatingService,
    notification_service: NotificationService,
    impressions_repo: ImpressionsRepository,
    user_id: UUID,
    lang: str,
) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer()
        return

    event_id = parse_uuid(parts[1])
    if event_id is None:
        await callback.answer()
        return

    try:
        score = int(parts[2])
    except ValueError:
        await callback.answer()
        return

    await callback.answer()

    try:
        event = await rating_service.rate_event(user_id, event_id, score)
    except PermissionError:
        await callback.message.answer(t("own_event", lang))
        return
    except ValueError as exc:
        if str(exc) == "already_rated":
            await callback.message.answer(t("already_rated", lang))
            return
        await callback.message.answer(t("error_generic", lang))
        return
    except Exception:
        logger.exception("Failed to rate event")
        await callback.message.answer(t("error_generic", lang))
        return

    try:
        await notification_service.on_event_rated(event_id)
    except Exception:
        logger.exception("Failed to notify author for event %s", event_id)

    batch_id = await impressions_repo.get_batch_id(user_id, event_id)
    keyboard = next_event_keyboard(lang, batch_id) if batch_id else None

    await callback.message.answer(
        rating_result_text(score, event, lang),
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("skip:"))
async def on_skip(
    callback: CallbackQuery,
    rating_service: RatingService,
    impressions_repo: ImpressionsRepository,
    feed_service: FeedService,
    translation_service: TranslationService,
    user_id: UUID,
    lang: str,
    content_lang: str,
) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    event_id = parse_uuid(callback.data.split(":", 1)[1])
    if event_id is None:
        await callback.answer()
        return

    await callback.answer()

    await rating_service.skip_event(user_id, event_id)
    batch_id = await impressions_repo.get_batch_id(user_id, event_id)

    await callback.message.answer(t("skipped", lang))
    if batch_id:
        await send_next_event(
            callback.message,
            user_id,
            batch_id,
            lang,
            content_lang,
            feed_service,
            translation_service,
        )


@router.callback_query(F.data.startswith("feed:next"))
async def on_feed_next(
    callback: CallbackQuery,
    feed_service: FeedService,
    translation_service: TranslationService,
    user_id: UUID,
    lang: str,
    content_lang: str,
) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    parts = callback.data.split(":", 2)
    batch_id = parse_uuid(parts[2]) if len(parts) == 3 else None
    if batch_id is None:
        await callback.answer()
        return

    await callback.answer()

    await send_next_event(
        callback.message,
        user_id,
        batch_id,
        lang,
        content_lang,
        feed_service,
        translation_service,
    )


@router.callback_query(F.data == "feed:new_batch")
async def on_new_batch(
    callback: CallbackQuery,
    feed_service: FeedService,
    translation_service: TranslationService,
    user_id: UUID,
    lang: str,
    content_lang: str,
) -> None:
    if not callback.message:
        await callback.answer()
        return

    await callback.answer()

    await send_feed(
        callback.message,
        user_id,
        lang,
        content_lang,
        feed_service,
        translation_service,
        show_batch_intro=True,
        force_new=True,
    )
