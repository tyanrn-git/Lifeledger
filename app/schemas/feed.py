from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class FeedEventCandidate:
    id: UUID
    created_at: datetime
    feed_tier: int
