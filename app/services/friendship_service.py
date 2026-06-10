from dataclasses import dataclass
from uuid import UUID

from app.db.repositories.friendships import FriendshipsRepository
from app.db.repositories.users import UsersRepository
from app.schemas.friendships import Friendship
from app.schemas.users import User


class FriendshipError(Exception):
    pass


class SelfInviteError(FriendshipError):
    pass


class AlreadyFriendsError(FriendshipError):
    pass


@dataclass
class PickerInviteResult:
    friendship: Friendship
    invitee: User
    invitee_display_name: str


class FriendshipService:
    def __init__(
        self,
        friendships_repo: FriendshipsRepository,
        users_repo: UsersRepository,
        bot_username: str,
    ) -> None:
        self._friendships = friendships_repo
        self._users = users_repo
        self._bot_username = bot_username

    def build_invite_link(self, user_id: UUID) -> str:
        return f"https://t.me/{self._bot_username}?start=invite_{user_id}"

    @staticmethod
    def parse_invite_payload(args: str | None) -> UUID | None:
        if not args or not args.startswith("invite_"):
            return None
        raw = args.removeprefix("invite_").strip()
        try:
            return UUID(raw)
        except ValueError:
            return None

    async def create_invite_from_link(
        self,
        inviter_id: UUID,
        invitee_id: UUID,
    ) -> Friendship:
        if inviter_id == invitee_id:
            raise SelfInviteError()

        inviter = await self._users.get_by_id(inviter_id)
        if not inviter:
            raise FriendshipError("inviter_not_found")

        if await self._friendships.are_friends(inviter_id, invitee_id):
            raise AlreadyFriendsError()

        existing = await self._friendships.get_between(inviter_id, invitee_id)
        if existing:
            if existing.status == "accepted":
                raise AlreadyFriendsError()
            if existing.status == "pending":
                if existing.requester_user_id == inviter_id:
                    return existing
                await self._friendships.force_accept(existing.id)
                friendship = await self._friendships.get_by_id(existing.id)
                if not friendship:
                    raise FriendshipError("friendship_not_found")
                return friendship

        return await self._friendships.create_pending(inviter_id, invitee_id)

    async def accept_friendship(self, friendship_id: UUID, user_id: UUID) -> bool:
        return await self._friendships.accept(friendship_id, user_id)

    async def reject_friendship(self, friendship_id: UUID, user_id: UUID) -> bool:
        return await self._friendships.reject(friendship_id, user_id)

    async def count_friends(self, user_id: UUID) -> int:
        return await self._friendships.count_accepted_friends(user_id)

    async def list_pending_incoming(self, user_id: UUID) -> list[Friendship]:
        return await self._friendships.list_pending_incoming(user_id)

    async def get_friendship(self, friendship_id: UUID) -> Friendship | None:
        return await self._friendships.get_by_id(friendship_id)

    async def create_invite_from_picker(
        self,
        inviter_id: UUID,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        default_language: str = "en",
    ) -> PickerInviteResult:
        invitee, _ = await self._users.get_or_create_from_telegram_profile(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            default_language=default_language,
        )
        friendship = await self.create_invite_from_link(inviter_id, invitee.id)
        display_name = first_name or username or "User"
        return PickerInviteResult(
            friendship=friendship,
            invitee=invitee,
            invitee_display_name=display_name,
        )
