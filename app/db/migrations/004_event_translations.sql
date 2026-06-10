create table if not exists event_translations (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  language_code text not null,
  translated_text text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(event_id, language_code)
);

create index if not exists idx_event_translations_event_id on event_translations(event_id);
create index if not exists idx_event_translations_language_code on event_translations(language_code);
