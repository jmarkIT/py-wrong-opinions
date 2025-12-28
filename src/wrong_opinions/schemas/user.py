"""Pydantic schemas for user and authentication API endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Schema for user registration."""

    username: str = Field(
        min_length=3,
        max_length=50,
        description="Unique username (3-50 characters)",
    )
    email: EmailStr = Field(description="Valid email address")
    password: str = Field(
        min_length=8,
        max_length=100,
        description="Password (8-100 characters)",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username contains only allowed characters."""
        if not v.replace("_", "").replace("-", "").isalnum():
            msg = "Username can only contain letters, numbers, underscores, and hyphens"
            raise ValueError(msg)
        return v.lower()


class UserResponse(BaseModel):
    """Response schema for user data (excludes password)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="User ID")
    username: str = Field(description="Username")
    email: str = Field(description="Email address")
    is_active: bool = Field(description="Whether the user account is active")
    created_at: datetime = Field(description="When the user was created")
