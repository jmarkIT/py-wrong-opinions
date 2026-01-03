"""MusicBrainz API client service."""

from typing import Any

import httpx

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

    # Cover Art Archive base URLs for album art
    COVER_ART_BASE_URL = "https://coverartarchive.org/release"
    COVER_ART_RELEASE_GROUP_BASE_URL = "https://coverartarchive.org/release-group"

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
        include_artist_credits: bool = False,
    ) -> MusicBrainzReleaseDetails:
        """Get detailed information about a specific release.

        Always includes release-group information for cover art fallback.

        Args:
            release_id: MusicBrainz release ID (UUID).
            include_artist_credits: If True, include full artist credit information.

        Returns:
            Detailed release information.

        Raises:
            NotFoundError: If the release is not found.
        """
        params: dict[str, Any] = {"fmt": "json"}  # Required for JSON response

        # Build inc parameter - always include release-groups for cover art fallback
        inc_parts = ["release-groups"]
        if include_artist_credits:
            inc_parts.append("artist-credits")
        params["inc"] = "+".join(inc_parts)

        data = await self.get(f"/release/{release_id}", params=params)
        return MusicBrainzReleaseDetails.model_validate(data)

    async def get_release_or_none(
        self,
        release_id: str,
        include_artist_credits: bool = False,
    ) -> MusicBrainzReleaseDetails | None:
        """Get release details, returning None if not found.

        Args:
            release_id: MusicBrainz release ID (UUID).
            include_artist_credits: If True, include full artist credit information.

        Returns:
            Release details or None if not found.
        """
        try:
            return await self.get_release(release_id, include_artist_credits)
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

    def get_cover_art_release_group_url(
        self,
        release_group_id: str,
    ) -> str:
        """Generate Cover Art Archive URL for a release-group's front cover.

        Args:
            release_group_id: MusicBrainz release-group ID (UUID).

        Returns:
            URL to fetch front cover art image from release-group.

        Note:
            This returns the URL but doesn't verify if cover art exists.
            The actual request to this URL may return 404 if no cover art is available.
        """
        return f"{self.COVER_ART_RELEASE_GROUP_BASE_URL}/{release_group_id}/front"

    async def _check_cover_art_exists(self, url: str) -> bool:
        """Check if cover art exists at the given URL using HEAD request.

        Cover Art Archive returns 307 redirect if cover art exists, 404 if not.

        Note:
            This does NOT use the MusicBrainz rate limiter since Cover Art Archive
            is a separate service with different rate limits.

        Args:
            url: Cover Art Archive URL to check.

        Returns:
            True if cover art exists, False otherwise.
        """
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            try:
                response = await client.head(url)
                # Cover Art Archive returns 307 redirect if cover exists
                return response.status_code in (200, 307)
            except httpx.RequestError:
                return False

    async def get_validated_cover_art_url(
        self,
        release_id: str,
        release_group_id: str | None = None,
    ) -> str | None:
        """Get a validated cover art URL, with release-group fallback.

        Checks if cover art actually exists before returning the URL.
        Falls back to release-group cover art if release has none.

        Args:
            release_id: MusicBrainz release ID (UUID).
            release_group_id: Optional release-group ID for fallback.

        Returns:
            Validated cover art URL, or None if no cover art exists.
        """
        # Try release cover art first
        release_url = self.get_cover_art_front_url(release_id)
        if await self._check_cover_art_exists(release_url):
            return release_url

        # Fall back to release-group cover art
        if release_group_id:
            release_group_url = self.get_cover_art_release_group_url(release_group_id)
            if await self._check_cover_art_exists(release_group_url):
                return release_group_url

        # No cover art found
        return None


async def get_musicbrainz_client() -> MusicBrainzClient:
    """Factory function to create a MusicBrainz client.

    Can be used as a FastAPI dependency.
    """
    return MusicBrainzClient()
