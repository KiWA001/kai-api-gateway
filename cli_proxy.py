"""
CLIProxyAPI integration helpers.

The Go sidecar owns OAuth/token storage and provider-specific routing. This
module keeps the Python API thin: it forwards management and inference requests
to the local sidecar and falls back to the embedded model catalog for docs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


CLI_PROXY_ENABLED = os.getenv("KAI_CLI_PROXY_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
CLI_PROXY_URL = os.getenv("KAI_CLI_PROXY_URL", "http://127.0.0.1:8317").rstrip("/")
CLI_PROXY_API_KEY = os.getenv("KAI_CLI_PROXY_API_KEY", "sk-kai-cli-proxy")
CLI_PROXY_MANAGEMENT_KEY = os.getenv(
    "KAI_CLI_PROXY_MANAGEMENT_KEY",
    "sk-kai-cli-management",
)
CLI_PROXY_TIMEOUT = float(os.getenv("KAI_CLI_PROXY_TIMEOUT", "120"))
CLI_PROXY_AUTH_DIR = Path(os.getenv("KAI_CLI_PROXY_AUTH_DIR", "/tmp/cliproxy/auths"))
OAUTH_SESSION_TABLE = os.getenv("KAI_OAUTH_SESSION_TABLE", "kaiapi_oauth_auth_files")

CLI_PROXY_MODEL_CATALOG = Path(__file__).parent / "CLIProxyAPI-main" / "internal" / "registry" / "models" / "models.json"


AUTH_PROVIDERS: dict[str, dict[str, str]] = {
    "codex": {
        "label": "Codex (OpenAI)",
        "management_endpoint": "codex-auth-url",
        "callback_provider": "codex",
    },
    "antigravity": {
        "label": "Google Antigravity",
        "management_endpoint": "antigravity-auth-url",
        "callback_provider": "antigravity",
    },
    "gemini": {
        "label": "Gemini CLI",
        "management_endpoint": "gemini-cli-auth-url",
        "callback_provider": "gemini",
    },
    "claude": {
        "label": "Claude Code",
        "management_endpoint": "anthropic-auth-url",
        "callback_provider": "anthropic",
    },
    "xai": {
        "label": "xAI / Grok",
        "management_endpoint": "xai-auth-url",
        "callback_provider": "xai",
    },
    "kimi": {
        "label": "Kimi",
        "management_endpoint": "kimi-auth-url",
        "callback_provider": "kimi",
    },
}

AUTH_PROVIDER_ALIASES = {
    "openai": "codex",
    "anthropic": "claude",
    "claude-code": "claude",
    "google": "gemini",
    "anti-gravity": "antigravity",
    "grok": "xai",
    "x-ai": "xai",
    "x.ai": "xai",
}


PUBLIC_CLI_MODEL_ALIASES: dict[str, str] = {
    # Anti-Gravity OAuth
    "anti-gravity-gemini-3.5-flash-low": "gemini-3.5-flash-low",
    "anti-gravity-gemini-3.1-pro-low": "gemini-3.1-pro-low",
    "anti-gravity-gemini-3-flash": "gemini-3-flash",
    "anti-gravity-gemini-3-pro-high": "gemini-3-pro-high",
    "anti-gravity-claude-sonnet-4-6": "claude-sonnet-4-6",
    # Codex / OpenAI OAuth
    "codex-gpt-5.5": "gpt-5.5",
    "codex-gpt-5.4": "gpt-5.4",
    "codex-gpt-5.4-mini": "gpt-5.4-mini",
    "codex-gpt-5.2": "gpt-5.2",
    "codex-gpt-5.3-codex": "gpt-5.3-codex",
    # Gemini CLI OAuth
    "gemini-3.5-flash": "gemini-3.5-flash",
    "gemini-3.1-pro-preview": "gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite-preview": "gemini-3.1-flash-lite-preview",
    "gemini-2.5-pro": "gemini-2.5-pro",
    "gemini-2.5-flash": "gemini-2.5-flash",
    "gemini-2.5-flash-lite": "gemini-2.5-flash-lite",
    "gemini-3-pro-preview": "gemini-3-pro-preview",
    "gemini-3-flash-preview": "gemini-3-flash-preview",
    # Claude OAuth
    "claude-opus-4-7": "claude-opus-4-7",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-sonnet-4-5": "claude-sonnet-4-5",
    "claude-opus-4-1": "claude-opus-4-1-20250805",
    "claude-3.7-sonnet": "claude-3-7-sonnet-20250219",
    # xAI OAuth
    "xai-grok-build": "grok-build-0.1",
    "xai-grok-4.3": "grok-4.3",
    "xai-grok-3-mini": "grok-3-mini",
    # Kimi OAuth
    "kimi-k2.6": "kimi-k2.6",
    "kimi-k2": "kimi-k2",
    "kimi-k2.5": "kimi-k2.5",
    "kimi-k2-thinking": "kimi-k2-thinking",
}

LEGACY_CLI_MODEL_ALIASES: dict[str, str] = {
    "cliproxy-codex-gpt-5.5": "gpt-5.5",
    "cliproxy-codex-gpt-5.4": "gpt-5.4",
    "cliproxy-codex-gpt-5.4-mini": "gpt-5.4-mini",
    "cliproxy-codex-gpt-5.2": "gpt-5.2",
    "cliproxy-codex-gpt-5.3-codex": "gpt-5.3-codex",
    "cliproxy-antigravity-gemini-3.5-flash-low": "gemini-3.5-flash-low",
    "cliproxy-antigravity-gemini-3.1-pro-low": "gemini-3.1-pro-low",
    "cliproxy-antigravity-gemini-3-flash": "gemini-3-flash",
    "cliproxy-antigravity-gemini-3-pro-high": "gemini-3-pro-high",
    "cliproxy-antigravity-claude-sonnet-4-6": "claude-sonnet-4-6",
    "cliproxy-gemini-3.5-flash": "gemini-3.5-flash",
    "cliproxy-gemini-3.1-pro-preview": "gemini-3.1-pro-preview",
    "cliproxy-gemini-3.1-flash-lite-preview": "gemini-3.1-flash-lite-preview",
    "cliproxy-gemini-2.5-pro": "gemini-2.5-pro",
    "cliproxy-gemini-2.5-flash": "gemini-2.5-flash",
    "cliproxy-gemini-2.5-flash-lite": "gemini-2.5-flash-lite",
    "cliproxy-gemini-3-pro-preview": "gemini-3-pro-preview",
    "cliproxy-gemini-3-flash-preview": "gemini-3-flash-preview",
    "cliproxy-claude-opus-4-7": "claude-opus-4-7",
    "cliproxy-claude-sonnet-4-6": "claude-sonnet-4-6",
    "cliproxy-claude-sonnet-4-5": "claude-sonnet-4-5",
    "cliproxy-claude-opus-4-1": "claude-opus-4-1-20250805",
    "cliproxy-claude-3.7-sonnet": "claude-3-7-sonnet-20250219",
    "cliproxy-xai-grok-build": "grok-build-0.1",
    "cliproxy-xai-grok-4.3": "grok-4.3",
    "cliproxy-xai-grok-3-mini": "grok-3-mini",
    "cliproxy-kimi-k2.6": "kimi-k2.6",
    "cliproxy-kimi-k2": "kimi-k2",
    "cliproxy-kimi-k2.5": "kimi-k2.5",
    "cliproxy-kimi-k2-thinking": "kimi-k2-thinking",
}

CLI_MODEL_ALIASES: dict[str, str] = {
    **PUBLIC_CLI_MODEL_ALIASES,
    **LEGACY_CLI_MODEL_ALIASES,
}

# Reverse map: target model name -> owning provider
# e.g. "gemini-3.5-flash-low" -> "antigravity"  (NOT "gemini")
# Built from PUBLIC_CLI_MODEL_ALIASES by resolving each key's provider
def _build_reverse_alias_map() -> dict[str, str]:
    result: dict[str, str] = {}
    for alias_key, target in PUBLIC_CLI_MODEL_ALIASES.items():
        # Determine provider from the alias key (which always has clear prefixes)
        provider = "cli"
        for prefix in AUTH_PROVIDERS:
            if alias_key.startswith(f"{prefix}-"):
                provider = prefix
                break
        if provider == "cli":
            for alias_pfx, canonical in AUTH_PROVIDER_ALIASES.items():
                if alias_key.startswith(f"{alias_pfx}-"):
                    provider = canonical
                    break
        if provider != "cli":
            result[target] = provider
    return result

_REVERSE_ALIAS_MAP: dict[str, str] = _build_reverse_alias_map()

MODEL_SETTINGS_KEY = "enabled_cli_models"
DEFAULT_ENABLED_CLI_MODELS = list(PUBLIC_CLI_MODEL_ALIASES.keys())
LOCAL_SETTINGS_PATH = Path(os.getenv("KAI_LOCAL_SETTINGS_PATH", "/tmp/kai-api-settings.json"))


def cli_model_provider(model: str) -> str:
    """Identify the provider for a model string, supporting dynamic prefixes."""
    # First: check if this is a known target of an aliased model (reverse lookup).
    # This handles cases like "gemini-3.5-flash-low" which belongs to "antigravity",
    # NOT the "gemini" provider, even though it starts with "gemini-".
    if model in _REVERSE_ALIAS_MAP:
        return _REVERSE_ALIAS_MAP[model]

    # Check for explicit alias keys (forward lookup, catches both public and legacy)
    if model in CLI_MODEL_ALIASES:
        target = CLI_MODEL_ALIASES[model]
        # Only recurse if the target differs (avoid infinite loop)
        if target != model:
            return cli_model_provider(target)

    # Check for explicit provider prefixes (dynamic model names like "codex-gpt-custom")
    for prefix in AUTH_PROVIDERS:
        if model.startswith(f"{prefix}-"):
            return prefix

    # Check for aliased prefixes (e.g. anti-gravity-)
    for alias, canonical in AUTH_PROVIDER_ALIASES.items():
        if model.startswith(f"{alias}-"):
            return canonical

    return "cli"


def canonical_auth_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    normalized = AUTH_PROVIDER_ALIASES.get(normalized, normalized)
    if normalized not in AUTH_PROVIDERS:
        raise ValueError(
            "Unsupported CLI auth provider. Use one of: "
            + ", ".join(sorted(AUTH_PROVIDERS))
        )
    return normalized


def cli_management_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {CLI_PROXY_MANAGEMENT_KEY}"}


def cli_api_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {CLI_PROXY_API_KEY}"}
    if extra:
        headers.update(extra)
    return headers


async def cli_management_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not CLI_PROXY_ENABLED:
        raise RuntimeError("CLI proxy integration is disabled")

    async with httpx.AsyncClient(timeout=CLI_PROXY_TIMEOUT) as client:
        response = await client.request(
            method,
            f"{CLI_PROXY_URL}/v0/management/{path.lstrip('/')}",
            params=params,
            json=json_body,
            headers=cli_management_headers(),
        )

    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text}

    if response.status_code >= 400:
        message = payload.get("error") or payload.get("message") or response.text
        raise RuntimeError(str(message))

    return payload


async def disable_cli_auth_session(auth_id: str) -> bool:
    """Disable a specific CLI auth session via the management API."""
    if not CLI_PROXY_ENABLED:
        return False
    try:
        await cli_management_request(
            "PATCH",
            "auth-files/status",
            json_body={"name": auth_id, "disabled": True},
        )
        return True
    except Exception as e:
        print(f"Failed to disable auth session {auth_id}: {e}")
        return False


async def enable_cli_auth_session(auth_id: str) -> bool:
    """Enable a specific CLI auth session via the management API."""
    if not CLI_PROXY_ENABLED:
        return False
    try:
        await cli_management_request(
            "PATCH",
            "auth-files/status",
            json_body={"name": auth_id, "disabled": False},
        )
        return True
    except Exception as e:
        print(f"Failed to enable auth session {auth_id}: {e}")
        return False


async def cli_api_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    content: bytes | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    if not CLI_PROXY_ENABLED:
        raise RuntimeError("CLI proxy integration is disabled")

    clean_headers = {}
    for key, value in (headers or {}).items():
        key_lower = key.lower()
        if key_lower in {"host", "content-length", "authorization"}:
            continue
        clean_headers[key] = value

    async with httpx.AsyncClient(timeout=CLI_PROXY_TIMEOUT) as client:
        return await client.request(
            method,
            f"{CLI_PROXY_URL}/{path.lstrip('/')}",
            params=params,
            content=content,
            json=json_body,
            headers=cli_api_headers(clean_headers),
        )


def resolve_cli_model(model: str | None) -> str:
    """Resolve a model name, optionally encoding the provider for systemic routing."""
    if not model:
        return PUBLIC_CLI_MODEL_ALIASES[DEFAULT_ENABLED_CLI_MODELS[0]]

    # Check forward aliases first (public + legacy)
    if model in CLI_MODEL_ALIASES:
        resolved = CLI_MODEL_ALIASES[model]
        provider = cli_model_provider(model)
        # Re-attach the provider for sidecar routing (e.g. "antigravity:gemini-3.5-flash-low")
        if provider != "cli" and ":" not in resolved and "/" not in resolved:
            return f"{provider}:{resolved}"
        return resolved

    # Check if this is itself a target model name (reverse alias lookup).
    # e.g. someone calls the API directly with "gemini-3.5-flash-low" instead
    # of "anti-gravity-gemini-3.5-flash-low".  We know the owning provider from
    # the reverse map, so we can route correctly without stripping any prefix.
    if model in _REVERSE_ALIAS_MAP:
        provider = _REVERSE_ALIAS_MAP[model]
        return f"{provider}:{model}"

    # Handle dynamic prefixes: detect provider and return in provider:model format
    provider = cli_model_provider(model)
    if provider != "cli":
        # Strip the known prefix to get the bare model ID
        prefixes = [f"{provider}-"] + [f"{a}-" for a, c in AUTH_PROVIDER_ALIASES.items() if c == provider]
        for p in prefixes:
            if model.startswith(p):
                return f"{provider}:{model[len(p):]}"

    return model


def get_cli_provider_models() -> list[str]:
    return list(PUBLIC_CLI_MODEL_ALIASES.keys())


def models_for_auth_providers(providers: set[str] | list[str]) -> list[str]:
    active = {AUTH_PROVIDER_ALIASES.get(str(provider).strip().lower(), str(provider).strip().lower()) for provider in providers}
    return [model for model in PUBLIC_CLI_MODEL_ALIASES if cli_model_provider(model) in active]


def _read_local_settings() -> dict[str, Any]:
    try:
        return json.loads(LOCAL_SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_local_settings(settings: dict[str, Any]) -> None:
    LOCAL_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_SETTINGS_PATH.write_text(json.dumps(settings), encoding="utf-8")


def _normalize_enabled_models(models: Any, *, default_if_missing: bool) -> list[str]:
    if not isinstance(models, list):
        return DEFAULT_ENABLED_CLI_MODELS.copy() if default_if_missing else []
    valid = set(PUBLIC_CLI_MODEL_ALIASES)
    return [model for model in models if isinstance(model, str) and model in valid]


def get_enabled_cli_models() -> list[str]:
    try:
        from db import get_supabase

        supabase = get_supabase()
        if supabase:
            result = supabase.table("kaiapi_settings").select("value").eq("key", MODEL_SETTINGS_KEY).execute()
            if result.data:
                return _normalize_enabled_models(result.data[0].get("value"), default_if_missing=False)
    except Exception:
        pass

    local_settings = _read_local_settings()
    if MODEL_SETTINGS_KEY in local_settings:
        return _normalize_enabled_models(local_settings.get(MODEL_SETTINGS_KEY), default_if_missing=False)
    return DEFAULT_ENABLED_CLI_MODELS.copy()


def _auth_file_values(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("files", "auth_files", "data", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _auth_file_provider(file: dict[str, Any]) -> str | None:
    haystack = " ".join(
        str(file.get(key, ""))
        for key in ("provider", "auth_provider", "type", "label", "name", "path", "id")
    ).lower()
    if "antigravity" in haystack or "anti-gravity" in haystack:
        return "antigravity"
    if "codex" in haystack or "openai" in haystack:
        return "codex"
    if "gemini" in haystack:
        return "gemini"
    if "anthropic" in haystack or "claude" in haystack:
        return "claude"
    if "xai" in haystack or "grok" in haystack:
        return "xai"
    if "kimi" in haystack:
        return "kimi"
    return None


def _auth_file_ready(file: dict[str, Any]) -> bool:
    if file.get("disabled") or file.get("unavailable"):
        return False
    status = str(file.get("status", "")).strip().lower()
    if any(term in status for term in ("disabled", "expired", "invalid", "unauthorized", "error", "failed")):
        return False
    cooldown = _parse_datetime(
        file.get("next_retry_after")
        or file.get("nextRetryAfter")
        or file.get("next_retry")
        or (file.get("quota") or {}).get("next_recover_at")
    )
    if cooldown and cooldown > datetime.now(timezone.utc):
        return False
    return True


async def get_active_cli_auth_providers() -> set[str]:
    try:
        payload = await cli_management_request("GET", "auth-files")
    except Exception:
        return set()
    providers: set[str] = set()
    for file in _auth_file_values(payload):
        provider = _auth_file_provider(file)
        if provider and _auth_file_ready(file):
            providers.add(provider)
    return providers


async def get_runtime_enabled_cli_models() -> list[str]:
    active_models = set(models_for_auth_providers(await get_active_cli_auth_providers()))
    if not active_models:
        return []
    selected = get_enabled_cli_models()
    return [model for model in selected if model in active_models]


def set_enabled_cli_models(models: list[str]) -> list[str]:
    enabled = _normalize_enabled_models(models, default_if_missing=False)
    saved = False
    try:
        from db import get_supabase

        supabase = get_supabase()
        if supabase:
            supabase.table("kaiapi_settings").upsert(
                {"key": MODEL_SETTINGS_KEY, "value": enabled}
            ).execute()
            saved = True
    except Exception:
        saved = False

    if not saved:
        local_settings = _read_local_settings()
        local_settings[MODEL_SETTINGS_KEY] = enabled
        _write_local_settings(local_settings)
    return enabled


def is_cli_model_enabled(model: str | None) -> bool:
    if not model or model == "auto":
        return True
        
    # If it uses a dynamic prefix, we allow it (as requested by the user)
    prefixes = ["antigravity-", "codex-", "gemini-", "claude-", "xai-", "kimi-"]
    if any(model.startswith(p) for p in prefixes):
        return True

    public_name = model if model in PUBLIC_CLI_MODEL_ALIASES else None
    if not public_name:
        for alias, target in LEGACY_CLI_MODEL_ALIASES.items():
            if alias == model:
                for clean_alias, clean_target in PUBLIC_CLI_MODEL_ALIASES.items():
                    if clean_target == target:
                        public_name = clean_alias
                        break
                break
    return bool(public_name and public_name in set(get_enabled_cli_models()))


def load_static_model_catalog() -> dict[str, Any]:
    try:
        with CLI_PROXY_MODEL_CATALOG.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def flattened_static_cli_models() -> list[dict[str, Any]]:
    catalog = load_static_model_catalog()
    rows: list[dict[str, Any]] = []
    for channel, models in catalog.items():
        if not isinstance(models, list):
            continue
        for model in models:
            if not isinstance(model, dict):
                continue
            model_id = model.get("id") or model.get("name")
            if not model_id:
                continue
            rows.append(
                {
                    "id": model_id,
                    "provider": channel,
                    "display_name": model.get("display_name") or model.get("name") or model_id,
                    "owned_by": model.get("owned_by"),
                    "type": model.get("type"),
                }
            )
    return rows


def _oauth_supabase_client():
    from config import SUPABASE_KEY, SUPABASE_SERVICE_KEY, SUPABASE_URL

    url = os.getenv("OAUTH_SUPABASE_URL") or os.getenv("SUPABASE_URL") or SUPABASE_URL
    key = (
        os.getenv("OAUTH_SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
        or SUPABASE_SERVICE_KEY
        or SUPABASE_KEY
    )
    if not url or not key:
        return None
    try:
        from supabase import create_client

        return create_client(url, key)
    except Exception:
        return None


def _infer_auth_provider(relative_path: str, content: Any) -> str:
    text = relative_path.lower()
    if isinstance(content, dict):
        for key in ("provider", "type", "issuer", "account_type"):
            value = str(content.get(key, "")).lower()
            if value:
                text += " " + value
    if "antigravity" in text:
        return "antigravity"
    if "codex" in text or "openai" in text:
        return "codex"
    if "gemini" in text:
        return "gemini"
    if "anthropic" in text or "claude" in text:
        return "claude"
    if "xai" in text or "grok" in text:
        return "xai"
    if "kimi" in text:
        return "kimi"
    return "unknown"


def sync_cli_auth_files_to_supabase() -> dict[str, Any]:
    client = _oauth_supabase_client()
    if not client:
        return {"status": "skipped", "reason": "Supabase OAuth backup credentials are not configured."}
    if not CLI_PROXY_AUTH_DIR.exists():
        return {"status": "ok", "synced": 0, "reason": "Auth directory does not exist yet."}

    rows = []
    for path in CLI_PROXY_AUTH_DIR.rglob("*"):
        if not path.is_file():
            continue
        try:
            content_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except Exception:
            continue

        try:
            content_json = json.loads(content_text)
        except Exception:
            content_json = None

        relative_path = path.relative_to(CLI_PROXY_AUTH_DIR).as_posix()
        stat = path.stat()
        rows.append(
            {
                "path": relative_path,
                "provider": _infer_auth_provider(relative_path, content_json),
                "content": content_json,
                "content_text": content_text,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "synced_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
            }
        )

    if rows:
        client.table(OAUTH_SESSION_TABLE).upsert(rows, on_conflict="path").execute()
    return {"status": "ok", "synced": len(rows)}


def restore_cli_auth_files_from_supabase() -> dict[str, Any]:
    client = _oauth_supabase_client()
    if not client:
        return {"status": "skipped", "reason": "Supabase OAuth backup credentials are not configured."}

    result = (
        client.table(OAUTH_SESSION_TABLE)
        .select("path,content_text")
        .eq("is_active", True)
        .execute()
    )
    rows = result.data or []
    restored = 0
    CLI_PROXY_AUTH_DIR.mkdir(parents=True, exist_ok=True)

    for row in rows:
        relative = Path(str(row.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts or not row.get("content_text"):
            continue
        destination = CLI_PROXY_AUTH_DIR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(row["content_text"], encoding="utf-8")
        restored += 1

    return {"status": "ok", "restored": restored}
