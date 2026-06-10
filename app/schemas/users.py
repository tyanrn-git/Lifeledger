from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    id: UUID
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str
    notifications_enabled: bool
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime | None
