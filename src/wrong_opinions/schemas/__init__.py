"""Pydantic schemas for request/response validation."""

from wrong_opinions.schemas.external import (
    MusicBrainzArtistCredit,
    MusicBrainzReleaseDetails,
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
    "MusicBrainzArtistCredit",
    "MusicBrainzReleaseResult",
    "MusicBrainzReleaseDetails",
    "MusicBrainzSearchResponse",
]
