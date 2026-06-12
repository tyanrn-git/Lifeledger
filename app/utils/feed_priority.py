from datetime import datetime

# Lower tier = shown earlier. AI-generated events are last.
FEED_TIER_FRIEND = 0
FEED_TIER_USER = 1
FEED_TIER_SEED = 2
FEED_TIER_AI = 3

_TIER_SCALE = 1_000_000_000_000

FEED_TIER_ORDER_SQL = """
case
  when e.author_user_id is not null and exists (
    select 1 from friendships f
    where f.status = 'accepted'
      and (
        (f.requester_user_id = $1 and f.addressee_user_id = e.author_user_id)
        or (f.addressee_user_id = $1 and f.requester_user_id = e.author_user_id)
      )
  ) then 0
  when e.author_user_id is not null
       and coalesce(e.source::text, 'user') = 'user' then 1
  when coalesce(e.source::text, 'user') = 'seed' then 2
  else 3
end
"""


def source_priority(tier: int, created_at: datetime) -> int:
    ts_ms = int(created_at.timestamp() * 1000)
    return tier * _TIER_SCALE - ts_ms
