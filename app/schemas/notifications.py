from dataclasses import dataclass
from uuid import UUID


@dataclass
class EventNotificationMeta:
    author_user_id: UUID | None
    friends_ratings_count: int
    latest_rating_scope: str | None
