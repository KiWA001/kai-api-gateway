"""
g4f Provider
------------
Uses the gpt4free library to access AI models without API keys.
Routes requests through third-party sites, masquerading as a browser.
Each request creates a fresh client — fully stateless, no history.
Rotates User-Agent per request to avoid fingerprinting.
"""

import asyncio
from providers.base import BaseProvider
from config import PROVIDER_MODELS
from useragent import get_random_user_agent


class G4FProvider(BaseProvider):
    """AI provider using g4f (gpt4free) library."""

    @property
    def name(self) -> str:
        return "g4f"

    def get_available_models(self) -> list[str]:
        return PROVIDER_MODELS.get("g4f", [])

    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> dict:
        """
        Send a message via g4f. Creates a fresh client per request
        so no conversation history is retained (stateless).
        Uses a fresh random User-Agent per request.
        """
        from g4f.client import Client

        selected_model = model or "gpt-4o-mini"

        # Build messages — fresh every time (no history)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Fresh User-Agent per request — no fingerprinting
        ua = get_random_user_agent()

        # Run in executor since g4f's Client may block
        def _call():
            # Fix for Vercel: G4F tries to write to HOME/.g4f or .cache
            # We must redirect this to /tmp
            import os
            os.environ["HOME"] = "/tmp"
            
            # Fresh client per request — cache cleared, no history
            client = Client(headers={"User-Agent": ua})
            response = client.chat.completions.create(
                model=selected_model,
                messages=messages,
            )
            return response.choices[0].message.content

        loop = asyncio.get_event_loop()
        response_text = await loop.run_in_executor(None, _call)

        return {
            "response": response_text,
            "model": selected_model,
        }
