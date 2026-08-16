from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging()

    app = FastAPI(
        title="Quant Market Intelligence",
        description=(
            "A trading and investing research/knowledge intelligence platform. "
            "Provides grounded, source-backed trading knowledge extraction and retrieval."
        ),
        version="0.1.0",
    )

    # Include routers
    app.include_router(health_router, prefix="/api/v1")

    return app


app = create_app()
