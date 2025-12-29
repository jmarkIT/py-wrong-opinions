"""Pytest fixtures and configuration."""

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

# Set test environment variables before importing the app
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-at-least-32-characters-long")
os.environ.setdefault("DEBUG", "true")

from wrong_opinions.main import app


@pytest.fixture
def anyio_backend() -> str:
    """Use asyncio as the async backend for tests."""
    return "asyncio"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
