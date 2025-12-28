"""Tests for TMDB API client."""

from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from wrong_opinions.schemas.external import (
    TMDBMovieDetails,
    TMDBMovieResult,
)
from wrong_opinions.services.base import APIError, NotFoundError, RateLimitError
from wrong_opinions.services.tmdb import TMDBClient

# Sample test data
SAMPLE_SEARCH_RESPONSE = {
    "page": 1,
    "total_pages": 1,
    "total_results": 2,
    "results": [
        {
            "id": 550,
            "title": "Fight Club",
            "original_title": "Fight Club",
            "release_date": "1999-10-15",
            "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            "overview": "A ticking-Loss insomnia insurance worker...",
            "vote_average": 8.4,
            "vote_count": 25000,
            "popularity": 50.5,
        },
        {
            "id": 551,
            "title": "Fight Club 2",
            "original_title": "Fight Club 2",
            "release_date": None,
            "poster_path": None,
            "overview": None,
            "vote_average": 0.0,
            "vote_count": 0,
            "popularity": 1.0,
        },
    ],
}

SAMPLE_MOVIE_DETAILS = {
    "id": 550,
    "title": "Fight Club",
    "original_title": "Fight Club",
    "release_date": "1999-10-15",
    "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
    "backdrop_path": "/87hTDiay2N/background.jpg",
    "overview": "A ticking-Loss insomnia insurance worker...",
    "runtime": 139,
    "vote_average": 8.4,
    "vote_count": 25000,
    "popularity": 50.5,
    "status": "Released",
    "tagline": "Mischief. Mayhem. Soap.",
    "budget": 63000000,
    "revenue": 100853753,
    "imdb_id": "tt0137523",
    "homepage": "https://www.foxmovies.com/movies/fight-club",
}

SAMPLE_CREDITS_RESPONSE = {
    "id": 550,
    "cast": [
        {
            "id": 819,
            "name": "Edward Norton",
            "character": "The Narrator",
            "order": 0,
            "profile_path": "/5XBzD5WuTyVQZeS4II6gs1nn5P6.jpg",
            "known_for_department": "Acting",
        },
        {
            "id": 287,
            "name": "Brad Pitt",
            "character": "Tyler Durden",
            "order": 1,
            "profile_path": "/oTB9vGIBacH5aQNS0pUM74QSWuf.jpg",
            "known_for_department": "Acting",
        },
    ],
    "crew": [
        {
            "id": 7467,
            "name": "David Fincher",
            "department": "Directing",
            "job": "Director",
            "profile_path": "/tpEczFclQZeKAiCeKZZ0adRvtfz.jpg",
            "known_for_department": "Directing",
        },
        {
            "id": 7468,
            "name": "Jim Uhls",
            "department": "Writing",
            "job": "Screenplay",
            "profile_path": None,
            "known_for_department": "Writing",
        },
    ],
}


@pytest.fixture
def mock_settings():
    """Mock settings with test API key."""
    with patch("wrong_opinions.services.tmdb.get_settings") as mock:
        mock.return_value.tmdb_api_key = "test-api-key"
        mock.return_value.tmdb_base_url = "https://api.themoviedb.org/3"
        yield mock


@pytest.fixture
def tmdb_client(mock_settings) -> TMDBClient:  # noqa: ARG001
    """Create a TMDB client for testing."""
    return TMDBClient()


class TestTMDBClientInit:
    """Tests for TMDB client initialization."""

    def test_init_with_api_key(self, mock_settings) -> None:  # noqa: ARG002
        """Test client initialization with explicit API key."""
        client = TMDBClient(api_key="custom-key")
        assert client._api_key == "custom-key"

    def test_init_with_custom_base_url(self, mock_settings) -> None:  # noqa: ARG002
        """Test client initialization with custom base URL."""
        client = TMDBClient(base_url="https://custom.api.com")
        assert client.base_url == "https://custom.api.com"

    def test_init_without_api_key_raises(self) -> None:
        """Test that initialization without API key raises error."""
        with patch("wrong_opinions.services.tmdb.get_settings") as mock:
            mock.return_value.tmdb_api_key = ""
            mock.return_value.tmdb_base_url = "https://api.themoviedb.org/3"
            with pytest.raises(ValueError, match="TMDB API key is required"):
                TMDBClient()

    def test_default_headers(self, tmdb_client: TMDBClient) -> None:
        """Test that default headers include authorization."""
        headers = tmdb_client.default_headers
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-api-key"
        assert headers["Accept"] == "application/json"


