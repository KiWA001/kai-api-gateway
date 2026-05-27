"""
K-AI API Configuration
----------------------
Models ranked by quality — the engine tries each one in order.
If a model fails on one provider, tries the next model.
Exhaustively tries ALL combinations before giving up.
"""

import os

# -------------------------------------------------------------------
# MODEL RANKING — Best to worst. Engine walks top-to-bottom.
# Each entry: (friendly_name, provider, provider_model_id)
#
# Naming convention: {provider}-{model-name}
# Examples: huggingchat-llama-3.3-70b, zai-glm-5, g4f-gpt-4, gemini-gemini-3-flash
# -------------------------------------------------------------------
MODEL_RANKING = [
    # Tier 0 — OAuth-backed CLIProxyAPI sidecar models (Docker only by default)
    ("anti-gravity-gemini-3.5-flash-low", "cli", "anti-gravity-gemini-3.5-flash-low"),
    ("anti-gravity-gemini-3.1-pro-low", "cli", "anti-gravity-gemini-3.1-pro-low"),
    ("anti-gravity-gemini-3-flash", "cli", "anti-gravity-gemini-3-flash"),
    ("anti-gravity-gemini-3-pro-high", "cli", "anti-gravity-gemini-3-pro-high"),
    ("anti-gravity-claude-sonnet-4-6", "cli", "anti-gravity-claude-sonnet-4-6"),
    ("codex-gpt-5.5", "cli", "codex-gpt-5.5"),
    ("codex-gpt-5.4", "cli", "codex-gpt-5.4"),
    ("codex-gpt-5.4-mini", "cli", "codex-gpt-5.4-mini"),
    ("gemini-3.5-flash", "cli", "gemini-3.5-flash"),
    ("gemini-3.1-pro-preview", "cli", "gemini-3.1-pro-preview"),
    ("claude-opus-4-7", "cli", "claude-opus-4-7"),
    ("claude-sonnet-4-6", "cli", "claude-sonnet-4-6"),
    ("xai-grok-build", "cli", "xai-grok-build"),
    ("kimi-k2.6", "cli", "kimi-k2.6"),
    ("codex-gpt-5.2", "cli", "codex-gpt-5.2"),
    ("codex-gpt-5.3-codex", "cli", "codex-gpt-5.3-codex"),
    ("gemini-2.5-pro", "cli", "gemini-2.5-pro"),
    ("gemini-2.5-flash", "cli", "gemini-2.5-flash"),
    ("claude-sonnet-4-5", "cli", "claude-sonnet-4-5"),
    ("xai-grok-4.3", "cli", "xai-grok-4.3"),
    ("kimi-k2.5", "cli", "kimi-k2.5"),

    # Tier 1 — Top Hugging Face Models (Best Quality via Widget)
    ("hf-kimi-k2.5", "huggingface_widget", "hf-kimi-k2.5"),
    ("hf-minimax-m2.5", "huggingface_widget", "hf-minimax-m2.5"),
    ("hf-glm-5", "huggingface_widget", "hf-glm-5"),
    ("hf-llama-4-scout", "huggingface_widget", "hf-llama-4-scout"),
    ("hf-llama-4-maverick", "huggingface_widget", "hf-llama-4-maverick"),
    ("hf-llama-3.3-70b", "huggingface_widget", "hf-llama-3.3-70b"),
    ("hf-deepseek-v3", "huggingface_widget", "hf-deepseek-v3"),
    ("hf-qwen3-32b", "huggingface_widget", "hf-qwen3-32b"),
    ("hf-qwen2.5-72b", "huggingface_widget", "hf-qwen2.5-72b"),
    ("hf-phi-4", "huggingface_widget", "hf-phi-4"),
    
    # Tier 2 — Other Providers
    ("g4f-gpt-4", "g4f", "gpt-4"),
    ("g4f-gpt-4o-mini", "g4f", "gpt-4o-mini"),
    ("zai-glm-5", "zai", "glm-5"),
    ("gemini-gemini-3-flash", "gemini", "gemini-3-flash"),
    
    # Tier 3 — Pollinations
    ("pollinations-gpt-oss-20b", "pollinations", "openai"),
    ("pollinations-mistral-small-3.2", "pollinations", "mistral"),
    ("pollinations-bidara", "pollinations", "bidara"),
    ("pollinations-chickytutor", "pollinations", "chickytutor"),
    ("pollinations-midijourney", "pollinations", "midijourney"),
    
    # Tier 4 — G4F Fallback Models
    ("g4f-gpt-3.5-turbo", "g4f", "gpt-3.5-turbo"),
    ("g4f-claude-3-haiku", "g4f", "claude-3-haiku"),
    ("g4f-mixtral-8x7b", "g4f", "mixtral-8x7b"),
    
    # Tier 5 — OpenCode Terminal Models (Free)
    ("opencode-kimi-k2.5-free", "opencode", "kimi-k2.5-free"),
    ("opencode-minimax-m2.5-free", "opencode", "minimax-m2.5-free"),
    ("opencode-big-pickle", "opencode", "big-pickle"),
    ("opencode-glm-4.7", "opencode", "glm-4.7"),
]

# Request timeout in seconds per individual attempt
REQUEST_TIMEOUT = 60

