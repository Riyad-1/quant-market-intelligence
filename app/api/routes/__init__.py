"""API routes module."""

from app.api.routes.health import router as health_router
from app.api.routes.documents import router as documents_router
from app.api.routes.search import router as search_router
from app.api.routes.research import router as research_router
from app.api.routes.extraction import router as extraction_router

__all__ = [
    "health_router",
    "documents_router",
    "search_router",
    "research_router",
    "extraction_router",
]