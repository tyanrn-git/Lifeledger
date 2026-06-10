from pydantic import BaseModel, Field


class EventAnalysis(BaseModel):
    original_language: str = "en"
    event_time_text: str | None = None
    event_time_iso: str | None = None
    action: str | None = None
    context: str | None = None
    category: str | None = None
    normalized_text: str
    ai_score: int = Field(ge=-10, le=10)
    score_explanation: str | None = None


class GeneratedEventDraft(BaseModel):
    normalized_text: str
    category: str | None = None
    ai_score: int = Field(ge=-10, le=10)
    action: str | None = None
    context: str | None = None


class GeneratedEventsBatch(BaseModel):
    events: list[GeneratedEventDraft]
