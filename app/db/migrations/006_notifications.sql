do $$ begin
  create type notification_type as enum (
    'new_ratings',
    'first_friend_rating',
    'community_score_changed'
  );
exception when duplicate_object then null;
end $$;

create table if not exists notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  event_id uuid references events(id) on delete cascade,
  notification_type notification_type not null,
  title text,
  body text,
  is_sent boolean not null default false,
  sent_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_notifications_user_id on notifications(user_id);
create index if not exists idx_notifications_is_sent on notifications(is_sent);
create index if not exists idx_notifications_created_at on notifications(created_at);
create index if not exists idx_notifications_event_type on notifications(event_id, notification_type);
