from engine import AIEngine
from search_engine import SearchEngine

import logging
import traceback

logger = logging.getLogger("kai_api.services")

# Singleton instances placeholder
engine = None
search_engine = None

try:
    engine = AIEngine()
    search_engine = SearchEngine()
    logger.info("✅ Services initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize services: {e}")
    logger.error(traceback.format_exc())
    # We don't raise here to allow the app to start (and report error via /health)
    # But wait, if engine is None, v1_router will crash when accessed.
    # We should define a dummy engine? Or handle None in routers.

