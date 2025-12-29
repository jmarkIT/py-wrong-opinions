"""Initial schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2025-12-29 17:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create base tables (no dependencies)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)
        batch_op.create_index(batch_op.f("ix_users_username"), ["username"], unique=True)

    op.create_table(
        "albums",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("musicbrainz_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("artist", sa.String(length=255), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("cover_art_url", sa.String(length=500), nullable=True),
        sa.Column("cached_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("albums", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_albums_musicbrainz_id"), ["musicbrainz_id"], unique=True
        )

    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("original_title", sa.String(length=255), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("poster_path", sa.String(length=255), nullable=True),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("cached_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("movies", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_movies_tmdb_id"), ["tmdb_id"], unique=True)

    op.create_table(
        "people",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("profile_path", sa.String(length=255), nullable=True),
        sa.Column("known_for_department", sa.String(length=100), nullable=True),
        sa.Column("cached_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_people_tmdb_id"), ["tmdb_id"], unique=True)

    op.create_table(
        "artists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("musicbrainz_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sort_name", sa.String(length=255), nullable=True),
        sa.Column("disambiguation", sa.Text(), nullable=True),
        sa.Column("artist_type", sa.String(length=50), nullable=True),
        sa.Column("country", sa.String(length=10), nullable=True),
        sa.Column("cached_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("artists", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_artists_musicbrainz_id"), ["musicbrainz_id"], unique=True
        )

    # Create tables with foreign key dependencies
    op.create_table(
        "weeks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year", "week_number", name="uq_year_week"),
    )
    with op.batch_alter_table("weeks", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_weeks_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_weeks_year"), ["year"], unique=False)

    op.create_table(
        "week_albums",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("week_id", sa.Integer(), nullable=False),
        sa.Column("album_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("position IN (1, 2)", name="ck_album_position_valid"),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["week_id"], ["weeks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_id", "position", name="uq_week_album_position"),
    )
    with op.batch_alter_table("week_albums", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_week_albums_album_id"), ["album_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_week_albums_week_id"), ["week_id"], unique=False)

    op.create_table(
        "week_movies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("week_id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("position IN (1, 2)", name="ck_movie_position_valid"),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["week_id"], ["weeks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_id", "position", name="uq_week_movie_position"),
    )
    with op.batch_alter_table("week_movies", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_week_movies_movie_id"), ["movie_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_week_movies_week_id"), ["week_id"], unique=False)

    op.create_table(
        "movie_cast",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("character", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("cached_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("movie_cast", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_movie_cast_movie_id"), ["movie_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_movie_cast_person_id"), ["person_id"], unique=False)

    op.create_table(
        "movie_crew",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("job", sa.String(length=100), nullable=True),
        sa.Column("cached_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("movie_crew", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_movie_crew_movie_id"), ["movie_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_movie_crew_person_id"), ["person_id"], unique=False)

    op.create_table(
        "album_artist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("album_id", sa.Integer(), nullable=False),
        sa.Column("artist_id", sa.Integer(), nullable=False),
        sa.Column("join_phrase", sa.String(length=50), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("cached_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("album_artist", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_album_artist_album_id"), ["album_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_album_artist_artist_id"), ["artist_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order of creation
    with op.batch_alter_table("album_artist", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_album_artist_artist_id"))
        batch_op.drop_index(batch_op.f("ix_album_artist_album_id"))
    op.drop_table("album_artist")

    with op.batch_alter_table("movie_crew", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_movie_crew_person_id"))
        batch_op.drop_index(batch_op.f("ix_movie_crew_movie_id"))
    op.drop_table("movie_crew")

    with op.batch_alter_table("movie_cast", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_movie_cast_person_id"))
        batch_op.drop_index(batch_op.f("ix_movie_cast_movie_id"))
    op.drop_table("movie_cast")

    with op.batch_alter_table("week_movies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_week_movies_week_id"))
        batch_op.drop_index(batch_op.f("ix_week_movies_movie_id"))
    op.drop_table("week_movies")

    with op.batch_alter_table("week_albums", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_week_albums_week_id"))
        batch_op.drop_index(batch_op.f("ix_week_albums_album_id"))
    op.drop_table("week_albums")

    with op.batch_alter_table("weeks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_weeks_year"))
        batch_op.drop_index(batch_op.f("ix_weeks_user_id"))
    op.drop_table("weeks")

    with op.batch_alter_table("artists", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_artists_musicbrainz_id"))
    op.drop_table("artists")

    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_people_tmdb_id"))
    op.drop_table("people")

    with op.batch_alter_table("movies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_movies_tmdb_id"))
    op.drop_table("movies")

    with op.batch_alter_table("albums", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_albums_musicbrainz_id"))
    op.drop_table("albums")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_username"))
        batch_op.drop_index(batch_op.f("ix_users_email"))
    op.drop_table("users")
