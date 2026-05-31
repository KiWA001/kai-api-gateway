"""
CLIProxyAPI integration helpers.

The Go sidecar owns OAuth/token storage and provider-specific routing. This
module keeps the Python API thin: it forwards management and inference requests
to the local sidecar and falls back to the embedded model catalog for docs.
"""

from __future__ import annotations

import json
import os
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
    "google": "gemini",
    "anti-gravity": "antigravity",
    "grok": "xai",
    "x-ai": "xai",
    "x.ai": "xai",
}


PUBLIC_CLI_MODEL_ALIASES: dict[str, str] = {
    # Anti-Gravity OAuth
    "anti-gravity-gemini-3.5-flash-low": "antigravity/gemini-3.5-flash-low",
    "anti-gravity-gemini-3.1-pro-low": "antigravity/gemini-3.1-pro-low",
    "anti-gravity-gemini-3-flash": "antigravity/gemini-3-flash",
    "anti-gravity-gemini-3-pro-high": "antigravity/gemini-3-pro-high",
    "anti-gravity-claude-sonnet-4-6": "antigravity/claude-sonnet-4-6",
    # Codex / OpenAI OAuth
    "codex-gpt-5.5": "codex/gpt-5.5",
    "codex-gpt-5.4": "codex/gpt-5.4",
    "codex-gpt-5.4-mini": "codex/gpt-5.4-mini",
    "codex-gpt-5.2": "codex/gpt-5.2",
    "codex-gpt-5.3-codex": "codex/gpt-5.3-codex",
    # Gemini CLI OAuth
    "gemini-3.5-flash": "gemini/gemini-3.5-flash",
    "gemini-3.1-pro-preview": "gemini/gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite-preview": "gemini/gemini-3.1-flash-lite-preview",
    "gemini-2.5-pro": "gemini/gemini-2.5-pro",
    "gemini-2.5-flash": "gemini/gemini-2.5-flash",
    "gemini-2.5-flash-lite": "gemini/gemini-2.5-flash-lite",
    "gemini-3-pro-preview": "gemini/gemini-3-pro-preview",
    "gemini-3-flash-preview": "gemini/gemini-3-flash-preview",
    # Claude OAuth
    "claude-opus-4-7": "claude/claude-opus-4-7",
    "claude-sonnet-4-6": "claude/claude-sonnet-4-6",
    "claude-sonnet-4-5": "claude/claude-sonnet-4-5",
    "claude-opus-4-1": "claude/claude-opus-4-1-20250805",
    "claude-3.7-sonnet": "claude/claude-3-7-sonnet-20250219",
    # xAI OAuth
    "xai-grok-build": "xai/grok-build-0.1",
    "xai-grok-4.3": "xai/grok-4.3",
    "xai-grok-3-mini": "xai/grok-3-mini",
    # Kimi OAuth
    "kimi-k2.6": "kimi/kimi-k2.6",
    "kimi-k2": "kimi/kimi-k2",
    "kimi-k2.5": "kimi/kimi-k2.5",
    "kimi-k2-thinking": "kimi/kimi-k2-thinking",
}

LEGACY_CLI_MODEL_ALIASES: dict[str, str] = {
    "cliproxy-codex-gpt-5.5": "codex/gpt-5.5",
    "cliproxy-codex-gpt-5.4": "codex/gpt-5.4",
    "cliproxy-codex-gpt-5.4-mini": "codex/gpt-5.4-mini",
    "cliproxy-codex-gpt-5.2": "codex/gpt-5.2",
    "cliproxy-codex-gpt-5.3-codex": "codex/gpt-5.3-codex",
    "cliproxy-antigravity-gemini-3.5-flash-low": "antigravity/gemini-3.5-flash-low",
    "cliproxy-antigravity-gemini-3.1-pro-low": "antigravity/gemini-3.1-pro-low",
    "cliproxy-antigravity-gemini-3-flash": "antigravity/gemini-3-flash",
    "cliproxy-antigravity-gemini-3-pro-high": "antigravity/gemini-3-pro-high",
    "cliproxy-antigravity-claude-sonnet-4-6": "antigravity/claude-sonnet-4-6",
    "cliproxy-gemini-3.5-flash": "gemini/gemini-3.5-flash",
    "cliproxy-gemini-3.1-pro-preview": "gemini/gemini-3.1-pro-preview",
    "cliproxy-gemini-3.1-flash-lite-preview": "gemini/gemini-3.1-flash-lite-preview",
    "cliproxy-gemini-2.5-pro": "gemini/gemini-2.5-pro",
    "cliproxy-gemini-2.5-flash": "gemini/gemini-2.5-flash",
    "cliproxy-gemini-2.5-flash-lite": "gemini/gemini-2.5-flash-lite",
    "cliproxy-gemini-3-pro-preview": "gemini/gemini-3-pro-preview",
    "cliproxy-gemini-3-flash-preview": "gemini/gemini-3-flash-preview",
    "cliproxy-claude-opus-4-7": "claude/claude-opus-4-7",
    "cliproxy-claude-sonnet-4-6": "claude/claude-sonnet-4-6",
    "cliproxy-claude-sonnet-4-5": "claude/claude-sonnet-4-5",
    "cliproxy-claude-opus-4-1": "claude/claude-opus-4-1-20250805",
    "cliproxy-claude-3.7-sonnet": "claude/claude-3-7-sonnet-20250219",
    "cliproxy-xai-grok-build": "xai/grok-build-0.1",
    "cliproxy-xai-grok-4.3": "xai/grok-4.3",
    "cliproxy-xai-grok-3-mini": "xai/grok-3-mini",
    "cliproxy-kimi-k2.6": "kimi/kimi-k2.6",
    "cliproxy-kimi-k2": "kimi/kimi-k2",
    "cliproxy-kimi-k2.5": "kimi/kimi-k2.5",
    "cliproxy-kimi-k2-thinking": "kimi/kimi-k2-thinking",
}

CLI_MODEL_ALIASES: dict[str, str] = {
    **PUBLIC_CLI_MODEL_ALIASES,
    **LEGACY_CLI_MODEL_ALIASES,
}

MODEL_SETTINGS_KEY = "enabled_cli_models"
DEFAULT_ENABLED_CLI_MODELS = list(PUBLIC_CLI_MODEL_ALIASES.keys())
LOCAL_SETTINGS_PATH = Path(os.getenv("KAI_LOCAL_SETTINGS_PATH", "/tmp/kai-api-settings.json"))


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
    if not model:
        return PUBLIC_CLI_MODEL_ALIASES[DEFAULT_ENABLED_CLI_MODELS[0]]
    return CLI_MODEL_ALIASES.get(model, model)


def get_cli_provider_models() -> list[str]:
    return list(PUBLIC_CLI_MODEL_ALIASES.keys())


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
