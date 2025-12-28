"""Tests for week API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from wrong_opinions.database import get_db
from wrong_opinions.main import app
from wrong_opinions.models.album import Album
from wrong_opinions.models.movie import Movie
from wrong_opinions.models.user import User
from wrong_opinions.models.week import Week, WeekAlbum, WeekMovie
from wrong_opinions.services.musicbrainz import get_musicbrainz_client
from wrong_opinions.services.tmdb import get_tmdb_client


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session


def create_mock_week(
    id: int = 1,
    user_id: int = 1,
    year: int = 2025,
    week_number: int = 1,
    notes: str | None = None,
) -> MagicMock:
    """Create a mock Week object."""
    mock_week = MagicMock(spec=Week)
    mock_week.id = id
    mock_week.user_id = user_id
    mock_week.year = year
    mock_week.week_number = week_number
    mock_week.notes = notes
    mock_week.created_at = datetime(2025, 1, 1, 12, 0, 0)
    mock_week.updated_at = datetime(2025, 1, 1, 12, 0, 0)
    mock_week.week_movies = []
    mock_week.week_albums = []
    return mock_week


def create_mock_user(id: int = 1) -> MagicMock:
    """Create a mock User object."""
    mock_user = MagicMock(spec=User)
    mock_user.id = id
    mock_user.username = f"user{id}"
    mock_user.email = f"user{id}@example.com"
    return mock_user


class TestListWeeks:
    """Tests for list weeks endpoint."""

    async def test_list_weeks_empty(self, client: AsyncClient, mock_db_session: AsyncMock) -> None:
        """Test listing weeks when none exist."""
        # Mock user check - user exists
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = create_mock_user()

        # Mock count query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        # Mock results query
        weeks_result = MagicMock()
        weeks_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(side_effect=[count_result, weeks_result])

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/weeks")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["page"] == 1
            assert data["results"] == []
        finally:
            app.dependency_overrides.clear()

    async def test_list_weeks_with_results(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test listing weeks with results."""
        mock_weeks = [
            create_mock_week(id=1, year=2025, week_number=2),
            create_mock_week(id=2, year=2025, week_number=1),
        ]

        # Mock count query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        # Mock results query
        weeks_result = MagicMock()
        weeks_result.scalars.return_value.all.return_value = mock_weeks

        mock_db_session.execute = AsyncMock(side_effect=[count_result, weeks_result])

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/weeks")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["results"]) == 2
            assert data["results"][0]["year"] == 2025
        finally:
            app.dependency_overrides.clear()

    async def test_list_weeks_with_year_filter(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test listing weeks filtered by year."""
        mock_weeks = [create_mock_week(id=1, year=2024, week_number=52)]

        # Mock count query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        # Mock results query
        weeks_result = MagicMock()
        weeks_result.scalars.return_value.all.return_value = mock_weeks

        mock_db_session.execute = AsyncMock(side_effect=[count_result, weeks_result])

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/weeks?year=2024")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["results"][0]["year"] == 2024
        finally:
            app.dependency_overrides.clear()


class TestCreateWeek:
    """Tests for create week endpoint."""

    async def test_create_week_success(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test successful week creation."""
        # Mock user check
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = create_mock_user()

        # Mock existing week check - no existing week
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[user_result, existing_result])

        # Mock flush and refresh to set the created week's properties
        async def mock_refresh(week):
            week.id = 1
            week.created_at = datetime(2025, 1, 1, 12, 0, 0)
            week.updated_at = datetime(2025, 1, 1, 12, 0, 0)

        mock_db_session.refresh = mock_refresh

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/weeks",
                json={"year": 2025, "week_number": 1, "notes": "Test week"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["year"] == 2025
            assert data["week_number"] == 1
            assert data["notes"] == "Test week"
        finally:
            app.dependency_overrides.clear()

    async def test_create_week_conflict(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test creating a week that already exists."""
        # Mock user check
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = create_mock_user()

        # Mock existing week check - week exists
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = create_mock_week()

        mock_db_session.execute = AsyncMock(side_effect=[user_result, existing_result])

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/weeks",
                json={"year": 2025, "week_number": 1},
            )

            assert response.status_code == 409
            assert "already exists" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    async def test_create_week_invalid_week_number(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test creating a week with invalid week number."""

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/weeks",
                json={"year": 2025, "week_number": 54},
            )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


class TestGetWeek:
    """Tests for get week endpoint."""

    async def test_get_week_success(self, client: AsyncClient, mock_db_session: AsyncMock) -> None:
        """Test successful week retrieval."""
        mock_week = create_mock_week(id=1, notes="Test notes")

        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_week
        mock_db_session.execute = AsyncMock(return_value=result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/weeks/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["notes"] == "Test notes"
            assert data["movies"] == []
            assert data["albums"] == []
        finally:
            app.dependency_overrides.clear()

    async def test_get_week_not_found(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test getting a non-existent week."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/weeks/999")

            assert response.status_code == 404
            assert response.json()["detail"] == "Week not found"
        finally:
            app.dependency_overrides.clear()


class TestUpdateWeek:
    """Tests for update week endpoint."""

    async def test_update_week_success(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test successful week update."""
        mock_week = create_mock_week(id=1, notes=None)

        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_week
        mock_db_session.execute = AsyncMock(return_value=result)

        async def mock_refresh(week):
            week.notes = "Updated notes"
            week.updated_at = datetime(2025, 1, 2, 12, 0, 0)

        mock_db_session.refresh = mock_refresh

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.patch(
                "/api/weeks/1",
                json={"notes": "Updated notes"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["notes"] == "Updated notes"
        finally:
            app.dependency_overrides.clear()

    async def test_update_week_not_found(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test updating a non-existent week."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.patch(
                "/api/weeks/999",
                json={"notes": "New notes"},
            )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestDeleteWeek:
    """Tests for delete week endpoint."""

    async def test_delete_week_success(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test successful week deletion."""
        mock_week = create_mock_week(id=1)

        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_week
        mock_db_session.execute = AsyncMock(return_value=result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.delete("/api/weeks/1")

            assert response.status_code == 204
            mock_db_session.delete.assert_called_once_with(mock_week)
        finally:
            app.dependency_overrides.clear()

    async def test_delete_week_not_found(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test deleting a non-existent week."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.delete("/api/weeks/999")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


def create_mock_movie(
    id: int = 1,
    tmdb_id: int = 550,
    title: str = "Fight Club",
    original_title: str | None = None,
    release_date=None,
    poster_path: str | None = "/poster.jpg",
    overview: str | None = "A movie about a club",
) -> MagicMock:
    """Create a mock Movie object."""
    mock_movie = MagicMock(spec=Movie)
    mock_movie.id = id
    mock_movie.tmdb_id = tmdb_id
    mock_movie.title = title
    mock_movie.original_title = original_title
    mock_movie.release_date = release_date
    mock_movie.poster_path = poster_path
    mock_movie.overview = overview
    mock_movie.cached_at = datetime(2025, 1, 1, 12, 0, 0)
    return mock_movie


def create_mock_week_movie(
    week_id: int = 1,
    movie_id: int = 1,
    position: int = 1,
) -> MagicMock:
    """Create a mock WeekMovie object."""
    mock_week_movie = MagicMock(spec=WeekMovie)
    mock_week_movie.id = 1
    mock_week_movie.week_id = week_id
    mock_week_movie.movie_id = movie_id
    mock_week_movie.position = position
    mock_week_movie.added_at = datetime(2025, 1, 1, 12, 0, 0)
    return mock_week_movie


@pytest.fixture
def mock_tmdb_client():
    """Create a mock TMDB client."""
    mock_client = AsyncMock()
    mock_client.close = AsyncMock()

    # Create a mock movie response
    mock_movie_response = MagicMock()
    mock_movie_response.id = 550
    mock_movie_response.title = "Fight Club"
    mock_movie_response.original_title = None
    mock_movie_response.release_date = None
    mock_movie_response.poster_path = "/poster.jpg"
    mock_movie_response.overview = "A movie about a club"

    mock_client.get_movie = AsyncMock(return_value=mock_movie_response)
    return mock_client


class TestAddMovieToWeek:
    """Tests for add movie to week endpoint."""

    async def test_add_movie_success_from_cache(
        self, client: AsyncClient, mock_db_session: AsyncMock, mock_tmdb_client: AsyncMock
    ) -> None:
        """Test successfully adding a cached movie to a week."""
        mock_week = create_mock_week(id=1)
        mock_movie = create_mock_movie(id=1, tmdb_id=550)

        # Mock week lookup
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = mock_week

        # Mock position check - no existing movie at position
        position_result = MagicMock()
        position_result.scalar_one_or_none.return_value = None

        # Mock movie lookup - movie exists in cache
        movie_result = MagicMock()
        movie_result.scalar_one_or_none.return_value = mock_movie

        mock_db_session.execute = AsyncMock(
            side_effect=[week_result, position_result, movie_result]
        )

        async def override_get_db():
            yield mock_db_session

        def override_get_tmdb_client():
            return mock_tmdb_client

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_tmdb_client] = override_get_tmdb_client

        try:
            response = await client.post(
                "/api/weeks/1/movies",
                json={"tmdb_id": 550, "position": 1},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["week_id"] == 1
            assert data["position"] == 1
            assert data["movie"]["tmdb_id"] == 550
            assert data["movie"]["title"] == "Fight Club"
        finally:
            app.dependency_overrides.clear()

    async def test_add_movie_success_from_tmdb(
        self, client: AsyncClient, mock_db_session: AsyncMock, mock_tmdb_client: AsyncMock
    ) -> None:
        """Test successfully adding a movie fetched from TMDB."""
        mock_week = create_mock_week(id=1)

        # Mock week lookup
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = mock_week

        # Mock position check - no existing movie at position
        position_result = MagicMock()
        position_result.scalar_one_or_none.return_value = None

        # Mock movie lookup - movie not in cache
        movie_result = MagicMock()
        movie_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[week_result, position_result, movie_result]
        )

        # Track added movie
        added_movie = None

        def capture_add(obj):
            nonlocal added_movie
            if isinstance(obj, MagicMock):
                # This is a WeekMovie
                pass
            else:
                added_movie = obj

        mock_db_session.add = MagicMock(side_effect=capture_add)

        async def mock_flush():
            if added_movie:
                added_movie.id = 1
                added_movie.cached_at = datetime(2025, 1, 1, 12, 0, 0)

        mock_db_session.flush = AsyncMock(side_effect=mock_flush)

        async def override_get_db():
            yield mock_db_session

        def override_get_tmdb_client():
            return mock_tmdb_client

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_tmdb_client] = override_get_tmdb_client

        try:
            response = await client.post(
                "/api/weeks/1/movies",
                json={"tmdb_id": 550, "position": 1},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["week_id"] == 1
            assert data["position"] == 1
            assert data["movie"]["tmdb_id"] == 550
        finally:
            app.dependency_overrides.clear()

    async def test_add_movie_week_not_found(
        self, client: AsyncClient, mock_db_session: AsyncMock, mock_tmdb_client: AsyncMock
    ) -> None:
        """Test adding a movie to a non-existent week."""
        # Mock week lookup - week not found
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(return_value=week_result)

        async def override_get_db():
            yield mock_db_session

        def override_get_tmdb_client():
            return mock_tmdb_client

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_tmdb_client] = override_get_tmdb_client

        try:
            response = await client.post(
                "/api/weeks/999/movies",
                json={"tmdb_id": 550, "position": 1},
            )

            assert response.status_code == 404
            assert response.json()["detail"] == "Week not found"
        finally:
            app.dependency_overrides.clear()

    async def test_add_movie_position_occupied(
        self, client: AsyncClient, mock_db_session: AsyncMock, mock_tmdb_client: AsyncMock
    ) -> None:
        """Test adding a movie to an already occupied position."""
        mock_week = create_mock_week(id=1)
        existing_week_movie = create_mock_week_movie(position=1)

        # Mock week lookup
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = mock_week

        # Mock position check - position is occupied
        position_result = MagicMock()
        position_result.scalar_one_or_none.return_value = existing_week_movie

        mock_db_session.execute = AsyncMock(side_effect=[week_result, position_result])

        async def override_get_db():
            yield mock_db_session

        def override_get_tmdb_client():
            return mock_tmdb_client

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_tmdb_client] = override_get_tmdb_client

        try:
            response = await client.post(
                "/api/weeks/1/movies",
                json={"tmdb_id": 550, "position": 1},
            )

            assert response.status_code == 409
            assert "already occupied" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    async def test_add_movie_invalid_position(
        self, client: AsyncClient, mock_db_session: AsyncMock, mock_tmdb_client: AsyncMock
    ) -> None:
        """Test adding a movie with invalid position."""

        async def override_get_db():
            yield mock_db_session

        def override_get_tmdb_client():
            return mock_tmdb_client

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_tmdb_client] = override_get_tmdb_client

        try:
            response = await client.post(
                "/api/weeks/1/movies",
                json={"tmdb_id": 550, "position": 3},
            )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


class TestRemoveMovieFromWeek:
    """Tests for remove movie from week endpoint."""

    async def test_remove_movie_success(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test successfully removing a movie from a week."""
        mock_week = create_mock_week(id=1)
        mock_week_movie = create_mock_week_movie(week_id=1, position=1)

        # Mock week lookup
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = mock_week

        # Mock week_movie lookup
        week_movie_result = MagicMock()
        week_movie_result.scalar_one_or_none.return_value = mock_week_movie

        mock_db_session.execute = AsyncMock(side_effect=[week_result, week_movie_result])

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.delete("/api/weeks/1/movies/1")

            assert response.status_code == 204
            mock_db_session.delete.assert_called_once_with(mock_week_movie)
        finally:
            app.dependency_overrides.clear()

    async def test_remove_movie_week_not_found(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test removing a movie from a non-existent week."""
        # Mock week lookup - week not found
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(return_value=week_result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.delete("/api/weeks/999/movies/1")

            assert response.status_code == 404
            assert response.json()["detail"] == "Week not found"
        finally:
            app.dependency_overrides.clear()

    async def test_remove_movie_not_found(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test removing a movie that doesn't exist at position."""
        mock_week = create_mock_week(id=1)

        # Mock week lookup
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = mock_week

        # Mock week_movie lookup - not found
        week_movie_result = MagicMock()
        week_movie_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[week_result, week_movie_result])

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.delete("/api/weeks/1/movies/1")

            assert response.status_code == 404
            assert "No movie found at position" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    async def test_remove_movie_invalid_position(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test removing a movie with invalid position."""

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.delete("/api/weeks/1/movies/3")

            assert response.status_code == 400
            assert "Position must be 1 or 2" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


def create_mock_album(
    id: int = 1,
    musicbrainz_id: str = "a3e6b6e8-9b3a-4a6e-8e5f-1d2c3b4a5e6f",
    title: str = "OK Computer",
    artist: str = "Radiohead",
    release_date=None,
    cover_art_url: str
    | None = "https://coverartarchive.org/release/a3e6b6e8-9b3a-4a6e-8e5f-1d2c3b4a5e6f/front",
) -> MagicMock:
    """Create a mock Album object."""
    mock_album = MagicMock(spec=Album)
    mock_album.id = id
    mock_album.musicbrainz_id = musicbrainz_id
    mock_album.title = title
    mock_album.artist = artist
    mock_album.release_date = release_date
    mock_album.cover_art_url = cover_art_url
    mock_album.cached_at = datetime(2025, 1, 1, 12, 0, 0)
    return mock_album


def create_mock_week_album(
    week_id: int = 1,
    album_id: int = 1,
    position: int = 1,
) -> MagicMock:
    """Create a mock WeekAlbum object."""
    mock_week_album = MagicMock(spec=WeekAlbum)
    mock_week_album.id = 1
    mock_week_album.week_id = week_id
    mock_week_album.album_id = album_id
    mock_week_album.position = position
    mock_week_album.added_at = datetime(2025, 1, 1, 12, 0, 0)
    return mock_week_album


@pytest.fixture
def mock_musicbrainz_client():
    """Create a mock MusicBrainz client."""
    mock_client = AsyncMock()
    mock_client.close = AsyncMock()

    # Create a mock release response
    mock_release_response = MagicMock()
    mock_release_response.id = "a3e6b6e8-9b3a-4a6e-8e5f-1d2c3b4a5e6f"
    mock_release_response.title = "OK Computer"
    mock_release_response.artist_credit = "Radiohead"
    mock_release_response.date = "1997-05-21"

    mock_client.get_release = AsyncMock(return_value=mock_release_response)
    mock_client.get_cover_art_front_url = MagicMock(
        return_value="https://coverartarchive.org/release/a3e6b6e8-9b3a-4a6e-8e5f-1d2c3b4a5e6f/front"
    )
    return mock_client


class TestAddAlbumToWeek:
    """Tests for add album to week endpoint."""

    async def test_add_album_success_from_cache(
        self, client: AsyncClient, mock_db_session: AsyncMock, mock_musicbrainz_client: AsyncMock
    ) -> None:
        """Test successfully adding a cached album to a week."""
        mock_week = create_mock_week(id=1)
        mock_album = create_mock_album(id=1)

        # Mock week lookup
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = mock_week

        # Mock position check - no existing album at position
        position_result = MagicMock()
        position_result.scalar_one_or_none.return_value = None

        # Mock album lookup - album exists in cache
        album_result = MagicMock()
        album_result.scalar_one_or_none.return_value = mock_album

        mock_db_session.execute = AsyncMock(
            side_effect=[week_result, position_result, album_result]
        )

        async def override_get_db():
            yield mock_db_session

        def override_get_musicbrainz_client():
            return mock_musicbrainz_client

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_musicbrainz_client] = override_get_musicbrainz_client

        try:
            response = await client.post(
                "/api/weeks/1/albums",
                json={"musicbrainz_id": "a3e6b6e8-9b3a-4a6e-8e5f-1d2c3b4a5e6f", "position": 1},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["week_id"] == 1
            assert data["position"] == 1
            assert data["album"]["musicbrainz_id"] == "a3e6b6e8-9b3a-4a6e-8e5f-1d2c3b4a5e6f"
            assert data["album"]["title"] == "OK Computer"
        finally:
            app.dependency_overrides.clear()

    async def test_add_album_success_from_musicbrainz(
        self, client: AsyncClient, mock_db_session: AsyncMock, mock_musicbrainz_client: AsyncMock
    ) -> None:
        """Test successfully adding an album fetched from MusicBrainz."""
        mock_week = create_mock_week(id=1)

        # Mock week lookup
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = mock_week

        # Mock position check - no existing album at position
        position_result = MagicMock()
        position_result.scalar_one_or_none.return_value = None

        # Mock album lookup - album not in cache
        album_result = MagicMock()
        album_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[week_result, position_result, album_result]
        )

        # Track added album
        added_album = None

        def capture_add(obj):
            nonlocal added_album
            if isinstance(obj, MagicMock):
                # This is a WeekAlbum
                pass
            else:
                added_album = obj

        mock_db_session.add = MagicMock(side_effect=capture_add)

        async def mock_flush():
            if added_album:
                added_album.id = 1
                added_album.cached_at = datetime(2025, 1, 1, 12, 0, 0)

        mock_db_session.flush = AsyncMock(side_effect=mock_flush)

        async def override_get_db():
            yield mock_db_session

        def override_get_musicbrainz_client():
            return mock_musicbrainz_client

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_musicbrainz_client] = override_get_musicbrainz_client

        try:
            response = await client.post(
                "/api/weeks/1/albums",
                json={"musicbrainz_id": "a3e6b6e8-9b3a-4a6e-8e5f-1d2c3b4a5e6f", "position": 1},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["week_id"] == 1
            assert data["position"] == 1
            assert data["album"]["musicbrainz_id"] == "a3e6b6e8-9b3a-4a6e-8e5f-1d2c3b4a5e6f"
        finally:
            app.dependency_overrides.clear()

    async def test_add_album_week_not_found(
        self, client: AsyncClient, mock_db_session: AsyncMock, mock_musicbrainz_client: AsyncMock
    ) -> None:
        """Test adding an album to a non-existent week."""
        # Mock week lookup - week not found
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(return_value=week_result)

        async def override_get_db():
            yield mock_db_session

        def override_get_musicbrainz_client():
            return mock_musicbrainz_client

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_musicbrainz_client] = override_get_musicbrainz_client

        try:
            response = await client.post(
                "/api/weeks/999/albums",
                json={"musicbrainz_id": "a3e6b6e8-9b3a-4a6e-8e5f-1d2c3b4a5e6f", "position": 1},
            )

            assert response.status_code == 404
            assert response.json()["detail"] == "Week not found"
        finally:
            app.dependency_overrides.clear()

    async def test_add_album_position_occupied(
        self, client: AsyncClient, mock_db_session: AsyncMock, mock_musicbrainz_client: AsyncMock
    ) -> None:
        """Test adding an album to an already occupied position."""
        mock_week = create_mock_week(id=1)
        existing_week_album = create_mock_week_album(position=1)

        # Mock week lookup
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = mock_week

        # Mock position check - position is occupied
        position_result = MagicMock()
        position_result.scalar_one_or_none.return_value = existing_week_album

        mock_db_session.execute = AsyncMock(side_effect=[week_result, position_result])

        async def override_get_db():
            yield mock_db_session

        def override_get_musicbrainz_client():
            return mock_musicbrainz_client

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_musicbrainz_client] = override_get_musicbrainz_client

        try:
            response = await client.post(
                "/api/weeks/1/albums",
                json={"musicbrainz_id": "a3e6b6e8-9b3a-4a6e-8e5f-1d2c3b4a5e6f", "position": 1},
            )

            assert response.status_code == 409
            assert "already occupied" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    async def test_add_album_invalid_position(
        self, client: AsyncClient, mock_db_session: AsyncMock, mock_musicbrainz_client: AsyncMock
    ) -> None:
        """Test adding an album with invalid position."""

        async def override_get_db():
            yield mock_db_session

        def override_get_musicbrainz_client():
            return mock_musicbrainz_client

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_musicbrainz_client] = override_get_musicbrainz_client

        try:
            response = await client.post(
                "/api/weeks/1/albums",
                json={"musicbrainz_id": "a3e6b6e8-9b3a-4a6e-8e5f-1d2c3b4a5e6f", "position": 3},
            )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


class TestRemoveAlbumFromWeek:
    """Tests for remove album from week endpoint."""

    async def test_remove_album_success(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test successfully removing an album from a week."""
        mock_week = create_mock_week(id=1)
        mock_week_album = create_mock_week_album(week_id=1, position=1)

        # Mock week lookup
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = mock_week

        # Mock week_album lookup
        week_album_result = MagicMock()
        week_album_result.scalar_one_or_none.return_value = mock_week_album

        mock_db_session.execute = AsyncMock(side_effect=[week_result, week_album_result])

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.delete("/api/weeks/1/albums/1")

            assert response.status_code == 204
            mock_db_session.delete.assert_called_once_with(mock_week_album)
        finally:
            app.dependency_overrides.clear()

    async def test_remove_album_week_not_found(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test removing an album from a non-existent week."""
        # Mock week lookup - week not found
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(return_value=week_result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.delete("/api/weeks/999/albums/1")

            assert response.status_code == 404
            assert response.json()["detail"] == "Week not found"
        finally:
            app.dependency_overrides.clear()

    async def test_remove_album_not_found(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test removing an album that doesn't exist at position."""
        mock_week = create_mock_week(id=1)

        # Mock week lookup
        week_result = MagicMock()
        week_result.scalar_one_or_none.return_value = mock_week

        # Mock week_album lookup - not found
        week_album_result = MagicMock()
        week_album_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[week_result, week_album_result])

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.delete("/api/weeks/1/albums/1")

            assert response.status_code == 404
            assert "No album found at position" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    async def test_remove_album_invalid_position(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test removing an album with invalid position."""

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.delete("/api/weeks/1/albums/3")

            assert response.status_code == 400
            assert "Position must be 1 or 2" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
