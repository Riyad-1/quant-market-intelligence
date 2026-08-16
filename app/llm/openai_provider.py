"""OpenAI LLM provider implementation."""

import logging
from typing import Any

from app.core.config import settings
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    """OpenAI-based LLM provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        max_tokens_default: int = 2048,
    ) -> None:
        """Initialize OpenAI LLM provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var).
            model: OpenAI model to use.
            max_tokens_default: Default maximum tokens to generate.
        """
        self._api_key = api_key or settings.openai_api_key
        self._model = model
        self._max_tokens_default = max_tokens_default
        self._client: Any | None = None

    def _get_client(self) -> Any:
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise RuntimeError(
                    "OpenAI package not installed. Install with: pip install openai"
                ) from e

            if not self._api_key:
                raise RuntimeError(
                    "OpenAI API key not provided. Set OPENAI_API_KEY environment variable."
                )

            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a text completion using OpenAI.

        Args:
            prompt: User prompt.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text completion.

        Raises:
            RuntimeError: If API call fails.
        """
        client = self._get_client()

        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or self._max_tokens_default,
            )

            content = response.choices[0].message.content
            return content if content else ""

        except Exception as e:
            error_msg = f"OpenAI LLM API error: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
