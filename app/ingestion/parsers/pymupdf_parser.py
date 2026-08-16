"""PyMuPDF-based PDF document parser."""

import hashlib
from pathlib import Path

import fitz  # PyMuPDF

from app.ingestion.parsers.base import (
    DocumentParser,
    ParsedDocument,
    ParsedPage,
    ParserError,
)


class PyMuPDFParser(DocumentParser):
    """PDF parser using PyMuPDF (fitz)."""

    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        return [".pdf"]

    async def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a PDF file and return structured content.

        Args:
            file_path: Path to the PDF file.

        Returns:
            ParsedDocument with extracted content.

        Raises:
            ParserError: If parsing fails.
        """
        if not file_path.exists():
            raise ParserError(f"File not found: {file_path}")

        if file_path.suffix.lower() not in self.supported_extensions():
            raise ParserError(
                f"Unsupported file type: {file_path.suffix}. "
                f"Supported types: {self.supported_extensions()}"
            )

        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise ParserError(f"Failed to open PDF: {e}") from e

        pages: list[ParsedPage] = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")

                # Extract basic metadata from page
                page_metadata = {
                    "width": page.rect.width,
                    "height": page.rect.height,
                }

                parsed_page = ParsedPage(
                    page_number=page_num + 1,  # 1-indexed
                    text=text,
                    metadata=page_metadata,
                )
                pages.append(parsed_page)

            # Try to extract document metadata
            doc_metadata = doc.metadata
            title = doc_metadata.get("title", "") or file_path.stem
            author = doc_metadata.get("author")

            parsed_doc = ParsedDocument(
                title=title,
                author=author,
                total_pages=len(pages),
                pages=pages,
                metadata={
                    "format": doc_metadata.get("format", "PDF"),
                    "encryption": doc_metadata.get("encryption", None),
                },
            )

            return parsed_doc

        finally:
            doc.close()


def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """Calculate hash of a file for deduplication.

    Args:
        file_path: Path to the file.
        algorithm: Hash algorithm to use.

    Returns:
        Hexadecimal hash string.
    """
    hash_obj = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()
