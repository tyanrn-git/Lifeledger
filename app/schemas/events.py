from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class EventForRating:
    id: UUID
    event_type: str
    normalized_text: str
    final_community_score: Decimal | None


@dataclass
class Event:
    id: UUID
    author_user_id: UUID | None
    event_type: str
    original_text: str
    normalized_text: str
    self_score: int
    friends_score: Decimal | None
    final_community_score: Decimal | None
