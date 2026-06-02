create or replace function public.handle_new_user()
returns trigger
security definer
set search_path = ''
as $$
begin
  insert into public.accounts (supabase_user_id, email)
  values (new.id, new.email);
  return new;
end;
$$ language plpgsql;
