"""Document ingestion module."""

from app.ingestion.pipeline import IngestionResult, ingest_document

__all__ = [
    "IngestionResult",
    "ingest_document",
]