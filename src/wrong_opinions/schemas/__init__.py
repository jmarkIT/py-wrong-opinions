"""Pydantic schemas for request/response validation."""

from wrong_opinions.schemas.album import (
    AlbumDetails,
    AlbumSearchResponse,
    AlbumSearchResult,
    CachedAlbum,
)
from wrong_opinions.schemas.external import (
    MusicBrainzArtistCredit,
    MusicBrainzReleaseDetails,
    MusicBrainzReleaseResult,
    MusicBrainzSearchResponse,
    TMDBMovieDetails,
    TMDBMovieResult,
    TMDBSearchResponse,
)
from wrong_opinions.schemas.movie import (
    CachedMovie,
    MovieDetails,
    MovieSearchResponse,
    MovieSearchResult,
)
from wrong_opinions.schemas.week import (
    AddAlbumToWeek,
    AddMovieToWeek,
    WeekAlbumResponse,
    WeekAlbumSelection,
    WeekBase,
    WeekCreate,
    WeekListResponse,
    WeekMovieResponse,
    WeekMovieSelection,
    WeekResponse,
    WeekUpdate,
    WeekWithSelections,
)

__all__ = [
    # External API schemas
    "TMDBMovieResult",
    "TMDBSearchResponse",
    "TMDBMovieDetails",
    "MusicBrainzArtistCredit",
    "MusicBrainzReleaseResult",
    "MusicBrainzReleaseDetails",
    "MusicBrainzSearchResponse",
    # Movie schemas
    "MovieSearchResult",
    "MovieSearchResponse",
    "MovieDetails",
    "CachedMovie",
    # Album schemas
    "AlbumSearchResult",
    "AlbumSearchResponse",
    "AlbumDetails",
    "CachedAlbum",
    # Week schemas
    "WeekBase",
    "WeekCreate",
    "WeekUpdate",
    "WeekResponse",
    "WeekWithSelections",
    "WeekListResponse",
    "WeekMovieSelection",
    "WeekAlbumSelection",
    "AddMovieToWeek",
    "AddAlbumToWeek",
    "WeekMovieResponse",
    "WeekAlbumResponse",
]
