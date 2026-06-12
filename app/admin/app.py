import asyncpg
from aiohttp import web

from app.admin.auth import admin_auth_middleware, admin_enabled
from app.admin.routes import admin_routes


def setup_admin_routes(app: web.Application, pool: asyncpg.Pool) -> None:
    if not admin_enabled():
        return

    app["pool"] = pool
    app.middlewares.insert(0, admin_auth_middleware)
    app.router.add_routes(admin_routes())
