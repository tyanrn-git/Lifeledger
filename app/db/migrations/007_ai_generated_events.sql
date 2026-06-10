do $$ begin
  create type event_source as enum ('seed', 'user', 'ai_generated');
exception when duplicate_object then null;
end $$;

alter table events
  add column if not exists source event_source not null default 'user',
  add column if not exists generation_batch_id uuid,
  add column if not exists content_hash text;

update events set source = 'seed' where author_user_id is null and source = 'user';

create extension if not exists pgcrypto;

update events
set content_hash = left(
  encode(
    digest(
      lower(regexp_replace(trim(coalesce(normalized_text, original_text)), '\s+', ' ', 'g')),
      'sha256'
    ),
    'hex'
  ),
  32
)
where content_hash is null
  and coalesce(normalized_text, original_text) is not null;

create index if not exists idx_events_source on events(source);
create index if not exists idx_events_generation_batch_id on events(generation_batch_id);
create index if not exists idx_events_content_hash on events(content_hash);
