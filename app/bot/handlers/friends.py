import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.keyboards import (
    friends_incoming_keyboard,
    friends_main_keyboard,
    invite_confirm_keyboard,
)
from app.i18n import t
from app.schemas.users import User
from app.schemas.friendships import FriendProfile, PendingFriendInvite
from app.services.friendship_service import (
    AlreadyFriendsError,
    FriendshipService,
    SelfInviteError,
)
from app.utils.user_display import format_user_display_name

logger = logging.getLogger(__name__)
router = Router()


def _format_name_list(profiles: list[FriendProfile], lang: str) -> str:
    if not profiles:
        return t("friends_none", lang)
    return "\n".join(
        f"• {format_user_display_name(first_name=p.first_name, last_name=p.last_name, username=p.username, lang=lang)}"
        for p in profiles
    )


def _friends_screen_text(
    lang: str,
    friends: list[FriendProfile],
) -> str:
    return t(
        "friends_screen",
        lang,
        count=len(friends),
        names=_format_name_list(friends, lang),
    )


def _incoming_screen_text(
    lang: str,
    invites: list[PendingFriendInvite],
) -> str:
    names = "\n".join(
        f"• {format_user_display_name(first_name=i.inviter.first_name, last_name=i.inviter.last_name, username=i.inviter.username, lang=lang)}"
        for i in invites
    )
    return t("friends_incoming_title", lang, count=len(invites), names=names)


def _friends_keyboard(
    lang: str,
    pending_count: int,
    friendship_service: FriendshipService,
    user_id: UUID,
) -> InlineKeyboardMarkup:
    invite_link = friendship_service.build_invite_link(user_id)
    share_url = friendship_service.build_invite_share_url(
        invite_link,
        t("friends_share_text", lang),
    )
    return friends_main_keyboard(lang, pending_count, share_url)


async def send_friends_screen(
    message: Message,
    user_id: UUID,
    lang: str,
    friendship_service: FriendshipService,
) -> None:
    friends = await friendship_service.list_friends(user_id)
    pending = await friendship_service.list_pending_incoming(user_id)
    await message.answer(
        _friends_screen_text(lang, friends),
        reply_markup=_friends_keyboard(lang, len(pending), friendship_service, user_id),
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
    friends = await friendship_service.list_friends(user_id)
    pending = await friendship_service.list_pending_incoming(user_id)
    await callback.message.edit_text(
        _friends_screen_text(lang, friends),
        reply_markup=_friends_keyboard(lang, len(pending), friendship_service, user_id),
    )
    await callback.answer()


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

    pending = await friendship_service.list_pending_incoming_with_profiles(user_id)
    if not pending:
        await callback.answer(t("friends_incoming_empty", lang), show_alert=True)
        return

    await callback.message.edit_text(
        _incoming_screen_text(lang, pending),
        reply_markup=friends_incoming_keyboard(
            [
                (
                    invite.friendship_id,
                    format_user_display_name(
                        first_name=invite.inviter.first_name,
                        last_name=invite.inviter.last_name,
                        username=invite.inviter.username,
                        lang=lang,
                    ),
                )
                for invite in pending
            ],
            lang,
        ),
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
