import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY

logger = logging.getLogger("kai_api.db")

try:
    supabase_server_key = SUPABASE_SERVICE_KEY or SUPABASE_KEY
    if SUPABASE_URL and supabase_server_key:
        supabase: Client = create_client(SUPABASE_URL, supabase_server_key)
        logger.info("✅ Supabase client initialized")
    else:
        supabase = None
        logger.warning("⚠️ Supabase credentials missing (check config.py)")
except Exception as e:
    supabase = None
    logger.error(f"❌ Failed to initialize Supabase: {e}")

def get_supabase() -> Client:
    return supabase
