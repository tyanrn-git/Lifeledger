import logging
from datetime import datetime

from app.schemas.ai import EventAnalysis, EventRescore, GeneratedEventsBatch
from app.services.ai.base import AIProvider

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def analyze_event(
        self,
        original_text: str,
        event_type: str,
        user_language: str,
    ) -> EventAnalysis:
        try:
            return await self._provider.analyze_event(
                original_text, event_type, user_language
            )
        except Exception:
            logger.exception("AI analysis failed, using fallback")
            return self._fallback_analysis(original_text, user_language)

    async def rescore_event(
        self,
        normalized_text: str,
        event_type: str,
    ) -> EventRescore:
        try:
            return await self._provider.rescore_event(normalized_text, event_type)
        except Exception:
            logger.exception("AI rescore failed for event text")
            return EventRescore(ai_score=0)

    async def generate_event_batch(
        self,
        avoid_texts: list[str],
        count: int,
    ) -> GeneratedEventsBatch:
        try:
            batch = await self._provider.generate_event_batch(avoid_texts, count)
            if batch.events:
                return batch
        except Exception:
            logger.exception("AI batch generation failed")
        return GeneratedEventsBatch(events=[])

    async def translate_event(
        self,
        normalized_text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        try:
            return await self._provider.translate_text(
                normalized_text, source_language, target_language
            )
        except Exception:
            logger.exception("AI translation failed")
            return normalized_text

    def _fallback_analysis(self, original_text: str, user_language: str) -> EventAnalysis:
        return EventAnalysis(
            original_language=user_language[:2] if user_language else "en",
            normalized_text=original_text.strip(),
            ai_score=0,
        )

    @staticmethod
    def parse_event_time(event_time_iso: str | None) -> datetime | None:
        if not event_time_iso:
            return None
        try:
            return datetime.fromisoformat(event_time_iso.replace("Z", "+00:00"))
        except ValueError:
            return None
