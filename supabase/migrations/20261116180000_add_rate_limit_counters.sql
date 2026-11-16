-- Shared run-creation rate limits, used by every Cloud Run instance.
--
-- Events live in the private schema (not exposed by the Data API). The
-- security definer function atomically checks and records a hit. A thin
-- public SECURITY INVOKER wrapper is callable only by service_role via
-- PostgREST (revoke execute from anon/authenticated/public).

create schema if not exists private;

revoke all on schema private from public;
revoke all on schema private from anon, authenticated;
grant usage on schema private to service_role;

create table private.rate_limit_events (
  id bigint generated always as identity primary key,
  bucket_key text not null,
  consumed_at timestamptz not null default now()
);

create index idx_rate_limit_events_key_consumed_at
  on private.rate_limit_events (bucket_key, consumed_at);

alter table private.rate_limit_events enable row level security;

-- Explicit deny-all policy so advisors do not flag "RLS enabled, no policy".
-- The security definer function runs as the table owner and can still write.
-- anon/authenticated have no grant and this policy denies any leftover access.

create policy "No direct access"
  on private.rate_limit_events
  for all
  using (false)
  with check (false);

revoke all on table private.rate_limit_events from public, anon, authenticated;
revoke all on all sequences in schema private from public, anon, authenticated;

create or replace function private.cleanup_rate_limit_events()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_deleted integer;
begin
  delete from private.rate_limit_events
  where consumed_at < pg_catalog.now() - interval '2 days';
  get diagnostics v_deleted = row_count;
  return v_deleted;
end;
$$;

revoke all on function private.cleanup_rate_limit_events() from public, anon, authenticated;
grant execute on function private.cleanup_rate_limit_events() to service_role;

create or replace function private.consume_rate_limit(
  p_key text,
  p_per_minute integer,
  p_per_day integer
)
returns table (
  allowed boolean,
  limit_window text,
  retry_after_seconds integer,
  remaining_minute integer,
  remaining_day integer
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_key text := coalesce(p_key, '');
  v_now timestamptz := pg_catalog.now();
  v_minute_count integer;
  v_day_count integer;
  v_oldest timestamptz;
  v_retry integer;
  v_remaining_minute integer;
  v_remaining_day integer;
begin
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_key, 0));

  -- Opportunistic global cleanup, plus always drop stale rows for this key.
  if pg_catalog.random() < 0.01 then
    perform private.cleanup_rate_limit_events();
  end if;

  delete from private.rate_limit_events
  where bucket_key = v_key
    and consumed_at < v_now - interval '2 days';

  select count(*) into v_minute_count
  from private.rate_limit_events
  where bucket_key = v_key
    and consumed_at > v_now - interval '1 minute';

  select count(*) into v_day_count
  from private.rate_limit_events
  where bucket_key = v_key
    and consumed_at > v_now - interval '1 day';

  v_remaining_minute := case
    when p_per_minute > 0 then case when p_per_minute - v_minute_count > 0 then p_per_minute - v_minute_count else 0 end
    else null
  end;
  v_remaining_day := case
    when p_per_day > 0 then case when p_per_day - v_day_count > 0 then p_per_day - v_day_count else 0 end
    else null
  end;

  if p_per_minute > 0 and v_minute_count >= p_per_minute then
    select min(consumed_at) into v_oldest
    from private.rate_limit_events
    where bucket_key = v_key
      and consumed_at > v_now - interval '1 minute';
    v_retry := pg_catalog.ceil(
      pg_catalog.date_part('epoch', v_oldest + interval '1 minute' - v_now)
    )::integer;
    if v_retry < 1 then
      v_retry := 1;
    end if;
    return query select false, 'minute'::text, v_retry, 0, v_remaining_day;
    return;
  end if;

  if p_per_day > 0 and v_day_count >= p_per_day then
    select min(consumed_at) into v_oldest
    from private.rate_limit_events
    where bucket_key = v_key
      and consumed_at > v_now - interval '1 day';
    v_retry := pg_catalog.ceil(
      pg_catalog.date_part('epoch', v_oldest + interval '1 day' - v_now)
    )::integer;
    if v_retry < 1 then
      v_retry := 1;
    end if;
    return query select false, 'day'::text, v_retry, v_remaining_minute, 0;
    return;
  end if;

  insert into private.rate_limit_events (bucket_key, consumed_at)
  values (v_key, v_now);

  return query select
    true,
    null::text,
    0,
    case
      when p_per_minute > 0 then case when p_per_minute - v_minute_count - 1 > 0 then p_per_minute - v_minute_count - 1 else 0 end
      else null
    end,
    case
      when p_per_day > 0 then case when p_per_day - v_day_count - 1 > 0 then p_per_day - v_day_count - 1 else 0 end
      else null
    end;
end;
$$;

revoke all on function private.consume_rate_limit(text, integer, integer) from public, anon, authenticated;
grant execute on function private.consume_rate_limit(text, integer, integer) to service_role;

-- Invoker wrapper so PostgREST can call this from the public schema without
-- placing a security definer function in an exposed schema. service_role is
-- the only caller; it then executes the private definer function.
create or replace function public.consume_rate_limit(
  p_key text,
  p_per_minute integer,
  p_per_day integer
)
returns table (
  allowed boolean,
  limit_window text,
  retry_after_seconds integer,
  remaining_minute integer,
  remaining_day integer
)
language sql
volatile
security invoker
set search_path = ''
as $$
  select *
  from private.consume_rate_limit(p_key, p_per_minute, p_per_day);
$$;

revoke all on function public.consume_rate_limit(text, integer, integer) from public, anon, authenticated;
grant execute on function public.consume_rate_limit(text, integer, integer) to service_role;
