import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    FRIENDS_PICK_REQUEST_ID,
    friends_incoming_keyboard,
    friends_main_keyboard,
    friends_pick_cancel_keyboard,
    friends_pick_user_keyboard,
    invite_confirm_keyboard,
)
from app.config import settings
from app.i18n import resolve_lang, t
from app.schemas.users import User
from app.services.friendship_service import (
    AlreadyFriendsError,
    FriendshipService,
    SelfInviteError,
)

logger = logging.getLogger(__name__)
router = Router()

_PICK_CANCEL_TEXTS = {"✖ Отмена", "✖ Cancel"}


async def send_friends_screen(
    message: Message,
    user_id: UUID,
    lang: str,
    friendship_service: FriendshipService,
) -> None:
    count = await friendship_service.count_friends(user_id)
    pending = await friendship_service.list_pending_incoming(user_id)
    await message.answer(
        t("friends_screen", lang, count=count),
        reply_markup=friends_main_keyboard(lang, len(pending)),
    )


async def send_invite_confirm(
    message: Message,
    friendship_id: UUID,
    lang: str,
) -> None:
    await message.answer(
        t("friends_invite_prompt", lang),
        reply_markup=invite_confirm_keyboard(friendship_id, lang),
    )


@router.message(Command("friends"))
async def cmd_friends(
    message: Message,
    user_id: UUID,
    lang: str,
    friendship_service: FriendshipService,
) -> None:
    await send_friends_screen(message, user_id, lang, friendship_service)


@router.callback_query(F.data == "friends:main")
async def friends_main(
    callback: CallbackQuery,
    user_id: UUID,
    lang: str,
    friendship_service: FriendshipService,
) -> None:
    if not callback.message:
        await callback.answer()
        return
    count = await friendship_service.count_friends(user_id)
    pending = await friendship_service.list_pending_incoming(user_id)
    await callback.message.edit_text(
        t("friends_screen", lang, count=count),
        reply_markup=friends_main_keyboard(lang, len(pending)),
    )
    await callback.answer()


@router.callback_query(F.data == "friends:pick")
async def friends_pick(
    callback: CallbackQuery,
    lang: str,
) -> None:
    if not callback.message:
        await callback.answer()
        return
    await callback.message.answer(
        t("friends_pick_prompt", lang),
        reply_markup=friends_pick_user_keyboard(lang),
    )
    await callback.answer()


@router.message(F.text.in_(_PICK_CANCEL_TEXTS))
async def friends_pick_cancel(message: Message, lang: str) -> None:
    await message.answer(
        t("friends_pick_cancelled", lang),
        reply_markup=friends_pick_cancel_keyboard(),
    )


@router.message(F.users_shared)
async def friends_user_shared(
    message: Message,
    user_id: UUID,
    lang: str,
    friendship_service: FriendshipService,
) -> None:
    shared = message.users_shared
    if not shared or shared.request_id != FRIENDS_PICK_REQUEST_ID or not shared.users:
        return

    picked = shared.users[0]
    name = picked.first_name or picked.username or "User"

    if message.from_user and picked.user_id == message.from_user.id:
        await message.answer(
            t("friends_self_invite", lang),
            reply_markup=friends_pick_cancel_keyboard(),
        )
        return

    try:
        result = await friendship_service.create_invite_from_picker(
            user_id,
            telegram_id=picked.user_id,
            username=picked.username,
            first_name=picked.first_name,
            last_name=picked.last_name,
            default_language=settings.default_language,
        )
    except SelfInviteError:
        await message.answer(
            t("friends_self_invite", lang),
            reply_markup=friends_pick_cancel_keyboard(),
        )
        return
    except AlreadyFriendsError:
        await message.answer(
            t("friends_pick_accepted", lang, name=name),
            reply_markup=friends_pick_cancel_keyboard(),
        )
        return
    except Exception:
        logger.exception("friends picker failed inviter=%s picked=%s", user_id, picked.user_id)
        await message.answer(t("error_generic", lang), reply_markup=friends_pick_cancel_keyboard())
        return
    invitee_lang = resolve_lang(result.invitee.language_code)

    if result.friendship.status == "accepted":
        await message.answer(
            t("friends_pick_accepted", lang, name=name),
            reply_markup=friends_pick_cancel_keyboard(),
        )
        return

    try:
        await message.bot.send_message(
            result.invitee.telegram_id,
            f"{t('friends_invite_incoming', invitee_lang)}\n\n{t('friends_invite_prompt', invitee_lang)}",
            reply_markup=invite_confirm_keyboard(result.friendship.id, invitee_lang),
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        logger.warning(
            "cannot message picked user inviter=%s invitee_tg=%s",
            user_id,
            result.invitee.telegram_id,
        )
        await message.answer(
            t("friends_pick_failed", lang, name=name),
            reply_markup=friends_pick_cancel_keyboard(),
        )
        return

    await message.answer(
        t("friends_pick_sent", lang, name=name),
        reply_markup=friends_pick_cancel_keyboard(),
    )


@router.callback_query(F.data == "friends:invite")
async def friends_invite(
    callback: CallbackQuery,
    user_id: UUID,
    lang: str,
    friendship_service: FriendshipService,
) -> None:
    link = friendship_service.build_invite_link(user_id)
    if callback.message:
        await callback.message.answer(t("friends_invite_link", lang, link=link))
    await callback.answer()


@router.callback_query(F.data == "friends:incoming")
async def friends_incoming(
    callback: CallbackQuery,
    user_id: UUID,
    lang: str,
    friendship_service: FriendshipService,
) -> None:
    if not callback.message:
        await callback.answer()
        return

    pending = await friendship_service.list_pending_incoming(user_id)
    if not pending:
        await callback.answer(t("friends_incoming_empty", lang), show_alert=True)
        return

    text = t("friends_incoming_title", lang, count=len(pending))
    await callback.message.edit_text(
        text,
        reply_markup=friends_incoming_keyboard([p.id for p in pending], lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("friend:accept:"))
async def friend_accept(
    callback: CallbackQuery,
    user_id: UUID,
    lang: str,
    friendship_service: FriendshipService,
) -> None:
    friendship_id = UUID(callback.data.split(":", 2)[2])
    ok = await friendship_service.accept_friendship(friendship_id, user_id)
    if not ok:
        await callback.answer(t("error_generic", lang), show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(t("friends_accepted", lang))
    await callback.answer()


@router.callback_query(F.data.startswith("friend:reject:"))
async def friend_reject(
    callback: CallbackQuery,
    user_id: UUID,
    lang: str,
    friendship_service: FriendshipService,
) -> None:
    friendship_id = UUID(callback.data.split(":", 2)[2])
    ok = await friendship_service.reject_friendship(friendship_id, user_id)
    if not ok:
        await callback.answer(t("error_generic", lang), show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(t("friends_rejected", lang))
    await callback.answer()


async def handle_invite_deep_link(
    message: Message,
    user: User,
    inviter_id: UUID,
    lang: str,
    friendship_service: FriendshipService,
) -> None:
    try:
        friendship = await friendship_service.create_invite_from_link(inviter_id, user.id)
    except SelfInviteError:
        await message.answer(t("friends_self_invite", lang))
        return
    except AlreadyFriendsError:
        await message.answer(t("friends_already", lang))
        return
    except Exception:
        logger.exception("invite deep link failed inviter=%s invitee=%s", inviter_id, user.id)
        await message.answer(t("friends_invalid_link", lang))
        return

    if friendship.status == "accepted":
        await message.answer(t("friends_accepted", lang))
        return

    await send_invite_confirm(message, friendship.id, lang)
