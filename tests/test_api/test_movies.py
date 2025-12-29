"""Tests for movie API endpoints."""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from wrong_opinions.database import get_db
from wrong_opinions.main import app
from wrong_opinions.models.user import User
from wrong_opinions.schemas.external import (
    TMDBCastMember,
    TMDBCreditsResponse,
    TMDBCrewMember,
    TMDBMovieDetails,
    TMDBMovieResult,
    TMDBSearchResponse,
)
from wrong_opinions.services.tmdb import TMDBClient, get_tmdb_client
from wrong_opinions.utils.security import get_current_active_user

# Sample test data
SAMPLE_SEARCH_RESPONSE = TMDBSearchResponse(
    page=1,
    total_pages=1,
    total_results=2,
    results=[
        TMDBMovieResult(
            id=550,
            title="Fight Club",
            original_title="Fight Club",
            release_date=date(1999, 10, 15),
            poster_path="/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            overview="A ticking-Loss insomnia insurance worker...",
            vote_average=8.4,
            vote_count=25000,
            popularity=50.5,
        ),
        TMDBMovieResult(
            id=551,
            title="Fight Club 2",
            original_title="Fight Club 2",
            release_date=None,
            poster_path=None,
            overview=None,
            vote_average=0.0,
            vote_count=0,
            popularity=1.0,
        ),
    ],
)

SAMPLE_MOVIE_DETAILS = TMDBMovieDetails(
    id=550,
    title="Fight Club",
    original_title="Fight Club",
    release_date=date(1999, 10, 15),
    poster_path="/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
    backdrop_path="/87hTDiay2N/background.jpg",
    overview="A ticking-Loss insomnia insurance worker...",
    runtime=139,
    vote_average=8.4,
    vote_count=25000,
    popularity=50.5,
    status="Released",
    tagline="Mischief. Mayhem. Soap.",
    budget=63000000,
    revenue=100853753,
    imdb_id="tt0137523",
    homepage="https://www.foxmovies.com/movies/fight-club",
)

SAMPLE_CREDITS_RESPONSE = TMDBCreditsResponse(
    id=550,
    cast=[
        TMDBCastMember(
            id=819,
            name="Edward Norton",
            character="The Narrator",
            order=0,
            profile_path="/5XBzD5WuTyVQZeS4II6gs1nn5P6.jpg",
            known_for_department="Acting",
        ),
        TMDBCastMember(
            id=287,
            name="Brad Pitt",
            character="Tyler Durden",
            order=1,
            profile_path="/oTB9vGIBacH5aQNS0pUM74QSWuf.jpg",
            known_for_department="Acting",
        ),
    ],
    crew=[
        TMDBCrewMember(
            id=7467,
            name="David Fincher",
            department="Directing",
            job="Director",
            profile_path="/tpEczFclQZeKAiCeKZZ0adRvtfz.jpg",
            known_for_department="Directing",
        ),
        TMDBCrewMember(
            id=7468,
            name="Jim Uhls",
            department="Writing",
            job="Screenplay",
            profile_path=None,
            known_for_department="Writing",
        ),
    ],
)


@pytest.fixture
def mock_tmdb_client():
    """Create a mock TMDB client."""
    mock_client = MagicMock(spec=TMDBClient)
    mock_client.search_movies = AsyncMock(return_value=SAMPLE_SEARCH_RESPONSE)
    mock_client.get_movie = AsyncMock(return_value=SAMPLE_MOVIE_DETAILS)
    mock_client.get_movie_credits = AsyncMock(return_value=SAMPLE_CREDITS_RESPONSE)
    mock_client.get_poster_url.side_effect = lambda path, size="w342": (
        f"https://image.tmdb.org/t/p/{size}{path}" if path else None
    )
    mock_client.get_backdrop_url.side_effect = lambda path, size="w780": (
        f"https://image.tmdb.org/t/p/{size}{path}" if path else None
    )
    mock_client.get_profile_url.side_effect = lambda path, size="w185": (
        f"https://image.tmdb.org/t/p/{size}{path}" if path else None
    )
    mock_client.close = AsyncMock()
    return mock_client


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = AsyncMock()
    # Result is sync, not async
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Not cached by default
    # execute is async but returns a sync Result
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    return mock_session


