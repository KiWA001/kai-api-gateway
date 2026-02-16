
import aiohttp
import logging
from typing import Any, Dict, List
from .base import BaseProvider

logger = logging.getLogger("kai_api.providers.opencode")

# AWS OpenCode Microservice URL
# Replace with your actual AWS IP after deployment
AWS_OPENCODE_URL = "http://44.201.146.74:8000"

class OpenCodeProvider(BaseProvider):
    """
    OpenCode AI Provider - Calls AWS Microservice.
    """

    @property
    def name(self) -> str:
        return "opencode"

    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Send message to OpenCode via AWS microservice."""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{AWS_OPENCODE_URL}/chat",
                    json={"message": prompt, "model": model or "kimi-k2.5-free"},
                    timeout=60
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"OpenCode service error {response.status}: {text}")
                        raise ValueError(f"OpenCode service error: {response.status}")
                    
                    data = await response.json()
                    return {
                        "response": data.get("response", "No response"),
                        "model": model or "kimi-k2.5-free",
                        "session_id": data.get("session_id"),
                        "message_count": data.get("message_count"),
                    }
                    
        except Exception as e:
            logger.error(f"OpenCode request failed: {e}")
            raise

    def get_available_models(self) -> List[str]:
        return [
            "opencode-kimi-k2.5-free",
            "opencode-minimax-m2.5-free",
            "opencode-big-pickle",
            "opencode-glm-4.7"
        ]

    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{AWS_OPENCODE_URL}/health",
                    timeout=10
                ) as response:
                    return response.status == 200
        except:
            return False
