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


@dataclass
class FriendProfile:
    user_id: UUID
    first_name: str | None
    last_name: str | None
    username: str | None


@dataclass
class PendingFriendInvite:
    friendship_id: UUID
    inviter: FriendProfile
