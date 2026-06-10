import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.rate import send_feed
from app.bot.keyboards import after_add_keyboard, event_type_keyboard, self_score_keyboard
from app.bot.states import AddEventStates
from app.bot.views import event_added_text
from app.i18n import t
from app.schemas.users import User
from app.services.event_service import EventService
from app.services.feed_service import FeedService
from app.services.translation_service import TranslationService

logger = logging.getLogger(__name__)
router = Router()


async def start_add_flow(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(AddEventStates.choosing_type)
    await message.answer(t("add_choose_type", lang), reply_markup=event_type_keyboard(lang))


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext, lang: str) -> None:
    await start_add_flow(message, state, lang)


@router.callback_query(F.data == "nav:add")
async def on_add_button(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    if callback.message:
        await start_add_flow(callback.message, state, lang)
    await callback.answer()


@router.callback_query(F.data == "add_cancel", StateFilter(AddEventStates))
async def on_add_cancel(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    if callback.message:
        await callback.message.answer(t("add_cancelled", lang))
    await callback.answer()


@router.message(Command("cancel"), StateFilter(AddEventStates))
async def cmd_cancel_add(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t("add_cancelled", lang))


@router.callback_query(F.data.startswith("add_type:"), AddEventStates.choosing_type)
async def on_choose_type(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    if not callback.data:
        await callback.answer()
        return

    event_type = callback.data.split(":", 1)[1]
    if event_type not in {"real", "hypothetical"}:
        await callback.answer()
        return

    await state.update_data(event_type=event_type)
    await state.set_state(AddEventStates.waiting_text)
    if callback.message:
        text_key = "add_enter_text_hypothetical" if event_type == "hypothetical" else "add_enter_text"
        await callback.message.answer(t(text_key, lang))
    await callback.answer()


@router.message(AddEventStates.waiting_text, F.text)
async def on_event_text(message: Message, state: FSMContext, lang: str) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer(t("add_text_empty", lang))
        return

    await state.update_data(original_text=text)
    await state.set_state(AddEventStates.waiting_self_score)
    await message.answer(t("add_self_score", lang), reply_markup=self_score_keyboard(lang))


@router.callback_query(F.data.startswith("add_score:"), AddEventStates.waiting_self_score)
async def on_self_score(
    callback: CallbackQuery,
    state: FSMContext,
    event_service: EventService,
    user_id: UUID,
    user: User,
    lang: str,
) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    try:
        score = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer()
        return

    if not (-10 <= score <= 10):
        await callback.answer()
        return

    data = await state.get_data()
    event_type = data.get("event_type")
    original_text = data.get("original_text")
    if not event_type or not original_text:
        await state.clear()
        await callback.answer(t("error_generic", lang), show_alert=True)
        return

    processing = await callback.message.answer(t("add_processing", lang))
    try:
        event = await event_service.create_event(
            author_id=user_id,
            event_type=event_type,
            original_text=original_text,
            original_language=user.language_code,
            self_score=score,
        )
    except Exception:
        logger.exception("Failed to create event")
        try:
            await processing.delete()
        except Exception:
            pass
        await callback.answer(t("error_generic", lang), show_alert=True)
        return

    try:
        await processing.delete()
    except Exception:
        pass
    await state.clear()
    await callback.message.answer(
        event_added_text(event, lang),
        reply_markup=after_add_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "nav:rate")
async def nav_rate(
    callback: CallbackQuery,
    feed_service: FeedService,
    translation_service: TranslationService,
    user_id: UUID,
    lang: str,
    content_lang: str,
) -> None:
    if callback.message:
        await send_feed(
            callback.message,
            user_id,
            lang,
            content_lang,
            feed_service,
            translation_service,
            show_batch_intro=True,
        )
    await callback.answer()
