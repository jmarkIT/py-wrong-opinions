"""Pytest fixtures and configuration."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from wrong_opinions.main import app


@pytest.fixture
def anyio_backend() -> str:
    """Use asyncio as the async backend for tests."""
    return "asyncio"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
