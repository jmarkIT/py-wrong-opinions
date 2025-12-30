"""Movie API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from wrong_opinions.database import get_db
from wrong_opinions.models.movie import Movie
from wrong_opinions.models.person import MovieCast, MovieCrew, Person
from wrong_opinions.models.week import WeekMovie
from wrong_opinions.schemas.movie import (
    CastMember,
    CrewMember,
    MovieCredits,
    MovieDetails,
    MovieSearchResponse,
    MovieSearchResult,
    MovieSelectionsListResponse,
    MovieSelectionWeek,
    MovieWithSelections,
)
from wrong_opinions.services.base import NotFoundError
from wrong_opinions.services.tmdb import TMDBClient, get_tmdb_client
from wrong_opinions.utils.security import CurrentUser

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search", response_model=MovieSearchResponse)
async def search_movies(
    current_user: CurrentUser,  # noqa: ARG001 - Required for auth enforcement
    query: str = Query(..., min_length=1, description="Search query for movies"),
    page: int = Query(1, ge=1, description="Page number"),
    year: int | None = Query(None, ge=1800, le=2100, description="Filter by release year"),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
) -> MovieSearchResponse:
    """Search for movies using TMDB.

    Returns a list of movies matching the search query.
    Requires authentication.
    """
    try:
        response = await tmdb_client.search_movies(query=query, page=page, year=year)

        results = [
            MovieSearchResult(
                tmdb_id=movie.id,
                title=movie.title,
                original_title=movie.original_title,
                release_date=movie.release_date,
                poster_url=tmdb_client.get_poster_url(movie.poster_path),
                overview=movie.overview,
                vote_average=movie.vote_average,
            )
            for movie in response.results
        ]

        return MovieSearchResponse(
            page=response.page,
            total_pages=response.total_pages,
            total_results=response.total_results,
            results=results,
        )
    finally:
        await tmdb_client.close()


@router.get("/selections", response_model=MovieSelectionsListResponse)
async def list_all_selected_movies(
    current_user: CurrentUser,  # noqa: ARG001 - Required for auth enforcement
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    db: AsyncSession = Depends(get_db),
) -> MovieSelectionsListResponse:
    """List all movies that have been selected in any week.

    Returns a paginated list of movies with their week selection context.
    Sorted alphabetically by title.
    Requires authentication.
    """
    # Count total distinct movies with selections
    count_query = select(func.count(func.distinct(Movie.id))).select_from(Movie).join(WeekMovie)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated movies with eager-loaded week associations
    offset = (page - 1) * page_size
    movies_query = (
        select(Movie)
        .join(WeekMovie)
        .distinct()
        .options(selectinload(Movie.week_movies).selectinload(WeekMovie.week))
        .order_by(func.lower(Movie.title))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(movies_query)
    movies = result.scalars().all()

    # Build response with selection details
    results = [
        MovieWithSelections(
            id=movie.id,
            tmdb_id=movie.tmdb_id,
            title=movie.title,
            original_title=movie.original_title,
            release_date=movie.release_date,
            poster_path=movie.poster_path,
            overview=movie.overview,
            cached_at=movie.cached_at,
            selections=[
                MovieSelectionWeek(
                    week_id=wm.week.id,
                    year=wm.week.year,
                    week_number=wm.week.week_number,
                    position=wm.position,
                    added_at=wm.added_at,
                )
                for wm in movie.week_movies
            ],
        )
        for movie in movies
    ]

    return MovieSelectionsListResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=results,
    )


@router.get("/{tmdb_id}", response_model=MovieDetails)
async def get_movie(
    tmdb_id: int,
    current_user: CurrentUser,  # noqa: ARG001 - Required for auth enforcement
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
) -> MovieDetails:
    """Get detailed movie information.

    First checks local cache, then fetches from TMDB if not cached.
    Caches the result in the local database for future requests.
    Requires authentication.
    """
    # Check local cache first
    result = await db.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
    cached_movie = result.scalar_one_or_none()

    if cached_movie:
        return MovieDetails(
            tmdb_id=cached_movie.tmdb_id,
            title=cached_movie.title,
            original_title=cached_movie.original_title,
            release_date=cached_movie.release_date,
            poster_url=tmdb_client.get_poster_url(cached_movie.poster_path),
            backdrop_url=None,  # Not stored in cache
            overview=cached_movie.overview,
            runtime=None,  # Not stored in cache
            vote_average=0.0,  # Not stored in cache
            vote_count=0,  # Not stored in cache
            tagline=None,  # Not stored in cache
            status=None,  # Not stored in cache
            imdb_id=None,  # Not stored in cache
            cached=True,
        )

    # Fetch from TMDB
    # APIError exceptions (except NotFoundError) are handled globally
    try:
        movie = await tmdb_client.get_movie(tmdb_id)

        # Cache the movie in the database
        new_movie = Movie(
            tmdb_id=movie.id,
            title=movie.title,
            original_title=movie.original_title,
            release_date=movie.release_date,
            poster_path=movie.poster_path,
            overview=movie.overview,
            cached_at=datetime.now(UTC),
        )
        db.add(new_movie)
        # Note: commit happens automatically via get_db dependency

        return MovieDetails(
            tmdb_id=movie.id,
            title=movie.title,
            original_title=movie.original_title,
            release_date=movie.release_date,
            poster_url=tmdb_client.get_poster_url(movie.poster_path),
            backdrop_url=tmdb_client.get_backdrop_url(movie.backdrop_path),
            overview=movie.overview,
            runtime=movie.runtime,
            vote_average=movie.vote_average,
            vote_count=movie.vote_count,
            tagline=movie.tagline,
            status=movie.status,
            imdb_id=movie.imdb_id,
            cached=False,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Movie not found") from None
    finally:
        await tmdb_client.close()


@router.get("/{tmdb_id}/credits", response_model=MovieCredits)
async def get_movie_credits(
    tmdb_id: int,
    current_user: CurrentUser,  # noqa: ARG001 - Required for auth enforcement
    limit: int = Query(10, ge=1, le=50, description="Max number of cast/crew to return"),
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
) -> MovieCredits:
    """Get cast and crew for a movie.

    First checks local cache, then fetches from TMDB if not cached.
    Caches the result in the local database for future requests.
    Requires authentication.
    """
    # Check if we have the movie in the database
    result = await db.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
    cached_movie = result.scalar_one_or_none()

    if cached_movie:
        # Check if we have cached credits for this movie
        cast_result = await db.execute(
            select(MovieCast)
            .where(MovieCast.movie_id == cached_movie.id)
            .order_by(MovieCast.order)
            .limit(limit)
        )
        cached_cast = cast_result.scalars().all()

        crew_result = await db.execute(
            select(MovieCrew).where(MovieCrew.movie_id == cached_movie.id).limit(limit)
        )
        cached_crew = crew_result.scalars().all()

        if cached_cast or cached_crew:
            # Load person data for cast
            cast_members = []
            for mc in cached_cast:
                person_result = await db.execute(select(Person).where(Person.id == mc.person_id))
                person = person_result.scalar_one()
                cast_members.append(
                    CastMember(
                        tmdb_id=person.tmdb_id,
                        name=person.name,
                        character=mc.character,
                        order=mc.order,
                        profile_url=tmdb_client.get_profile_url(person.profile_path),
                    )
                )

            # Load person data for crew
            crew_members = []
            for mc in cached_crew:
                person_result = await db.execute(select(Person).where(Person.id == mc.person_id))
                person = person_result.scalar_one()
                crew_members.append(
                    CrewMember(
                        tmdb_id=person.tmdb_id,
                        name=person.name,
                        department=mc.department,
                        job=mc.job,
                        profile_url=tmdb_client.get_profile_url(person.profile_path),
                    )
                )

            return MovieCredits(cast=cast_members, crew=crew_members)

    # Fetch from TMDB
    try:
        credits = await tmdb_client.get_movie_credits(tmdb_id)

        # If movie doesn't exist yet, fetch and cache it first
        if not cached_movie:
            movie_data = await tmdb_client.get_movie(tmdb_id)
            cached_movie = Movie(
                tmdb_id=movie_data.id,
                title=movie_data.title,
                original_title=movie_data.original_title,
                release_date=movie_data.release_date,
                poster_path=movie_data.poster_path,
                overview=movie_data.overview,
                cached_at=datetime.now(UTC),
            )
            db.add(cached_movie)
            await db.flush()  # Flush to get the movie ID

        # Cache cast members
        for cast_data in credits.cast[:limit]:
            # Get or create person
            person_result = await db.execute(select(Person).where(Person.tmdb_id == cast_data.id))
            person = person_result.scalar_one_or_none()

            if not person:
                person = Person(
                    tmdb_id=cast_data.id,
                    name=cast_data.name,
                    profile_path=cast_data.profile_path,
                    known_for_department=cast_data.known_for_department,
                    cached_at=datetime.now(UTC),
                )
                db.add(person)
                await db.flush()

            # Add cast credit
            movie_cast = MovieCast(
                movie_id=cached_movie.id,
                person_id=person.id,
                character=cast_data.character,
                order=cast_data.order,
                cached_at=datetime.now(UTC),
            )
            db.add(movie_cast)

        # Cache crew members (filter to key roles)
        key_jobs = {"Director", "Writer", "Screenplay", "Composer", "Producer", "Cinematography"}
        filtered_crew = [c for c in credits.crew if c.job in key_jobs][:limit]

        for crew_data in filtered_crew:
            # Get or create person
            person_result = await db.execute(select(Person).where(Person.tmdb_id == crew_data.id))
            person = person_result.scalar_one_or_none()

            if not person:
                person = Person(
                    tmdb_id=crew_data.id,
                    name=crew_data.name,
                    profile_path=crew_data.profile_path,
                    known_for_department=crew_data.known_for_department,
                    cached_at=datetime.now(UTC),
                )
                db.add(person)
                await db.flush()

            # Add crew credit
            movie_crew = MovieCrew(
                movie_id=cached_movie.id,
                person_id=person.id,
                department=crew_data.department,
                job=crew_data.job,
                cached_at=datetime.now(UTC),
            )
            db.add(movie_crew)

        # Build response
        cast_members = [
            CastMember(
                tmdb_id=c.id,
                name=c.name,
                character=c.character,
                order=c.order,
                profile_url=tmdb_client.get_profile_url(c.profile_path),
            )
            for c in credits.cast[:limit]
        ]

        crew_members = [
            CrewMember(
                tmdb_id=c.id,
                name=c.name,
                department=c.department,
                job=c.job,
                profile_url=tmdb_client.get_profile_url(c.profile_path),
            )
            for c in filtered_crew
        ]

        return MovieCredits(cast=cast_members, crew=crew_members)

    except NotFoundError:
        raise HTTPException(status_code=404, detail="Movie not found") from None
    finally:
        await tmdb_client.close()
