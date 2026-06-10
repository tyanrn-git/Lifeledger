from uuid import UUID

import asyncpg

from app.schemas.friendships import Friendship


def _row_to_friendship(row: asyncpg.Record) -> Friendship:
    return Friendship(
        id=row["id"],
        requester_user_id=row["requester_user_id"],
        addressee_user_id=row["addressee_user_id"],
        status=row["status"],
        created_at=row["created_at"],
        responded_at=row["responded_at"],
    )


class FriendshipsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def are_friends(self, user_a: UUID, user_b: UUID) -> bool:
        if user_a == user_b:
            return False
        val = await self._pool.fetchval(
            """
            select 1 from friendships
            where status = 'accepted'
              and (
                (requester_user_id = $1 and addressee_user_id = $2)
                or (requester_user_id = $2 and addressee_user_id = $1)
              )
            """,
            user_a,
            user_b,
        )
        return val is not None

    async def get_by_id(self, friendship_id: UUID) -> Friendship | None:
        row = await self._pool.fetchrow(
            "select * from friendships where id = $1",
            friendship_id,
        )
        return _row_to_friendship(row) if row else None

    async def get_between(self, user_a: UUID, user_b: UUID) -> Friendship | None:
        row = await self._pool.fetchrow(
            """
            select * from friendships
            where (requester_user_id = $1 and addressee_user_id = $2)
               or (requester_user_id = $2 and addressee_user_id = $1)
            order by created_at desc
            limit 1
            """,
            user_a,
            user_b,
        )
        return _row_to_friendship(row) if row else None

    async def create_pending(self, requester_id: UUID, addressee_id: UUID) -> Friendship:
        row = await self._pool.fetchrow(
            """
            insert into friendships (requester_user_id, addressee_user_id, status)
            values ($1, $2, 'pending')
            on conflict (requester_user_id, addressee_user_id) do update
              set status = case
                    when friendships.status = 'accepted' then friendships.status
                    else 'pending'
                  end,
                  responded_at = case
                    when friendships.status = 'accepted' then friendships.responded_at
                    else null
                  end
            returning *
            """,
            requester_id,
            addressee_id,
        )
        return _row_to_friendship(row)

    async def force_accept(self, friendship_id: UUID) -> bool:
        result = await self._pool.execute(
            """
            update friendships
            set status = 'accepted', responded_at = now()
            where id = $1 and status = 'pending'
            """,
            friendship_id,
        )
        return result.endswith("1")

    async def accept(self, friendship_id: UUID, addressee_id: UUID) -> bool:
        result = await self._pool.execute(
            """
            update friendships
            set status = 'accepted', responded_at = now()
            where id = $1
              and addressee_user_id = $2
              and status = 'pending'
            """,
            friendship_id,
            addressee_id,
        )
        return result.endswith("1")

    async def reject(self, friendship_id: UUID, addressee_id: UUID) -> bool:
        result = await self._pool.execute(
            """
            update friendships
            set status = 'rejected', responded_at = now()
            where id = $1
              and addressee_user_id = $2
              and status = 'pending'
            """,
            friendship_id,
            addressee_id,
        )
        return result.endswith("1")

    async def count_accepted_friends(self, user_id: UUID) -> int:
        val = await self._pool.fetchval(
            """
            select count(*)::int from friendships
            where status = 'accepted'
              and (requester_user_id = $1 or addressee_user_id = $1)
            """,
            user_id,
        )
        return val or 0

    async def list_pending_incoming(self, user_id: UUID) -> list[Friendship]:
        rows = await self._pool.fetch(
            """
            select * from friendships
            where addressee_user_id = $1 and status = 'pending'
            order by created_at desc
            """,
            user_id,
        )
        return [_row_to_friendship(row) for row in rows]
