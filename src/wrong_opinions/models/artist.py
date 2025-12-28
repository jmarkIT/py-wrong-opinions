"""Artist and album credits ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wrong_opinions.database import Base

if TYPE_CHECKING:
    from wrong_opinions.models.album import Album


class Artist(Base):
    """Cached artist data from MusicBrainz."""

    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(primary_key=True)
    musicbrainz_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)  # UUID
    name: Mapped[str] = mapped_column(String(255))
    sort_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    disambiguation: Mapped[str | None] = mapped_column(Text, nullable=True)
    artist_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # Person, Group, etc.
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ISO country code
    cached_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    album_credits: Mapped[list[AlbumArtist]] = relationship(
        back_populates="artist", cascade="all, delete-orphan"
    )


class AlbumArtist(Base):
    """Association between an album and an artist."""

    __tablename__ = "album_artist"

    id: Mapped[int] = mapped_column(primary_key=True)
    album_id: Mapped[int] = mapped_column(ForeignKey("albums.id", ondelete="CASCADE"), index=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), index=True)
    join_phrase: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g., " & ", " feat. "
    order: Mapped[int] = mapped_column(default=0)  # Order in credits list
    cached_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    album: Mapped[Album] = relationship(back_populates="artist_credits")
    artist: Mapped[Artist] = relationship(back_populates="album_credits")
