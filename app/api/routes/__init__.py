"""API routes module."""

from app.api.routes.health import router as health_router
from app.api.routes.documents import router as documents_router

__all__ = ["health_router", "documents_router"]