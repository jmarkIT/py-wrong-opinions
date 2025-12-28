"""Tests for authentication API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from wrong_opinions.database import get_db
from wrong_opinions.main import app
from wrong_opinions.models.user import User
from wrong_opinions.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
)


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
    password: str = "securepassword123",
    is_active: bool = True,
) -> MagicMock:
    """Create a mock User object."""
    mock_user = MagicMock(spec=User)
    mock_user.id = id
    mock_user.username = username
    mock_user.email = email
    mock_user.hashed_password = hash_password(password)
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


class TestLogin:
    """Tests for user login endpoint."""

    async def test_login_success_with_username(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test successful login with username."""
        mock_user = create_mock_user()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute = AsyncMock(return_value=user_result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/login",
                json={
                    "username": "testuser",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

            # Verify token is valid and contains correct user id
            payload = decode_access_token(data["access_token"])
            assert payload is not None
            assert payload["sub"] == str(mock_user.id)
        finally:
            app.dependency_overrides.clear()

    async def test_login_success_with_email(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test successful login with email."""
        mock_user = create_mock_user()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute = AsyncMock(return_value=user_result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/login",
                json={
                    "username": "test@example.com",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
        finally:
            app.dependency_overrides.clear()

    async def test_login_invalid_password(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test login with incorrect password."""
        mock_user = create_mock_user()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute = AsyncMock(return_value=user_result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/login",
                json={
                    "username": "testuser",
                    "password": "wrongpassword",
                },
            )

            assert response.status_code == 401
            assert "Invalid username or password" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    async def test_login_user_not_found(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test login with non-existent user."""
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=user_result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/login",
                json={
                    "username": "nonexistent",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 401
            assert "Invalid username or password" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    async def test_login_inactive_user(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ) -> None:
        """Test login with inactive user account."""
        mock_user = create_mock_user(is_active=False)

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute = AsyncMock(return_value=user_result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.post(
                "/api/auth/login",
                json={
                    "username": "testuser",
                    "password": "securepassword123",
                },
            )

            assert response.status_code == 403
            assert "User account is inactive" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


class TestJWT:
    """Tests for JWT token generation and validation."""

    def test_create_access_token(self) -> None:
        """Test JWT token creation."""
        token = create_access_token(data={"sub": "123"})

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token_valid(self) -> None:
        """Test decoding a valid JWT token."""
        user_id = "42"
        token = create_access_token(data={"sub": user_id})
        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == user_id
        assert "exp" in payload

    def test_decode_access_token_invalid(self) -> None:
        """Test decoding an invalid JWT token."""
        payload = decode_access_token("invalid.token.here")

        assert payload is None

    def test_decode_access_token_tampered(self) -> None:
        """Test decoding a tampered JWT token."""
        token = create_access_token(data={"sub": "1"})
        # Tamper with the token by modifying it
        tampered_token = token[:-5] + "xxxxx"
        payload = decode_access_token(tampered_token)

        assert payload is None
