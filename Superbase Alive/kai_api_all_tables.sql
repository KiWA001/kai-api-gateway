create table if not exists public.kaiapi_api_keys (
  id bigserial primary key,
  name text not null,
  token text unique not null,
  usage_tokens integer not null default 0,
  limit_tokens integer not null default 1000000,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_kaiapi_api_keys_token
on public.kaiapi_api_keys(token);

create index if not exists idx_kaiapi_api_keys_active
on public.kaiapi_api_keys(is_active);

create table if not exists public.kaiapi_model_stats (
  id text primary key,
  success integer not null default 0,
  failure integer not null default 0,
  consecutive_failures integer not null default 0,
  avg_time_ms double precision not null default 0,
  total_time_ms double precision not null default 0,
  count_samples integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.kaiapi_settings (
  key text primary key,
  value jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.kaiapi_oauth_auth_files (
  path text primary key,
  provider text not null default 'unknown',
  content jsonb,
  content_text text not null,
  size_bytes integer not null default 0,
  modified_at timestamptz,
  synced_at timestamptz not null default now(),
  is_active boolean not null default true
);

create index if not exists idx_kaiapi_oauth_auth_files_provider
on public.kaiapi_oauth_auth_files(provider);

create index if not exists idx_kaiapi_oauth_auth_files_active
on public.kaiapi_oauth_auth_files(is_active);

create table if not exists public.keepalive (
  id integer primary key,
  touched_at timestamptz not null default now()
);

insert into public.keepalive (id)
values (1)
on conflict (id) do nothing;

create or replace function public.kaiapi_touch_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists kaiapi_api_keys_updated_at on public.kaiapi_api_keys;
create trigger kaiapi_api_keys_updated_at
before update on public.kaiapi_api_keys
for each row execute function public.kaiapi_touch_updated_at();

drop trigger if exists kaiapi_model_stats_updated_at on public.kaiapi_model_stats;
create trigger kaiapi_model_stats_updated_at
before update on public.kaiapi_model_stats
for each row execute function public.kaiapi_touch_updated_at();

drop trigger if exists kaiapi_settings_updated_at on public.kaiapi_settings;
create trigger kaiapi_settings_updated_at
before update on public.kaiapi_settings
for each row execute function public.kaiapi_touch_updated_at();

alter table public.kaiapi_api_keys disable row level security;
alter table public.kaiapi_model_stats disable row level security;
alter table public.kaiapi_settings disable row level security;
alter table public.kaiapi_oauth_auth_files disable row level security;
alter table public.keepalive disable row level security;

drop policy if exists "anon manages api keys" on public.kaiapi_api_keys;
drop policy if exists "anon manages model stats" on public.kaiapi_model_stats;
drop policy if exists "anon manages settings" on public.kaiapi_settings;
drop policy if exists "service role manages oauth auth files" on public.kaiapi_oauth_auth_files;
drop policy if exists "allow keepalive read" on public.keepalive;
