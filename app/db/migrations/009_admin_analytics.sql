create table if not exists admin_event_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete set null,
  event_name text not null,
  properties jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index if not exists idx_admin_event_log_event_name_created
  on admin_event_log (event_name, created_at desc);
create index if not exists idx_admin_event_log_user_created
  on admin_event_log (user_id, created_at desc);

create table if not exists admin_action_log (
  id uuid primary key default gen_random_uuid(),
  action text not null,
  target_type text,
  target_id uuid,
  comment text,
  created_at timestamptz not null default now()
);

create index if not exists idx_admin_action_log_created
  on admin_action_log (created_at desc);

create table if not exists analytics_daily (
  date date primary key,
  new_users integer not null default 0,
  active_users integer not null default 0,
  events_created integer not null default 0,
  ratings_count integer not null default 0,
  ai_events_generated integer not null default 0,
  feed_empty_count integer not null default 0,
  batches_created integer not null default 0,
  avg_batch_size numeric(6, 2)
);

alter table event_impressions
  add column if not exists feed_tier smallint;

alter table events
  add column if not exists is_feed_hidden boolean not null default false;

create index if not exists idx_events_is_feed_hidden on events(is_feed_hidden);
