-- Create a simple key-value store for application settings
create table if not exists kaiapi_settings (
  key text primary key,
  value jsonb not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS (Optional, but good practice)
alter table kaiapi_settings enable row level security;

-- Allow public read/write (since we use service key mostly, or anon if public)
-- Adjust policies as needed for your security model
create policy "Allow generic access" on kaiapi_settings for all using (true) with check (true);
