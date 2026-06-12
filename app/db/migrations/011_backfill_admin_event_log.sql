-- Восстановление admin_event_log из исторических таблиц (до включения track()).
-- Помечаем properties.backfilled = true; повторный прогон миграции не дублирует строки.

insert into admin_event_log (user_id, event_name, properties, created_at)
select u.id, 'user_registered',
       jsonb_build_object('telegram_id', u.telegram_id, 'backfilled', true),
       u.created_at
from users u
where not exists (
  select 1 from admin_event_log l
  where l.event_name = 'user_registered' and l.user_id = u.id
);

insert into admin_event_log (user_id, event_name, properties, created_at)
select e.author_user_id, 'event_created',
       jsonb_build_object(
         'event_id', e.id,
         'event_type', e.event_type::text,
         'source', e.source::text,
         'backfilled', true
       ),
       e.created_at
from events e
where e.author_user_id is not null
  and not exists (
    select 1 from admin_event_log l
    where l.event_name = 'event_created'
      and l.properties->>'event_id' = e.id::text
  );

insert into admin_event_log (user_id, event_name, properties, created_at)
select r.rater_user_id, 'event_rated',
       jsonb_build_object(
         'event_id', r.event_id,
         'score', r.score,
         'rating_scope', r.rating_scope::text,
         'backfilled', true
       ),
       r.created_at
from ratings r
where not exists (
  select 1 from admin_event_log l
  where l.event_name = 'event_rated'
    and l.user_id = r.rater_user_id
    and l.properties->>'event_id' = r.event_id::text
    and abs(extract(epoch from (l.created_at - r.created_at))) < 2
);

insert into admin_event_log (user_id, event_name, properties, created_at)
select i.user_id, 'event_skipped',
       jsonb_build_object(
         'event_id', i.event_id,
         'batch_id', i.batch_id,
         'feed_tier', i.feed_tier,
         'backfilled', true
       ),
       coalesce(i.skipped_at, i.shown_at)
from event_impressions i
where i.status = 'skipped'
  and not exists (
    select 1 from admin_event_log l
    where l.event_name = 'event_skipped'
      and l.user_id = i.user_id
      and l.properties->>'event_id' = i.event_id::text
  );

insert into admin_event_log (user_id, event_name, properties, created_at)
select i.user_id, 'event_shown',
       jsonb_build_object(
         'event_id', i.event_id,
         'batch_id', i.batch_id,
         'feed_tier', i.feed_tier,
         'backfilled', true
       ),
       i.shown_at
from event_impressions i
where not exists (
  select 1 from admin_event_log l
  where l.event_name = 'event_shown'
    and l.user_id = i.user_id
    and l.properties->>'event_id' = i.event_id::text
    and l.properties->>'batch_id' = i.batch_id::text
);

insert into admin_event_log (user_id, event_name, properties, created_at)
select f.addressee_user_id, 'friendship_accepted',
       jsonb_build_object(
         'friend_user_id', f.requester_user_id,
         'backfilled', true
       ),
       coalesce(f.responded_at, f.created_at)
from friendships f
where f.status = 'accepted'
  and not exists (
    select 1 from admin_event_log l
    where l.event_name = 'friendship_accepted'
      and l.user_id = f.addressee_user_id
      and l.properties->>'friend_user_id' = f.requester_user_id::text
  );

insert into admin_event_log (user_id, event_name, properties, created_at)
select b.user_id, 'batch_created',
       jsonb_build_object(
         'batch_id', b.id,
         'requested_size', b.requested_size,
         'actual_size', b.actual_size,
         'backfilled', true
       ),
       b.created_at
from rating_batches b
where not exists (
  select 1 from admin_event_log l
  where l.event_name = 'batch_created'
    and l.properties->>'batch_id' = b.id::text
);

insert into admin_event_log (user_id, event_name, properties, created_at)
select n.user_id, 'notification_created',
       jsonb_build_object(
         'notification_id', n.id,
         'notification_type', n.notification_type::text,
         'event_id', n.event_id,
         'backfilled', true
       ),
       n.created_at
from notifications n
where not exists (
  select 1 from admin_event_log l
  where l.event_name = 'notification_created'
    and l.properties->>'notification_id' = n.id::text
);

insert into admin_event_log (user_id, event_name, properties, created_at)
select n.user_id, 'notification_sent',
       jsonb_build_object(
         'notification_id', n.id,
         'backfilled', true
       ),
       coalesce(n.sent_at, n.created_at)
from notifications n
where n.is_sent = true
  and not exists (
    select 1 from admin_event_log l
    where l.event_name = 'notification_sent'
      and l.properties->>'notification_id' = n.id::text
  );
