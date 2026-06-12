import logging
from typing import Any
from uuid import UUID

from app.db.repositories.admin_event_log import AdminEventLogRepository

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, repo: AdminEventLogRepository) -> None:
        self._repo = repo

    async def track(
        self,
        event_name: str,
        user_id: UUID | None = None,
        **properties: Any,
    ) -> None:
        try:
            await self._repo.insert(event_name, user_id, properties)
        except Exception:
            logger.exception("Failed to track analytics event %s", event_name)
