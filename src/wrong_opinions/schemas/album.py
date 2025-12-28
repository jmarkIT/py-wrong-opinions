"""Pydantic schemas for album API endpoints."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class AlbumSearchResult(BaseModel):
    """A single album result for API response."""

    model_config = ConfigDict(extra="ignore")

    musicbrainz_id: str = Field(description="MusicBrainz release ID (UUID)")
    title: str = Field(description="Album/release title")
    artist: str | None = Field(default=None, description="Primary artist name")
    release_date: str | None = Field(default=None, description="Release date (YYYY-MM-DD)")
    country: str | None = Field(default=None, description="Release country")
    score: int = Field(default=0, description="Search relevance score")
    cover_art_url: str | None = Field(default=None, description="Cover art URL")


class AlbumSearchResponse(BaseModel):
    """Response for album search endpoint."""

    model_config = ConfigDict(extra="ignore")

    count: int = Field(description="Total number of results")
    offset: int = Field(default=0, description="Result offset")
    results: list[AlbumSearchResult] = Field(default_factory=list, description="Album results")


class AlbumDetails(BaseModel):
    """Detailed album information for API response."""

    model_config = ConfigDict(extra="ignore")

    musicbrainz_id: str = Field(description="MusicBrainz release ID (UUID)")
    title: str = Field(description="Album/release title")
    artist: str | None = Field(default=None, description="Primary artist name")
    release_date: str | None = Field(default=None, description="Release date (YYYY-MM-DD)")
    country: str | None = Field(default=None, description="Release country")
    status: str | None = Field(default=None, description="Release status")
    cover_art_url: str | None = Field(default=None, description="Cover art URL")
    # Caching info
    cached: bool = Field(default=False, description="Whether this data is from cache")


class CachedAlbum(BaseModel):
    """Album data from local cache."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Local database ID")
    musicbrainz_id: str = Field(description="MusicBrainz release ID (UUID)")
    title: str = Field(description="Album/release title")
    artist: str = Field(description="Primary artist name")
    release_date: date | None = Field(default=None, description="Release date")
    cover_art_url: str | None = Field(default=None, description="Cover art URL")


class ArtistCredit(BaseModel):
    """An artist credit in API response."""

    model_config = ConfigDict(extra="ignore")

    musicbrainz_id: str = Field(description="MusicBrainz artist ID (UUID)")
    name: str = Field(description="Artist name")
    sort_name: str | None = Field(default=None, description="Sort name")
    disambiguation: str | None = Field(default=None, description="Disambiguation info")
    artist_type: str | None = Field(default=None, description="Artist type (Person, Group, etc.)")
    country: str | None = Field(default=None, description="Artist country")
    join_phrase: str | None = Field(
        default=None, description="Join phrase (e.g., ' & ', ' feat. ')"
    )
    order: int = Field(default=0, description="Order in credits list")


class AlbumCredits(BaseModel):
    """Album credits (artists) for API response."""

    model_config = ConfigDict(extra="ignore")

    artists: list[ArtistCredit] = Field(default_factory=list, description="Artist credits")


class AlbumDetailsWithCredits(AlbumDetails):
    """Album details including artist credits."""

    credits: AlbumCredits | None = Field(default=None, description="Album artist credits")