class TestSearchMovies:
    """Tests for movie search functionality."""

    async def test_search_movies_success(self, tmdb_client: TMDBClient) -> None:
        """Test successful movie search."""
        mock_response = httpx.Response(200, json=SAMPLE_SEARCH_RESPONSE)

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await tmdb_client.search_movies("Fight Club")

            assert result.page == 1
            assert result.total_results == 2
            assert len(result.results) == 2
            assert result.results[0].title == "Fight Club"
            assert result.results[0].id == 550

    async def test_search_movies_with_year_filter(self, tmdb_client: TMDBClient) -> None:
        """Test movie search with year filter."""
        mock_response = httpx.Response(200, json=SAMPLE_SEARCH_RESPONSE)

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            await tmdb_client.search_movies("Fight Club", year=1999)

            # Verify year was passed in params
            call_args = mock_client.request.call_args
            assert call_args.kwargs["params"]["year"] == 1999

    async def test_search_movies_empty_results(self, tmdb_client: TMDBClient) -> None:
        """Test movie search with no results."""
        empty_response = {
            "page": 1,
            "total_pages": 0,
            "total_results": 0,
            "results": [],
        }
        mock_response = httpx.Response(200, json=empty_response)

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await tmdb_client.search_movies("NonexistentMovie12345")

            assert result.total_results == 0
            assert len(result.results) == 0


class TestGetMovie:
    """Tests for getting movie details."""

    async def test_get_movie_success(self, tmdb_client: TMDBClient) -> None:
        """Test successful movie details fetch."""
        mock_response = httpx.Response(200, json=SAMPLE_MOVIE_DETAILS)

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await tmdb_client.get_movie(550)

            assert result.id == 550
            assert result.title == "Fight Club"
            assert result.runtime == 139
            assert result.release_date == date(1999, 10, 15)

    async def test_get_movie_not_found(self, tmdb_client: TMDBClient) -> None:
        """Test movie details fetch for non-existent movie."""
        mock_response = httpx.Response(404, json={"status_code": 34})

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            with pytest.raises(NotFoundError):
                await tmdb_client.get_movie(99999999)

    async def test_get_movie_or_none_returns_none(self, tmdb_client: TMDBClient) -> None:
        """Test get_movie_or_none returns None for non-existent movie."""
        mock_response = httpx.Response(404, json={"status_code": 34})

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await tmdb_client.get_movie_or_none(99999999)

            assert result is None

    async def test_get_movie_or_none_returns_movie(self, tmdb_client: TMDBClient) -> None:
        """Test get_movie_or_none returns movie when found."""
        mock_response = httpx.Response(200, json=SAMPLE_MOVIE_DETAILS)

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await tmdb_client.get_movie_or_none(550)

            assert result is not None
            assert result.id == 550


class TestRateLimitHandling:
    """Tests for rate limit handling."""

    async def test_rate_limit_error(self, tmdb_client: TMDBClient) -> None:
        """Test that rate limit response raises RateLimitError."""
        mock_response = httpx.Response(
            429,
            headers={"Retry-After": "30"},
            json={"status_code": 25},
        )

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            with pytest.raises(RateLimitError) as exc_info:
                await tmdb_client.search_movies("test")

            assert exc_info.value.retry_after == 30


class TestImageURLGeneration:
    """Tests for image URL generation methods."""

    def test_get_poster_url_valid(self, tmdb_client: TMDBClient) -> None:
        """Test poster URL generation with valid path."""
        url = tmdb_client.get_poster_url("/abc123.jpg")
        assert url == "https://image.tmdb.org/t/p/w342/abc123.jpg"

    def test_get_poster_url_custom_size(self, tmdb_client: TMDBClient) -> None:
        """Test poster URL generation with custom size."""
        url = tmdb_client.get_poster_url("/abc123.jpg", size="w500")
        assert url == "https://image.tmdb.org/t/p/w500/abc123.jpg"

    def test_get_poster_url_original_size(self, tmdb_client: TMDBClient) -> None:
        """Test poster URL generation with original size."""
        url = tmdb_client.get_poster_url("/abc123.jpg", size="original")
        assert url == "https://image.tmdb.org/t/p/original/abc123.jpg"

    def test_get_poster_url_invalid_size_fallback(self, tmdb_client: TMDBClient) -> None:
        """Test poster URL generation falls back for invalid size."""
        url = tmdb_client.get_poster_url("/abc123.jpg", size="invalid")
        assert url == "https://image.tmdb.org/t/p/w342/abc123.jpg"

    def test_get_poster_url_none_path(self, tmdb_client: TMDBClient) -> None:
        """Test poster URL generation with None path returns None."""
        url = tmdb_client.get_poster_url(None)
        assert url is None

    def test_get_backdrop_url_valid(self, tmdb_client: TMDBClient) -> None:
        """Test backdrop URL generation with valid path."""
        url = tmdb_client.get_backdrop_url("/backdrop.jpg")
        assert url == "https://image.tmdb.org/t/p/w780/backdrop.jpg"

    def test_get_backdrop_url_none_path(self, tmdb_client: TMDBClient) -> None:
        """Test backdrop URL generation with None path returns None."""
        url = tmdb_client.get_backdrop_url(None)
        assert url is None


