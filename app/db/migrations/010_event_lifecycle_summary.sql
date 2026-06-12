-- Event lifecycle analytics view (global per-event milestones)
create or replace view event_lifecycle_summary as
with imp as (
  select
    event_id,
    min(shown_at) as first_shown_at,
    min(skipped_at) filter (where status = 'skipped') as first_skipped_at,
    count(*)::int as impressions_count,
    count(*) filter (where status = 'skipped')::int as skips_count
  from event_impressions
  group by event_id
),
rat_agg as (
  select
    event_id,
    min(created_at) as first_rated_at,
    min(created_at) filter (where rating_scope = 'community') as first_community_rated_at,
    min(created_at) filter (where rating_scope = 'friend') as first_friend_rated_at,
    count(*)::int as ratings_total,
    count(*) filter (where rating_scope = 'community')::int as ratings_community,
    count(*) filter (where rating_scope = 'friend')::int as ratings_friend
  from ratings
  group by event_id
),
rat5 as (
  select event_id, created_at as rated_at_5_total
  from (
    select event_id, created_at,
           row_number() over (partition by event_id order by created_at) as rn
    from ratings
  ) t
  where rn = 5
),
rat10 as (
  select event_id, created_at as rated_at_10_total
  from (
    select event_id, created_at,
           row_number() over (partition by event_id order by created_at) as rn
    from ratings
  ) t
  where rn = 10
),
rat5c as (
  select event_id, created_at as rated_at_5_community
  from (
    select event_id, created_at,
           row_number() over (partition by event_id order by created_at) as rn
    from ratings
    where rating_scope = 'community'
  ) t
  where rn = 5
)
select
  e.id as event_id,
  left(coalesce(e.normalized_text, e.original_text), 80) as preview,
  e.source,
  e.event_type,
  e.category,
  e.created_at,
  imp.first_shown_at,
  imp.first_skipped_at,
  rat_agg.first_rated_at,
  rat_agg.first_community_rated_at,
  rat_agg.first_friend_rated_at,
  rat5.rated_at_5_total,
  rat10.rated_at_10_total,
  rat5c.rated_at_5_community,
  coalesce(imp.impressions_count, 0) as impressions_count,
  coalesce(imp.skips_count, 0) as skips_count,
  coalesce(rat_agg.ratings_total, 0) as ratings_total,
  coalesce(rat_agg.ratings_community, 0) as ratings_community,
  coalesce(rat_agg.ratings_friend, 0) as ratings_friend,
  case
    when coalesce(imp.impressions_count, 0) > 0
    then round(imp.skips_count::numeric / imp.impressions_count, 3)
    else null
  end as skip_rate,
  case
    when imp.first_shown_at is not null
    then round(extract(epoch from (imp.first_shown_at - e.created_at)) / 3600.0, 2)
    else null
  end as hours_to_first_show,
  case
    when rat_agg.first_rated_at is not null
    then round(extract(epoch from (rat_agg.first_rated_at - e.created_at)) / 3600.0, 2)
    else null
  end as hours_to_first_rating,
  case
    when e.source = 'ai_generated' and imp.first_shown_at is not null
    then round(extract(epoch from (imp.first_shown_at - e.created_at)) / 3600.0, 2)
    else null
  end as pool_wait_hours,
  e.is_deleted,
  e.deleted_at,
  e.is_feed_hidden,
  null::timestamptz as hidden_at,
  e.ai_score,
  e.community_user_score,
  case
    when e.ai_score is not null and e.community_user_score is not null
    then abs(e.ai_score - e.community_user_score)
    else null
  end as dispute_delta
from events e
left join imp on imp.event_id = e.id
left join rat_agg on rat_agg.event_id = e.id
left join rat5 on rat5.event_id = e.id
left join rat10 on rat10.event_id = e.id
left join rat5c on rat5c.event_id = e.id;
