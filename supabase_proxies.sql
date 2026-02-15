-- ============================================
-- K-AI API Gateway - IP/Proxy Management SQL
-- ============================================
-- This script creates tables for managing multiple proxy IPs

-- ============================================
-- Create kaiapi_proxies table for IP management
-- ============================================
CREATE TABLE IF NOT EXISTS kaiapi_proxies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100), -- Optional friendly name (e.g., "USA Proxy 1")
    ip VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    protocol VARCHAR(20) DEFAULT 'http',
    username VARCHAR(255), -- Optional auth
    password VARCHAR(255), -- Optional auth
    country VARCHAR(100),
    city VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT false,
    is_default BOOLEAN NOT NULL DEFAULT false, -- Only one can be default
    last_tested TIMESTAMP WITH TIME ZONE,
    is_working BOOLEAN DEFAULT true,
    response_time_ms INTEGER,
    fail_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    notes TEXT, -- User notes about this proxy
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_kaiapi_proxies_active ON kaiapi_proxies(is_active);
CREATE INDEX IF NOT EXISTS idx_kaiapi_proxies_default ON kaiapi_proxies(is_default) WHERE is_default = true;
CREATE INDEX IF NOT EXISTS idx_kaiapi_proxies_working ON kaiapi_proxies(is_working);

-- ============================================
-- Insert sample proxies (optional examples)
-- ============================================
-- Uncomment to add sample data:
-- INSERT INTO kaiapi_proxies (name, ip, port, protocol, country, is_active, notes) VALUES
--     ('US Proxy 1', '192.168.1.100', 8080, 'http', 'United States', true, 'Main proxy'),
--     ('UK Proxy 1', '10.0.0.50', 3128, 'http', 'United Kingdom', false, 'Backup');

-- ============================================
-- Create trigger to ensure only one default proxy
-- ============================================
CREATE OR REPLACE FUNCTION ensure_single_default_proxy()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_default = true THEN
        -- Set all other proxies to not default
        UPDATE kaiapi_proxies SET is_default = false WHERE id != NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_single_default_proxy ON kaiapi_proxies;
CREATE TRIGGER trigger_single_default_proxy
    BEFORE INSERT OR UPDATE ON kaiapi_proxies
    FOR EACH ROW
    EXECUTE FUNCTION ensure_single_default_proxy();

-- ============================================
-- Create updated_at trigger
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

DROP TRIGGER IF EXISTS update_kaiapi_proxies_updated_at ON kaiapi_proxies;
CREATE TRIGGER update_kaiapi_proxies_updated_at
    BEFORE UPDATE ON kaiapi_proxies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Useful Queries
-- ============================================

-- Get all active proxies:
-- SELECT * FROM kaiapi_proxies WHERE is_active = true ORDER BY created_at DESC;

-- Get default proxy:
-- SELECT * FROM kaiapi_proxies WHERE is_default = true LIMIT 1;

-- Activate a proxy:
-- UPDATE kaiapi_proxies SET is_active = true WHERE id = 1;

-- Deactivate a proxy:
-- UPDATE kaiapi_proxies SET is_active = false WHERE id = 1;

-- Delete a proxy:
-- DELETE FROM kaiapi_proxies WHERE id = 1;

-- Mark proxy as tested:
-- UPDATE kaiapi_proxies SET 
--     last_tested = NOW(), 
--     is_working = true, 
--     response_time_ms = 500,
--     success_count = success_count + 1
-- WHERE id = 1;

-- Mark proxy as failed:
-- UPDATE kaiapi_proxies SET 
--     last_tested = NOW(), 
--     is_working = false,
--     fail_count = fail_count + 1
-- WHERE id = 1;

-- Get proxy statistics:
-- SELECT 
--     COUNT(*) as total,
--     COUNT(*) FILTER (WHERE is_active) as active,
--     COUNT(*) FILTER (WHERE is_working) as working,
--     COUNT(*) FILTER (WHERE is_default) as default_proxy
-- FROM kaiapi_proxies;

-- ============================================
-- Verification
-- ============================================
SELECT 'kaiapi_proxies table created successfully' as message;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'kaiapi_proxies' 
ORDER BY ordinal_position;
