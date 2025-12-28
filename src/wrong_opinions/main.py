"""FastAPI application entry point."""

from fastapi import FastAPI

from wrong_opinions import __version__
from wrong_opinions.api import api_router
from wrong_opinions.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    debug=settings.debug,
)

# Include API router
app.include_router(api_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint to verify the API is running."""
    return {"status": "healthy", "version": __version__}
