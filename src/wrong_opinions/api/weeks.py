"""Week selection API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from wrong_opinions.database import get_db
from wrong_opinions.models.album import Album
from wrong_opinions.models.movie import Movie
from wrong_opinions.models.week import Week, WeekAlbum, WeekMovie
from wrong_opinions.schemas.album import CachedAlbum
from wrong_opinions.schemas.movie import CachedMovie
from wrong_opinions.schemas.week import (
    AddAlbumToWeek,
    AddMovieToWeek,
    WeekAlbumResponse,
    WeekCreate,
    WeekListResponse,
    WeekMovieResponse,
    WeekOwner,
    WeekResponse,
    WeekUpdate,
    WeekWithSelections,
)
from wrong_opinions.services.base import APIError, NotFoundError
from wrong_opinions.services.musicbrainz import MusicBrainzClient, get_musicbrainz_client
from wrong_opinions.services.tmdb import TMDBClient, get_tmdb_client
from wrong_opinions.utils.security import CurrentUser

router = APIRouter(prefix="/weeks", tags=["weeks"])


def week_to_response(week: Week) -> WeekResponse:
    """Convert a Week model to WeekResponse schema.

    Requires week.user to be loaded for owner info.
    """
    owner = None
    if week.user:
        owner = WeekOwner(id=week.user.id, username=week.user.username)

    return WeekResponse(
        id=week.id,
        user_id=week.user_id,
        owner=owner,
        year=week.year,
        week_number=week.week_number,
        notes=week.notes,
        created_at=week.created_at,
        updated_at=week.updated_at,
    )


def week_to_response_with_selections(week: Week) -> WeekWithSelections:
    """Convert a Week model to WeekWithSelections schema.

    Requires week.user to be loaded for owner info.
    """
    from wrong_opinions.schemas.album import CachedAlbum
    from wrong_opinions.schemas.movie import CachedMovie
    from wrong_opinions.schemas.week import WeekAlbumSelection, WeekMovieSelection

    owner = None
    if week.user:
        owner = WeekOwner(id=week.user.id, username=week.user.username)

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
        owner=owner,
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
    current_user: CurrentUser,  # noqa: ARG001 - Required for auth enforcement
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    year: int | None = Query(None, ge=1900, le=2100, description="Filter by year"),
    db: AsyncSession = Depends(get_db),
) -> WeekListResponse:
    """List all weeks globally.

    Returns a paginated list of all week selections, optionally filtered by year.
    All authenticated users can view all weeks.
    Requires authentication.
    """
    # Build base query - no user filter, show all weeks globally
    base_query = select(Week)

    if year is not None:
        base_query = base_query.where(Week.year == year)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated results with user info loaded
    offset = (page - 1) * page_size
    results_query = (
        base_query.options(selectinload(Week.user))
        .order_by(Week.year.desc(), Week.week_number.desc())
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
    current_user: CurrentUser,
    week_data: WeekCreate,
    db: AsyncSession = Depends(get_db),
) -> WeekResponse:
    """Create a new week selection.

    Creates a new week with the current user as owner. Only one selection
    can exist per ISO week (year + week_number combination) globally.
    Requires authentication.
    """
    # Check if week already exists globally
    existing_query = (
        select(Week)
        .where(
            Week.year == week_data.year,
            Week.week_number == week_data.week_number,
        )
        .options(selectinload(Week.user))
    )
    existing_result = await db.execute(existing_query)
    existing_week = existing_result.scalar_one_or_none()

    if existing_week:
        owner_name = existing_week.user.username if existing_week.user else "unknown"
        raise HTTPException(
            status_code=409,
            detail=f"Week {week_data.year}-W{week_data.week_number:02d} already exists (created by {owner_name})",
        )

    # Create new week with current user as owner
    now = datetime.now(UTC)
    new_week = Week(
        user_id=current_user.id,
        year=week_data.year,
        week_number=week_data.week_number,
        notes=week_data.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(new_week)
    await db.flush()
    await db.refresh(new_week)

    # Load user for response
    new_week.user = current_user

    return week_to_response(new_week)


@router.get("/current", response_model=WeekWithSelections)
async def get_current_week(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WeekWithSelections:
    """Get or create the current week selection.

    Returns the week selection for the current ISO week. If no selection
    exists for the current week, one is automatically created with the
    current user as owner.
    Requires authentication.
    """
    # Get current ISO week
    now = datetime.now(UTC)
    iso_calendar = now.isocalendar()
    current_year = iso_calendar[0]
    current_week = iso_calendar[1]

    # Try to find existing week globally
    query = (
        select(Week)
        .where(
            Week.year == current_year,
            Week.week_number == current_week,
        )
        .options(
            selectinload(Week.user),
            selectinload(Week.week_movies).selectinload(WeekMovie.movie),
            selectinload(Week.week_albums).selectinload(WeekAlbum.album),
        )
    )
    result = await db.execute(query)
    week = result.scalar_one_or_none()

    if not week:
        # Create new week for current period with current user as owner
        week = Week(
            user_id=current_user.id,
            year=current_year,
            week_number=current_week,
            notes=None,
            created_at=now,
            updated_at=now,
        )
        db.add(week)
        await db.flush()
        await db.refresh(week)

        # Initialize empty relationship lists and user for the response
        week.week_movies = []
        week.week_albums = []
        week.user = current_user

    return week_to_response_with_selections(week)


@router.get("/{week_id}", response_model=WeekWithSelections)
async def get_week(
    week_id: int,
    current_user: CurrentUser,  # noqa: ARG001 - Required for auth enforcement
    db: AsyncSession = Depends(get_db),
) -> WeekWithSelections:
    """Get a week with its movie and album selections.

    Returns the week details including all associated movies and albums.
    Any authenticated user can view any week.
    Requires authentication.
    """
    query = (
        select(Week)
        .where(Week.id == week_id)
        .options(
            selectinload(Week.user),
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
    current_user: CurrentUser,
    week_data: WeekUpdate,
    db: AsyncSession = Depends(get_db),
) -> WeekResponse:
    """Update a week selection.

    Currently only supports updating the notes field.
    Only the owner can update a week.
    Requires authentication.
    """
    query = select(Week).where(Week.id == week_id).options(selectinload(Week.user))
    result = await db.execute(query)
    week = result.scalar_one_or_none()

    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    if week.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can modify this week")

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
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a week selection.

    Deletes the week and all associated movie/album selections.
    Only the owner can delete a week.
    Requires authentication.
    """
    query = select(Week).where(Week.id == week_id)
    result = await db.execute(query)
    week = result.scalar_one_or_none()

    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    if week.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete this week")

    await db.delete(week)


