"""Main API router aggregation."""

from fastapi import APIRouter

from wrong_opinions.api.albums import router as albums_router
from wrong_opinions.api.auth import router as auth_router
from wrong_opinions.api.movies import router as movies_router
from wrong_opinions.api.weeks import router as weeks_router

# Main API router
api_router = APIRouter(prefix="/api")

# Include all sub-routers
api_router.include_router(auth_router)
api_router.include_router(movies_router)
api_router.include_router(albums_router)
api_router.include_router(weeks_router)
