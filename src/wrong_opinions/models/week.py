"""Week and association ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wrong_opinions.database import Base

if TYPE_CHECKING:
    from wrong_opinions.models.album import Album
    from wrong_opinions.models.movie import Movie
    from wrong_opinions.models.user import User


class Week(Base):
    """Weekly selection period for a user."""

    __tablename__ = "weeks"
    __table_args__ = (UniqueConstraint("user_id", "year", "week_number", name="uq_user_year_week"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(index=True)
    week_number: Mapped[int] = mapped_column()  # ISO week number (1-53)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped[User] = relationship(back_populates="weeks")
    week_movies: Mapped[list[WeekMovie]] = relationship(
        back_populates="week", cascade="all, delete-orphan"
    )
    week_albums: Mapped[list[WeekAlbum]] = relationship(
        back_populates="week", cascade="all, delete-orphan"
    )


class WeekMovie(Base):
    """Association between a week and a movie selection."""

    __tablename__ = "week_movies"
    __table_args__ = (
        UniqueConstraint("week_id", "position", name="uq_week_movie_position"),
        CheckConstraint("position IN (1, 2)", name="ck_movie_position_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column()  # 1 or 2 (first or second movie)
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    week: Mapped[Week] = relationship(back_populates="week_movies")
    movie: Mapped[Movie] = relationship(back_populates="week_movies")


class WeekAlbum(Base):
    """Association between a week and an album selection."""

    __tablename__ = "week_albums"
    __table_args__ = (
        UniqueConstraint("week_id", "position", name="uq_week_album_position"),
        CheckConstraint("position IN (1, 2)", name="ck_album_position_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"), index=True)
    album_id: Mapped[int] = mapped_column(ForeignKey("albums.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column()  # 1 or 2 (first or second album)
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    week: Mapped[Week] = relationship(back_populates="week_albums")
    album: Mapped[Album] = relationship(back_populates="week_albums")
