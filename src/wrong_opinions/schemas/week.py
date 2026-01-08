"""Pydantic schemas for week selection API endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wrong_opinions.schemas.album import CachedAlbum
from wrong_opinions.schemas.movie import CachedMovie


class WeekOwner(BaseModel):
    """Minimal user info for week ownership display."""

    id: int = Field(description="User ID")
    username: str = Field(description="Username")


class WeekBase(BaseModel):
    """Base schema for week data."""

    year: int = Field(description="Year (e.g., 2025)")
    week_number: int = Field(description="ISO week number (1-53)")
    notes: str | None = Field(default=None, description="Optional notes/commentary")

    @field_validator("week_number")
    @classmethod
    def validate_week_number(cls, v: int) -> int:
        """Validate week number is within ISO week range."""
        if not 1 <= v <= 53:
            msg = "Week number must be between 1 and 53"
            raise ValueError(msg)
        return v

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Validate year is reasonable."""
        if not 1900 <= v <= 2100:
            msg = "Year must be between 1900 and 2100"
            raise ValueError(msg)
        return v


class WeekCreate(WeekBase):
    """Schema for creating a new week selection."""

    pass


class WeekUpdate(BaseModel):
    """Schema for updating a week selection."""

    notes: str | None = Field(default=None, description="Optional notes/commentary")


class WeekMovieSelection(BaseModel):
    """Movie selection within a week."""

    model_config = ConfigDict(from_attributes=True)

    position: int = Field(description="Position in week (1 or 2)")
    added_at: datetime = Field(description="When the movie was added to this week")
    movie: CachedMovie = Field(description="Movie details")


class WeekAlbumSelection(BaseModel):
    """Album selection within a week."""

    model_config = ConfigDict(from_attributes=True)

    position: int = Field(description="Position in week (1 or 2)")
    added_at: datetime = Field(description="When the album was added to this week")
    album: CachedAlbum = Field(description="Album details")


class WeekResponse(BaseModel):
    """Response schema for a week without selections."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Week ID")
    user_id: int | None = Field(default=None, description="Owner user ID (null if unclaimed)")
    owner: WeekOwner | None = Field(default=None, description="Owner information (null if unclaimed)")
    year: int = Field(description="Year")
    week_number: int = Field(description="ISO week number (1-53)")
    notes: str | None = Field(default=None, description="Optional notes/commentary")
    created_at: datetime = Field(description="When the week was created")
    updated_at: datetime = Field(description="When the week was last updated")


class WeekWithSelections(WeekResponse):
    """Response schema for a week with movie and album selections."""

    movies: list[WeekMovieSelection] = Field(
        default_factory=list, description="Movie selections (1-2)"
    )
    albums: list[WeekAlbumSelection] = Field(
        default_factory=list, description="Album selections (1-2)"
    )


class WeekListResponse(BaseModel):
    """Paginated response for listing weeks."""

    model_config = ConfigDict(extra="ignore")

    total: int = Field(description="Total number of weeks")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")
    results: list[WeekResponse] = Field(default_factory=list, description="Week results")


class AddMovieToWeek(BaseModel):
    """Schema for adding a movie to a week."""

    tmdb_id: int = Field(description="TMDB movie ID to add")
    position: int = Field(description="Position in week (1 or 2)")

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: int) -> int:
        """Validate position is 1 or 2."""
        if v not in (1, 2):
            msg = "Position must be 1 or 2"
            raise ValueError(msg)
        return v


class AddAlbumToWeek(BaseModel):
    """Schema for adding an album to a week."""

    musicbrainz_id: str = Field(description="MusicBrainz release ID (UUID) to add")
    position: int = Field(description="Position in week (1 or 2)")

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: int) -> int:
        """Validate position is 1 or 2."""
        if v not in (1, 2):
            msg = "Position must be 1 or 2"
            raise ValueError(msg)
        return v


class WeekMovieResponse(BaseModel):
    """Response after adding a movie to a week."""

    model_config = ConfigDict(from_attributes=True)

    week_id: int = Field(description="Week ID")
    position: int = Field(description="Position in week (1 or 2)")
    added_at: datetime = Field(description="When the movie was added")
    movie: CachedMovie = Field(description="Movie details")


class WeekAlbumResponse(BaseModel):
    """Response after adding an album to a week."""

    model_config = ConfigDict(from_attributes=True)

    week_id: int = Field(description="Week ID")
    position: int = Field(description="Position in week (1 or 2)")
    added_at: datetime = Field(description="When the album was added")
    album: CachedAlbum = Field(description="Album details")
