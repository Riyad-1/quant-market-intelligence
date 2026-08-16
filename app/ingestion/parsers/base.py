"""Base protocol for document parsers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedPage:
    """Represents a parsed page from a document."""

    page_number: int
    text: str
    metadata: dict | None = None


@dataclass
class ParsedDocument:
    """Represents a fully parsed document."""

    title: str
    author: str | None
    total_pages: int
    pages: list[ParsedPage]
    metadata: dict | None = None


class DocumentParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    async def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a document file and return structured content.

        Args:
            file_path: Path to the document file.

        Returns:
            ParsedDocument with extracted content.

        Raises:
            ParserError: If parsing fails.
        """
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions (e.g., ['.pdf'])."""
        pass


class ParserError(Exception):
    """Exception raised when document parsing fails."""

    pass