@router.post("/{week_id}/movies", response_model=WeekMovieResponse, status_code=201)
async def add_movie_to_week(
    week_id: int,
    current_user: CurrentUser,
    movie_data: AddMovieToWeek,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
) -> WeekMovieResponse:
    """Add a movie to a week selection.

    Fetches the movie from TMDB (or cache) and adds it to the specified position.
    Position must be 1 or 2, and cannot be already occupied.
    Only the owner can add movies to a week.
    Requires authentication.
    """
    # Verify week exists
    week_query = select(Week).where(Week.id == week_id)
    week_result = await db.execute(week_query)
    week = week_result.scalar_one_or_none()

    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    if week.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can modify this week")

    # Check if position is already occupied
    existing_query = select(WeekMovie).where(
        WeekMovie.week_id == week_id, WeekMovie.position == movie_data.position
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Position {movie_data.position} is already occupied",
        )

    # Get or fetch movie from cache/TMDB
    try:
        movie_query = select(Movie).where(Movie.tmdb_id == movie_data.tmdb_id)
        movie_result = await db.execute(movie_query)
        movie = movie_result.scalar_one_or_none()

        if not movie:
            # Fetch from TMDB and cache
            tmdb_movie = await tmdb_client.get_movie(movie_data.tmdb_id)
            movie = Movie(
                tmdb_id=tmdb_movie.id,
                title=tmdb_movie.title,
                original_title=tmdb_movie.original_title,
                release_date=tmdb_movie.release_date,
                poster_path=tmdb_movie.poster_path,
                overview=tmdb_movie.overview,
                cached_at=datetime.now(UTC),
            )
            db.add(movie)
            await db.flush()

        # Create the week-movie association
        now = datetime.now(UTC)
        week_movie = WeekMovie(
            week_id=week_id,
            movie_id=movie.id,
            position=movie_data.position,
            added_at=now,
        )
        db.add(week_movie)
        await db.flush()

        # Update week's updated_at timestamp
        week.updated_at = now

        return WeekMovieResponse(
            week_id=week_id,
            position=movie_data.position,
            added_at=now,
            movie=CachedMovie(
                id=movie.id,
                tmdb_id=movie.tmdb_id,
                title=movie.title,
                original_title=movie.original_title,
                release_date=movie.release_date,
                poster_path=movie.poster_path,
                overview=movie.overview,
                cached_at=movie.cached_at,
            ),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail="Movie not found in TMDB") from e
    except APIError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    finally:
        await tmdb_client.close()


