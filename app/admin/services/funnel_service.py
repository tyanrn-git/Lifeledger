from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True)
class FunnelStep:
    number: int
    key: str
    label: str
    count: int
    pct_registration: float
    pct_previous: float


FUNNEL_STEP_DEFS: list[tuple[int, str, str]] = [
    (1, "registration", "Registration"),
    (2, "first_feed", "First Feed"),
    (3, "first_event_viewed", "First Event Viewed"),
    (4, "first_rating", "First Rating"),
    (5, "five_ratings", "5 Ratings"),
    (6, "ten_ratings", "10 Ratings"),
    (7, "first_event_created", "First Event Created"),
    (8, "first_community_rating", "First Community Rating Received"),
    (9, "friend_invite_sent", "Friend Invite Sent"),
    (10, "friendship_accepted", "Friendship Accepted"),
    (11, "first_friend_rating", "First Friend Rating Received"),
    (12, "returned_d1", "Returned Next Day"),
    (13, "returned_d2_7", "Returned Within 7 Days"),
]


class FunnelService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def compute(self) -> list[FunnelStep]:
        counts = await self._fetch_counts()
        registration = counts.get("registration", 0)
        steps: list[FunnelStep] = []
        prev = registration

        for number, key, label in FUNNEL_STEP_DEFS:
            count = counts.get(key, 0)
            pct_reg = (count / registration * 100) if registration else 0.0
            pct_prev = (count / prev * 100) if prev else 0.0
            steps.append(
                FunnelStep(
                    number=number,
                    key=key,
                    label=label,
                    count=count,
                    pct_registration=round(pct_reg, 1),
                    pct_previous=round(pct_prev, 1),
                )
            )
            prev = count

        return steps

    async def _fetch_counts(self) -> dict[str, int]:
        row = await self._pool.fetchrow(
            """
            select
              (select count(*)::int from users) as registration,
              (select count(distinct user_id)::int from admin_event_log
               where event_name = 'feed_started' and user_id is not null) as first_feed,
              (select count(distinct user_id)::int from admin_event_log
               where event_name = 'event_shown' and user_id is not null) as first_event_viewed,
              (select count(distinct user_id)::int from admin_event_log
               where event_name = 'event_rated' and user_id is not null) as first_rating,
              (select count(*)::int from (
                 select user_id from admin_event_log
                 where event_name = 'event_rated' and user_id is not null
                 group by user_id having count(*) >= 5
               ) s5) as five_ratings,
              (select count(*)::int from (
                 select user_id from admin_event_log
                 where event_name = 'event_rated' and user_id is not null
                 group by user_id having count(*) >= 10
               ) s10) as ten_ratings,
              (select count(distinct user_id)::int from admin_event_log
               where event_name = 'event_created' and user_id is not null) as first_event_created,
              (select count(distinct e.author_user_id)::int
               from ratings r
               join events e on e.id = r.event_id
               where r.rating_scope = 'community' and e.author_user_id is not null
              ) as first_community_rating,
              (select count(distinct user_id)::int from admin_event_log
               where event_name = 'friend_invite_sent' and user_id is not null) as friend_invite_sent,
              (select count(distinct user_id)::int from admin_event_log
               where event_name = 'friendship_accepted' and user_id is not null) as friendship_accepted,
              (select count(distinct e.author_user_id)::int
               from ratings r
               join events e on e.id = r.event_id
               where r.rating_scope = 'friend' and e.author_user_id is not null
              ) as first_friend_rating,
              (select count(*)::int from users u
               where exists (
                 select 1 from admin_event_log l
                 where l.user_id = u.id and l.event_name = 'user_seen'
                   and l.created_at::date = (u.created_at at time zone 'utc')::date + 1
               )) as returned_d1,
              (select count(*)::int from users u
               where exists (
                 select 1 from admin_event_log l
                 where l.user_id = u.id and l.event_name = 'user_seen'
                   and l.created_at::date between
                     (u.created_at at time zone 'utc')::date + 2
                     and (u.created_at at time zone 'utc')::date + 7
               )) as returned_d2_7
            """
        )
        return dict(row) if row else {}
