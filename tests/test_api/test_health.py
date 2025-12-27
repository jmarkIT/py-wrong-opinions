"""Tests for health check endpoint."""

from httpx import AsyncClient

from wrong_opinions import __version__


async def test_health_check(client: AsyncClient) -> None:
    """Test that health check endpoint returns expected response."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == __version__
