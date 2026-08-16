"""Embedding service module.

This module provides the embedding service for managing document embeddings.
"""

from app.embeddings.base import EmbeddingError, EmbeddingProvider
from app.embeddings.openai_provider import OpenAIEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "EmbeddingError",
    "OpenAIEmbeddingProvider",
]