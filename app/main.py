import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

from app.bot.dispatcher import setup_dispatcher
from app.config import settings
from app.db.connection import close_pool, init_pool
from app.db.migrate import run_migrations
from app.db.repositories.batches import BatchesRepository
from app.db.repositories.events import EventsRepository
from app.db.repositories.friendships import FriendshipsRepository
from app.db.repositories.notifications import NotificationsRepository
from app.db.repositories.impressions import ImpressionsRepository
from app.db.repositories.ratings import RatingsRepository
from app.db.repositories.stats import StatsRepository
from app.db.repositories.translations import TranslationsRepository
from app.db.repositories.users import UsersRepository
from app.logging_config import setup_logging
from app.services.ai.factory import build_ai_provider
from app.services.ai_generation_service import AIGenerationService
from app.services.ai_service import AIService
from app.services.event_service import EventService
from app.services.feed_service import FeedService
from app.services.friendship_service import FriendshipService
from app.services.notification_service import NotificationService
from app.services.rating_service import RatingService
from app.services.score_recalibration_service import ScoreRecalibrationService
from app.services.stats_service import StatsService
from app.services.translation_service import TranslationService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


def build_services(pool, bot_username: str, bot: Bot, *, ai_service: AIService | None = None):
    users_repo = UsersRepository(pool)
    events_repo = EventsRepository(pool)
    impressions_repo = ImpressionsRepository(pool)
    ratings_repo = RatingsRepository(pool)
    friendships_repo = FriendshipsRepository(pool)
    translations_repo = TranslationsRepository(pool)
    batches_repo = BatchesRepository(pool)
    stats_repo = StatsRepository(pool)
    notifications_repo = NotificationsRepository(pool)

    if ai_service is None:
        ai_service = AIService(build_ai_provider())
    ai_generation_service = AIGenerationService(pool, events_repo, ai_service)

    return {
        "user_service": UserService(users_repo),
        "event_service": EventService(events_repo, ai_service),
        "feed_service": FeedService(
            events_repo, impressions_repo, batches_repo, ai_generation_service
        ),
        "rating_service": RatingService(
            pool, ratings_repo, impressions_repo, events_repo, friendships_repo
        ),
        "translation_service": TranslationService(pool, translations_repo, ai_service),
        "friendship_service": FriendshipService(friendships_repo, users_repo, bot_username),
        "stats_service": StatsService(stats_repo),
        "notification_service": NotificationService(
            notifications_repo, users_repo, events_repo, bot
        ),
        "impressions_repo": impressions_repo,
    }


async def bootstrap() -> tuple[Bot, Dispatcher]:
    setup_logging()
    pool = await init_pool()
    await run_migrations(pool)

    bot = Bot(token=settings.telegram_bot_token)
    me = await bot.get_me()
    bot_username = me.username or "MyLifeledgerbot"

    ai_service = AIService(build_ai_provider())
    recalibration = ScoreRecalibrationService(pool, ai_service)
    await recalibration.refresh_all_community_scores()
    asyncio.create_task(recalibration.run_background_rescore())

    services = build_services(pool, bot_username, bot, ai_service=ai_service)
    dp = setup_dispatcher(services)
    return bot, dp


async def run_polling() -> None:
    bot, dp = await bootstrap()
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info("LifeLedger bot started (polling)")
        await dp.start_polling(bot)
    finally:
        await close_pool()


async def run_webhook() -> None:
    webhook_url = settings.resolved_webhook_url()
    if not webhook_url:
        raise RuntimeError(
            "WEBHOOK_URL or RAILWAY_PUBLIC_DOMAIN must be set when BOT_MODE=webhook"
        )

    bot, dp = await bootstrap()
    app = web.Application()

    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret or None,
    )
    webhook_handler.register(app, path=settings.webhook_path)

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_get("/health", health)
    app.router.add_get("/", health)

    async def on_shutdown(_app: web.Application) -> None:
        await bot.delete_webhook()
        await close_pool()

    app.on_shutdown.append(on_shutdown)

    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook_secret or None,
    )

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.port)
    await site.start()

    logger.info("LifeLedger bot started (webhook)")
    logger.info("Webhook URL: %s", webhook_url)
    logger.info("Listening on 0.0.0.0:%s", settings.port)

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def run() -> None:
    if settings.is_webhook:
        await run_webhook()
    else:
        await run_polling()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
