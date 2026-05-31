from __future__ import annotations

import logging
import threading
import time
from typing import Any

from db import get_supabase
from local_db import list_api_keys

logger = logging.getLogger("kai_api.auth_cache")

_lock = threading.Lock()
_keys_by_token: dict[str, dict[str, Any]] = {}
_last_loaded_at = 0.0
_loaded_once = False


def refresh_api_key_cache() -> dict[str, Any]:
    global _keys_by_token, _last_loaded_at, _loaded_once

    supabase = get_supabase()
    if not supabase:
        return {"status": "skipped", "reason": "Database unavailable", "count": len(_keys_by_token)}

    try:
        response = supabase.table("kaiapi_api_keys").select("*").execute()
        rows = response.data or []
    except Exception as exc:
        logger.warning("Supabase API key cache load failed, using local fallback: %s", exc)
        rows = list_api_keys()
    next_cache = {
        row["token"]: row
        for row in rows
        if row.get("token") and row.get("is_active", True)
    }

    with _lock:
        _keys_by_token = next_cache
        _last_loaded_at = time.time()
        _loaded_once = True

    logger.info("Loaded %s active API keys into memory", len(next_cache))
    return {"status": "ok", "count": len(next_cache), "loaded_at": _last_loaded_at}


def get_cached_api_key(token: str) -> dict[str, Any] | None:
    if not _loaded_once:
        try:
            refresh_api_key_cache()
        except Exception as exc:
            logger.warning("Initial API key cache load failed: %s", exc)

    with _lock:
        key = _keys_by_token.get(token)
        return dict(key) if key else None


def increment_cached_usage(key_id: str, tokens: int) -> None:
    if tokens <= 0:
        return
    with _lock:
        for key in _keys_by_token.values():
            if str(key.get("id")) == str(key_id):
                key["usage_tokens"] = (key.get("usage_tokens") or 0) + tokens
                return


def api_key_cache_status() -> dict[str, Any]:
    with _lock:
        return {
            "loaded": _loaded_once,
            "count": len(_keys_by_token),
            "last_loaded_at": _last_loaded_at,
        }
