"""Pydantic schemas for request/response validation."""

from wrong_opinions.schemas.external import (
    MusicBrainzReleaseResult,
    MusicBrainzSearchResponse,
    TMDBMovieDetails,
    TMDBMovieResult,
    TMDBSearchResponse,
)

__all__ = [
    "TMDBMovieResult",
    "TMDBSearchResponse",
    "TMDBMovieDetails",
    "MusicBrainzReleaseResult",
    "MusicBrainzSearchResponse",
]
