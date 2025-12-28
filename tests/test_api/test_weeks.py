"""Tests for week API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from wrong_opinions.database import get_db
from wrong_opinions.main import app
from wrong_opinions.models.user import User
from wrong_opinions.models.week import Week


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
