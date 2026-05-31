-- K-AI API Gateway - Supabase SQL Setup

CREATE TABLE IF NOT EXISTS kaiapi_api_keys (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    usage_tokens INTEGER NOT NULL DEFAULT 0,
    limit_tokens INTEGER NOT NULL DEFAULT 1000000,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kaiapi_api_keys_token ON kaiapi_api_keys(token);
CREATE INDEX IF NOT EXISTS idx_kaiapi_api_keys_is_active ON kaiapi_api_keys(is_active);

CREATE TABLE IF NOT EXISTS kaiapi_model_stats (
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

CREATE INDEX IF NOT EXISTS idx_kaiapi_model_stats_id ON kaiapi_model_stats(id);

CREATE TABLE IF NOT EXISTS kaiapi_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_kaiapi_api_keys_updated_at ON kaiapi_api_keys;
CREATE TRIGGER update_kaiapi_api_keys_updated_at
    BEFORE UPDATE ON kaiapi_api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_kaiapi_model_stats_updated_at ON kaiapi_model_stats;
CREATE TRIGGER update_kaiapi_model_stats_updated_at
    BEFORE UPDATE ON kaiapi_model_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_kaiapi_settings_updated_at ON kaiapi_settings;
CREATE TRIGGER update_kaiapi_settings_updated_at
    BEFORE UPDATE ON kaiapi_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
