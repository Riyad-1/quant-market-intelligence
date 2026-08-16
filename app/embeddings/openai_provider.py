"""OpenAI embedding provider implementation.

This module provides an OpenAI-based implementation of the EmbeddingProvider interface.
"""

import logging
from typing import Any

from app.core.config import settings
from app.embeddings.base import EmbeddingError, EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-based embedding provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        dimensions: int | None = None,
        max_batch_size: int = 100,
    ) -> None:
        """Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var).
            model: OpenAI embedding model to use.
            dimensions: Number of dimensions for embeddings (model-dependent).
            max_batch_size: Maximum number of texts to embed in a single request.
        """
        self._api_key = api_key or settings.openai_api_key
        self._model = model
        self._dimensions = dimensions or self._get_default_dimensions(model)
        self._max_batch_size = max_batch_size
        self._client: Any | None = None

    def _get_default_dimensions(self, model: str) -> int:
        """Get default dimensions for a model."""
        # OpenAI embedding model dimensions
        dimensions_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dimensions_map.get(model, 1536)

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimensions

    def _get_client(self) -> Any:
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise EmbeddingError(
                    "OpenAI package not installed. Install with: pip install openai"
                ) from e

            if not self._api_key:
                raise EmbeddingError(
                    "OpenAI API key not provided. Set OPENAI_API_KEY environment variable."
                )

            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts using OpenAI.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingError: If API call fails or rate limit is exceeded.
        """
        if not texts:
            return []

        client = self._get_client()

        # Process in batches to avoid hitting token limits
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self._max_batch_size):
            batch = texts[i : i + self._max_batch_size]

            try:
                logger.debug(f"Embedding batch {i // self._max_batch_size + 1}")

                # Prepare input - handle empty strings
                cleaned_batch = [text if text.strip() else " " for text in batch]

                response = await client.embeddings.create(
                    model=self._model,
                    input=cleaned_batch,
                    dimensions=self._dimensions if self._dimensions else None,
                )

                # Extract embeddings in order
                batch_embeddings = [
                    item.embedding
                    for item in sorted(response.data, key=lambda x: x.index)
                ]
                all_embeddings.extend(batch_embeddings)

            except Exception as e:
                error_msg = f"OpenAI embedding API error: {str(e)}"
                logger.error(error_msg)
                raise EmbeddingError(error_msg) from e

        return all_embeddings

    async def embed_text(self, text: str) -> list[float]:
        """Convenience method to embed a single text.

        Args:
            text: Text string to embed.

        Returns:
            Embedding vector.
        """
        result = await self.embed_texts([text])
        return result[0] if result else []
