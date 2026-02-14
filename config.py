"""
K-AI API Configuration
----------------------
Models ranked by quality — the engine tries each one in order.
If a model fails on one provider, tries the next model.
Exhaustively tries ALL combinations before giving up.
"""

# -------------------------------------------------------------------
# MODEL RANKING — Best to worst. Engine walks top-to-bottom.
# Each entry: (friendly_name, provider, provider_model_id)
#
# Ranking based on 2026 benchmarks:
# - GPT-4o > Claude 3.5 Sonnet > GPT-4 > GPT-4o-mini (g4f)
# - Gemini 2.5 Flash Lite, GPT-OSS 20B, Mistral Small 3.2 (Pollinations)
# - Open-source: Llama 3.1 70B > Mixtral 8x7B (g4f)
# - Older: Claude 3 Haiku > GPT-3.5 Turbo (g4f)
#
# The user doesn't care about wait time — reliability is king.
# Try EVERY combination before returning an error.
# -------------------------------------------------------------------
MODEL_RANKING = [
    # Tier 1 — Verified Working Models (Best Quality)
    ("gpt-4", "g4f", "gpt-4"),
    ("gpt-4o-mini", "g4f", "gpt-4o-mini"),
    ("glm-5", "zai", "glm-5"),
    ("gemini-3-flash", "gemini", "gemini-3-flash"),
    ("huggingface-omni", "huggingchat", "omni"),
    ("huggingface-llama-3.3-70b", "huggingchat", "meta-llama/Llama-3.3-70B-Instruct"),
    ("huggingface-qwen-72b", "huggingchat", "Qwen/Qwen2.5-72B-Instruct"),
    ("huggingface-deepseek-r1", "huggingchat", "deepseek-ai/DeepSeek-R1"),
    ("huggingface-kimi-k2", "huggingchat", "moonshotai/Kimi-K2-Instruct"),
    ("gpt-oss-20b", "pollinations", "openai"),
    ("mistral-small-3.2", "pollinations", "mistral"),
    
    # Tier 2 — New Pollinations Discoveries
    ("bidara", "pollinations", "bidara"),
    ("chickytutor", "pollinations", "chickytutor"),
    ("midijourney", "pollinations", "midijourney"),
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

# API Keys
DEMO_API_KEY = "sk-kai-demo-public"

# Models per provider (for /models endpoint)
PROVIDER_MODELS = {
    "g4f": [
        "gpt-4",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "claude-3-haiku",
        "mixtral-8x7b",
    ],
    "zai": [
        "glm-5",
    ],
    "gemini": [
        "gemini-3-flash",
    ],
    "huggingchat": [
        "huggingface-omni",
        "huggingface-llama-3.3-70b",
        "huggingface-qwen-72b",
        "huggingface-deepseek-r1",
        "huggingface-kimi-k2",
    ],
    "pollinations": [
        "gpt-oss-20b",
        "mistral-small-3.2-24b",
        "bidara",
        "chickytutor",
        "midijourney",
    ],
}
