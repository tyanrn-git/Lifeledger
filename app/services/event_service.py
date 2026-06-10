from datetime import datetime
from uuid import UUID

from app.db.repositories.events import EventsRepository
from app.schemas.events import Event
from app.services.ai_service import AIService


class EventService:
    def __init__(self, events_repo: EventsRepository, ai_service: AIService) -> None:
        self._events = events_repo
        self._ai = ai_service

    async def create_event(
        self,
        author_id: UUID,
        event_type: str,
        original_text: str,
        original_language: str,
        self_score: int,
    ) -> Event:
        text = original_text.strip()
        analysis = await self._ai.analyze_event(text, event_type, original_language)
        event_time = AIService.parse_event_time(analysis.event_time_iso)
        ai_score = float(analysis.ai_score)

        return await self._events.create(
            author_id=author_id,
            event_type=event_type,
            original_text=text,
            original_language=analysis.original_language or original_language,
            normalized_text=analysis.normalized_text,
            self_score=self_score,
            ai_score=ai_score,
            final_community_score=ai_score,
            event_time=event_time,
            action_text=analysis.action,
            context_text=analysis.context,
            category=analysis.category,
        )

    async def get_user_events(self, user_id: UUID) -> list[Event]:
        return await self._events.list_by_author(user_id)

    async def get_event_details(self, event_id: UUID, user_id: UUID) -> Event | None:
        return await self._events.get_for_author(event_id, user_id)

    async def delete_event(self, event_id: UUID, user_id: UUID) -> bool:
        return await self._events.soft_delete(event_id, user_id)
