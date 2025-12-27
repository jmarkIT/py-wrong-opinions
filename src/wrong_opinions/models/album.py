"""Album ORM model."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wrong_opinions.database import Base

if TYPE_CHECKING:
    from wrong_opinions.models.week import WeekAlbum


class Album(Base):
    """Cached album data from MusicBrainz."""

    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(primary_key=True)
    musicbrainz_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)  # UUID
    title: Mapped[str] = mapped_column(String(255))
    artist: Mapped[str] = mapped_column(String(255))
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cover_art_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cached_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    week_albums: Mapped[list[WeekAlbum]] = relationship(
        back_populates="album", cascade="all, delete-orphan"
    )
