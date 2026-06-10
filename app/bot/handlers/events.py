import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import delete_confirm_keyboard, event_detail_keyboard, events_list_keyboard
from app.bot.views import event_detail_text, event_list_item_text, parse_uuid
from app.i18n import t
from app.services.event_service import EventService

logger = logging.getLogger(__name__)
router = Router()


async def show_events_list(message: Message, event_service: EventService, user_id: UUID, lang: str) -> None:
    events = await event_service.get_user_events(user_id)
    if not events:
        await message.answer(t("my_events_empty", lang))
        return

    lines = [t("my_events_title", lang), ""]
    for i, event in enumerate(events, start=1):
        lines.append(event_list_item_text(i, event, lang))
        lines.append("")

    await message.answer(
        "\n".join(lines).strip(),
        reply_markup=events_list_keyboard(events, lang),
    )


@router.message(Command("events"))
async def cmd_events(message: Message, event_service: EventService, user_id: UUID, lang: str) -> None:
    await show_events_list(message, event_service, user_id, lang)


@router.callback_query(F.data == "nav:events")
async def nav_events(callback: CallbackQuery, event_service: EventService, user_id: UUID, lang: str) -> None:
    if callback.message:
        await show_events_list(callback.message, event_service, user_id, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("event_open:"))
async def on_event_open(callback: CallbackQuery, event_service: EventService, user_id: UUID, lang: str) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    event_id = parse_uuid(callback.data.split(":", 1)[1])
    if event_id is None:
        await callback.answer()
        return

    event = await event_service.get_event_details(event_id, user_id)
    if not event:
        await callback.answer(t("event_not_found", lang), show_alert=True)
        return

    await callback.message.answer(
        event_detail_text(event, lang),
        reply_markup=event_detail_keyboard(event.id, lang),
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("event_delete:") & ~F.data.startswith("event_delete_confirm:")
)
async def on_event_delete_prompt(callback: CallbackQuery, user_id: UUID, lang: str) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    event_id = parse_uuid(callback.data.split(":", 1)[1])
    if event_id is None:
        await callback.answer()
        return

    await callback.message.answer(
        t("delete_confirm", lang),
        reply_markup=delete_confirm_keyboard(event_id, lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("event_delete_confirm:"))
async def on_event_delete_confirm(
    callback: CallbackQuery,
    event_service: EventService,
    user_id: UUID,
    lang: str,
) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    event_id = parse_uuid(callback.data.split(":", 1)[1])
    if event_id is None:
        await callback.answer()
        return

    deleted = await event_service.delete_event(event_id, user_id)
    if not deleted:
        await callback.answer(t("event_not_found", lang), show_alert=True)
        return

    await callback.message.answer(t("event_deleted", lang))
    await show_events_list(callback.message, event_service, user_id, lang)
    await callback.answer()
