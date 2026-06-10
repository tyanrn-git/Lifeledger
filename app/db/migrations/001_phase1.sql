create extension if not exists "pgcrypto";

do $$ begin
  create type event_type as enum ('real', 'hypothetical');
exception when duplicate_object then null;
end $$;

do $$ begin
  create type rating_scope as enum ('friend', 'community');
exception when duplicate_object then null;
end $$;

do $$ begin
  create type impression_status as enum ('shown', 'rated', 'skipped');
exception when duplicate_object then null;
end $$;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  telegram_id bigint not null unique,
  username text,
  first_name text,
  last_name text,
  language_code text not null default 'en',
  notifications_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_seen_at timestamptz
);

create index if not exists idx_users_language_code on users(language_code);
create index if not exists idx_users_last_seen_at on users(last_seen_at);

create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  author_user_id uuid references users(id) on delete set null,
  event_type event_type not null,
  original_text text not null,
  original_language text not null,
  event_time timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  action_text text,
  context_text text,
  category text,
  normalized_text text,
  self_score integer not null check (self_score between -10 and 10),
  ai_score numeric(5,2),
  community_user_score numeric(5,2),
  final_community_score numeric(5,2),
  friends_score numeric(5,2),
  friends_ratings_count integer not null default 0,
  community_ratings_count integer not null default 0,
  is_deleted boolean not null default false,
  deleted_at timestamptz,
  anonymized_after_delete boolean not null default false
);

create index if not exists idx_events_author_user_id on events(author_user_id);
create index if not exists idx_events_is_deleted on events(is_deleted);
create index if not exists idx_events_community_ratings_count on events(community_ratings_count);

create table if not exists ratings (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  rater_user_id uuid not null references users(id) on delete cascade,
  rating_scope rating_scope not null,
  score integer not null check (score between -10 and 10),
  created_at timestamptz not null default now(),
  unique(event_id, rater_user_id)
);

create index if not exists idx_ratings_event_id on ratings(event_id);
create index if not exists idx_ratings_rater_user_id on ratings(rater_user_id);

create table if not exists rating_batches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  created_at timestamptz not null default now(),
  completed_at timestamptz,
  requested_size integer not null default 30,
  actual_size integer not null default 0
);

create index if not exists idx_rating_batches_user_id on rating_batches(user_id);

create table if not exists event_impressions (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  status impression_status not null default 'shown',
  source_priority integer,
  batch_id uuid references rating_batches(id) on delete set null,
  shown_at timestamptz not null default now(),
  rated_at timestamptz,
  skipped_at timestamptz,
  unique(event_id, user_id)
);

create index if not exists idx_event_impressions_user_id on event_impressions(user_id);
create index if not exists idx_event_impressions_batch_id on event_impressions(batch_id);
create index if not exists idx_event_impressions_status on event_impressions(status);

-- Static seed events for Phase 1 (system-owned, no author)
insert into events (
  id, author_user_id, event_type, original_text, original_language,
  normalized_text, self_score, ai_score, final_community_score, category
) values
  (
    'a0000001-0000-4000-8000-000000000001',
    null, 'real',
    'Родитель отругал ребенка за курение.',
    'ru',
    'Родитель отругал ребенка за курение.',
    -2, -3.00, -4.00, 'семья'
  ),
  (
    'a0000001-0000-4000-8000-000000000002',
    null, 'real',
    'Помог соседу донести тяжелые вещи до квартиры.',
    'ru',
    'Помог соседу донести тяжелые вещи до квартиры.',
    5, 6.00, 5.50, 'помощь'
  ),
  (
    'a0000001-0000-4000-8000-000000000003',
    null, 'hypothetical',
    'Человек вернул найденный на улице кошелек с деньгами владельцу.',
    'ru',
    'Человек вернул найденный на улице кошелек с деньгами владельцу.',
    8, 7.00, 6.50, 'честность'
  ),
  (
    'a0000001-0000-4000-8000-000000000004',
    null, 'real',
    'Опоздал на важную встречу из-за того, что не вышел из дома вовремя.',
    'ru',
    'Человек опоздал на важную встречу, потому что не вышел из дома вовремя.',
    -3, -4.00, -3.50, 'ответственность'
  ),
  (
    'a0000001-0000-4000-8000-000000000005',
    null, 'hypothetical',
    'Человек солгал начальнику друга, что тот был болен, хотя друг просто отдыхал.',
    'ru',
    'Человек солгал начальнику друга, что тот был болен, хотя друг просто отдыхал.',
    -5, -6.00, -5.00, 'ложь'
  ),
  (
    'a0000001-0000-4000-8000-000000000006',
    null, 'real',
    'Пожертвовал деньги бездомному на улице.',
    'ru',
    'Человек пожертвовал деньги бездомному на улице.',
    4, 5.00, 4.50, 'благотворительность'
  ),
  (
    'a0000001-0000-4000-8000-000000000007',
    null, 'real',
    'Списал домашнее задание у одноклассника перед контрольной.',
    'ru',
    'Ученик списал домашнее задание у одноклассника перед контрольной работой.',
    -6, -7.00, -6.50, 'честность'
  ),
  (
    'a0000001-0000-4000-8000-000000000008',
    null, 'hypothetical',
    'Человек догнал незнакомца и вернул ему уроненный телефон.',
    'ru',
    'Человек догнал незнакомца и вернул ему уроненный телефон.',
    7, 8.00, 7.50, 'честность'
  )
on conflict (id) do nothing;
