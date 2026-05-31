"""
K-AI API configuration.

The deployed app is intentionally CLIProxy-only. Legacy provider fallbacks are
not part of the runtime.
"""

import os


# CLIProxy OAuth model ranking. The public names route to provider/model IDs in
# cli_proxy.py.
MODEL_RANKING = [
    ("anti-gravity-gemini-3.5-flash-low", "cli", "anti-gravity-gemini-3.5-flash-low"),
    ("anti-gravity-gemini-3.1-pro-low", "cli", "anti-gravity-gemini-3.1-pro-low"),
    ("anti-gravity-gemini-3-flash", "cli", "anti-gravity-gemini-3-flash"),
    ("anti-gravity-gemini-3-pro-high", "cli", "anti-gravity-gemini-3-pro-high"),
    ("anti-gravity-claude-sonnet-4-6", "cli", "anti-gravity-claude-sonnet-4-6"),
    ("codex-gpt-5.5", "cli", "codex-gpt-5.5"),
    ("codex-gpt-5.4", "cli", "codex-gpt-5.4"),
    ("codex-gpt-5.4-mini", "cli", "codex-gpt-5.4-mini"),
    ("codex-gpt-5.2", "cli", "codex-gpt-5.2"),
    ("codex-gpt-5.3-codex", "cli", "codex-gpt-5.3-codex"),
    ("gemini-3.5-flash", "cli", "gemini-3.5-flash"),
    ("gemini-3.1-pro-preview", "cli", "gemini-3.1-pro-preview"),
    ("gemini-3.1-flash-lite-preview", "cli", "gemini-3.1-flash-lite-preview"),
    ("gemini-2.5-pro", "cli", "gemini-2.5-pro"),
    ("gemini-2.5-flash", "cli", "gemini-2.5-flash"),
    ("gemini-2.5-flash-lite", "cli", "gemini-2.5-flash-lite"),
    ("gemini-3-pro-preview", "cli", "gemini-3-pro-preview"),
    ("gemini-3-flash-preview", "cli", "gemini-3-flash-preview"),
    ("claude-opus-4-7", "cli", "claude-opus-4-7"),
    ("claude-sonnet-4-6", "cli", "claude-sonnet-4-6"),
    ("claude-sonnet-4-5", "cli", "claude-sonnet-4-5"),
    ("claude-opus-4-1", "cli", "claude-opus-4-1"),
    ("claude-3.7-sonnet", "cli", "claude-3.7-sonnet"),
    ("xai-grok-build", "cli", "xai-grok-build"),
    ("xai-grok-4.3", "cli", "xai-grok-4.3"),
    ("xai-grok-3-mini", "cli", "xai-grok-3-mini"),
    ("kimi-k2.6", "cli", "kimi-k2.6"),
    ("kimi-k2", "cli", "kimi-k2"),
    ("kimi-k2.5", "cli", "kimi-k2.5"),
    ("kimi-k2-thinking", "cli", "kimi-k2-thinking"),
]

REQUEST_TIMEOUT = 60

CORS_ORIGINS = ["*"]
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

API_TITLE = "K-AI API"
API_DESCRIPTION = "CLIProxy OAuth API gateway."
API_VERSION = "3.0.0"

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ixktspjwtzhpcpedfjij.supabase.co")
SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3RzcGp3dHpocGNwZWRmamlqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc3NjA1OTgsImV4cCI6MjA4MzMzNjU5OH0.YllBhJl5XEClqjyJe9Il6rrejNP3Xom9Uy6XhlDNMmU",
)

ENABLE_CLI_PROXY = os.getenv("KAI_CLI_PROXY_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

PROVIDERS = {
    "cli": {"enabled": ENABLE_CLI_PROXY, "name": "CLI Proxy OAuth", "type": "cli"},
}

PROVIDER_MODELS = {
    "cli": [friendly for friendly, provider, _ in MODEL_RANKING if provider == "cli"],
}

DEMO_API_KEY = "sk-kai-demo-public"
