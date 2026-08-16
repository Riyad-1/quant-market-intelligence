import pytest


@pytest.fixture
def sample_document_data() -> dict:
    """Fixture providing sample document data for tests."""
    return {
        "title": "Test Trading Book",
        "author": "John Doe",
        "document_type": "book",
        "publication_date": "2023-01-15",
        "filename": "test_book.pdf",
    }
