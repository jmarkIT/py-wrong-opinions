"""Week selection API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from wrong_opinions.database import get_db
from wrong_opinions.models.user import User
from wrong_opinions.models.week import Week, WeekAlbum, WeekMovie
from wrong_opinions.schemas.week import (
    WeekCreate,
    WeekListResponse,
    WeekResponse,
    WeekUpdate,
    WeekWithSelections,
)

router = APIRouter(prefix="/weeks", tags=["weeks"])

# Temporary: Until authentication is implemented (Phase 6),
# we use a default user_id. This should be replaced with
# proper auth dependency.
DEFAULT_USER_ID = 1


async def get_current_user_id() -> int:
    """Get current user ID. Placeholder until auth is implemented."""
    return DEFAULT_USER_ID


async def ensure_user_exists(db: AsyncSession, user_id: int) -> None:
    """Ensure a user exists, creating a placeholder if needed for development."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        # Create placeholder user for development
        placeholder_user = User(
            id=user_id,
            username=f"user{user_id}",
            email=f"user{user_id}@example.com",
            hashed_password="placeholder",
        )
        db.add(placeholder_user)
        await db.flush()


def week_to_response(week: Week) -> WeekResponse:
    """Convert a Week model to WeekResponse schema."""
    return WeekResponse(
        id=week.id,
        user_id=week.user_id,
        year=week.year,
        week_number=week.week_number,
        notes=week.notes,
        created_at=week.created_at,
        updated_at=week.updated_at,
    )


def week_to_response_with_selections(week: Week) -> WeekWithSelections:
    """Convert a Week model to WeekWithSelections schema."""
    from wrong_opinions.schemas.album import CachedAlbum
    from wrong_opinions.schemas.movie import CachedMovie
    from wrong_opinions.schemas.week import WeekAlbumSelection, WeekMovieSelection

    movies = [
        WeekMovieSelection(
            position=wm.position,
            added_at=wm.added_at,
            movie=CachedMovie(
                id=wm.movie.id,
                tmdb_id=wm.movie.tmdb_id,
                title=wm.movie.title,
                original_title=wm.movie.original_title,
                release_date=wm.movie.release_date,
                poster_path=wm.movie.poster_path,
                overview=wm.movie.overview,
                cached_at=wm.movie.cached_at,
            ),
        )
        for wm in week.week_movies
    ]

    albums = [
        WeekAlbumSelection(
            position=wa.position,
            added_at=wa.added_at,
            album=CachedAlbum(
                id=wa.album.id,
                musicbrainz_id=wa.album.musicbrainz_id,
                title=wa.album.title,
                artist=wa.album.artist,
                release_date=wa.album.release_date,
                cover_art_url=wa.album.cover_art_url,
                cached_at=wa.album.cached_at,
            ),
        )
        for wa in week.week_albums
    ]

    return WeekWithSelections(
        id=week.id,
        user_id=week.user_id,
        year=week.year,
        week_number=week.week_number,
        notes=week.notes,
        created_at=week.created_at,
        updated_at=week.updated_at,
        movies=movies,
        albums=albums,
    )


@router.get("", response_model=WeekListResponse)
async def list_weeks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    year: int | None = Query(None, ge=1900, le=2100, description="Filter by year"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> WeekListResponse:
    """List all weeks for the current user.

    Returns a paginated list of week selections, optionally filtered by year.
    """
    # Build base query
    base_query = select(Week).where(Week.user_id == user_id)

    if year is not None:
        base_query = base_query.where(Week.year == year)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated results
    offset = (page - 1) * page_size
    results_query = (
        base_query.order_by(Week.year.desc(), Week.week_number.desc())
        .offset(offset)
        .limit(page_size)
    )
    results = await db.execute(results_query)
    weeks = results.scalars().all()

    return WeekListResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=[week_to_response(week) for week in weeks],
    )


@router.post("", response_model=WeekResponse, status_code=201)
async def create_week(
    week_data: WeekCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> WeekResponse:
    """Create a new week selection.

    Creates a new week for the current user. A user can only have one
    selection per ISO week (year + week_number combination).
    """
    # Ensure user exists (for development without auth)
    await ensure_user_exists(db, user_id)

    # Check if week already exists for this user
    existing_query = select(Week).where(
        Week.user_id == user_id,
        Week.year == week_data.year,
        Week.week_number == week_data.week_number,
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Week {week_data.year}-W{week_data.week_number:02d} already exists",
        )

    # Create new week
    now = datetime.now(UTC)
    new_week = Week(
        user_id=user_id,
        year=week_data.year,
        week_number=week_data.week_number,
        notes=week_data.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(new_week)
    await db.flush()
    await db.refresh(new_week)

    return week_to_response(new_week)


@router.get("/{week_id}", response_model=WeekWithSelections)
async def get_week(
    week_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> WeekWithSelections:
    """Get a week with its movie and album selections.

    Returns the week details including all associated movies and albums.
    """
    query = (
        select(Week)
        .where(Week.id == week_id, Week.user_id == user_id)
        .options(
            selectinload(Week.week_movies).selectinload(WeekMovie.movie),
            selectinload(Week.week_albums).selectinload(WeekAlbum.album),
        )
    )
    result = await db.execute(query)
    week = result.scalar_one_or_none()

    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    return week_to_response_with_selections(week)


@router.patch("/{week_id}", response_model=WeekResponse)
async def update_week(
    week_id: int,
    week_data: WeekUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> WeekResponse:
    """Update a week selection.

    Currently only supports updating the notes field.
    """
    query = select(Week).where(Week.id == week_id, Week.user_id == user_id)
    result = await db.execute(query)
    week = result.scalar_one_or_none()

    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    # Update notes if provided
    if week_data.notes is not None:
        week.notes = week_data.notes
        week.updated_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(week)

    return week_to_response(week)


@router.delete("/{week_id}", status_code=204)
async def delete_week(
    week_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> None:
    """Delete a week selection.

    Deletes the week and all associated movie/album selections.
    """
    query = select(Week).where(Week.id == week_id, Week.user_id == user_id)
    result = await db.execute(query)
    week = result.scalar_one_or_none()

    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    await db.delete(week)
