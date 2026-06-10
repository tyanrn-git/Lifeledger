import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.views import stats_text
from app.services.stats_service import StatsService

logger = logging.getLogger(__name__)
router = Router()


async def send_stats(
    message: Message,
    user_id,
    lang: str,
    stats_service: StatsService,
) -> None:
    author = await stats_service.calculate_author_stats(user_id)
    evaluator = await stats_service.calculate_evaluator_stats(user_id)
    await message.answer(stats_text(author, evaluator, lang))


@router.message(Command("stats"))
async def cmd_stats(
    message: Message,
    user_id,
    lang: str,
    stats_service: StatsService,
) -> None:
    await send_stats(message, user_id, lang, stats_service)


@router.callback_query(F.data == "nav:stats")
async def nav_stats(
    callback: CallbackQuery,
    user_id,
    lang: str,
    stats_service: StatsService,
) -> None:
    if not callback.message:
        await callback.answer()
        return
    await send_stats(callback.message, user_id, lang, stats_service)
    await callback.answer()
