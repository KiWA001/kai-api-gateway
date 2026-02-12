"""
Base Provider
-------------
Abstract base class that all AI providers must implement.
"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this provider."""
        ...

    @abstractmethod
    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> dict:
        """
        Send a message and return the AI response.

        Each call MUST be stateless — no conversation history retained.
        Creates a fresh session/client per request and discards it after.

        Args:
            prompt: The user's message.
            model: Optional model name to use.
            system_prompt: Optional system prompt.

        Returns:
            dict with keys: "response" (str), "model" (str)
        """
        ...

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Return list of model names this provider supports."""
        ...

    async def health_check(self) -> bool:
        """
        Quick health check — send a trivial prompt and verify response.
        Returns True if the provider is responsive.
        """
        try:
            result = await self.send_message("Say 'ok'", model=None)
            return bool(result and result.get("response"))
        except Exception:
            return False
