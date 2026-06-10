from app.config import settings
from app.services.ai.base import AIProvider
from app.services.ai.openai_provider import OpenAIProvider


def build_ai_provider() -> AIProvider:
    provider = settings.ai_provider.lower()
    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        return OpenAIProvider(settings.openai_api_key)
    raise RuntimeError(f"Unsupported AI provider: {provider}")
