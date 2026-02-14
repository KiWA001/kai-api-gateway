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
# Naming convention: {provider}-{model-name}
# Examples: huggingchat-llama-3.3-70b, zai-glm-5, g4f-gpt-4, gemini-gemini-3-flash
# -------------------------------------------------------------------
MODEL_RANKING = [
    # Tier 1 — Verified Working Models (Best Quality)
    ("g4f-gpt-4", "g4f", "gpt-4"),
    ("g4f-gpt-4o-mini", "g4f", "gpt-4o-mini"),
    ("zai-glm-5", "zai", "glm-5"),
    ("gemini-gemini-3-flash", "gemini", "gemini-3-flash"),
    
    # Tier 2 — HuggingChat Models (Top 20 by popularity/quality)
    ("huggingchat-omni", "huggingchat", "omni"),
    ("huggingchat-llama-3.3-70b", "huggingchat", "meta-llama/Llama-3.3-70B-Instruct"),
    ("huggingchat-llama-4-scout", "huggingchat", "meta-llama/Llama-4-Scout-17B-16E-Instruct"),
    ("huggingchat-llama-4-maverick", "huggingchat", "meta-llama/Llama-4-Maverick-17B-128E-Instruct"),
    ("huggingchat-kimi-k2.5", "huggingchat", "moonshotai/Kimi-K2.5"),
    ("huggingchat-kimi-k2", "huggingchat", "moonshotai/Kimi-K2-Instruct"),
    ("huggingchat-qwen3-235b", "huggingchat", "Qwen/Qwen3-235B-A22B"),
    ("huggingchat-qwen3-32b", "huggingchat", "Qwen/Qwen3-32B"),
    ("huggingchat-qwen3-14b", "huggingchat", "Qwen/Qwen3-14B"),
    ("huggingchat-qwen3-8b", "huggingchat", "Qwen/Qwen3-8B"),
    ("huggingchat-qwen2.5-72b", "huggingchat", "Qwen/Qwen2.5-72B-Instruct"),
    ("huggingchat-qwen2.5-32b", "huggingchat", "Qwen/Qwen2.5-32B-Instruct"),
    ("huggingchat-qwen2.5-7b", "huggingchat", "Qwen/Qwen2.5-7B-Instruct"),
    ("huggingchat-qwen3-coder-480b", "huggingchat", "Qwen/Qwen3-Coder-480B-A35B-Instruct"),
    ("huggingchat-qwen3-coder-30b", "huggingchat", "Qwen/Qwen3-Coder-30B-A3B-Instruct"),
    ("huggingchat-deepseek-r1", "huggingchat", "deepseek-ai/DeepSeek-R1"),
    ("huggingchat-deepseek-v3", "huggingchat", "deepseek-ai/DeepSeek-V3"),
    ("huggingchat-deepseek-v3.2", "huggingchat", "deepseek-ai/DeepSeek-V3.2"),
    ("huggingchat-zai-glm-5", "huggingchat", "zai-org/GLM-5"),
    ("huggingchat-zai-glm-4.7", "huggingchat", "zai-org/GLM-4.7"),
    ("huggingchat-zai-glm-4.5", "huggingchat", "zai-org/GLM-4.5"),
    ("huggingchat-minimax-m2.5", "huggingchat", "MiniMaxAI/MiniMax-M2.5"),
    ("huggingchat-minimax-m2.1", "huggingchat", "MiniMaxAI/MiniMax-M2.1"),
    ("huggingchat-minimax-m2", "huggingchat", "MiniMaxAI/MiniMax-M2"),
    
    # Tier 3 — Pollinations
    ("pollinations-gpt-oss-20b", "pollinations", "openai"),
    ("pollinations-mistral-small-3.2", "pollinations", "mistral"),
    ("pollinations-bidara", "pollinations", "bidara"),
    ("pollinations-chickytutor", "pollinations", "chickytutor"),
    ("pollinations-midijourney", "pollinations", "midijourney"),
    
    # Tier 4 — HuggingChat Additional Models
    ("huggingchat-llama-3.1-70b", "huggingchat", "meta-llama/Meta-Llama-3-70B-Instruct"),
    ("huggingchat-llama-3.1-8b", "huggingchat", "meta-llama/Llama-3.1-8B-Instruct"),
    ("huggingchat-llama-3.2-3b", "huggingchat", "meta-llama/Llama-3.2-3B-Instruct"),
    ("huggingchat-llama-3.2-1b", "huggingchat", "meta-llama/Llama-3.2-1B-Instruct"),
    ("huggingchat-llama-3-8b", "huggingchat", "meta-llama/Meta-Llama-3-8B-Instruct"),
    ("huggingchat-qwen3-vl-235b", "huggingchat", "Qwen/Qwen3-VL-235B-A22B-Instruct"),
    ("huggingchat-qwen3-vl-32b", "huggingchat", "Qwen/Qwen3-VL-32B-Instruct"),
    ("huggingchat-qwen3-vl-30b", "huggingchat", "Qwen/Qwen3-VL-30B-A3B-Instruct"),
    ("huggingchat-qwen3-vl-8b", "huggingchat", "Qwen/Qwen3-VL-8B-Instruct"),
    ("huggingchat-qwen3-4b", "huggingchat", "Qwen/Qwen3-4B-Instruct-2507"),
    ("huggingchat-qwen2.5-vl-72b", "huggingchat", "Qwen/Qwen2.5-VL-72B-Instruct"),
    ("huggingchat-qwen2.5-vl-32b", "huggingchat", "Qwen/Qwen2.5-VL-32B-Instruct"),
    ("huggingchat-qwen2.5-vl-7b", "huggingchat", "Qwen/Qwen2.5-VL-7B-Instruct"),
    ("huggingchat-qwen2.5-coder-32b", "huggingchat", "Qwen/Qwen2.5-Coder-32B-Instruct"),
    ("huggingchat-qwen2.5-coder-7b", "huggingchat", "Qwen/Qwen2.5-Coder-7B-Instruct"),
    ("huggingchat-qwen2.5-coder-3b", "huggingchat", "Qwen/Qwen2.5-Coder-3B-Instruct"),
    ("huggingchat-qwq-32b", "huggingchat", "Qwen/QwQ-32B"),
    ("huggingchat-deepseek-r1-distill-qwen-32b", "huggingchat", "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"),
    ("huggingchat-deepseek-r1-distill-qwen-7b", "huggingchat", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"),
    ("huggingchat-deepseek-r1-distill-llama-70b", "huggingchat", "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"),
    ("huggingchat-deepseek-r1-distill-llama-8b", "huggingchat", "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"),
    ("huggingchat-gemma-3-27b", "huggingchat", "google/gemma-3-27b-it"),
    ("huggingchat-mistral-7b", "huggingchat", "mistralai/Mistral-7B-Instruct-v0.2"),
    ("huggingchat-cohere-command-r", "huggingchat", "CohereLabs/c4ai-command-r-08-2024"),
    ("huggingchat-cohere-command-a", "huggingchat", "CohereLabs/c4ai-command-a-03-2025"),
    ("huggingchat-olmo-3-32b", "huggingchat", "allenai/Olmo-3.1-32B-Instruct"),
    ("huggingchat-olmo-3-7b", "huggingchat", "allenai/Olmo-3-7B-Instruct"),
    ("huggingchat-olmo-3-7b-think", "huggingchat", "allenai/Olmo-3-7B-Think"),
    ("huggingchat-saol10k-l3-70b", "huggingchat", "Sao10K/L3-70B-Euryale-v2.1"),
    ("huggingchat-saol10k-l3-8b", "huggingchat", "Sao10K/L3-8B-Stheno-v3.2"),
    ("huggingchat-wizardlm-2-8x22b", "huggingchat", "alpindale/WizardLM-2-8x22B"),
    ("huggingchat-cogito-671b", "huggingchat", "deepcogito/cogito-671b-v2.1"),
    ("huggingchat-gpt-oss-120b", "huggingchat", "openai/gpt-oss-120b"),
    ("huggingchat-gpt-oss-20b", "huggingchat", "openai/gpt-oss-20b"),
    ("huggingchat-minimax-m1-80k", "huggingchat", "MiniMaxAI/MiniMax-M1-80k"),
    ("huggingchat-zai-autoglm-phone-9b", "huggingchat", "zai-org/AutoGLM-Phone-9B-Multilingual"),
    ("huggingchat-zai-glm-4.7-fp8", "huggingchat", "zai-org/GLM-4.7-FP8"),
    ("huggingchat-zai-glm-4.6v", "huggingchat", "zai-org/GLM-4.6V"),
    ("huggingchat-zai-glm-4.6v-fp8", "huggingchat", "zai-org/GLM-4.6V-FP8"),
    ("huggingchat-zai-glm-4.6v-flash", "huggingchat", "zai-org/GLM-4.6V-Flash"),
    ("huggingchat-zai-glm-4.5-air", "huggingchat", "zai-org/GLM-4.5-Air"),
    ("huggingchat-zai-glm-4.5-air-fp8", "huggingchat", "zai-org/GLM-4.5-Air-FP8"),
    ("huggingchat-zai-glm-4.5v", "huggingchat", "zai-org/GLM-4.5V"),
    ("huggingchat-zai-glm-4.5v-fp8", "huggingchat", "zai-org/GLM-4.5V-FP8"),
    ("huggingchat-zai-glm-4.6", "huggingchat", "zai-org/GLM-4.6"),
    ("huggingchat-zai-glm-4.6-fp8", "huggingchat", "zai-org/GLM-4.6-FP8"),
    ("huggingchat-zai-glm-4-32b", "huggingchat", "zai-org/GLM-4-32B-0414"),
    ("huggingchat-nvidia-nemotron-nano-9b", "huggingchat", "nvidia/NVIDIA-Nemotron-Nano-9B-v2"),
    ("huggingchat-mimo-v2-flash", "huggingchat", "XiaomiMiMo/MiMo-V2-Flash"),
    ("huggingchat-eurollm-22b", "huggingchat", "utter-project/EuroLLM-22B-Instruct-2512"),
    ("huggingchat-trinity-mini", "huggingchat", "arcee-ai/Trinity-Mini"),
    ("huggingchat-apriel-15b-thinker", "huggingchat", "ServiceNow-AI/Apriel-1.6-15b-Thinker"),
    ("huggingchat-arch-router-1.5b", "huggingchat", "katanemo/Arch-Router-1.5B"),
    ("huggingchat-smollm3-3b", "huggingchat", "HuggingFaceTB/SmolLM3-3B"),
    ("huggingchat-hermes-2-pro-llama-3-8b", "huggingchat", "NousResearch/Hermes-2-Pro-Llama-3-8B"),
    ("huggingchat-aya-expanse-32b", "huggingchat", "CohereLabs/aya-expanse-32b"),
    ("huggingchat-aya-vision-32b", "huggingchat", "CohereLabs/aya-vision-32b"),
    ("huggingchat-gemma-sea-lion-v4-27b", "huggingchat", "aisingapore/Gemma-SEA-LION-v4-27B-IT"),
    ("huggingchat-qwen-sea-lion-v4-32b", "huggingchat", "aisingapore/Qwen-SEA-LION-v4-32B-IT"),
    ("huggingchat-dictalm-3.0-24b", "huggingchat", "dicta-il/DictaLM-3.0-24B-Thinking"),
    ("huggingchat-apertus-8b", "huggingchat", "swiss-ai/Apertus-8B-Instruct-2509"),
    ("huggingchat-swallow-70b", "huggingchat", "tokyotech-llm/Llama-3.3-Swallow-70B-Instruct-v0.4"),
    ("huggingchat-marin-8b", "huggingchat", "marin-community/marin-8b-instruct"),
    ("huggingchat-ernie-4.5-vl-424b", "huggingchat", "baidu/ERNIE-4.5-VL-424B-A47B-Base-PT"),
    ("huggingchat-ernie-4.5-vl-28b", "huggingchat", "baidu/ERNIE-4.5-VL-28B-A3B-PT"),
    ("huggingchat-ernie-4.5-300b", "huggingchat", "baidu/ERNIE-4.5-300B-A47B-Base-PT"),
    ("huggingchat-ernie-4.5-21b", "huggingchat", "baidu/ERNIE-4.5-21B-A3B-PT"),
    ("huggingchat-rnj-1-instruct", "huggingchat", "EssentialAI/rnj-1-instruct"),
    ("huggingchat-l3-8b-lunaris", "huggingchat", "Sao10K/L3-8B-Lunaris-v1"),
    
    # Tier 5 — G4F Fallback Models
    ("g4f-gpt-3.5-turbo", "g4f", "gpt-3.5-turbo"),
    ("g4f-claude-3-haiku", "g4f", "claude-3-haiku"),
    ("g4f-mixtral-8x7b", "g4f", "mixtral-8x7b"),
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
# All names follow the pattern: {provider}-{model-name}
PROVIDER_MODELS = {
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
    "huggingchat": [
        # Top Tier
        "huggingchat-omni",
        "huggingchat-llama-3.3-70b",
        "huggingchat-llama-4-scout",
        "huggingchat-llama-4-maverick",
        "huggingchat-llama-3.1-70b",
        "huggingchat-llama-3.1-8b",
        "huggingchat-llama-3.2-3b",
        "huggingchat-llama-3.2-1b",
        "huggingchat-llama-3-8b",
        "huggingchat-llama-3-70b",
        
        # Kimi Models
        "huggingchat-kimi-k2.5",
        "huggingchat-kimi-k2",
        "huggingchat-kimi-k2-thinking",
        "huggingchat-kimi-k2-instruct-0905",
        
        # Qwen3 Models (Large)
        "huggingchat-qwen3-235b",
        "huggingchat-qwen3-32b",
        "huggingchat-qwen3-14b",
        "huggingchat-qwen3-8b",
        "huggingchat-qwen3-4b",
        
        # Qwen3 Vision Models
        "huggingchat-qwen3-vl-235b",
        "huggingchat-qwen3-vl-32b",
        "huggingchat-qwen3-vl-30b",
        "huggingchat-qwen3-vl-8b",
        
        # Qwen2.5 Models
        "huggingchat-qwen2.5-72b",
        "huggingchat-qwen2.5-32b",
        "huggingchat-qwen2.5-7b",
        "huggingchat-qwen2.5-vl-72b",
        "huggingchat-qwen2.5-vl-32b",
        "huggingchat-qwen2.5-vl-7b",
        "huggingchat-qwen2.5-coder-32b",
        "huggingchat-qwen2.5-coder-7b",
        "huggingchat-qwen2.5-coder-3b",
        
        # Qwen Coder Models
        "huggingchat-qwen3-coder-480b",
        "huggingchat-qwen3-coder-30b",
        "huggingchat-qwen3-coder-next",
        "huggingchat-qwen3-coder-next-fp8",
        
        # Qwen Thinking/Reasoning
        "huggingchat-qwq-32b",
        "huggingchat-qwen3-4b-thinking",
        "huggingchat-qwen3-vl-235b-thinking",
        "huggingchat-qwen3-vl-30b-thinking",
        "huggingchat-qwen3-next-80b",
        "huggingchat-qwen3-next-80b-thinking",
        
        # DeepSeek Models
        "huggingchat-deepseek-r1",
        "huggingchat-deepseek-v3",
        "huggingchat-deepseek-v3.2",
        "huggingchat-deepseek-v3.2-exp",
        "huggingchat-deepseek-r1-0528",
        "huggingchat-deepseek-prover-v2-671b",
        "huggingchat-deepseek-r1-distill-qwen-32b",
        "huggingchat-deepseek-r1-distill-qwen-7b",
        "huggingchat-deepseek-r1-distill-qwen-1.5b",
        "huggingchat-deepseek-r1-distill-llama-70b",
        "huggingchat-deepseek-r1-distill-llama-8b",
        
        # Z.ai GLM Models
        "huggingchat-zai-glm-5",
        "huggingchat-zai-glm-4.7",
        "huggingchat-zai-glm-4.7-fp8",
        "huggingchat-zai-glm-4.7-flash",
        "huggingchat-zai-glm-4.6v",
        "huggingchat-zai-glm-4.6v-fp8",
        "huggingchat-zai-glm-4.6v-flash",
        "huggingchat-zai-glm-4.6",
        "huggingchat-zai-glm-4.6-fp8",
        "huggingchat-zai-glm-4.5",
        "huggingchat-zai-glm-4.5-air",
        "huggingchat-zai-glm-4.5-air-fp8",
        "huggingchat-zai-glm-4.5v",
        "huggingchat-zai-glm-4.5v-fp8",
        "huggingchat-zai-glm-4-32b",
        "huggingchat-zai-autoglm-phone-9b",
        
        # MiniMax Models
        "huggingchat-minimax-m2.5",
        "huggingchat-minimax-m2.1",
        "huggingchat-minimax-m2",
        "huggingchat-minimax-m1-80k",
        
        # Google Models
        "huggingchat-gemma-3-27b",
        "huggingchat-gemma-3n-e4b",
        
        # Mistral
        "huggingchat-mistral-7b",
        
        # Cohere
        "huggingchat-cohere-command-r",
        "huggingchat-cohere-command-a",
        "huggingchat-cohere-command-r7b",
        "huggingchat-cohere-command-r7b-arabic",
        "huggingchat-cohere-command-a-vision",
        "huggingchat-cohere-command-a-reasoning",
        "huggingchat-cohere-command-a-translate",
        "huggingchat-cohere-aya-expanse-32b",
        "huggingchat-cohere-aya-vision-32b",
        
        # Allen AI (OLMo)
        "huggingchat-olmo-3-32b",
        "huggingchat-olmo-3-7b",
        "huggingchat-olmo-3-7b-think",
        
        # Sao10K
        "huggingchat-saol10k-l3-70b",
        "huggingchat-saol10k-l3-8b",
        "huggingchat-l3-8b-lunaris",
        
        # Other Notable Models
        "huggingchat-wizardlm-2-8x22b",
        "huggingchat-cogito-671b",
        "huggingchat-cogito-671b-fp8",
        "huggingchat-gpt-oss-120b",
        "huggingchat-gpt-oss-20b",
        "huggingchat-gpt-oss-safeguard-20b",
        "huggingchat-nvidia-nemotron-nano-9b",
        "huggingchat-mimo-v2-flash",
        "huggingchat-eurollm-22b",
        "huggingchat-trinity-mini",
        "huggingchat-apriel-15b-thinker",
        "huggingchat-arch-router-1.5b",
        "huggingchat-smollm3-3b",
        "huggingchat-hermes-2-pro-llama-3-8b",
        "huggingchat-dictalm-3.0-24b",
        "huggingchat-apertus-8b",
        "huggingchat-swallow-70b",
        "huggingchat-marin-8b",
        "huggingchat-ernie-4.5-vl-424b",
        "huggingchat-ernie-4.5-vl-28b",
        "huggingchat-ernie-4.5-300b",
        "huggingchat-ernie-4.5-21b",
        "huggingchat-rnj-1-instruct",
        
        # Sea Lion (Singapore)
        "huggingchat-gemma-sea-lion-v4-27b",
        "huggingchat-qwen-sea-lion-v4-32b",
    ],
    "pollinations": [
        "pollinations-gpt-oss-20b",
        "pollinations-mistral-small-3.2",
        "pollinations-bidara",
        "pollinations-chickytutor",
        "pollinations-midijourney",
    ],
}
