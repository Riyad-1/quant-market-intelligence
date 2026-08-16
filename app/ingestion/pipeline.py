"""Document ingestion pipeline.

This module orchestrates the document ingestion process:
1. Parse document (PDF, etc.)
2. Extract text and metadata
3. Chunk text into smaller segments
4. Store in database with provenance tracking
"""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk, DocumentSection, DocumentType
from app.ingestion.chunking.strategies import TextChunk, chunk_by_characters
from app.ingestion.parsers.base import ParsedDocument, ParserError
from app.ingestion.parsers.pymupdf_parser import PyMuPDFParser, calculate_file_hash

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of document ingestion."""

    document_id: int
    title: str
    total_pages: int
    total_chunks: int
    sections_created: int
    chunks_created: int
    duplicates_skipped: int


class ParserRegistry:
    """Registry for document parsers."""

    def __init__(self) -> None:
        self._parsers: dict[str, type] = {}

    def register(self, parser_class: type, extensions: list[str]) -> None:
        """Register a parser for specific file extensions."""
        for ext in extensions:
            self._parsers[ext.lower()] = parser_class

    def get_parser(self, file_path: Path):
        """Get appropriate parser for file extension."""
        ext = file_path.suffix.lower()
        parser_class = self._parsers.get(ext)
        if not parser_class:
            raise ParserError(f"No parser registered for extension: {ext}")
        return parser_class()


# Global parser registry
parser_registry = ParserRegistry()
parser_registry.register(PyMuPDFParser, [".pdf"])


def calculate_chunk_hash(text: str, page_start: int | None, chunk_index: int) -> str:
    """Calculate deterministic hash for a chunk.

    This allows detection of duplicate chunks during re-ingestion.
    """
    content = f"{text}:{page_start}:{chunk_index}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def ingest_document(
    session: AsyncSession,
    file_path: Path,
    document_type: DocumentType | None = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> IngestionResult:
    """Ingest a document into the database.

    Args:
        session: Database session.
        file_path: Path to the document file.
        document_type: Type of document (inferred from path if not provided).
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Overlap between chunks.

    Returns:
        IngestionResult with statistics.

    Raises:
        ParserError: If parsing fails.
        FileNotFoundError: If file doesn't exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get appropriate parser
    parser = parser_registry.get_parser(file_path)

    # Calculate file hash for deduplication
    file_hash = calculate_file_hash(file_path)

    # Check if document already exists
    existing_doc = await session.execute(
        Document.__table__.select().where(Document.hash == file_hash)
    )
    existing_row = existing_doc.first()

    if existing_row:
        logger.info(f"Document already exists with hash {file_hash[:16]}...")
        # Return info about existing document instead of re-ingesting
        # In a real system, we might want to update or skip
        doc_id = existing_row.id
        # Count existing chunks
        result = await session.execute(
            DocumentChunk.__table__.select().where(DocumentChunk.document_id == doc_id)
        )
        existing_chunks = len(result.fetchall())

        return IngestionResult(
            document_id=doc_id,
            title="Existing Document",
            total_pages=0,
            total_chunks=existing_chunks,
            sections_created=0,
            chunks_created=0,
            duplicates_skipped=existing_chunks,
        )

    # Parse document
    logger.info(f"Parsing document: {file_path}")
    parsed_doc: ParsedDocument = await parser.parse(file_path)

    # Create document record
    doc_type = document_type or DocumentType.OTHER

    new_doc = Document(
        title=parsed_doc.title,
        author=parsed_doc.author,
        document_type=doc_type,
        filename=file_path.name,
        hash=file_hash,
        metadata_json=parsed_doc.metadata,
    )

    session.add(new_doc)
    await session.flush()  # Get the ID

    assert new_doc.id is not None
    logger.info(f"Created document record with ID: {new_doc.id}")

    total_chunks = 0
    sections_created = 0
    chunks_created = 0
    duplicates_skipped = 0

    # Process each page as a section (simplified - can be enhanced later)
    for page in parsed_doc.pages:
        # Create section for this page
        section = DocumentSection(
            document_id=new_doc.id,
            heading=f"Page {page.page_number}",
            hierarchy_level=1,
            page_start=page.page_number,
            page_end=page.page_number,
        )
        session.add(section)
        await session.flush()
        sections_created += 1

        assert section.id is not None

        # Chunk the page text
        text_chunks: list[TextChunk] = chunk_by_characters(
            page.text,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )

        # Create chunk records
        for idx, chunk in enumerate(text_chunks):
            chunk_hash = calculate_chunk_hash(chunk.text, page.page_number, idx)

            # Check for duplicate chunk
            existing_chunk = await session.execute(
                DocumentChunk.__table__.select().where(
                    DocumentChunk.chunk_hash == chunk_hash
                )
            )

            if existing_chunk.first():
                duplicates_skipped += 1
                continue

            doc_chunk = DocumentChunk(
                document_id=new_doc.id,
                section_id=section.id,
                text=chunk.text,
                page_start=page.page_number,
                page_end=page.page_number,
                chunk_index=idx,
                token_count=chunk.token_count,
                chunk_hash=chunk_hash,
                metadata_json=page.metadata,
            )
            session.add(doc_chunk)
            chunks_created += 1
            total_chunks += 1

    await session.commit()

    logger.info(
        f"Ingestion complete: {chunks_created} chunks created, "
        f"{duplicates_skipped} duplicates skipped"
    )

    return IngestionResult(
        document_id=new_doc.id,
        title=new_doc.title,
        total_pages=parsed_doc.total_pages,
        total_chunks=total_chunks,
        sections_created=sections_created,
        chunks_created=chunks_created,
        duplicates_skipped=duplicates_skipped,
    )
