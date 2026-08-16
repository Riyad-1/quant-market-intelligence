"""Embedding provider abstraction.

This module defines the interface for embedding providers.
Implementations can support OpenAI, SentenceTransformers, HuggingFace, etc.
"""

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Interface for embedding providers."""

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each vector is a list of floats).

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        ...

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...


class EmbeddingError(Exception):
    """Exception raised when embedding generation fails."""

    pass
