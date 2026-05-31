from engine import AIEngine

import logging
import traceback

logger = logging.getLogger("kai_api.services")

engine = None

try:
    engine = AIEngine()
    logger.info("Services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize services: {e}")
    logger.error(traceback.format_exc())
