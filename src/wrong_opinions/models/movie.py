"""Movie ORM model."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wrong_opinions.database import Base

if TYPE_CHECKING:
    from wrong_opinions.models.person import MovieCast, MovieCrew
    from wrong_opinions.models.week import WeekMovie


class Movie(Base):
    """Cached movie data from TMDB."""

    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    original_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    week_movies: Mapped[list[WeekMovie]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )
    cast: Mapped[list[MovieCast]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )
    crew: Mapped[list[MovieCrew]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )
