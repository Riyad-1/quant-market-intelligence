"""Semantic search using pgvector.

This module implements semantic search using PostgreSQL pgvector extension.
It performs similarity search on document chunk embeddings.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.models import Document, DocumentChunk, DocumentSection
from app.retrieval.base import RetrievalError, RetrievalProvider, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class SemanticSearchProvider(RetrievalProvider):
    """Semantic search provider using pgvector."""

    def __init__(self, session_factory: Any) -> None:
        """Initialize semantic search provider.

        Args:
            session_factory: Async session factory for database access.
        """
        self._session_factory = session_factory

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        """Perform semantic search using vector similarity.

        Args:
            query: Search query with text and parameters.

        Returns:
            List of search results ordered by relevance score.

        Raises:
            RetrievalError: If search fails.
        """
        try:
            async with self._session_factory() as session:
                # First, we need to get the embedding for the query
                # This requires an embedding provider - injected or configured
                from app.core.config import settings
                from app.embeddings.openai_provider import OpenAIEmbeddingProvider

                if not hasattr(self, "_embedding_provider"):
                    self._embedding_provider = OpenAIEmbeddingProvider(
                        api_key=settings.openai_api_key,
                        model=settings.openai_embedding_model,
                    )

                # Generate query embedding
                query_embedding = await self._embedding_provider.embed_text(query.query)

                # Build the similarity search query
                # Using cosine distance (<=>) - lower is more similar
                # Score is calculated as 1 - distance for intuitive higher=better scoring

                filters_sql = ""
                params: dict[str, Any] = {"query_embedding": str(query_embedding)}

                if query.filters:
                    filter_conditions = []
                    if "document_id" in query.filters:
                        filter_conditions.append("dc.document_id = :document_id")
                        params["document_id"] = query.filters["document_id"]
                    if "author" in query.filters:
                        filter_conditions.append("d.author ILIKE :author")
                        params["author"] = f"%{query.filters['author']}%"
                    if "document_type" in query.filters:
                        filter_conditions.append("d.document_type = :document_type")
                        params["document_type"] = query.filters["document_type"]

                    if filter_conditions:
                        filters_sql = " AND " + " AND ".join(filter_conditions)

                sql = text(f"""
                    SELECT 
                        dc.id as chunk_id,
                        dc.document_id,
                        dc.text,
                        1 - (dc.embedding <=> :query_embedding::vector) as score,
                        dc.page_start,
                        dc.page_end,
                        d.title as document_title,
                        d.author as document_author,
                        ds.heading as section_heading
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    LEFT JOIN document_sections ds ON dc.section_id = ds.id
                    WHERE dc.embedding IS NOT NULL
                    {filters_sql}
                    ORDER BY dc.embedding <=> :query_embedding::vector
                    LIMIT :top_k
                """)

                params["top_k"] = query.top_k

                result = await session.execute(sql, params)
                rows = result.fetchall()

                return [
                    SearchResult(
                        chunk_id=row.chunk_id,
                        document_id=row.document_id,
                        text=row.text,
                        score=float(row.score) if row.score is not None else 0.0,
                        page_start=row.page_start,
                        page_end=row.page_end,
                        document_title=row.document_title,
                        document_author=row.document_author,
                        section_heading=row.section_heading,
                    )
                    for row in rows
                ]

        except Exception as e:
            error_msg = f"Semantic search failed: {str(e)}"
            logger.error(error_msg)
            raise RetrievalError(error_msg) from e
