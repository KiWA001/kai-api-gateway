-- Supabase SQL Schema for Provider Session Management
-- This stores cookies/sessions for all browser-based providers

-- Enable RLS (Row Level Security) for security
alter table if exists provider_sessions enable row level security;

-- Provider Sessions Table
-- Stores session cookies and metadata for browser-based providers
create table if not exists provider_sessions (
    id uuid default gen_random_uuid() primary key,
    provider text not null,                    -- 'huggingchat', 'zai', 'gemini', etc.
    session_data jsonb not null,               -- cookies, tokens, etc.
    conversation_count integer default 0,      -- number of conversations used
    max_conversations integer default 50,      -- max before requiring re-login
    expires_at timestamp with time zone,       -- session expiration
    last_used_at timestamp with time zone default now(),
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now(),
    
    -- Ensure unique provider sessions
    constraint unique_provider unique (provider)
);

-- Indexes for performance
create index if not exists idx_provider_sessions_provider on provider_sessions(provider);
create index if not exists idx_provider_sessions_expires on provider_sessions(expires_at);

-- Function to automatically update updated_at
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Trigger to auto-update updated_at
drop trigger if exists update_provider_sessions_updated_at on provider_sessions;
create trigger update_provider_sessions_updated_at
    before update on provider_sessions
    for each row
    execute function update_updated_at_column();

-- RLS Policy: Allow all operations (since this is for backend use)
-- In production, you might want to restrict this to specific service roles
create policy "Allow all operations on provider_sessions"
    on provider_sessions
    for all
    to anon, authenticated
    using (true)
    with check (true);

-- Comments for documentation
comment on table provider_sessions is 'Stores authentication sessions for browser-based AI providers';
comment on column provider_sessions.provider is 'Provider name: huggingchat, zai, gemini, etc.';
comment on column provider_sessions.session_data is 'JSON containing cookies, tokens, and other session info';
comment on column provider_sessions.conversation_count is 'Number of API calls made with this session';
comment on column provider_sessions.max_conversations is 'Maximum allowed conversations before re-login required';
comment on column provider_sessions.expires_at is 'When this session expires and requires re-login';

-- Insert/Update function for upserting sessions
create or replace function upsert_provider_session(
    p_provider text,
    p_session_data jsonb,
    p_conversation_count integer default 0,
    p_max_conversations integer default 50,
    p_expires_at timestamp with time zone default null
)
returns uuid as $$
declare
    v_id uuid;
begin
    insert into provider_sessions (provider, session_data, conversation_count, max_conversations, expires_at)
    values (p_provider, p_session_data, p_conversation_count, p_max_conversations, p_expires_at)
    on conflict (provider) 
    do update set 
        session_data = excluded.session_data,
        conversation_count = excluded.conversation_count,
        max_conversations = excluded.max_conversations,
        expires_at = excluded.expires_at,
        last_used_at = now()
    returning id into v_id;
    
    return v_id;
end;
$$ language plpgsql;

-- Function to increment conversation count
create or replace function increment_conversation_count(p_provider text)
returns void as $$
begin
    update provider_sessions 
    set conversation_count = conversation_count + 1,
        last_used_at = now()
    where provider = p_provider;
end;
$$ language plpgsql;

-- Grant permissions
grant all on provider_sessions to anon, authenticated;
grant all on sequence provider_sessions_id_seq to anon, authenticated;
grant execute on function upsert_provider_session to anon, authenticated;
grant execute on function increment_conversation_count to anon, authenticated;

-- Sample query to check current sessions:
-- select provider, conversation_count, max_conversations, expires_at, last_used_at from provider_sessions;

-- Sample query to clean up expired sessions:
-- delete from provider_sessions where expires_at < now();
