-- ============================================
-- K-AI API Gateway - Complete Supabase SQL Setup
-- ============================================
-- This script handles both creating tables with KAIAPI_ prefix
-- and migrating data from old tables (if they exist)

-- ============================================
-- STEP 1: Rename existing tables to add KAIAPI_ prefix
-- ============================================

-- Rename api_keys table if it exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'public' 
               AND table_name = 'api_keys') THEN
        ALTER TABLE api_keys RENAME TO KAIAPI_api_keys;
        RAISE NOTICE 'Renamed api_keys to KAIAPI_api_keys';
    END IF;
END $$;

-- Rename model_stats table if it exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'public' 
               AND table_name = 'model_stats') THEN
        ALTER TABLE model_stats RENAME TO KAIAPI_model_stats;
        RAISE NOTICE 'Renamed model_stats to KAIAPI_model_stats';
    END IF;
END $$;

-- Rename provider_sessions table if it exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'public' 
               AND table_name = 'provider_sessions') THEN
        ALTER TABLE provider_sessions RENAME TO KAIAPI_provider_sessions;
        RAISE NOTICE 'Renamed provider_sessions to KAIAPI_provider_sessions';
    END IF;
END $$;

-- Rename provider_states table if it exists (for consistency)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'public' 
               AND table_name = 'provider_states') THEN
        ALTER TABLE provider_states RENAME TO KAIAPI_provider_states;
        RAISE NOTICE 'Renamed provider_states to KAIAPI_provider_states';
    END IF;
END $$;

-- ============================================
-- STEP 2: Create KAIAPI_api_keys table (if not exists)
-- ============================================
CREATE TABLE IF NOT EXISTS KAIAPI_api_keys (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    usage_tokens INTEGER NOT NULL DEFAULT 0,
    limit_tokens INTEGER NOT NULL DEFAULT 1000000,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_KAIAPI_api_keys_token ON KAIAPI_api_keys(token);
CREATE INDEX IF NOT EXISTS idx_KAIAPI_api_keys_is_active ON KAIAPI_api_keys(is_active);

-- ============================================
-- STEP 3: Create KAIAPI_model_stats table (if not exists)
-- ============================================
CREATE TABLE IF NOT EXISTS KAIAPI_model_stats (
    id VARCHAR(255) PRIMARY KEY,
    success INTEGER NOT NULL DEFAULT 0,
    failure INTEGER NOT NULL DEFAULT 0,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    avg_time_ms FLOAT NOT NULL DEFAULT 0,
    total_time_ms FLOAT NOT NULL DEFAULT 0,
    count_samples INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_KAIAPI_model_stats_id ON KAIAPI_model_stats(id);

-- ============================================
-- STEP 4: Create KAIAPI_provider_sessions table (if not exists)
-- ============================================
CREATE TABLE IF NOT EXISTS KAIAPI_provider_sessions (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) UNIQUE NOT NULL,
    cookies JSONB,
    session_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_KAIAPI_provider_sessions_provider ON KAIAPI_provider_sessions(provider);

-- ============================================
-- STEP 5: Create KAIAPI_provider_states table (NEW - for toggle management)
-- ============================================
CREATE TABLE IF NOT EXISTS KAIAPI_provider_states (
    id SERIAL PRIMARY KEY,
    provider_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'api',
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_KAIAPI_provider_states_provider_id ON KAIAPI_provider_states(provider_id);
CREATE INDEX IF NOT EXISTS idx_KAIAPI_provider_states_enabled ON KAIAPI_provider_states(enabled);

-- Insert default providers (if table is empty)
INSERT INTO KAIAPI_provider_states (provider_id, name, type, enabled) VALUES
    ('g4f', 'G4F (Free GPT-4)', 'api', true),
    ('zai', 'Z.ai (GLM-5)', 'api', true),
    ('gemini', 'Google Gemini', 'api', true),
    ('pollinations', 'Pollinations', 'api', true),
    ('huggingchat', 'HuggingChat', 'browser', true),
    ('copilot', 'Microsoft Copilot', 'browser', false),
    ('chatgpt', 'ChatGPT', 'browser', false)
ON CONFLICT (provider_id) DO NOTHING;

-- ============================================
-- STEP 6: Create helper functions and triggers
-- ============================================

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for all tables
DROP TRIGGER IF EXISTS update_KAIAPI_api_keys_updated_at ON KAIAPI_api_keys;
CREATE TRIGGER update_KAIAPI_api_keys_updated_at
    BEFORE UPDATE ON KAIAPI_api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_KAIAPI_model_stats_updated_at ON KAIAPI_model_stats;
CREATE TRIGGER update_KAIAPI_model_stats_updated_at
    BEFORE UPDATE ON KAIAPI_model_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_KAIAPI_provider_sessions_updated_at ON KAIAPI_provider_sessions;
CREATE TRIGGER update_KAIAPI_provider_sessions_updated_at
    BEFORE UPDATE ON KAIAPI_provider_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_KAIAPI_provider_states_updated_at ON KAIAPI_provider_states;
CREATE TRIGGER update_KAIAPI_provider_states_updated_at
    BEFORE UPDATE ON KAIAPI_provider_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- STEP 7: Enable Row Level Security (Optional)
-- ============================================
-- Uncomment the following lines if you want to enable RLS

-- ALTER TABLE KAIAPI_api_keys ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE KAIAPI_model_stats ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE KAIAPI_provider_sessions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE KAIAPI_provider_states ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations (adjust as needed)
-- CREATE POLICY "Allow all operations on KAIAPI_api_keys" 
--     ON KAIAPI_api_keys 
--     FOR ALL 
--     TO anon, authenticated 
--     USING (true) 
--     WITH CHECK (true);

-- CREATE POLICY "Allow all operations on KAIAPI_model_stats" 
--     ON KAIAPI_model_stats 
--     FOR ALL 
--     TO anon, authenticated 
--     USING (true) 
--     WITH CHECK (true);

-- CREATE POLICY "Allow all operations on KAIAPI_provider_sessions" 
--     ON KAIAPI_provider_sessions 
--     FOR ALL 
--     TO anon, authenticated 
--     USING (true) 
--     WITH CHECK (true);

-- CREATE POLICY "Allow all operations on KAIAPI_provider_states" 
--     ON KAIAPI_provider_states 
--     FOR ALL 
--     TO anon, authenticated 
--     USING (true) 
--     WITH CHECK (true);

-- ============================================
-- VERIFICATION: Check all created tables
-- ============================================
SELECT 'Tables created successfully:' as message;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'KAIAPI_%'
ORDER BY table_name;
