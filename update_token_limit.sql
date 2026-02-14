-- SQL: Update API Key Token Limits to 1000

-- 1. Update existing keys to have max 1000 tokens
UPDATE api_keys 
SET limit_tokens = 1000 
WHERE limit_tokens > 1000 OR limit_tokens IS NULL;

-- 2. Verify the update
SELECT name, token, usage_tokens, limit_tokens, 
       (usage_tokens::float / limit_tokens * 100) as usage_percent
FROM api_keys 
ORDER BY created_at DESC;

-- 3. To set default for NEW keys (run this once):
-- Alter the table to set default value
ALTER TABLE api_keys 
ALTER COLUMN limit_tokens SET DEFAULT 1000;

-- 4. Optional: Create a trigger to enforce max 1000 on insert/update
CREATE OR REPLACE FUNCTION enforce_token_limit()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.limit_tokens > 1000 THEN
        NEW.limit_tokens := 1000;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS check_token_limit ON api_keys;

CREATE TRIGGER check_token_limit
    BEFORE INSERT OR UPDATE ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION enforce_token_limit();

-- 5. Grant permissions for the trigger
COMMENT ON FUNCTION enforce_token_limit() IS 'Ensures no API key can have more than 1000 tokens limit';
