import asyncio
import logging
from typing import Any
from uuid import UUID

from app.db.repositories.admin_event_log import AdminEventLogRepository

logger = logging.getLogger(__name__)

AnalyticsEvent = tuple[str, UUID | None, dict[str, Any]]


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

    def track_background(
        self,
        event_name: str,
        user_id: UUID | None = None,
        **properties: Any,
    ) -> None:
        asyncio.create_task(self.track(event_name, user_id, **properties))

    async def track_many(self, events: list[AnalyticsEvent]) -> None:
        if not events:
            return
        try:
            await self._repo.insert_many(events)
        except Exception:
            logger.exception("Failed to track %s analytics events", len(events))

    def track_many_background(self, events: list[AnalyticsEvent]) -> None:
        if events:
            asyncio.create_task(self.track_many(events))
