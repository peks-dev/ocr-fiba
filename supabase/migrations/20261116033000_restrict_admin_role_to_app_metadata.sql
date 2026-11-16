-- Admin role may only be granted from Auth app_metadata (raw_app_meta_data),
-- which is service-role-managed. user_metadata is user-editable and must not
-- be able to self-promote to admin. Invitation fields (assigned_demo, invited_by)
-- may still be copied from user_metadata so the existing invite flow works.
--
-- Note: the previous admin-invite migration is applied remotely as
-- 20260620085016_add_admin_invite_demo_access, while this repo's file is
-- named 20260620090000_add_admin_invite_demo_access.sql. Do not re-apply that
-- migration; only apply this new one.

create or replace function public.handle_new_user()
returns trigger
security definer
set search_path = ''
as $$
declare
  requested_role text := coalesce(new.raw_app_meta_data ->> 'role', 'tester');
  requested_demo text := coalesce(
    new.raw_app_meta_data ->> 'assigned_demo',
    new.raw_user_meta_data ->> 'assigned_demo'
  );
  inviter_account_id uuid := nullif(
    coalesce(
      new.raw_app_meta_data ->> 'invited_by',
      new.raw_user_meta_data ->> 'invited_by'
    ),
    ''
  )::uuid;
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
