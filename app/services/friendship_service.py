from typing import TYPE_CHECKING
from urllib.parse import quote
from uuid import UUID

from app.db.repositories.friendships import FriendshipsRepository
from app.db.repositories.users import UsersRepository
from app.schemas.friendships import FriendProfile, Friendship, PendingFriendInvite

if TYPE_CHECKING:
    from app.services.analytics_service import AnalyticsService


class FriendshipError(Exception):
    pass


class SelfInviteError(FriendshipError):
    pass


class AlreadyFriendsError(FriendshipError):
    pass


class FriendshipService:
    def __init__(
        self,
        friendships_repo: FriendshipsRepository,
        users_repo: UsersRepository,
        bot_username: str,
        analytics_service: "AnalyticsService | None" = None,
    ) -> None:
        self._friendships = friendships_repo
        self._users = users_repo
        self._bot_username = bot_username
        self._analytics = analytics_service

    def build_invite_link(self, user_id: UUID) -> str:
        return f"https://t.me/{self._bot_username}?start=invite_{user_id}"

    @staticmethod
    def build_invite_share_url(invite_link: str, share_text: str) -> str:
        return (
            "https://t.me/share/url?"
            f"url={quote(invite_link, safe='')}&text={quote(share_text, safe='')}"
        )

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
                await self._track_acceptance(invitee_id, inviter_id)
                return friendship

        friendship = await self._friendships.create_pending(inviter_id, invitee_id)
        await self._track_invite(inviter_id, invitee_id)
        return friendship

    async def accept_friendship(self, friendship_id: UUID, user_id: UUID) -> bool:
        friendship = await self._friendships.get_by_id(friendship_id)
        if not friendship:
            return False
        ok = await self._friendships.accept(friendship_id, user_id)
        if ok:
            friend_id = self._other_user_id(friendship, user_id)
            if friend_id:
                await self._track_acceptance(user_id, friend_id)
        return ok

    async def reject_friendship(self, friendship_id: UUID, user_id: UUID) -> bool:
        friendship = await self._friendships.get_by_id(friendship_id)
        if not friendship:
            return False
        ok = await self._friendships.reject(friendship_id, user_id)
        if ok and self._analytics:
            friend_id = self._other_user_id(friendship, user_id)
            props = {}
            if friend_id:
                props["friend_user_id"] = str(friend_id)
            await self._analytics.track("friendship_rejected", user_id, **props)
        return ok

    async def track_invite_link_requested(self, user_id: UUID) -> None:
        await self._track_invite(user_id, None)

    async def count_friends(self, user_id: UUID) -> int:
        return await self._friendships.count_accepted_friends(user_id)

    async def list_pending_incoming(self, user_id: UUID) -> list[Friendship]:
        return await self._friendships.list_pending_incoming(user_id)

    async def list_friends(self, user_id: UUID) -> list[FriendProfile]:
        return await self._friendships.list_accepted_friend_profiles(user_id)

    async def list_pending_incoming_with_profiles(
        self, user_id: UUID
    ) -> list[PendingFriendInvite]:
        return await self._friendships.list_pending_incoming_with_profiles(user_id)

    async def get_friendship(self, friendship_id: UUID) -> Friendship | None:
        return await self._friendships.get_by_id(friendship_id)

    @staticmethod
    def _other_user_id(friendship: Friendship, user_id: UUID) -> UUID | None:
        if friendship.requester_user_id == user_id:
            return friendship.addressee_user_id
        if friendship.addressee_user_id == user_id:
            return friendship.requester_user_id
        return None

    async def _track_invite(self, inviter_id: UUID, invitee_id: UUID | None) -> None:
        if not self._analytics:
            return
        props: dict[str, str] = {}
        if invitee_id:
            props["friend_user_id"] = str(invitee_id)
        await self._analytics.track("friend_invite_sent", inviter_id, **props)

    async def _track_acceptance(self, user_id: UUID, friend_id: UUID) -> None:
        if not self._analytics:
            return
        await self._analytics.track(
            "friendship_accepted",
            user_id,
            friend_user_id=str(friend_id),
        )
