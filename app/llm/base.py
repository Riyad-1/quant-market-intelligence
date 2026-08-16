"""LLM provider abstraction."""

from typing import Protocol


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate a text completion.

        Args:
            prompt: User prompt.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text completion.
        """
        ...
