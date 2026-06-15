import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import language_picker_keyboard, settings_keyboard
from app.i18n import t
from app.services.analytics_service import AnalyticsService
from app.services.user_service import UserService
from app.utils.languages import language_display_name

logger = logging.getLogger(__name__)
router = Router()


def settings_text(enabled: bool, content_lang: str, ui_lang: str) -> str:
    status = t("settings_notifications_on", ui_lang) if enabled else t("settings_notifications_off", ui_lang)
    language = language_display_name(content_lang, ui_lang)
    return (
        f"{t('settings_title', ui_lang)}\n\n"
        f"{status}\n"
        f"{t('settings_content_language', ui_lang, language=language)}\n\n"
        f"{t('settings_ui_language_hint', ui_lang)}"
    )


async def _send_settings(message: Message, user_service: UserService, user_id, ui_lang: str) -> None:
    user = await user_service.get_user(user_id)
    if not user:
        return
    await message.answer(
        settings_text(user.notifications_enabled, user.language_code, ui_lang),
        reply_markup=settings_keyboard(user.notifications_enabled, ui_lang),
    )


async def _edit_settings(
    callback: CallbackQuery,
    user_service: UserService,
    user_id,
    ui_lang: str,
) -> None:
    if not callback.message:
        return
    user = await user_service.get_user(user_id)
    if not user:
        return
    await callback.message.edit_text(
        settings_text(user.notifications_enabled, user.language_code, ui_lang),
        reply_markup=settings_keyboard(user.notifications_enabled, ui_lang),
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, user_id, lang: str, user_service: UserService) -> None:
    await _send_settings(message, user_service, user_id, lang)


@router.callback_query(F.data == "settings:main")
async def settings_main(
    callback: CallbackQuery,
    user_id,
    lang: str,
    user_service: UserService,
) -> None:
    await _edit_settings(callback, user_service, user_id, lang)
    await callback.answer()


@router.callback_query(F.data == "settings:noop")
async def settings_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "settings:enable")
async def settings_enable(
    callback: CallbackQuery,
    user_id,
    lang: str,
    user_service: UserService,
    analytics_service: AnalyticsService,
) -> None:
    if not callback.message:
        await callback.answer()
        return

    await callback.answer()

    await user_service.set_notifications_enabled(user_id, True)
    analytics_service.track_background(
        "settings_notifications_changed",
        user_id,
        enabled=True,
    )
    await _edit_settings(callback, user_service, user_id, lang)


@router.callback_query(F.data == "settings:disable")
async def settings_disable(
    callback: CallbackQuery,
    user_id,
    lang: str,
    user_service: UserService,
    analytics_service: AnalyticsService,
) -> None:
    if not callback.message:
        await callback.answer()
        return

    await callback.answer()

    await user_service.set_notifications_enabled(user_id, False)
    analytics_service.track_background(
        "settings_notifications_changed",
        user_id,
        enabled=False,
    )
    await _edit_settings(callback, user_service, user_id, lang)


@router.callback_query(F.data.startswith("settings:lang:page:"))
async def settings_language_page(
    callback: CallbackQuery,
    user_id,
    lang: str,
    user_service: UserService,
) -> None:
    if not callback.message or not callback.data:
        await callback.answer()
        return

    try:
        page = int(callback.data.split(":", 3)[3])
    except ValueError:
        await callback.answer()
        return

    user = await user_service.get_user(user_id)
    if not user:
        await callback.answer()
        return

    await callback.message.edit_text(
        t("settings_pick_language", lang),
        reply_markup=language_picker_keyboard(page, user.language_code, lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:lang:set:"))
async def settings_language_set(
    callback: CallbackQuery,
    user_id,
    lang: str,
    user_service: UserService,
    analytics_service: AnalyticsService,
) -> None:
    if not callback.message or not callback.data:
        await callback.answer()
        return

    await callback.answer()

    code = callback.data.split(":", 3)[3]
    await user_service.set_content_language(user_id, code)
    analytics_service.track_background(
        "settings_language_changed",
        user_id,
        language_code=code,
    )
    await _edit_settings(callback, user_service, user_id, lang)
