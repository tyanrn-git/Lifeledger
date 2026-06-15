import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from app.bot.handlers.friends import handle_invite_deep_link
from app.bot.handlers.rate import send_feed
from app.db.repositories.impressions import ImpressionsRepository
from app.i18n import t
from app.services.feed_service import FeedService
from app.services.friendship_service import FriendshipService
from app.services.translation_service import TranslationService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    user_service: UserService,
    feed_service: FeedService,
    translation_service: TranslationService,
    impressions_repo: ImpressionsRepository,
    friendship_service: FriendshipService,
    lang: str,
    content_lang: str,
) -> None:
    if not message.from_user:
        return

    user, is_new = await user_service.get_or_create_user(message.from_user)

    inviter_id = FriendshipService.parse_invite_payload(command.args)
    if inviter_id:
        if is_new:
            await message.answer(t("welcome", lang))
        await handle_invite_deep_link(message, user, inviter_id, lang, friendship_service)
        return

    if is_new:
        await message.answer(t("welcome", lang))

    await send_feed(
        message,
        user.id,
        lang,
        content_lang,
        feed_service,
        translation_service,
        impressions_repo,
        show_batch_intro=is_new,
    )


@router.message(Command("rate"))
async def cmd_rate(
    message: Message,
    user_id,
    feed_service: FeedService,
    translation_service: TranslationService,
    impressions_repo: ImpressionsRepository,
    lang: str,
    content_lang: str,
) -> None:
    if not message.from_user:
        return

    await send_feed(
        message,
        user_id,
        lang,
        content_lang,
        feed_service,
        translation_service,
        impressions_repo,
        show_batch_intro=True,
    )
