"""Text chunking strategies for document processing."""

from dataclasses import dataclass


@dataclass
class TextChunk:
    """Represents a chunk of text from a document.

    Attributes:
        text: The chunk text content.
        start_char: Starting character position in original text.
        end_char: Ending character position in original text.
        token_count: Estimated token count (if available).
    """

    text: str
    start_char: int
    end_char: int
    token_count: int | None = None


def estimate_token_count(text: str, chars_per_token: int = 4) -> int:
    """Estimate token count based on character count.

    This is a rough approximation. For accurate counts, use a tokenizer.

    Args:
        text: The text to estimate tokens for.
        chars_per_token: Average characters per token (default 4 for English).

    Returns:
        Estimated token count.
    """
    return max(1, len(text) // chars_per_token)


def chunk_by_characters(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[TextChunk]:
    """Split text into chunks by character count with overlap.

    Args:
        text: The text to chunk.
        chunk_size: Maximum characters per chunk.
        overlap: Number of overlapping characters between chunks.

    Returns:
        List of TextChunk objects.
    """
    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size")

    chunks: list[TextChunk] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # If not at the end, try to break at a sentence or word boundary
        if end < text_length:
            # Try to find a sentence boundary first
            last_period = text.rfind(".", start, end)
            last_question = text.rfind("?", start, end)
            last_exclamation = text.rfind("!", start, end)

            boundaries = [
                b for b in [last_period, last_question, last_exclamation] if b > start
            ]

            if boundaries and (end - max(boundaries)) < (chunk_size // 2):
                # Use the last boundary if it's reasonable
                end = max(boundaries) + 1
            else:
                # Try word boundary
                last_space = text.rfind(" ", start, end)
                if last_space > start and (end - last_space) < (chunk_size // 3):
                    end = last_space + 1

        chunk_text = text[start:end].strip()

        if chunk_text:  # Only add non-empty chunks
            chunk = TextChunk(
                text=chunk_text,
                start_char=start,
                end_char=end,
                token_count=estimate_token_count(chunk_text),
            )
            chunks.append(chunk)

        # Move start position with overlap
        start = end - overlap if end < text_length else text_length

        # Prevent infinite loop if overlap caused no progress
        if start >= text_length:
            break

    return chunks


def chunk_by_sentences(
    text: str,
    sentences_per_chunk: int = 3,
) -> list[TextChunk]:
    """Split text into chunks by sentence count.

    Simple sentence splitting based on common delimiters.

    Args:
        text: The text to chunk.
        sentences_per_chunk: Number of sentences per chunk.

    Returns:
        List of TextChunk objects.
    """
    if not text:
        return []

    # Simple sentence splitting - can be improved with NLTK/spaCy later
    import re

    # Split on sentence boundaries (. ! ? followed by space or end)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks: list[TextChunk] = []
    current_pos = 0

    for i in range(0, len(sentences), sentences_per_chunk):
        chunk_sentences = sentences[i : i + sentences_per_chunk]
        chunk_text = " ".join(chunk_sentences)

        # Find position in original text
        start_pos = text.find(chunk_text, current_pos)
        if start_pos == -1:
            start_pos = current_pos

        end_pos = start_pos + len(chunk_text)

        chunk = TextChunk(
            text=chunk_text,
            start_char=start_pos,
            end_char=end_pos,
            token_count=estimate_token_count(chunk_text),
        )
        chunks.append(chunk)

        current_pos = end_pos

    return chunks
