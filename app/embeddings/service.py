"""Embedding service for managing document embeddings.

This service coordinates the embedding generation and storage process:
- Generates embeddings for document chunks using configured provider
- Stores embeddings in PostgreSQL with pgvector
- Handles batching, retries, and error handling
- Avoids re-embedding already processed chunks
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.models import DocumentChunk
from app.embeddings.base import EmbeddingError, EmbeddingProvider

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingStats:
    """Statistics from an embedding operation."""

    total_chunks: int
    embedded_count: int
    skipped_count: int
    failed_count: int


class EmbeddingService:
    """Service for generating and storing document embeddings."""

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        """Initialize embedding service.

        Args:
            embedding_provider: The embedding provider to use.
        """
        self._provider = embedding_provider

    async def embed_pending_chunks(
        self,
        session: AsyncSession,
        batch_size: int = 50,
        max_batches: int | None = None,
    ) -> EmbeddingStats:
        """Generate embeddings for chunks that don't have them yet.

        Args:
            session: Database session.
            batch_size: Number of chunks to process per batch.
            max_batches: Maximum number of batches to process (None for unlimited).

        Returns:
            EmbeddingStats with operation statistics.
        """
        total_embedded = 0
        total_skipped = 0
        total_failed = 0

        batches_processed = 0

        while True:
            if max_batches and batches_processed >= max_batches:
                logger.info(f"Reached max batches limit: {max_batches}")
                break

            # Fetch chunks without embeddings
            result = await session.execute(
                select(DocumentChunk)
                .where(DocumentChunk.embedding.is_(None))
                .limit(batch_size)
            )
            chunks = result.scalars().all()

            if not chunks:
                logger.info("No pending chunks to embed")
                break

            texts = [chunk.text for chunk in chunks]

            try:
                # Generate embeddings
                embeddings = await self._provider.embed_texts(texts)

                # Store embeddings
                for chunk, embedding in zip(chunks, embeddings):
                    chunk.embedding = embedding
                    total_embedded += 1

                await session.commit()
                batches_processed += 1

                logger.info(
                    f"Embedded batch {batches_processed}: {len(chunks)} chunks, "
                    f"total: {total_embedded}"
                )

            except EmbeddingError as e:
                logger.error(f"Embedding batch failed: {e}")
                total_failed += len(chunks)
                await session.rollback()
                # Continue with next batch instead of failing entirely
                break

            except Exception as e:
                logger.exception(f"Unexpected error during embedding: {e}")
                total_failed += len(chunks)
                await session.rollback()
                break

        return EmbeddingStats(
            total_chunks=total_embedded + total_skipped + total_failed,
            embedded_count=total_embedded,
            skipped_count=total_skipped,
            failed_count=total_failed,
        )

    async def embed_specific_chunks(
        self,
        session: AsyncSession,
        chunk_ids: list[int],
    ) -> EmbeddingStats:
        """Generate embeddings for specific chunk IDs.

        Args:
            session: Database session.
            chunk_ids: List of chunk IDs to embed.

        Returns:
            EmbeddingStats with operation statistics.
        """
        if not chunk_ids:
            return EmbeddingStats(
                total_chunks=0, embedded_count=0, skipped_count=0, failed_count=0
            )

        # Fetch the specified chunks
        result = await session.execute(
            select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
        )
        chunks = result.scalars().all()

        # Separate into those needing embedding and those already embedded
        to_embed = [c for c in chunks if c.embedding is None]
        already_embedded = [c for c in chunks if c.embedding is not None]

        logger.info(
            f"Requested {len(chunk_ids)} chunks: "
            f"{len(to_embed)} need embedding, "
            f"{len(already_embedded)} already embedded"
        )

        total_failed = 0

        if to_embed:
            texts = [chunk.text for chunk in to_embed]

            try:
                # Generate embeddings
                embeddings = await self._provider.embed_texts(texts)

                # Store embeddings
                for chunk, embedding in zip(to_embed, embeddings):
                    chunk.embedding = embedding

                await session.commit()

            except EmbeddingError as e:
                logger.error(f"Embedding failed: {e}")
                total_failed = len(to_embed)
                await session.rollback()

            except Exception as e:
                logger.exception(f"Unexpected error during embedding: {e}")
                total_failed = len(to_embed)
                await session.rollback()

        return EmbeddingStats(
            total_chunks=len(chunk_ids),
            embedded_count=len(to_embed) - total_failed,
            skipped_count=len(already_embedded),
            failed_count=total_failed,
        )

    async def reembed_document_chunks(
        self,
        session: AsyncSession,
        document_id: int,
    ) -> EmbeddingStats:
        """Re-generate embeddings for all chunks in a document.

        This clears existing embeddings and regenerates them.
        Useful when changing embedding models or parameters.

        Args:
            session: Database session.
            document_id: ID of document to re-embed.

        Returns:
            EmbeddingStats with operation statistics.
        """
        # Clear existing embeddings for this document
        await session.execute(
            update(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .values(embedding=None)
        )
        await session.commit()

        logger.info(f"Cleared embeddings for document {document_id}")

        # Now embed all chunks
        return await self.embed_pending_chunks(session, max_batches=None)
