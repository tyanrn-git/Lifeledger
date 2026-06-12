from aiohttp import web

from app.admin.routes.activity import activity_list
from app.admin.routes.ai import ai_page
from app.admin.routes.auth import login_get, login_post, logout
from app.admin.routes.dashboard import dashboard
from app.admin.routes.events import event_detail, events_list
from app.admin.routes.export import export_download, export_page
from app.admin.routes.feed import feed_page
from app.admin.routes.funnels import funnels
from app.admin.routes.home import home
from app.admin.routes.lifecycle import lifecycle_list
from app.admin.routes.moderation import event_hide, event_unhide
from app.admin.routes.notifications import notifications_page
from app.admin.routes.ratings import ratings_page
from app.admin.routes.system import system_page
from app.admin.routes.users import user_detail, users_list


def admin_routes() -> list[web.RouteDef]:
    return [
        web.get("/admin/login", login_get),
        web.post("/admin/login", login_post),
        web.get("/admin/logout", logout),
        web.get("/admin", home),
        web.get("/admin/", home),
        web.get("/admin/dashboard", dashboard),
        web.get("/admin/funnels", funnels),
        web.get("/admin/users", users_list),
        web.get("/admin/users/{id}", user_detail),
        web.get("/admin/activity", activity_list),
        web.get("/admin/events/lifecycle", lifecycle_list),
        web.get("/admin/events", events_list),
        web.get("/admin/events/{id}", event_detail),
        web.get("/admin/ratings", ratings_page),
        web.get("/admin/feed", feed_page),
        web.get("/admin/ai", ai_page),
        web.get("/admin/notifications", notifications_page),
        web.get("/admin/export", export_page),
        web.post("/admin/export", export_download),
        web.get("/admin/system", system_page),
        web.post("/admin/events/{id}/hide", event_hide),
        web.post("/admin/events/{id}/unhide", event_unhide),
    ]
