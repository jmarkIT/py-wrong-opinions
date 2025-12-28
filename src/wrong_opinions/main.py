"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from wrong_opinions import __version__
from wrong_opinions.api import api_router
from wrong_opinions.config import get_settings
from wrong_opinions.services.base import APIError, NotFoundError, RateLimitError

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    debug=settings.debug,
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
