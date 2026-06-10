from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Friendship:
    id: UUID
    requester_user_id: UUID
    addressee_user_id: UUID
    status: str
    created_at: datetime
    responded_at: datetime | None
