"""Security utilities for password hashing and JWT handling."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from wrong_opinions.config import get_settings
from wrong_opinions.database import get_db

if TYPE_CHECKING:
    from wrong_opinions.models.user import User

# OAuth2 scheme for Bearer token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password."""
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data to encode in the token. The "sub" (subject) claim
              must be a string (e.g., {"sub": str(user_id)}).
        expires_delta: Optional custom expiration time. Defaults to settings value.

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT token string to decode

    Returns:
        Decoded token payload if valid, None if invalid or expired
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
):
    """Get the current authenticated user from JWT token.

    This is a FastAPI dependency that validates the JWT token from the
    Authorization header and returns the corresponding user.

    Args:
        token: JWT token extracted from Authorization header
        db: Database session

    Returns:
        The authenticated User object

    Raises:
        HTTPException 401: If token is invalid, expired, or user not found
    """
    # Import here to avoid circular import
    from wrong_opinions.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception from None

    # Look up user in database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated["User", Depends(get_current_user)],
):
    """Get the current active user.

    This dependency builds on get_current_user and additionally checks
    that the user account is active.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        The authenticated active User object

    Raises:
        HTTPException 403: If user account is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


# Type alias for use in route dependencies
CurrentUser = Annotated["User", Depends(get_current_active_user)]
