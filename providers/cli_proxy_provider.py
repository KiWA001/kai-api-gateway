"""
CLIProxyAPI provider.

This provider lets the regular KAI engine route to OAuth-backed coding-model
accounts through the local Go sidecar when it is enabled.
"""

from __future__ import annotations

from typing import Any

from cli_proxy import get_cli_provider_models, cli_api_request, resolve_cli_model
from .base import BaseProvider


class CLIProxyProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "cli"

    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        target_model = resolve_cli_model(model)
        response = await cli_api_request(
            "POST",
            "v1/chat/completions",
            json_body={
                "model": target_model,
                "messages": messages,
                "stream": False,
            },
            headers={"content-type": "application/json"},
        )

        if response.status_code >= 400:
            raise ValueError(f"CLI proxy error {response.status_code}: {response.text[:500]}")

        data = response.json()
        response_text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        return {
            "response": response_text,
            "model": target_model,
        }

    def get_available_models(self) -> list[str]:
        return get_cli_provider_models()

    async def health_check(self) -> bool:
        try:
            response = await cli_api_request("GET", "v1/models")
            return response.status_code < 500
        except Exception:
            return False