@router.delete("/{week_id}/movies/{position}", status_code=204)
async def remove_movie_from_week(
    week_id: int,
    position: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a movie from a week selection.

    Removes the movie at the specified position (1 or 2) from the week.
    Only the owner can remove movies from a week.
    Requires authentication.
    """
    # Validate position
    if position not in (1, 2):
        raise HTTPException(status_code=400, detail="Position must be 1 or 2")

    # Verify week exists
    week_query = select(Week).where(Week.id == week_id)
    week_result = await db.execute(week_query)
    week = week_result.scalar_one_or_none()

    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    if week.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can modify this week")

    # Find and delete the week-movie association
    week_movie_query = select(WeekMovie).where(
        WeekMovie.week_id == week_id, WeekMovie.position == position
    )
    week_movie_result = await db.execute(week_movie_query)
    week_movie = week_movie_result.scalar_one_or_none()

    if not week_movie:
        raise HTTPException(status_code=404, detail=f"No movie found at position {position}")

    await db.delete(week_movie)

    # Update week's updated_at timestamp
    week.updated_at = datetime.now(UTC)


@router.post("/{week_id}/albums", response_model=WeekAlbumResponse, status_code=201)
async def add_album_to_week(
    week_id: int,
    current_user: CurrentUser,
    album_data: AddAlbumToWeek,
    db: AsyncSession = Depends(get_db),
    musicbrainz_client: MusicBrainzClient = Depends(get_musicbrainz_client),
) -> WeekAlbumResponse:
    """Add an album to a week selection.

    Fetches the album from MusicBrainz (or cache) and adds it to the specified position.
    Position must be 1 or 2, and cannot be already occupied.
    Only the owner can add albums to a week.
    Requires authentication.
    """
    # Verify week exists
    week_query = select(Week).where(Week.id == week_id)
    week_result = await db.execute(week_query)
    week = week_result.scalar_one_or_none()

    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    if week.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can modify this week")

    # Check if position is already occupied
    existing_query = select(WeekAlbum).where(
        WeekAlbum.week_id == week_id, WeekAlbum.position == album_data.position
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Position {album_data.position} is already occupied",
        )

    # Get or fetch album from cache/MusicBrainz
    try:
        album_query = select(Album).where(Album.musicbrainz_id == album_data.musicbrainz_id)
        album_result = await db.execute(album_query)
        album = album_result.scalar_one_or_none()

        if not album:
            # Fetch from MusicBrainz and cache
            mb_release = await musicbrainz_client.get_release(album_data.musicbrainz_id)

            # Get artist name from the release
            artist_name = "Unknown Artist"
            if mb_release.artist_credit:
                artist_name = mb_release.artist_credit

            # Parse release date if available
            release_date = None
            if mb_release.date:
                try:
                    # MusicBrainz dates can be YYYY, YYYY-MM, or YYYY-MM-DD
                    date_str = mb_release.date
                    if len(date_str) == 4:  # YYYY
                        from datetime import date as date_type

                        release_date = date_type(int(date_str), 1, 1)
                    elif len(date_str) == 7:  # YYYY-MM
                        from datetime import date as date_type

                        parts = date_str.split("-")
                        release_date = date_type(int(parts[0]), int(parts[1]), 1)
                    elif len(date_str) == 10:  # YYYY-MM-DD
                        from datetime import date as date_type

                        parts = date_str.split("-")
                        release_date = date_type(int(parts[0]), int(parts[1]), int(parts[2]))
                except (ValueError, IndexError):
                    pass  # Keep release_date as None if parsing fails

            # Get cover art URL
            cover_art_url = musicbrainz_client.get_cover_art_front_url(album_data.musicbrainz_id)

            album = Album(
                musicbrainz_id=mb_release.id,
                title=mb_release.title,
                artist=artist_name,
                release_date=release_date,
                cover_art_url=cover_art_url,
                cached_at=datetime.now(UTC),
            )
            db.add(album)
            await db.flush()

        # Create the week-album association
        now = datetime.now(UTC)
        week_album = WeekAlbum(
            week_id=week_id,
            album_id=album.id,
            position=album_data.position,
            added_at=now,
        )
        db.add(week_album)
        await db.flush()

        # Update week's updated_at timestamp
        week.updated_at = now

        return WeekAlbumResponse(
            week_id=week_id,
            position=album_data.position,
            added_at=now,
            album=CachedAlbum(
                id=album.id,
                musicbrainz_id=album.musicbrainz_id,
                title=album.title,
                artist=album.artist,
                release_date=album.release_date,
                cover_art_url=album.cover_art_url,
            ),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail="Album not found in MusicBrainz") from e
    except APIError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    finally:
        await musicbrainz_client.close()


@router.delete("/{week_id}/albums/{position}", status_code=204)
async def remove_album_from_week(
    week_id: int,
    position: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove an album from a week selection.

    Removes the album at the specified position (1 or 2) from the week.
    Only the owner can remove albums from a week.
    Requires authentication.
    """
    # Validate position
    if position not in (1, 2):
        raise HTTPException(status_code=400, detail="Position must be 1 or 2")

    # Verify week exists
    week_query = select(Week).where(Week.id == week_id)
    week_result = await db.execute(week_query)
    week = week_result.scalar_one_or_none()

    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    if week.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can modify this week")

    # Find and delete the week-album association
    week_album_query = select(WeekAlbum).where(
        WeekAlbum.week_id == week_id, WeekAlbum.position == position
    )
    week_album_result = await db.execute(week_album_query)
    week_album = week_album_result.scalar_one_or_none()

    if not week_album:
        raise HTTPException(status_code=404, detail=f"No album found at position {position}")

    await db.delete(week_album)

    # Update week's updated_at timestamp
    week.updated_at = datetime.now(UTC)
