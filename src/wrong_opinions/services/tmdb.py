"""TMDB (The Movie Database) API client service."""

from typing import Any

from wrong_opinions.config import get_settings
from wrong_opinions.schemas.external import (
    TMDBCreditsResponse,
    TMDBMovieDetails,
    TMDBMovieResult,
    TMDBSearchResponse,
)
from wrong_opinions.services.base import BaseAPIClient, NotFoundError


class TMDBClient(BaseAPIClient):
    """Client for The Movie Database (TMDB) API.

    Provides methods to search for movies and fetch movie details.
    Uses Bearer token authentication.
    """

    # TMDB image base URLs
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p"
    POSTER_SIZES = ("w92", "w154", "w185", "w342", "w500", "w780", "original")
    BACKDROP_SIZES = ("w300", "w780", "w1280", "original")
    PROFILE_SIZES = ("w45", "w185", "h632", "original")

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the TMDB client.

        Args:
            api_key: TMDB API key. If not provided, uses settings.
            base_url: TMDB base URL. If not provided, uses settings.
            timeout: Request timeout in seconds.
        """
        settings = get_settings()
        self._api_key = api_key or settings.tmdb_api_key
        base = base_url or settings.tmdb_base_url

        if not self._api_key:
            raise ValueError("TMDB API key is required")

        super().__init__(base_url=base, timeout=timeout)

    @property
    def default_headers(self) -> dict[str, str]:
        """Return default headers including Bearer token authentication."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

    async def search_movies(
        self,
        query: str,
        page: int = 1,
        include_adult: bool = False,
        year: int | None = None,
        language: str = "en-US",
    ) -> TMDBSearchResponse:
        """Search for movies by title.

        Args:
            query: Search query string.
            page: Page number (1-based).
            include_adult: Whether to include adult content.
            year: Filter by release year.
            language: Response language code.

        Returns:
            Search response containing movie results.
        """
        params: dict[str, Any] = {
            "query": query,
            "page": page,
            "include_adult": str(include_adult).lower(),
            "language": language,
        }
        if year is not None:
            params["year"] = year

        data = await self.get("/search/movie", params=params)
        return TMDBSearchResponse.model_validate(data)

    async def get_movie(
        self,
        movie_id: int,
        language: str = "en-US",
    ) -> TMDBMovieDetails:
        """Get detailed information about a specific movie.

        Args:
            movie_id: TMDB movie ID.
            language: Response language code.

        Returns:
            Detailed movie information.

        Raises:
            NotFoundError: If the movie is not found.
        """
        params = {"language": language}
        data = await self.get(f"/movie/{movie_id}", params=params)
        return TMDBMovieDetails.model_validate(data)

    async def get_movie_or_none(
        self,
        movie_id: int,
        language: str = "en-US",
    ) -> TMDBMovieDetails | None:
        """Get movie details, returning None if not found.

        Args:
            movie_id: TMDB movie ID.
            language: Response language code.

        Returns:
            Movie details or None if not found.
        """
        try:
            return await self.get_movie(movie_id, language=language)
        except NotFoundError:
            return None

    async def get_movie_credits(
        self,
        movie_id: int,
        language: str = "en-US",
    ) -> TMDBCreditsResponse:
        """Get cast and crew for a specific movie.

        Args:
            movie_id: TMDB movie ID.
            language: Response language code.

        Returns:
            Credits response containing cast and crew.

        Raises:
            NotFoundError: If the movie is not found.
        """
        params = {"language": language}
        data = await self.get(f"/movie/{movie_id}/credits", params=params)
        return TMDBCreditsResponse.model_validate(data)

    async def get_movie_credits_or_none(
        self,
        movie_id: int,
        language: str = "en-US",
    ) -> TMDBCreditsResponse | None:
        """Get movie credits, returning None if not found.

        Args:
            movie_id: TMDB movie ID.
            language: Response language code.

        Returns:
            Credits response or None if not found.
        """
        try:
            return await self.get_movie_credits(movie_id, language=language)
        except NotFoundError:
            return None

    def get_poster_url(
        self,
        poster_path: str | None,
        size: str = "w342",
    ) -> str | None:
        """Generate full poster image URL.

        Args:
            poster_path: Poster path from TMDB (e.g., "/abc123.jpg").
            size: Image size. Valid sizes: w92, w154, w185, w342, w500, w780, original.

        Returns:
            Full poster URL or None if no poster path provided.
        """
        if not poster_path:
            return None

        if size not in self.POSTER_SIZES:
            size = "w342"  # Default fallback

        return f"{self.IMAGE_BASE_URL}/{size}{poster_path}"

    def get_backdrop_url(
        self,
        backdrop_path: str | None,
        size: str = "w780",
    ) -> str | None:
        """Generate full backdrop image URL.

        Args:
            backdrop_path: Backdrop path from TMDB (e.g., "/abc123.jpg").
            size: Image size. Valid sizes: w300, w780, w1280, original.

        Returns:
            Full backdrop URL or None if no backdrop path provided.
        """
        if not backdrop_path:
            return None

        if size not in self.BACKDROP_SIZES:
            size = "w780"  # Default fallback

        return f"{self.IMAGE_BASE_URL}/{size}{backdrop_path}"

    def get_profile_url(
        self,
        profile_path: str | None,
        size: str = "w185",
    ) -> str | None:
        """Generate full profile image URL.

        Args:
            profile_path: Profile path from TMDB (e.g., "/abc123.jpg").
            size: Image size. Valid sizes: w45, w185, h632, original.

        Returns:
            Full profile URL or None if no profile path provided.
        """
        if not profile_path:
            return None

        if size not in self.PROFILE_SIZES:
            size = "w185"  # Default fallback

        return f"{self.IMAGE_BASE_URL}/{size}{profile_path}"

    def to_movie_result_with_urls(
        self,
        result: TMDBMovieResult,
        poster_size: str = "w342",
    ) -> dict[str, Any]:
        """Convert a movie result to a dict with full image URLs.

        Args:
            result: TMDB movie result.
            poster_size: Size for poster image.

        Returns:
            Dictionary with movie data and full image URLs.
        """
        data = result.model_dump()
        data["poster_url"] = self.get_poster_url(result.poster_path, poster_size)
        return data

    def to_movie_details_with_urls(
        self,
        details: TMDBMovieDetails,
        poster_size: str = "w342",
        backdrop_size: str = "w780",
    ) -> dict[str, Any]:
        """Convert movie details to a dict with full image URLs.

        Args:
            details: TMDB movie details.
            poster_size: Size for poster image.
            backdrop_size: Size for backdrop image.

        Returns:
            Dictionary with movie data and full image URLs.
        """
        data = details.model_dump()
        data["poster_url"] = self.get_poster_url(details.poster_path, poster_size)
        data["backdrop_url"] = self.get_backdrop_url(details.backdrop_path, backdrop_size)
        return data


async def get_tmdb_client() -> TMDBClient:
    """Factory function to create a TMDB client.

    Can be used as a FastAPI dependency.
    """
    return TMDBClient()
