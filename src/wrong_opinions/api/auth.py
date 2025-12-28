"""Authentication API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from wrong_opinions.database import get_db
from wrong_opinions.models.user import User
from wrong_opinions.schemas.user import Token, UserCreate, UserLogin, UserResponse
from wrong_opinions.utils.security import (
    CurrentUser,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user.

    Creates a new user account with the provided username, email, and password.
    The password is securely hashed before storage.

    Raises:
        HTTPException 409: If username or email already exists
    """
    # Check if username already exists
    username_query = select(User).where(User.username == user_data.username)
    username_result = await db.execute(username_query)
    if username_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Username already registered",
        )

    # Check if email already exists
    email_query = select(User).where(User.email == user_data.email)
    email_result = await db.execute(email_query)
    if email_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    # Create new user with hashed password
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        created_at=datetime.now(UTC),
        is_active=True,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
    )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate user and return JWT token.

    Accepts either username or email in the username field.

    Raises:
        HTTPException 401: If credentials are invalid
        HTTPException 403: If user account is inactive
    """
    # Look up user by username or email
    query = select(User).where(
        or_(
            User.username == credentials.username.lower(),
            User.email == credentials.username.lower(),
        )
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # Validate user exists and password is correct
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive",
        )

    # Create and return access token
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get the current authenticated user's information.

    Requires a valid JWT token in the Authorization header.

    Returns:
        Current user's profile information (excluding password)
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
