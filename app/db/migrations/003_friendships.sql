do $$ begin
  create type friendship_status as enum ('pending', 'accepted', 'rejected', 'blocked');
exception when duplicate_object then null;
end $$;

create table if not exists friendships (
  id uuid primary key default gen_random_uuid(),
  requester_user_id uuid not null references users(id) on delete cascade,
  addressee_user_id uuid not null references users(id) on delete cascade,
  status friendship_status not null default 'pending',
  created_at timestamptz not null default now(),
  responded_at timestamptz,
  constraint no_self_friendship check (requester_user_id <> addressee_user_id),
  unique(requester_user_id, addressee_user_id)
);

create index if not exists idx_friendships_requester on friendships(requester_user_id);
create index if not exists idx_friendships_addressee on friendships(addressee_user_id);
create index if not exists idx_friendships_status on friendships(status);