@pytest.fixture
def mock_current_user():
    """Create a mock authenticated user."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.is_active = True
    mock_user.created_at = datetime(2025, 1, 1, 12, 0, 0)
    return mock_user


class TestMovieSearch:
    """Tests for movie search endpoint."""

    async def test_search_movies_success(
        self, client: AsyncClient, mock_tmdb_client: MagicMock, mock_current_user: MagicMock
    ) -> None:
        """Test successful movie search."""
        app.dependency_overrides[get_tmdb_client] = lambda: mock_tmdb_client
        app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

        try:
            response = await client.get("/api/movies/search?query=Fight Club")

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 1
            assert data["total_results"] == 2
            assert len(data["results"]) == 2
            assert data["results"][0]["tmdb_id"] == 550
            assert data["results"][0]["title"] == "Fight Club"
            assert data["results"][0]["poster_url"] is not None
        finally:
            app.dependency_overrides.clear()

    async def test_search_movies_with_year(
        self, client: AsyncClient, mock_tmdb_client: MagicMock, mock_current_user: MagicMock
    ) -> None:
        """Test movie search with year filter."""
        app.dependency_overrides[get_tmdb_client] = lambda: mock_tmdb_client
        app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

        try:
            response = await client.get("/api/movies/search?query=Fight&year=1999")

            assert response.status_code == 200
            mock_tmdb_client.search_movies.assert_called_once_with(query="Fight", page=1, year=1999)
        finally:
            app.dependency_overrides.clear()

    async def test_search_movies_empty_query(
        self, client: AsyncClient, mock_tmdb_client: MagicMock, mock_current_user: MagicMock
    ) -> None:
        """Test movie search with empty query returns 422."""
        # Need mock because dependency is resolved before validation
        app.dependency_overrides[get_tmdb_client] = lambda: mock_tmdb_client
        app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

        try:
            response = await client.get("/api/movies/search?query=")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_search_movies_missing_query(
        self, client: AsyncClient, mock_tmdb_client: MagicMock, mock_current_user: MagicMock
    ) -> None:
        """Test movie search without query parameter returns 422."""
        # Need mock because dependency is resolved before validation
        app.dependency_overrides[get_tmdb_client] = lambda: mock_tmdb_client
        app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

        try:
            response = await client.get("/api/movies/search")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_search_movies_pagination(
        self, client: AsyncClient, mock_tmdb_client: MagicMock, mock_current_user: MagicMock
    ) -> None:
        """Test movie search with pagination."""
        app.dependency_overrides[get_tmdb_client] = lambda: mock_tmdb_client
        app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

        try:
            response = await client.get("/api/movies/search?query=test&page=2")

            assert response.status_code == 200
            mock_tmdb_client.search_movies.assert_called_once_with(query="test", page=2, year=None)
        finally:
            app.dependency_overrides.clear()


class TestGetMovie:
    """Tests for get movie details endpoint."""

    async def test_get_movie_success(
        self,
        client: AsyncClient,
        mock_tmdb_client: MagicMock,
        mock_db_session: AsyncMock,
        mock_current_user: MagicMock,
    ) -> None:
        """Test successful movie details fetch from API."""

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_tmdb_client] = lambda: mock_tmdb_client
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

        try:
            response = await client.get("/api/movies/550")

            assert response.status_code == 200
            data = response.json()
            assert data["tmdb_id"] == 550
            assert data["title"] == "Fight Club"
            assert data["runtime"] == 139
            assert data["cached"] is False
        finally:
            app.dependency_overrides.clear()

    async def test_get_movie_from_cache(
        self,
        client: AsyncClient,
        mock_tmdb_client: MagicMock,
        mock_db_session: AsyncMock,
        mock_current_user: MagicMock,
    ) -> None:
        """Test movie details fetch from cache."""
        # Set up cached movie
        cached_movie = MagicMock()
        cached_movie.tmdb_id = 550
        cached_movie.title = "Fight Club"
        cached_movie.original_title = "Fight Club"
        cached_movie.release_date = date(1999, 10, 15)
        cached_movie.poster_path = "/poster.jpg"
        cached_movie.overview = "A movie about fighting."

        # Result is sync, not async
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cached_movie
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_tmdb_client] = lambda: mock_tmdb_client
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

        try:
            response = await client.get("/api/movies/550")

            assert response.status_code == 200
            data = response.json()
            assert data["tmdb_id"] == 550
            assert data["cached"] is True
            # TMDB client get_movie should not be called
            mock_tmdb_client.get_movie.assert_not_called()
        finally:
            app.dependency_overrides.clear()

    async def test_get_movie_not_found(
        self,
        client: AsyncClient,
        mock_tmdb_client: MagicMock,
        mock_db_session: AsyncMock,
        mock_current_user: MagicMock,
    ) -> None:
        """Test movie details fetch for non-existent movie."""
        from wrong_opinions.services.base import NotFoundError

        mock_tmdb_client.get_movie.side_effect = NotFoundError("Movie not found")

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_tmdb_client] = lambda: mock_tmdb_client
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

        try:
            response = await client.get("/api/movies/99999999")

            assert response.status_code == 404
            assert response.json()["detail"] == "Movie not found"
        finally:
            app.dependency_overrides.clear()


class TestGetMovieCredits:
    """Tests for get movie credits endpoint."""

    async def test_get_movie_credits_success(
        self,
        client: AsyncClient,
        mock_tmdb_client: MagicMock,
        mock_db_session: AsyncMock,
        mock_current_user: MagicMock,
    ) -> None:
        """Test successful movie credits fetch from API."""

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_tmdb_client] = lambda: mock_tmdb_client
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

        try:
            response = await client.get("/api/movies/550/credits")

            assert response.status_code == 200
            data = response.json()
            assert "cast" in data
            assert "crew" in data
            assert len(data["cast"]) == 2
            assert data["cast"][0]["tmdb_id"] == 819
            assert data["cast"][0]["name"] == "Edward Norton"
            assert data["cast"][0]["character"] == "The Narrator"
            assert data["cast"][0]["profile_url"] is not None
            # Crew is filtered to key roles only
            assert len(data["crew"]) == 2
            assert data["crew"][0]["tmdb_id"] == 7467
            assert data["crew"][0]["name"] == "David Fincher"
            assert data["crew"][0]["job"] == "Director"
        finally:
            app.dependency_overrides.clear()

    async def test_get_movie_credits_not_found(
        self,
        client: AsyncClient,
        mock_tmdb_client: MagicMock,
        mock_db_session: AsyncMock,
        mock_current_user: MagicMock,
    ) -> None:
        """Test movie credits fetch for non-existent movie."""
        from wrong_opinions.services.base import NotFoundError

        mock_tmdb_client.get_movie_credits.side_effect = NotFoundError("Movie not found")

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_tmdb_client] = lambda: mock_tmdb_client
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

        try:
            response = await client.get("/api/movies/99999999/credits")

            assert response.status_code == 404
            assert response.json()["detail"] == "Movie not found"
        finally:
            app.dependency_overrides.clear()

    async def test_get_movie_credits_with_limit(
        self,
        client: AsyncClient,
        mock_tmdb_client: MagicMock,
        mock_db_session: AsyncMock,
        mock_current_user: MagicMock,
    ) -> None:
        """Test movie credits fetch with custom limit."""

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_tmdb_client] = lambda: mock_tmdb_client
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = lambda: mock_current_user

        try:
            response = await client.get("/api/movies/550/credits?limit=5")

            assert response.status_code == 200
            # The endpoint was called successfully with limit
            mock_tmdb_client.get_movie_credits.assert_called_once_with(550)
        finally:
            app.dependency_overrides.clear()
