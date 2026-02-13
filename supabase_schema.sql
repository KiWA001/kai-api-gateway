-- Create API Keys Table
create table public.api_keys (
  id uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  name text not null,
  token text not null unique,
  usage_tokens bigint default 0,
  limit_tokens bigint default 1000000, -- Default 1M tokens
  is_active boolean default true
);

-- Indexes for performance
create index idx_api_keys_token on public.api_keys(token);
