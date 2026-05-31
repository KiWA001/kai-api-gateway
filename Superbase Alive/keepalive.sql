create table if not exists public.keepalive (
  id integer primary key,
  touched_at timestamptz not null default now()
);

insert into public.keepalive (id)
values (1)
on conflict (id) do nothing;

alter table public.keepalive disable row level security;
