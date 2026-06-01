create table public.accounts (
  id uuid primary key default gen_random_uuid(),
  supabase_user_id uuid unique references auth.users(id) on delete cascade,
  email text not null,
  status text not null default 'active',
  plan text not null default 'beta',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.accounts enable row level security;

create policy "Users can read own account"
  on public.accounts for select
  using (auth.uid() = supabase_user_id);

create policy "Service role full access"
  on public.accounts for all
  using (auth.role() = 'service_role');
