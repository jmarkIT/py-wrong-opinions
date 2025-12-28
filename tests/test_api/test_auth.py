"""Tests for authentication API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from wrong_opinions.database import get_db
from wrong_opinions.main import app
from wrong_opinions.models.user import User


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session


def create_mock_user(
    id: int = 1,
    username: str = "testuser",
    email: str = "test@example.com",
    is_active: bool = True,
) -> MagicMock:
    """Create a mock User object."""
    mock_user = MagicMock(spec=User)
    mock_user.id = id
    mock_user.username = username
    mock_user.email = email
    mock_user.hashed_password = "hashedpassword123"
    mock_user.is_active = is_active
    mock_user.created_at = datetime(2025, 1, 1, 12, 0, 0)
    return mock_user


class TestRegister:
    """Tests for user registration endpoint."""

    async def test_register_success(self, client: AsyncClient, mock_db_session: AsyncMock) -> None:
        """Test successful user registration."""
        # Mock username check - no existing user
        username_result = MagicMock()
        username_result.scalar_one_or_none.return_value = None

        # Mock email check - no existing user
        email_result = MagicMock()
        email_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[username_result, email_result])

        # Mock flush and refresh to set the created user's properties
        async def mock_refresh(user):
            user.id = 1
            user.created_at = datetime(2025, 1, 1, 12, 0, 0)

        mock_db_session.refresh = mock_refresh

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["username"] == "newuser"
            assert data["email"] == "newuser@example.com"
            assert data["is_active"] is True
            assert "id" in data
            assert "created_at" in data
            # Password should NOT be in response
            assert "password" not in data
            assert "hashed_password" not in data
        finally:
            app.dependency_overrides.clear()

    async def test_register_username_already_exists(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test registration with existing username."""
        # Mock username check - user exists
        username_result = MagicMock()
        username_result.scalar_one_or_none.return_value = create_mock_user()

        mock_db_session.execute = AsyncMock(return_value=username_result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "testuser",
                    "email": "new@example.com",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 409
            assert "Username already registered" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    async def test_register_email_already_exists(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test registration with existing email."""
        # Mock username check - no existing user
        username_result = MagicMock()
        username_result.scalar_one_or_none.return_value = None

        # Mock email check - user exists
        email_result = MagicMock()
        email_result.scalar_one_or_none.return_value = create_mock_user()

        mock_db_session.execute = AsyncMock(side_effect=[username_result, email_result])

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "newuser",
                    "email": "test@example.com",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 409
            assert "Email already registered" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    async def test_register_invalid_email(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test registration with invalid email format."""

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "newuser",
                    "email": "not-an-email",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_register_password_too_short(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test registration with password that is too short."""

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "password": "short",
                },
            )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_register_username_too_short(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test registration with username that is too short."""

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "ab",
                    "email": "newuser@example.com",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_register_username_invalid_characters(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test registration with username containing invalid characters."""

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "user@name",
                    "email": "newuser@example.com",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_register_username_normalized_to_lowercase(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test that username is normalized to lowercase."""
        # Mock username check - no existing user
        username_result = MagicMock()
        username_result.scalar_one_or_none.return_value = None

        # Mock email check - no existing user
        email_result = MagicMock()
        email_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[username_result, email_result])

        # Mock flush and refresh to set the created user's properties
        async def mock_refresh(user):
            user.id = 1
            user.created_at = datetime(2025, 1, 1, 12, 0, 0)

        mock_db_session.refresh = mock_refresh

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "NewUser",
                    "email": "newuser@example.com",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["username"] == "newuser"  # Should be lowercase
        finally:
            app.dependency_overrides.clear()

    async def test_register_username_with_allowed_special_chars(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test registration with username containing allowed special characters."""
        # Mock username check - no existing user
        username_result = MagicMock()
        username_result.scalar_one_or_none.return_value = None

        # Mock email check - no existing user
        email_result = MagicMock()
        email_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[username_result, email_result])

        # Mock flush and refresh to set the created user's properties
        async def mock_refresh(user):
            user.id = 1
            user.created_at = datetime(2025, 1, 1, 12, 0, 0)

        mock_db_session.refresh = mock_refresh

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "user_name-123",
                    "email": "newuser@example.com",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["username"] == "user_name-123"
        finally:
            app.dependency_overrides.clear()
