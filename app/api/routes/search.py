"""Search API routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.schemas import DocumentChunkWithScore, SearchRequest, SearchResponse
from app.retrieval.base import RetrievalError, SearchQuery
from app.retrieval.semantic_search import SemanticSearchProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search_documents(
    q: Annotated[str, Query(description="Search query text")],
    top_k: Annotated[
        int, Query(description="Number of results to return", ge=1, le=100)
    ] = 10,
    document_id: Annotated[int | None, Query(description="Filter by document ID")] = None,
    author: Annotated[str | None, Query(description="Filter by author")] = None,
    document_type: Annotated[str | None, Query(description="Filter by document type")] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SearchResponse:
    """Search for relevant document chunks using semantic similarity.

    Returns chunks ranked by relevance to the query text.
    Results include source provenance (document, page, section).
    """
    # Build filters
    filters: dict = {}
    if document_id is not None:
        filters["document_id"] = document_id
    if author:
        filters["author"] = author
    if document_type:
        filters["document_type"] = document_type

    # Create search provider
    from app.db.session import async_session_factory

    provider = SemanticSearchProvider(async_session_factory)

    try:
        search_query = SearchQuery(query=q, top_k=top_k, filters=filters if filters else None)
        results = await provider.search(search_query)

        return SearchResponse(
            query=q,
            results=[
                DocumentChunkWithScore(
                    id=r.chunk_id,
                    document_id=r.document_id,
                    section_id=None,  # Would need to fetch from DB
                    text=r.text,
                    page_start=r.page_start,
                    page_end=r.page_end,
                    chunk_index=0,  # Would need to fetch from DB
                    token_count=None,
                    metadata_json=None,
                    created_at="",  # Would need to fetch from DB
                    score=r.score,
                    document_title=r.document_title,
                    document_author=r.document_author,
                    section_heading=r.section_heading,
                )
                for r in results
            ],
        )

    except RetrievalError as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e


@router.post("", response_model=SearchResponse)
async def search_documents_post(
    request: SearchRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SearchResponse:
    """Search for relevant document chunks using semantic similarity (POST version).

    POST version allows more complex queries and filters in the request body.
    """
    filters = request.filters.model_dump(exclude_unset=True) if request.filters else None

    from app.db.session import async_session_factory

    provider = SemanticSearchProvider(async_session_factory)

    try:
        search_query = SearchQuery(query=request.query, top_k=request.top_k, filters=filters)
        results = await provider.search(search_query)

        return SearchResponse(
            query=request.query,
            results=[
                DocumentChunkWithScore(
                    id=r.chunk_id,
                    document_id=r.document_id,
                    section_id=None,
                    text=r.text,
                    page_start=r.page_start,
                    page_end=r.page_end,
                    chunk_index=0,
                    token_count=None,
                    metadata_json=None,
                    created_at="",
                    score=r.score,
                    document_title=r.document_title,
                    document_author=r.document_author,
                    section_heading=r.section_heading,
                )
                for r in results
            ],
        )

    except RetrievalError as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e
