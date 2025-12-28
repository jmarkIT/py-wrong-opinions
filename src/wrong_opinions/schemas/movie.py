"""Pydantic schemas for movie API endpoints."""

from datetime import date, datetime

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
    cached_at: datetime = Field(description="When the movie data was cached")


class CastMember(BaseModel):
    """A cast member in API response."""

    model_config = ConfigDict(extra="ignore")

    tmdb_id: int = Field(description="TMDB person ID")
    name: str = Field(description="Person's name")
    character: str | None = Field(default=None, description="Character name")
    order: int = Field(default=0, description="Billing order")
    profile_url: str | None = Field(default=None, description="Full profile image URL")


class CrewMember(BaseModel):
    """A crew member in API response."""

    model_config = ConfigDict(extra="ignore")

    tmdb_id: int = Field(description="TMDB person ID")
    name: str = Field(description="Person's name")
    department: str | None = Field(default=None, description="Department")
    job: str | None = Field(default=None, description="Job title")
    profile_url: str | None = Field(default=None, description="Full profile image URL")


class MovieCredits(BaseModel):
    """Movie credits (cast and crew) for API response."""

    model_config = ConfigDict(extra="ignore")

    cast: list[CastMember] = Field(default_factory=list, description="Cast members")
    crew: list[CrewMember] = Field(default_factory=list, description="Crew members")


class MovieDetailsWithCredits(MovieDetails):
    """Movie details including cast and crew."""

    credits: MovieCredits | None = Field(default=None, description="Movie cast and crew")
