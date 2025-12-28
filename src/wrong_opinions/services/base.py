"""Base HTTP client for external API integrations."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any

import httpx


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class NotFoundError(APIError):
    """Raised when a resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class BaseAPIClient(ABC):
    """Abstract base class for external API clients.

    Provides common functionality for HTTP requests, error handling,
    and rate limiting support.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        rate_limit_delay: float = 0.0,
    ) -> None:
        """Initialize the base API client.

        Args:
            base_url: The base URL for the API.
            timeout: Request timeout in seconds.
            rate_limit_delay: Minimum delay between requests in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time: float = 0.0
        self._client: httpx.AsyncClient | None = None

    @property
    @abstractmethod
    def default_headers(self) -> dict[str, str]:
        """Return default headers for API requests."""
        ...

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.default_headers,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits."""
        if self.rate_limit_delay > 0:
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - self._last_request_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            params: Query parameters.
            headers: Additional headers to include.

        Returns:
            JSON response as a dictionary.

        Raises:
            NotFoundError: If the resource is not found (404).
            RateLimitError: If rate limit is exceeded (429).
            APIError: For other HTTP errors.
        """
        await self._wait_for_rate_limit()

        client = await self._get_client()
        url = f"{endpoint.lstrip('/')}"

        request_headers = dict(self.default_headers)
        if headers:
            request_headers.update(headers)

        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                headers=request_headers,
            )
        except httpx.TimeoutException as e:
            raise APIError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise APIError(f"Request failed: {e}") from e

        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle the HTTP response.

        Args:
            response: The HTTP response object.

        Returns:
            JSON response as a dictionary.

        Raises:
            NotFoundError: If the resource is not found (404).
            RateLimitError: If rate limit is exceeded (429).
            APIError: For other HTTP errors.
        """
        if response.status_code == 404:
            raise NotFoundError()

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(retry_after=int(retry_after) if retry_after else None)

        if response.status_code >= 400:
            raise APIError(
                f"API error: {response.text}",
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as e:
            raise APIError(f"Invalid JSON response: {e}") from e

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make a GET request to the API."""
        return await self._request("GET", endpoint, params=params, headers=headers)

    async def __aenter__(self) -> "BaseAPIClient":
        """Async context manager entry."""
        await self._get_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
