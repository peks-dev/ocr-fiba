create table public.api_keys (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references public.accounts(id) on delete cascade,
  key_hash text unique not null,
  key_prefix text not null,
  name text not null default 'default',
  status text not null default 'active',
  created_at timestamptz not null default now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);

create index idx_api_keys_key_hash on public.api_keys(key_hash);
create index idx_api_keys_account_id on public.api_keys(account_id);

alter table public.api_keys enable row level security;

create policy "Service role full access"
  on public.api_keys for all
  using (auth.role() = 'service_role');
