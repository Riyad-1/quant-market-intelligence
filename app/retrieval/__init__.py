"""Retrieval service module.

This module provides retrieval services for searching document chunks.
"""

from app.retrieval.base import RetrievalError, RetrievalProvider, SearchQuery, SearchResult
from app.retrieval.semantic_search import SemanticSearchProvider

__all__ = [
    "RetrievalProvider",
    "RetrievalError",
    "SearchQuery",
    "SearchResult",
    "SemanticSearchProvider",
]