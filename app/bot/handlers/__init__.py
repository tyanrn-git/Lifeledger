from app.bot.handlers.add_event import router as add_event_router
from app.bot.handlers.common import router as common_router
from app.bot.handlers.events import router as events_router
from app.bot.handlers.friends import router as friends_router
from app.bot.handlers.rate import router as rate_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.settings import router as settings_router
from app.bot.handlers.stats import router as stats_router


def get_routers():
    return [
        start_router,
        rate_router,
        add_event_router,
        events_router,
        friends_router,
        stats_router,
        settings_router,
        common_router,
    ]
