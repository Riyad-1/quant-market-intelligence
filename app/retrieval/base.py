"""Retrieval service abstraction.

This module defines the interface for retrieval providers.
Implementations can support semantic search, hybrid search, etc.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class SearchResult:
    """A single search result."""

    chunk_id: int
    document_id: int
    text: str
    score: float
    page_start: int | None = None
    page_end: int | None = None
    document_title: str | None = None
    document_author: str | None = None
    section_heading: str | None = None


@dataclass
class SearchQuery:
    """Search query parameters."""

    query: str
    top_k: int = 10
    filters: dict[str, Any] | None = None


class RetrievalProvider(Protocol):
    """Interface for retrieval providers."""

    async def search(
        self,
        query: SearchQuery,
    ) -> list[SearchResult]:
        """Search for relevant document chunks.

        Args:
            query: Search query with text and parameters.

        Returns:
            List of search results ordered by relevance score.

        Raises:
            RetrievalError: If search fails.
        """
        ...


class RetrievalError(Exception):
    """Exception raised when retrieval fails."""

    pass
