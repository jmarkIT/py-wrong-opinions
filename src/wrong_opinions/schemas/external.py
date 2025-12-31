"""Pydantic schemas for external API responses (TMDB, MusicBrainz)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    @field_validator("release_date", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | date | None) -> str | date | None:
        """Convert empty strings to None for date fields."""
        if v == "":
            return None
        return v


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

    @field_validator("release_date", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | date | None) -> str | date | None:
        """Convert empty strings to None for date fields."""
        if v == "":
            return None
        return v


class TMDBCastMember(BaseModel):
    """A single cast member from TMDB credits."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(description="TMDB person ID")
    name: str = Field(description="Person's name")
    character: str | None = Field(default=None, description="Character name")
    order: int = Field(default=0, description="Billing order")
    profile_path: str | None = Field(default=None, description="Profile image path")
    known_for_department: str | None = Field(default=None, description="Primary department")


class TMDBCrewMember(BaseModel):
    """A single crew member from TMDB credits."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(description="TMDB person ID")
    name: str = Field(description="Person's name")
    department: str | None = Field(default=None, description="Department")
    job: str | None = Field(default=None, description="Job title")
    profile_path: str | None = Field(default=None, description="Profile image path")
    known_for_department: str | None = Field(default=None, description="Primary department")


class TMDBCreditsResponse(BaseModel):
    """Response from TMDB movie credits endpoint."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(description="TMDB movie ID")
    cast: list[TMDBCastMember] = Field(default_factory=list, description="Cast members")
    crew: list[TMDBCrewMember] = Field(default_factory=list, description="Crew members")


# MusicBrainz Schemas
class MusicBrainzArtist(BaseModel):
    """Artist information from MusicBrainz."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="MusicBrainz artist ID (UUID)")
    name: str = Field(description="Artist name")
    sort_name: str | None = Field(default=None, alias="sort-name", description="Sort name")
    disambiguation: str | None = Field(default=None, description="Disambiguation info")
    type: str | None = Field(default=None, description="Artist type (Person, Group, etc.)")
    country: str | None = Field(default=None, description="Artist country")


class MusicBrainzArtistCredit(BaseModel):
    """Artist credit information from MusicBrainz."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="Credited artist name")
    joinphrase: str | None = Field(default=None, description="Join phrase")
    artist: MusicBrainzArtist | None = Field(default=None, description="Full artist details")


class MusicBrainzReleaseResult(BaseModel):
    """A single release/album result from MusicBrainz search."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="MusicBrainz release ID (UUID)")
    title: str = Field(description="Album/release title")
    score: int = Field(default=0, description="Search relevance score")
    country: str | None = Field(default=None, description="Release country")
    status: str | None = Field(default=None, description="Release status")
    date: str | None = Field(default=None, description="Release date (YYYY-MM-DD)")
    barcode: str | None = Field(default=None, description="Barcode")
    artist_credit: list[MusicBrainzArtistCredit] = Field(
        default_factory=list, alias="artist-credit", description="Artist credits"
    )

    @property
    def artist_name(self) -> str | None:
        """Get the full artist name with join phrases."""
        if not self.artist_credit:
            return None
        # Concatenate all artist names with their join phrases
        result = ""
        for credit in self.artist_credit:
            result += credit.name
            if credit.joinphrase:
                result += credit.joinphrase
        return result or None


class MusicBrainzSearchResponse(BaseModel):
    """Response from MusicBrainz release search endpoint."""

    model_config = ConfigDict(extra="ignore")

    count: int = Field(description="Total number of results")
    offset: int = Field(default=0, description="Result offset")
    releases: list[MusicBrainzReleaseResult] = Field(
        default_factory=list, description="Release results"
    )


class MusicBrainzReleaseDetails(BaseModel):
    """Detailed release information from MusicBrainz."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="MusicBrainz release ID (UUID)")
    title: str = Field(description="Album/release title")
    status: str | None = Field(default=None, description="Release status")
    country: str | None = Field(default=None, description="Release country")
    date: str | None = Field(default=None, description="Release date (YYYY-MM-DD)")
    barcode: str | None = Field(default=None, description="Barcode")
    artist_credit: list[MusicBrainzArtistCredit] = Field(
        default_factory=list, alias="artist-credit", description="Artist credits"
    )

    @property
    def artist_name(self) -> str | None:
        """Get the full artist name with join phrases."""
        if not self.artist_credit:
            return None
        # Concatenate all artist names with their join phrases
        result = ""
        for credit in self.artist_credit:
            result += credit.name
            if credit.joinphrase:
                result += credit.joinphrase
        return result or None
