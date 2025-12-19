"""FastAPI application entry point for DDT Dataset Generator API.

This module initializes the FastAPI application, configures middleware,
and defines core endpoints including health checks.
"""

import logging
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.routes import router as api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info(f"Max parallel PDFs: {settings.MAX_PARALLEL_PDFS}")
    logger.info(f"CORS origins: {settings.CORS_ORIGINS}")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.API_TITLE}")


# Initialize FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="API for processing Italian DDT documents and generating training datasets",
    lifespan=lifespan,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint.

    Returns:
        Dict containing status and version information.

    Example:
        >>> GET /health
        {
            "status": "ok",
            "version": "1.0.0",
            "environment": "development"
        }
    """
    return {
        "status": "ok",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint with API information.

    Returns:
        Dict containing API metadata and links.
    """
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "docs_url": "/docs",
        "health_url": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
