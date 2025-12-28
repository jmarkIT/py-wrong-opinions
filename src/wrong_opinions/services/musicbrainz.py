"""MusicBrainz API client service."""

from typing import Any

from wrong_opinions.config import get_settings
from wrong_opinions.schemas.external import (
    MusicBrainzReleaseDetails,
    MusicBrainzSearchResponse,
)
from wrong_opinions.services.base import BaseAPIClient, NotFoundError


class MusicBrainzClient(BaseAPIClient):
    """Client for MusicBrainz API.

    Provides methods to search for albums/releases and fetch release details.
    Important: MusicBrainz has a rate limit of 1 request per second.
    """

    # Cover Art Archive base URL for album art
    COVER_ART_BASE_URL = "https://coverartarchive.org/release"

    def __init__(
        self,
        user_agent: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the MusicBrainz client.

        Args:
            user_agent: User-Agent header. If not provided, uses settings.
            base_url: MusicBrainz base URL. If not provided, uses settings.
            timeout: Request timeout in seconds.
        """
        settings = get_settings()
        self._user_agent = user_agent or settings.musicbrainz_user_agent
        base = base_url or settings.musicbrainz_base_url

        if not self._user_agent:
            raise ValueError("MusicBrainz User-Agent is required")

        # MusicBrainz rate limit: 1 request per second
        super().__init__(base_url=base, timeout=timeout, rate_limit_delay=1.0)

    @property
    def default_headers(self) -> dict[str, str]:
        """Return default headers including User-Agent."""
        return {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
        }

    async def search_releases(
        self,
        query: str,
        limit: int = 25,
        offset: int = 0,
    ) -> MusicBrainzSearchResponse:
        """Search for releases/albums by query.

        Args:
            query: Search query string (can include artist, album, etc.).
            limit: Maximum number of results (default 25, max 100).
            offset: Result offset for pagination.

        Returns:
            Search response containing release results.
        """
        params: dict[str, Any] = {
            "query": query,
            "limit": min(limit, 100),  # MusicBrainz max is 100
            "offset": offset,
            "fmt": "json",  # Required for JSON response
        }

        data = await self.get("/release", params=params)
        return MusicBrainzSearchResponse.model_validate(data)

    async def get_release(
        self,
        release_id: str,
    ) -> MusicBrainzReleaseDetails:
        """Get detailed information about a specific release.

        Args:
            release_id: MusicBrainz release ID (UUID).

        Returns:
            Detailed release information.

        Raises:
            NotFoundError: If the release is not found.
        """
        params = {"fmt": "json"}  # Required for JSON response
        data = await self.get(f"/release/{release_id}", params=params)
        return MusicBrainzReleaseDetails.model_validate(data)

    async def get_release_or_none(
        self,
        release_id: str,
    ) -> MusicBrainzReleaseDetails | None:
        """Get release details, returning None if not found.

        Args:
            release_id: MusicBrainz release ID (UUID).

        Returns:
            Release details or None if not found.
        """
        try:
            return await self.get_release(release_id)
        except NotFoundError:
            return None

    def get_cover_art_url(
        self,
        release_id: str,
    ) -> str:
        """Generate Cover Art Archive URL for a release.

        Args:
            release_id: MusicBrainz release ID (UUID).

        Returns:
            URL to fetch cover art from Cover Art Archive.

        Note:
            This returns the URL but doesn't verify if cover art exists.
            The actual request to this URL may return 404 if no cover art is available.
        """
        return f"{self.COVER_ART_BASE_URL}/{release_id}"

    def get_cover_art_front_url(
        self,
        release_id: str,
    ) -> str:
        """Generate Cover Art Archive URL for front cover art.

        Args:
            release_id: MusicBrainz release ID (UUID).

        Returns:
            URL to fetch front cover art image.

        Note:
            This returns the URL but doesn't verify if cover art exists.
            The actual request to this URL may return 404 if no cover art is available.
        """
        return f"{self.COVER_ART_BASE_URL}/{release_id}/front"


async def get_musicbrainz_client() -> MusicBrainzClient:
    """Factory function to create a MusicBrainz client.

    Can be used as a FastAPI dependency.
    """
    return MusicBrainzClient()
