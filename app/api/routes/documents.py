"""Document management API routes."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import async_session_factory
from app.db.models import Document, DocumentChunk, DocumentSection, DocumentType
from app.api.schemas import (
    DocumentRead,
    DocumentUpload,
    DocumentChunkRead,
    DocumentSectionRead,
)
from app.ingestion.pipeline import ingest_document
from app.ingestion.parsers.pymupdf_parser import calculate_file_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


async def get_db() -> AsyncSession:
    """Get database session."""
    async with async_session_factory() as session:
        yield session


@router.post("", response_model=DocumentRead, status_code=201)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF document to upload")],
    db: Annotated[AsyncSession, Depends(get_db)],
    document_type: Annotated[
        str | None,
        Query(description="Type of document"),
    ] = None,
    chunk_size: Annotated[
        int,
        Query(description="Characters per chunk", ge=100, le=2000),
    ] = 500,
    chunk_overlap: Annotated[
        int,
        Query(description="Overlap between chunks", ge=0, lt=500),
    ] = 50,
) -> DocumentRead:
    """Upload and ingest a PDF document.

    The document will be:
    1. Parsed to extract text and metadata
    2. Split into chunks for retrieval
    3. Stored with provenance tracking

    Duplicate documents (by hash) are not re-ingested.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Other formats coming soon.",
        )

    # Validate file size (max 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB",
        )

    # Save to temporary location
    import tempfile
    import shutil

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(content)
        tmp_path = Path(tmp_file.name)

    try:
        # Map document type string to enum
        doc_type = None
        if document_type:
            try:
                doc_type = DocumentType(document_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid document type: {document_type}",
                )

        # Ingest document
        result = await ingest_document(
            session=db,
            file_path=tmp_path,
            document_type=doc_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Fetch the full document record
        doc_result = await db.execute(
            select(Document).where(Document.id == result.document_id)
        )
        doc = doc_result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=500, detail="Failed to retrieve document")

        # Get counts
        sections_count = await db.execute(
            select(func.count()).select_from(DocumentSection).where(
                DocumentSection.document_id == doc.id
            )
        )
        chunks_count = await db.execute(
            select(func.count()).select_from(DocumentChunk).where(
                DocumentChunk.document_id == doc.id
            )
        )

        return DocumentRead(
            id=doc.id,
            title=doc.title,
            author=doc.author,
            document_type=DocumentType(doc.document_type),
            publication_date=doc.publication_date,
            filename=doc.filename,
            hash=doc.hash,
            metadata_json=doc.metadata_json,
            created_at=doc.created_at.isoformat(),
            total_sections=sections_count.scalar(),
            total_chunks=chunks_count.scalar(),
        )

    finally:
        # Clean up temp file
        tmp_path.unlink(missing_ok=True)


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentRead]:
    """List all ingested documents with pagination."""
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit)
    )
    docs = result.scalars().all()

    # Get counts for each document
    doc_list = []
    for doc in docs:
        sections_count = await db.execute(
            select(func.count()).select_from(DocumentSection).where(
                DocumentSection.document_id == doc.id
            )
        )
        chunks_count = await db.execute(
            select(func.count()).select_from(DocumentChunk).where(
                DocumentChunk.document_id == doc.id
            )
        )

        doc_list.append(
            DocumentRead(
                id=doc.id,
                title=doc.title,
                author=doc.author,
                document_type=DocumentType(doc.document_type),
                publication_date=doc.publication_date,
                filename=doc.filename,
                hash=doc.hash,
                metadata_json=doc.metadata_json,
                created_at=doc.created_at.isoformat(),
                total_sections=sections_count.scalar(),
                total_chunks=chunks_count.scalar(),
            )
        )

    return doc_list


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentRead:
    """Get a specific document by ID."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    sections_count = await db.execute(
        select(func.count()).select_from(DocumentSection).where(
            DocumentSection.document_id == doc.id
        )
    )
    chunks_count = await db.execute(
        select(func.count()).select_from(DocumentChunk).where(
            DocumentChunk.document_id == doc.id
        )
    )

    return DocumentRead(
        id=doc.id,
        title=doc.title,
        author=doc.author,
        document_type=DocumentType(doc.document_type),
        publication_date=doc.publication_date,
        filename=doc.filename,
        hash=doc.hash,
        metadata_json=doc.metadata_json,
        created_at=doc.created_at.isoformat(),
        total_sections=sections_count.scalar(),
        total_chunks=chunks_count.scalar(),
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a document and all its sections/chunks."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.delete(doc)
    await db.commit()


@router.get("/{document_id}/sections", response_model=list[DocumentSectionRead])
async def list_document_sections(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentSectionRead]:
    """List all sections for a document."""
    # Verify document exists
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    result = await db.execute(
        select(DocumentSection)
        .where(DocumentSection.document_id == document_id)
        .order_by(DocumentSection.page_start)
    )
    sections = result.scalars().all()

    return [
        DocumentSectionRead(
            id=s.id,
            document_id=s.document_id,
            heading=s.heading,
            hierarchy_level=s.hierarchy_level,
            page_start=s.page_start,
            page_end=s.page_end,
            created_at=s.created_at.isoformat(),
        )
        for s in sections
    ]


@router.get(
    "/{document_id}/chunks",
    response_model=list[DocumentChunkRead],
)
async def list_document_chunks(
    document_id: int,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentChunkRead]:
    """List chunks for a document with pagination."""
    # Verify document exists
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(skip)
        .limit(limit)
    )
    chunks = result.scalars().all()

    return [
        DocumentChunkRead(
            id=c.id,
            document_id=c.document_id,
            section_id=c.section_id,
            text=c.text,
            page_start=c.page_start,
            page_end=c.page_end,
            chunk_index=c.chunk_index,
            token_count=c.token_count,
            metadata_json=c.metadata_json,
            created_at=c.created_at.isoformat(),
        )
        for c in chunks
    ]
