alter table public.accounts
  add column role text not null default 'tester',
  add column assigned_demo text default 'player',
  add column invited_by uuid references public.accounts(id) on delete set null,
  add column invited_at timestamptz,
  add column accepted_at timestamptz;

alter table public.accounts
  add constraint accounts_role_check check (role in ('admin', 'tester')),
  add constraint accounts_assigned_demo_check check (assigned_demo is null or assigned_demo in ('referee', 'player', 'club')),
  add constraint accounts_tester_assigned_demo_check check (role <> 'tester' or assigned_demo is not null);

create index idx_accounts_role on public.accounts(role);
create index idx_accounts_assigned_demo on public.accounts(assigned_demo);

create table public.admin_invitations (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  assigned_demo text not null check (assigned_demo in ('referee', 'player', 'club')),
  status text not null default 'invited' check (status in ('invited', 'accepted', 'cancelled', 'failed')),
  invited_by uuid references public.accounts(id) on delete set null,
  invited_user_id uuid references auth.users(id) on delete set null,
  error_message text,
  created_at timestamptz not null default now(),
  accepted_at timestamptz,
  updated_at timestamptz not null default now()
);

create index idx_admin_invitations_email on public.admin_invitations(lower(email));
create index idx_admin_invitations_status on public.admin_invitations(status);
create index idx_admin_invitations_invited_by on public.admin_invitations(invited_by);

alter table public.admin_invitations enable row level security;

create policy "Service role full access"
  on public.admin_invitations for all
  using (auth.role() = 'service_role');

create or replace function public.handle_new_user()
returns trigger
security definer
set search_path = ''
as $$
declare
  requested_role text := coalesce(new.raw_user_meta_data ->> 'role', 'tester');
  requested_demo text := new.raw_user_meta_data ->> 'assigned_demo';
  inviter_account_id uuid := nullif(new.raw_user_meta_data ->> 'invited_by', '')::uuid;
begin
  insert into public.accounts (supabase_user_id, email, role, assigned_demo, invited_by, invited_at)
  values (
    new.id,
    new.email,
    case when requested_role = 'admin' then 'admin' else 'tester' end,
    case
      when requested_role = 'admin' then null
      when requested_demo in ('referee', 'player', 'club') then requested_demo
      else 'player'
    end,
    inviter_account_id,
    case when inviter_account_id is not null then now() else null end
  );
  return new;
end;
$$ language plpgsql;

revoke execute on function public.handle_new_user() from public, anon, authenticated;
