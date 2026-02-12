"""
Pollinations AI Provider
-------------------------
Uses the free Pollinations AI API — no signup, no API key.
Simple HTTP GET requests to text.pollinations.ai.
Inherently stateless — each request is independent.
Rotates User-Agent per request to avoid fingerprinting.
"""

import httpx
import urllib.parse
from providers.base import BaseProvider
from config import PROVIDER_MODELS, POLLINATIONS_TEXT_URL, REQUEST_TIMEOUT, POLLINATIONS_MODEL_NAMES
from useragent import get_random_user_agent


class PollinationsProvider(BaseProvider):
    """AI provider using Pollinations AI free API."""

    @property
    def name(self) -> str:
        return "pollinations"

    def get_available_models(self) -> list[str]:
        return PROVIDER_MODELS.get("pollinations", [])

    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> dict:
        """
        Send a message via Pollinations AI GET endpoint.
        Uses a fresh random User-Agent per request.
        """
        selected_model = model or "openai"

        # Build the prompt — prepend system prompt if provided
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\nUser: {prompt}"
        else:
            full_prompt = prompt

        encoded_prompt = urllib.parse.quote(full_prompt)
        url = f"{POLLINATIONS_TEXT_URL}/{encoded_prompt}"

        params = {"model": selected_model}

        # Fresh User-Agent per request — no fingerprinting
        headers = {
            "User-Agent": get_random_user_agent(),
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

            response_text = response.text.strip()

            if not response_text:
                raise ValueError("Empty response from Pollinations")

            # Return the actual model name, not the vague API identifier
            actual_model_name = POLLINATIONS_MODEL_NAMES.get(
                selected_model, selected_model
            )

            return {
                "response": response_text,
                "model": actual_model_name,
            }
