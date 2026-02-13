import logging

logger = logging.getLogger("kai_api.utils")

def estimate_tokens(text: str) -> int:
    """
    Estimate token count using a simple rule of thumb:
    1 word = ~1.33 tokens (English).
    Or roughly 4 chars = 1 token.
    
    We'll use (len(text) / 4) as a fast approximation.
    Minimum 1 token if text exists.
    """
    if not text:
        return 0
    
    count = int(len(text) / 4)
    return max(1, count)

def calculate_usage(messages: list[dict], response_text: str) -> dict:
    """
    Calculate prompt_tokens and completion_tokens.
    """
    prompt_text = ""
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            prompt_text += content + "\n"
            
    prompt_tokens = estimate_tokens(prompt_text)
    completion_tokens = estimate_tokens(response_text)
    
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens
    }
