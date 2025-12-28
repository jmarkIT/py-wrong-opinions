"""Person and movie credits ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wrong_opinions.database import Base

if TYPE_CHECKING:
    from wrong_opinions.models.movie import Movie


class Person(Base):
    """Cached person data from TMDB (actors, directors, etc.)."""

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    profile_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    known_for_department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cached_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    cast_credits: Mapped[list[MovieCast]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )
    crew_credits: Mapped[list[MovieCrew]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )


class MovieCast(Base):
    """Association between a movie and a cast member."""

    __tablename__ = "movie_cast"

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), index=True
    )
    character: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(default=0)  # Billing order in credits
    cached_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    movie: Mapped[Movie] = relationship(back_populates="cast")
    person: Mapped[Person] = relationship(back_populates="cast_credits")


class MovieCrew(Base):
    """Association between a movie and a crew member."""

    __tablename__ = "movie_crew"

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), index=True
    )
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cached_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    movie: Mapped[Movie] = relationship(back_populates="crew")
    person: Mapped[Person] = relationship(back_populates="crew_credits")
