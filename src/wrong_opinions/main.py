"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from wrong_opinions import __version__
from wrong_opinions.api import api_router
from wrong_opinions.config import get_settings
from wrong_opinions.services.base import APIError, NotFoundError, RateLimitError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan - runs on startup and shutdown."""
    # Startup
    logger.info("Starting %s v%s", settings.app_name, __version__)
    logger.info("Debug mode: %s", settings.debug)
    logger.info("Database: %s", settings.database_url.split("///")[-1])  # Hide path details
    logger.info("TMDB API: %s", "configured" if settings.tmdb_api_key else "NOT CONFIGURED")

    # Validate and log warnings
    warnings = settings.validate_runtime_config()
    if warnings:
        logger.warning("Configuration warnings:")
        for warning in warnings:
            logger.warning("  - %s", warning)
    else:
        logger.info("Configuration validation passed - no warnings")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.exception_handler(NotFoundError)
async def not_found_error_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
    """Handle NotFoundError exceptions globally."""
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc) or "Resource not found"},
    )


@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(_request: Request, exc: RateLimitError) -> JSONResponse:
    """Handle RateLimitError exceptions globally."""
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc) or "Rate limit exceeded"},
        headers=headers,
    )


@app.exception_handler(APIError)
async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions globally."""
    return JSONResponse(
        status_code=exc.status_code or 500,
        content={"detail": str(exc) or "External API error"},
    )


# Include API router
app.include_router(api_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint to verify the API is running."""
    return {"status": "healthy", "version": __version__}
