"""Pydantic schemas for external API responses (TMDB, MusicBrainz)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


# TMDB Schemas
class TMDBMovieResult(BaseModel):
    """A single movie result from TMDB search."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(description="TMDB movie ID")
    title: str = Field(description="Movie title")
    original_title: str | None = Field(default=None, description="Original title")
    release_date: date | None = Field(default=None, description="Release date")
    poster_path: str | None = Field(default=None, description="Poster image path")
    overview: str | None = Field(default=None, description="Movie overview/synopsis")
    vote_average: float = Field(default=0.0, description="Average vote score")
    vote_count: int = Field(default=0, description="Number of votes")
    popularity: float = Field(default=0.0, description="Popularity score")


class TMDBSearchResponse(BaseModel):
    """Response from TMDB movie search endpoint."""

    model_config = ConfigDict(extra="ignore")

    page: int = Field(description="Current page number")
    total_pages: int = Field(description="Total number of pages")
    total_results: int = Field(description="Total number of results")
    results: list[TMDBMovieResult] = Field(default_factory=list, description="Movie results")


class TMDBMovieDetails(BaseModel):
    """Detailed movie information from TMDB."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(description="TMDB movie ID")
    title: str = Field(description="Movie title")
    original_title: str | None = Field(default=None, description="Original title")
    release_date: date | None = Field(default=None, description="Release date")
    poster_path: str | None = Field(default=None, description="Poster image path")
    backdrop_path: str | None = Field(default=None, description="Backdrop image path")
    overview: str | None = Field(default=None, description="Movie overview/synopsis")
    runtime: int | None = Field(default=None, description="Runtime in minutes")
    vote_average: float = Field(default=0.0, description="Average vote score")
    vote_count: int = Field(default=0, description="Number of votes")
    popularity: float = Field(default=0.0, description="Popularity score")
    status: str | None = Field(default=None, description="Release status")
    tagline: str | None = Field(default=None, description="Movie tagline")
    budget: int = Field(default=0, description="Production budget")
    revenue: int = Field(default=0, description="Box office revenue")
    imdb_id: str | None = Field(default=None, description="IMDB ID")
    homepage: str | None = Field(default=None, description="Official homepage URL")


# MusicBrainz Schemas (placeholder for future implementation)
class MusicBrainzReleaseResult(BaseModel):
    """A single release/album result from MusicBrainz search."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="MusicBrainz release ID (UUID)")
    title: str = Field(description="Album/release title")
    artist_credit: str | None = Field(default=None, description="Artist credit string")
    release_date: date | None = Field(default=None, description="Release date")
    country: str | None = Field(default=None, description="Release country")
    status: str | None = Field(default=None, description="Release status")
    score: int = Field(default=0, description="Search relevance score")


class MusicBrainzSearchResponse(BaseModel):
    """Response from MusicBrainz release search endpoint."""

    model_config = ConfigDict(extra="ignore")

    count: int = Field(description="Total number of results")
    offset: int = Field(default=0, description="Result offset")
    releases: list[MusicBrainzReleaseResult] = Field(
        default_factory=list, description="Release results"
    )
