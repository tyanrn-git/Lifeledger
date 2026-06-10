from abc import ABC, abstractmethod

from app.schemas.ai import EventAnalysis


class AIProvider(ABC):
    @abstractmethod
    async def analyze_event(
        self,
        original_text: str,
        event_type: str,
        user_language: str,
    ) -> EventAnalysis:
        raise NotImplementedError

    @abstractmethod
    async def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        raise NotImplementedError
