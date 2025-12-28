"""Movie API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from wrong_opinions.database import get_db
from wrong_opinions.models.movie import Movie
from wrong_opinions.schemas.movie import MovieDetails, MovieSearchResponse, MovieSearchResult
from wrong_opinions.services.base import APIError, NotFoundError
from wrong_opinions.services.tmdb import TMDBClient, get_tmdb_client

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search", response_model=MovieSearchResponse)
async def search_movies(
    query: str = Query(..., min_length=1, description="Search query for movies"),
    page: int = Query(1, ge=1, description="Page number"),
    year: int | None = Query(None, ge=1800, le=2100, description="Filter by release year"),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
) -> MovieSearchResponse:
    """Search for movies using TMDB.

    Returns a list of movies matching the search query.
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
    except APIError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    finally:
        await tmdb_client.close()


@router.get("/{tmdb_id}", response_model=MovieDetails)
async def get_movie(
    tmdb_id: int,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
) -> MovieDetails:
    """Get detailed movie information.

    First checks local cache, then fetches from TMDB if not cached.
    Caches the result in the local database for future requests.
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
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail="Movie not found") from e
    except APIError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    finally:
        await tmdb_client.close()
