
import aiohttp
import json
import logging
import asyncio
from typing import Any, Dict, List
from .base import BaseProvider

logger = logging.getLogger("kai_api.providers.opencode")

class OpenCodeProvider(BaseProvider):
    """
    OpenCode AI Provider.
    Uses the https://opencode.ai/zen/v1 compatible endpoint.
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
        """Send message to OpenCode API."""
        if not model:
            model = "kimi-k2.5-free"

        # The opencode config suggests:
        # baseURL: "https://opencode.ai/zen/v1"
        # We assume standard OpenAI format
        
        url = "https://opencode.ai/zen/v1/chat/completions"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # The config says model: "opencode-zen/{model}"
        api_model = f"opencode-zen/{model}" if "/" not in model else model

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={
                        "model": api_model,
                        "messages": messages,
                        "stream": False
                    },
                    headers={
                        "Content-Type": "application/json",
                        # "Authorization": "Bearer ..." # No key needed? We'll assume open for now
                    },
                    timeout=60
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"OpenCode API error {response.status}: {text}")
                        # If error, try fallback or just raise
                        raise ValueError(f"OpenCode API error {response.status}: {text}")

                    data = await response.json()
                    
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"]
                        return {
                            "response": content,
                            "model": model
                        }
                    else:
                        raise ValueError(f"Invalid response from OpenCode: {data}")
                    
        except Exception as e:
            logger.error(f"OpenCode request failed: {e}")
            raise

    def get_available_models(self) -> List[str]:
        # Copied from opencode_terminal.py
        return [
            "kimi-k2.5-free",
            "minimax-m2.5-free",
            "big-pickle",
            "glm-4.7"
        ]

    async def health_check(self) -> bool:
        try:
            # Simple check
            res = await self.send_message("hi", model="kimi-k2.5-free")
            return bool(res and res.get("response"))
        except:
            return False
