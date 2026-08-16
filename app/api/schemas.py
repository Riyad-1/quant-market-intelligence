"""Pydantic schemas for document API."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentTypeSchema(str, Enum):
    """Document type enumeration for API schemas."""

    BOOK = "book"
    RESEARCH_PAPER = "research_paper"
    INTERVIEW = "interview"
    STRATEGY_DOCUMENT = "strategy_document"
    RESEARCH_NOTE = "research_note"
    REPORT = "report"
    OTHER = "other"


class DocumentBase(BaseModel):
    """Base schema for Document."""

    title: str = Field(..., min_length=1, max_length=500)
    author: str | None = Field(None, max_length=200)
    document_type: DocumentTypeSchema = DocumentTypeSchema.OTHER
    publication_date: str | None = Field(None, max_length=50)
    metadata_json: dict[str, Any] | None = None


class DocumentCreate(DocumentBase):
    """Schema for creating a Document."""

    pass


class DocumentUpload(BaseModel):
    """Schema for uploading a document file."""

    document_type: DocumentTypeSchema | None = None
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, lt=500)


class DocumentRead(DocumentBase):
    """Schema for reading a Document."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str | None
    hash: str | None
    created_at: str

    # Computed fields
    total_sections: int = 0
    total_chunks: int = 0


class DocumentSectionBase(BaseModel):
    """Base schema for DocumentSection."""

    heading: str | None = Field(None, max_length=500)
    hierarchy_level: int = Field(default=1, ge=1)
    page_start: int | None = None
    page_end: int | None = None


class DocumentSectionRead(DocumentSectionBase):
    """Schema for reading a DocumentSection."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    created_at: str


class DocumentChunkBase(BaseModel):
    """Base schema for DocumentChunk."""

    text: str
    page_start: int | None = None
    page_end: int | None = None
    chunk_index: int
    token_count: int | None = None
    metadata_json: dict[str, Any] | None = None


class DocumentChunkRead(DocumentChunkBase):
    """Schema for reading a DocumentChunk."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    section_id: int | None
    created_at: str


class DocumentChunkWithScore(DocumentChunkRead):
    """Schema for search results with relevance score."""

    score: float | None = None
    document_title: str | None = None
    document_author: str | None = None
    section_heading: str | None = None


class SearchFilterSchema(BaseModel):
    """Schema for search filters."""

    document_id: int | None = None
    author: str | None = None
    document_type: DocumentTypeSchema | None = None


class SearchRequest(BaseModel):
    """Schema for search request."""

    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results")
    filters: SearchFilterSchema | None = None


class SearchResponse(BaseModel):
    """Schema for search response."""

    query: str
    results: list[DocumentChunkWithScore]