# CORS — allow all origins by default
CORS_ORIGINS = ["*"]
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# API metadata
API_TITLE = "K-AI API"
API_DESCRIPTION = "Free AI proxy API. No signup, no API keys. Feel free to AI."
API_VERSION = "1.0.0"

# Pollinations API base URL
POLLINATIONS_TEXT_URL = "https://text.pollinations.ai"

# Supabase Credentials
SUPABASE_URL = "https://ixktspjwtzhpcpedfjij.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a3RzcGp3dHpocGNwZWRmamlqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc3NjA1OTgsImV4cCI6MjA4MzMzNjU5OH0.YllBhJl5XEClqjyJe9Il6rrejNP3Xom9Uy6XhlDNMmU"

POLLINATIONS_MODEL_NAMES = {
    "openai": "gpt-oss-20b",
    "gemini": "gemini-2.5-flash-lite",
    "mistral": "mistral-small-3.2-24b",
    "bidara": "bidara",
    "chickytutor": "chickytutor",
    "midijourney": "midijourney",
}

# Browser-backed providers stay in the codebase, but are off by default for Docker/API deploys.
# Set KAI_ENABLE_BROWSER_PROVIDERS=true to make Playwright providers visible again.
ENABLE_BROWSER_PROVIDERS = os.getenv("KAI_ENABLE_BROWSER_PROVIDERS", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
HIDE_BROWSER_PROVIDERS = os.getenv("KAI_HIDE_BROWSER_PROVIDERS", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ENABLE_CLI_PROXY = os.getenv("KAI_CLI_PROXY_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Provider Configuration - Enable/Disable providers
# These can be toggled via admin panel
HIDDEN_MODEL_PROVIDERS = {"g4f", "pollinations"}
HIDDEN_MODEL_PREFIXES = ("g4f-", "pollinations-")

PROVIDERS = {
    "g4f": {"enabled": False, "name": "G4F (Free GPT-4)", "type": "api"},
    "zai": {"enabled": ENABLE_BROWSER_PROVIDERS, "name": "Z.ai (GLM-5)", "type": "browser"},
    "gemini": {"enabled": ENABLE_BROWSER_PROVIDERS, "name": "Google Gemini Browser", "type": "browser"},
    "pollinations": {"enabled": False, "name": "Pollinations", "type": "api"},
    "huggingface_widget": {"enabled": ENABLE_BROWSER_PROVIDERS, "name": "Hugging Face Widget", "type": "browser"},
    "copilot": {"enabled": False, "name": "Microsoft Copilot", "type": "browser"},
    "chatgpt": {"enabled": False, "name": "ChatGPT", "type": "browser"},
    "opencode": {"enabled": False, "name": "OpenCode Terminal", "type": "terminal"},
    "cli": {"enabled": ENABLE_CLI_PROXY, "name": "CLI Proxy OAuth", "type": "cli"},
}

# API Keys
DEMO_API_KEY = "sk-kai-demo-public"

# Models per provider (for /models endpoint)
# All names follow the pattern: {provider}-{model-name}
PROVIDER_MODELS = {
    "huggingface_widget": [
        "hf-kimi-k2.5",
        "hf-minimax-m2.5",
        "hf-glm-5",
        "hf-llama-4-scout",
        "hf-llama-4-maverick",
        "hf-llama-3.3-70b",
        "hf-deepseek-v3",
        "hf-qwen3-32b",
        "hf-qwen2.5-72b",
        "hf-phi-4",
    ],
    "g4f": [
        "g4f-gpt-4",
        "g4f-gpt-4o-mini",
        "g4f-gpt-3.5-turbo",
        "g4f-claude-3-haiku",
        "g4f-mixtral-8x7b",
    ],
    "zai": [
        "zai-glm-5",
    ],
    "gemini": [
        "gemini-gemini-3-flash",
    ],
    "pollinations": [
        "pollinations-gpt-oss-20b",
        "pollinations-mistral-small-3.2",
        "pollinations-bidara",
        "pollinations-chickytutor",
        "pollinations-midijourney",
    ],
    "opencode": [
        "opencode-kimi-k2.5-free",
        "opencode-minimax-m2.5-free",
        "opencode-big-pickle",
        "opencode-glm-4.7",
    ],
    "cli": [
        "anti-gravity-gemini-3.5-flash-low",
        "anti-gravity-gemini-3.1-pro-low",
        "anti-gravity-gemini-3-flash",
        "anti-gravity-gemini-3-pro-high",
        "anti-gravity-claude-sonnet-4-6",
        "codex-gpt-5.5",
        "codex-gpt-5.4",
        "codex-gpt-5.4-mini",
        "codex-gpt-5.2",
        "codex-gpt-5.3-codex",
        "gemini-3.5-flash",
        "gemini-3.1-pro-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3-pro-preview",
        "gemini-3-flash-preview",
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-sonnet-4-5",
        "claude-opus-4-1",
        "claude-3.7-sonnet",
        "xai-grok-build",
        "xai-grok-4.3",
        "xai-grok-3-mini",
        "kimi-k2.6",
        "kimi-k2",
        "kimi-k2.5",
        "kimi-k2-thinking",
    ],
}
