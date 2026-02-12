"""
DuckDuckGo AI Provider
-----------------------
Uses DuckDuckGo's duckchat API endpoint directly.
Masquerades as a browser with proper headers.
Each request creates a fresh session — fully stateless, no history.
"""

import asyncio
import json
import requests
from queue import Queue
from providers.base import BaseProvider
from config import PROVIDER_MODELS


# DuckDuckGo duckchat constants
DDG_STATUS_URL = "https://duckduckgo.com/duckchat/v1/status"
DDG_CHAT_URL = "https://duckduckgo.com/duckchat/v1/chat"
DDG_HEADERS_BASE = {
    "accept": "text/event-stream",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "pragma": "no-cache",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/133.0.0.0 Safari/537.36"
    ),
    "origin": "https://duckduckgo.com",
    "referer": "https://duckduckgo.com/",
}

# Model mapping: friendly names -> DuckDuckGo model identifiers
DDG_MODEL_MAP = {
    "gpt-4o-mini": "gpt-4o-mini",
    "claude-3-haiku": "claude-3-haiku-20240307",
    "claude-3-haiku-20240307": "claude-3-haiku-20240307",
    "llama-3.1-70b": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "mistral-small": "mistralai/Mistral-Small-24B-Instruct-2501",
    "mistralai/Mistral-Small-24B-Instruct-2501": "mistralai/Mistral-Small-24B-Instruct-2501",
    "o3-mini": "o3-mini",
}


def _fetch_vqd() -> tuple[str, str]:
    """
    Fetch a fresh VQD token from DuckDuckGo.
    This is required to authenticate each chat request.
    """
    headers = {**DDG_HEADERS_BASE, "x-vqd-accept": "1"}
    response = requests.get(DDG_STATUS_URL, headers=headers)

    if response.status_code == 200:
        vqd = response.headers.get("x-vqd-4", "")
        vqd_hash = response.headers.get("x-vqd-hash-1", "")
        if vqd:
            return vqd, vqd_hash
    raise Exception(
        f"Failed to get DuckDuckGo VQD token: {response.status_code}"
    )


def _send_chat(vqd: str, model: str, messages: list[dict]) -> str:
    """
    Send a chat message to DuckDuckGo's duckchat API.
    Returns the full response text.
    """
    headers = {
        **DDG_HEADERS_BASE,
        "x-vqd-4": vqd,
        "x-vqd-hash-1": "",
    }
    payload = {"model": model, "messages": messages}

    response = requests.post(
        DDG_CHAT_URL, headers=headers, json=payload, stream=True
    )

    if response.status_code != 200:
        raise Exception(
            f"DuckDuckGo chat error: {response.status_code} {response.text}"
        )

    # Process the SSE stream
    full_response = []
    for line in response.iter_lines():
        if line:
            line = line.decode("utf-8")
            if line == "data: [DONE]":
                break
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    message = data.get("message", "")
                    if message:
                        full_response.append(message)
                except json.JSONDecodeError:
                    continue

    return "".join(full_response)


class DuckDuckGoProvider(BaseProvider):
    """AI provider using DuckDuckGo's duckchat API directly."""

    @property
    def name(self) -> str:
        return "duckduckgo"

    def get_available_models(self) -> list[str]:
        return PROVIDER_MODELS.get("duckduckgo", [])

    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> dict:
        """
        Send a message via DuckDuckGo duckchat.
        Each call fetches a fresh VQD token — fully stateless.
        """
        # Resolve model name
        selected_model = DDG_MODEL_MAP.get(
            model or "gpt-4o-mini", "gpt-4o-mini"
        )

        # Build messages — fresh every time (no history)
        messages = []

        # DuckDuckGo doesn't have a system role, so prepend to user message
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\nUser: {prompt}"
        else:
            full_prompt = prompt

        messages.append({"role": "user", "content": full_prompt})

        # Run blocking I/O in executor
        def _call():
            # Fresh VQD token per request — no session reuse
            vqd, _ = _fetch_vqd()
            return _send_chat(vqd, selected_model, messages)

        loop = asyncio.get_event_loop()
        response_text = await loop.run_in_executor(None, _call)

        # Determine friendly model name for response
        friendly_model = model or "gpt-4o-mini"
        for friendly, ddg_id in DDG_MODEL_MAP.items():
            if ddg_id == selected_model and "/" not in friendly:
                friendly_model = friendly
                break

        return {
            "response": response_text.strip() if response_text else "",
            "model": friendly_model,
        }
