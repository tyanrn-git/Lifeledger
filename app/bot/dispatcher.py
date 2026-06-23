from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import get_routers
from app.bot.middlewares import (
    ServicesMiddleware,
    UserContextMiddleware,
    on_dispatcher_error,
)


def setup_dispatcher(services: dict) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.errors.register(on_dispatcher_error)
    dp.update.middleware(ServicesMiddleware(services))
    dp.update.middleware(
        UserContextMiddleware(
            services["user_service"],
            services.get("analytics_service"),
        )
    )

    for router in get_routers():
        dp.include_router(router)

    return dp
