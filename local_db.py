from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOCAL_DB_PATH = Path(os.getenv("KAI_LOCAL_DB_PATH", "/tmp/kai-api-local-db.json"))


def _read() -> dict[str, Any]:
    try:
        return json.loads(LOCAL_DB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"api_keys": []}


def _write(data: dict[str, Any]) -> None:
    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_DB_PATH.write_text(json.dumps(data), encoding="utf-8")


def list_api_keys() -> list[dict[str, Any]]:
    return list(_read().get("api_keys", []))


def create_api_key(name: str, limit_tokens: int | None = 1000000) -> dict[str, Any]:
    data = _read()
    keys = data.setdefault("api_keys", [])
    row = {
        "id": f"local-{secrets.token_urlsafe(8)}",
        "name": name,
        "token": f"sk-kai-{secrets.token_urlsafe(16)}",
        "usage_tokens": 0,
        "limit_tokens": limit_tokens or 1000000,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
    }
    keys.insert(0, row)
    _write(data)
    return row


def delete_api_key(key_id: str) -> bool:
    data = _read()
    before = len(data.get("api_keys", []))
    data["api_keys"] = [key for key in data.get("api_keys", []) if str(key.get("id")) != str(key_id)]
    _write(data)
    return len(data["api_keys"]) != before


def reset_usage(key_id: str) -> bool:
    data = _read()
    found = False
    for key in data.get("api_keys", []):
        if str(key.get("id")) == str(key_id):
            key["usage_tokens"] = 0
            found = True
            break
    _write(data)
    return found


def lookup_api_key(token: str) -> dict[str, Any] | None:
    for key in list_api_keys():
        if key.get("token") == token:
            return key
    return None


def increment_usage(key_id: str, tokens: int) -> None:
    if tokens <= 0:
        return
    data = _read()
    for key in data.get("api_keys", []):
        if str(key.get("id")) == str(key_id):
            key["usage_tokens"] = (key.get("usage_tokens") or 0) + tokens
            break
    _write(data)
