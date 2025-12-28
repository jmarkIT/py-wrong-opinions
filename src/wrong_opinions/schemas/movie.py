"""Pydantic schemas for movie API endpoints."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class MovieSearchResult(BaseModel):
    """A single movie result for API response."""

    model_config = ConfigDict(extra="ignore")

    tmdb_id: int = Field(description="TMDB movie ID")
    title: str = Field(description="Movie title")
    original_title: str | None = Field(default=None, description="Original title")
    release_date: date | None = Field(default=None, description="Release date")
    poster_url: str | None = Field(default=None, description="Full poster image URL")
    overview: str | None = Field(default=None, description="Movie overview/synopsis")
    vote_average: float = Field(default=0.0, description="Average vote score")


class MovieSearchResponse(BaseModel):
    """Response for movie search endpoint."""

    model_config = ConfigDict(extra="ignore")

    page: int = Field(description="Current page number")
    total_pages: int = Field(description="Total number of pages")
    total_results: int = Field(description="Total number of results")
    results: list[MovieSearchResult] = Field(default_factory=list, description="Movie results")


class MovieDetails(BaseModel):
    """Detailed movie information for API response."""

    model_config = ConfigDict(extra="ignore")

    tmdb_id: int = Field(description="TMDB movie ID")
    title: str = Field(description="Movie title")
    original_title: str | None = Field(default=None, description="Original title")
    release_date: date | None = Field(default=None, description="Release date")
    poster_url: str | None = Field(default=None, description="Full poster image URL")
    backdrop_url: str | None = Field(default=None, description="Full backdrop image URL")
    overview: str | None = Field(default=None, description="Movie overview/synopsis")
    runtime: int | None = Field(default=None, description="Runtime in minutes")
    vote_average: float = Field(default=0.0, description="Average vote score")
    vote_count: int = Field(default=0, description="Number of votes")
    tagline: str | None = Field(default=None, description="Movie tagline")
    status: str | None = Field(default=None, description="Release status")
    imdb_id: str | None = Field(default=None, description="IMDB ID")
    # Caching info
    cached: bool = Field(default=False, description="Whether this data is from cache")


class CachedMovie(BaseModel):
    """Movie data from local cache."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Local database ID")
    tmdb_id: int = Field(description="TMDB movie ID")
    title: str = Field(description="Movie title")
    original_title: str | None = Field(default=None, description="Original title")
    release_date: date | None = Field(default=None, description="Release date")
    poster_path: str | None = Field(default=None, description="Poster image path")
    overview: str | None = Field(default=None, description="Movie overview/synopsis")
