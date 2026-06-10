import json
import logging

from openai import AsyncOpenAI

from app.schemas.ai import EventAnalysis, GeneratedEventsBatch
from app.services.ai.base import AIProvider
from app.services.ai.prompts import (
    ANALYZE_SYSTEM,
    GENERATE_BATCH_SYSTEM,
    TRANSLATE_SYSTEM,
    analyze_user_message,
    generate_batch_user_message,
    translate_user_message,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def analyze_event(
        self,
        original_text: str,
        event_type: str,
        user_language: str,
    ) -> EventAnalysis:
        response = await self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ANALYZE_SYSTEM},
                {
                    "role": "user",
                    "content": analyze_user_message(original_text, event_type),
                },
            ],
            temperature=0.1,
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        return EventAnalysis.model_validate(data)

    async def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": TRANSLATE_SYSTEM},
                {
                    "role": "user",
                    "content": translate_user_message(text, source_language, target_language),
                },
            ],
            temperature=0.2,
        )
        return (response.choices[0].message.content or text).strip()

    async def generate_event_batch(
        self,
        avoid_texts: list[str],
        count: int,
    ) -> GeneratedEventsBatch:
        response = await self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": GENERATE_BATCH_SYSTEM},
                {
                    "role": "user",
                    "content": generate_batch_user_message(avoid_texts, count),
                },
            ],
            temperature=0.4,
        )
        raw = response.choices[0].message.content or '{"events":[]}'
        data = json.loads(raw)
        return GeneratedEventsBatch.model_validate(data)