class TestResultConversion:
    """Tests for result conversion methods."""

    def test_to_movie_result_with_urls(self, tmdb_client: TMDBClient) -> None:
        """Test converting movie result to dict with URLs."""
        result = TMDBMovieResult(
            id=550,
            title="Fight Club",
            poster_path="/poster.jpg",
        )

        data = tmdb_client.to_movie_result_with_urls(result)

        assert data["id"] == 550
        assert data["title"] == "Fight Club"
        assert data["poster_url"] == "https://image.tmdb.org/t/p/w342/poster.jpg"

    def test_to_movie_details_with_urls(self, tmdb_client: TMDBClient) -> None:
        """Test converting movie details to dict with URLs."""
        details = TMDBMovieDetails(
            id=550,
            title="Fight Club",
            poster_path="/poster.jpg",
            backdrop_path="/backdrop.jpg",
        )

        data = tmdb_client.to_movie_details_with_urls(details)

        assert data["id"] == 550
        assert data["poster_url"] == "https://image.tmdb.org/t/p/w342/poster.jpg"
        assert data["backdrop_url"] == "https://image.tmdb.org/t/p/w780/backdrop.jpg"


class TestContextManager:
    """Tests for async context manager functionality."""

    async def test_context_manager(self, mock_settings) -> None:  # noqa: ARG002
        """Test client can be used as async context manager."""
        async with TMDBClient() as client:
            assert client._client is not None

        # Client should be closed after exiting context
        assert client._client is None or client._client.is_closed


class TestAPIErrorHandling:
    """Tests for API error handling."""

    async def test_api_error_on_server_error(self, tmdb_client: TMDBClient) -> None:
        """Test that server errors raise APIError."""
        mock_response = httpx.Response(500, text="Internal Server Error")

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            with pytest.raises(APIError) as exc_info:
                await tmdb_client.search_movies("test")

            assert exc_info.value.status_code == 500


class TestGetMovieCredits:
    """Tests for getting movie credits."""

    async def test_get_movie_credits_success(self, tmdb_client: TMDBClient) -> None:
        """Test successful movie credits fetch."""
        mock_response = httpx.Response(200, json=SAMPLE_CREDITS_RESPONSE)

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await tmdb_client.get_movie_credits(550)

            assert result.id == 550
            assert len(result.cast) == 2
            assert len(result.crew) == 2
            assert result.cast[0].name == "Edward Norton"
            assert result.cast[0].character == "The Narrator"
            assert result.crew[0].name == "David Fincher"
            assert result.crew[0].job == "Director"

    async def test_get_movie_credits_not_found(self, tmdb_client: TMDBClient) -> None:
        """Test movie credits fetch for non-existent movie."""
        mock_response = httpx.Response(404, json={"status_code": 34})

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            with pytest.raises(NotFoundError):
                await tmdb_client.get_movie_credits(99999999)

    async def test_get_movie_credits_or_none_returns_none(self, tmdb_client: TMDBClient) -> None:
        """Test get_movie_credits_or_none returns None for non-existent movie."""
        mock_response = httpx.Response(404, json={"status_code": 34})

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await tmdb_client.get_movie_credits_or_none(99999999)

            assert result is None

    async def test_get_movie_credits_or_none_returns_credits(self, tmdb_client: TMDBClient) -> None:
        """Test get_movie_credits_or_none returns credits when found."""
        mock_response = httpx.Response(200, json=SAMPLE_CREDITS_RESPONSE)

        with patch.object(tmdb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await tmdb_client.get_movie_credits_or_none(550)

            assert result is not None
            assert result.id == 550
            assert len(result.cast) == 2


class TestProfileURLGeneration:
    """Tests for profile URL generation."""

    def test_get_profile_url_valid(self, tmdb_client: TMDBClient) -> None:
        """Test profile URL generation with valid path."""
        url = tmdb_client.get_profile_url("/abc123.jpg")
        assert url == "https://image.tmdb.org/t/p/w185/abc123.jpg"

    def test_get_profile_url_custom_size(self, tmdb_client: TMDBClient) -> None:
        """Test profile URL generation with custom size."""
        url = tmdb_client.get_profile_url("/abc123.jpg", size="h632")
        assert url == "https://image.tmdb.org/t/p/h632/abc123.jpg"

    def test_get_profile_url_original_size(self, tmdb_client: TMDBClient) -> None:
        """Test profile URL generation with original size."""
        url = tmdb_client.get_profile_url("/abc123.jpg", size="original")
        assert url == "https://image.tmdb.org/t/p/original/abc123.jpg"

    def test_get_profile_url_invalid_size_fallback(self, tmdb_client: TMDBClient) -> None:
        """Test profile URL generation falls back for invalid size."""
        url = tmdb_client.get_profile_url("/abc123.jpg", size="invalid")
        assert url == "https://image.tmdb.org/t/p/w185/abc123.jpg"

    def test_get_profile_url_none_path(self, tmdb_client: TMDBClient) -> None:
        """Test profile URL generation with None path returns None."""
        url = tmdb_client.get_profile_url(None)
        assert url is None
