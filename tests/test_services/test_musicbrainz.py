"""Tests for MusicBrainz API client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from wrong_opinions.services.base import APIError, NotFoundError, RateLimitError
from wrong_opinions.services.musicbrainz import MusicBrainzClient

# Sample test data
SAMPLE_SEARCH_RESPONSE = {
    "count": 2,
    "offset": 0,
    "releases": [
        {
            "id": "abc-123-uuid",
            "title": "The Dark Side of the Moon",
            "score": 100,
            "country": "GB",
            "status": "Official",
            "date": "1973-03-01",
            "barcode": "077774644426",
            "artist-credit": [
                {"name": "Pink Floyd"},
            ],
        },
        {
            "id": "def-456-uuid",
            "title": "The Dark Side of the Moon (Remaster)",
            "score": 95,
            "country": "US",
            "status": "Official",
            "date": "2011-09-27",
            "barcode": None,
            "artist-credit": [
                {"name": "Pink Floyd"},
            ],
        },
    ],
}

SAMPLE_RELEASE_DETAILS = {
    "id": "abc-123-uuid",
    "title": "The Dark Side of the Moon",
    "status": "Official",
    "country": "GB",
    "date": "1973-03-01",
    "barcode": "077774644426",
    "artist-credit": [
        {"name": "Pink Floyd"},
    ],
    "release-group": {
        "id": "rg-789-uuid",
        "title": "The Dark Side of the Moon",
        "primary-type": "Album",
    },
}


@pytest.fixture
def mock_settings():
    """Mock settings with test user agent."""
    with patch("wrong_opinions.services.musicbrainz.get_settings") as mock:
        mock.return_value.musicbrainz_user_agent = "WrongOpinions/1.0 (test@example.com)"
        mock.return_value.musicbrainz_base_url = "https://musicbrainz.org/ws/2"
        yield mock


@pytest.fixture
def mb_client(mock_settings) -> MusicBrainzClient:  # noqa: ARG001
    """Create a MusicBrainz client for testing."""
    return MusicBrainzClient()


class TestMusicBrainzClientInit:
    """Tests for MusicBrainz client initialization."""

    def test_init_with_user_agent(self, mock_settings) -> None:  # noqa: ARG002
        """Test client initialization with explicit user agent."""
        client = MusicBrainzClient(user_agent="CustomAgent/1.0")
        assert client._user_agent == "CustomAgent/1.0"

    def test_init_with_custom_base_url(self, mock_settings) -> None:  # noqa: ARG002
        """Test client initialization with custom base URL."""
        client = MusicBrainzClient(base_url="https://custom.musicbrainz.org/ws/2")
        assert client.base_url == "https://custom.musicbrainz.org/ws/2"

    def test_init_without_user_agent_raises(self) -> None:
        """Test that initialization without user agent raises error."""
        with patch("wrong_opinions.services.musicbrainz.get_settings") as mock:
            mock.return_value.musicbrainz_user_agent = ""
            mock.return_value.musicbrainz_base_url = "https://musicbrainz.org/ws/2"
            with pytest.raises(ValueError, match="MusicBrainz User-Agent is required"):
                MusicBrainzClient()

    def test_rate_limit_delay_is_one_second(self, mb_client: MusicBrainzClient) -> None:
        """Test that rate limit delay is set to 1 second for MusicBrainz."""
        assert mb_client.rate_limit_delay == 1.0

    def test_default_headers(self, mb_client: MusicBrainzClient) -> None:
        """Test that default headers include User-Agent."""
        headers = mb_client.default_headers
        assert "User-Agent" in headers
        assert headers["User-Agent"] == "WrongOpinions/1.0 (test@example.com)"
        assert headers["Accept"] == "application/json"


class TestSearchReleases:
    """Tests for release search functionality."""

    async def test_search_releases_success(self, mb_client: MusicBrainzClient) -> None:
        """Test successful release search."""
        mock_response = httpx.Response(200, json=SAMPLE_SEARCH_RESPONSE)

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await mb_client.search_releases("Dark Side of the Moon")

            assert result.count == 2
            assert len(result.releases) == 2
            assert result.releases[0].title == "The Dark Side of the Moon"
            assert result.releases[0].id == "abc-123-uuid"
            assert result.releases[0].artist_name == "Pink Floyd"

    async def test_search_releases_includes_fmt_json(self, mb_client: MusicBrainzClient) -> None:
        """Test that search includes fmt=json parameter."""
        mock_response = httpx.Response(200, json=SAMPLE_SEARCH_RESPONSE)

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            await mb_client.search_releases("test")

            # Verify fmt=json was passed in params
            call_args = mock_client.request.call_args
            assert call_args.kwargs["params"]["fmt"] == "json"

    async def test_search_releases_limit_enforced(self, mb_client: MusicBrainzClient) -> None:
        """Test that search limit is capped at 100."""
        mock_response = httpx.Response(200, json=SAMPLE_SEARCH_RESPONSE)

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            await mb_client.search_releases("test", limit=200)

            # Verify limit was capped at 100
            call_args = mock_client.request.call_args
            assert call_args.kwargs["params"]["limit"] == 100

    async def test_search_releases_empty_results(self, mb_client: MusicBrainzClient) -> None:
        """Test release search with no results."""
        empty_response = {
            "count": 0,
            "offset": 0,
            "releases": [],
        }
        mock_response = httpx.Response(200, json=empty_response)

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await mb_client.search_releases("NonexistentAlbum12345")

            assert result.count == 0
            assert len(result.releases) == 0

    async def test_search_releases_with_pagination(self, mb_client: MusicBrainzClient) -> None:
        """Test release search with pagination parameters."""
        mock_response = httpx.Response(200, json=SAMPLE_SEARCH_RESPONSE)

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            await mb_client.search_releases("test", limit=50, offset=25)

            # Verify pagination params were passed
            call_args = mock_client.request.call_args
            assert call_args.kwargs["params"]["limit"] == 50
            assert call_args.kwargs["params"]["offset"] == 25


class TestGetRelease:
    """Tests for getting release details."""

    async def test_get_release_success(self, mb_client: MusicBrainzClient) -> None:
        """Test successful release details fetch."""
        mock_response = httpx.Response(200, json=SAMPLE_RELEASE_DETAILS)

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await mb_client.get_release("abc-123-uuid")

            assert result.id == "abc-123-uuid"
            assert result.title == "The Dark Side of the Moon"
            assert result.country == "GB"
            assert result.artist_name == "Pink Floyd"

    async def test_get_release_includes_fmt_json(self, mb_client: MusicBrainzClient) -> None:
        """Test that get release includes fmt=json parameter."""
        mock_response = httpx.Response(200, json=SAMPLE_RELEASE_DETAILS)

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            await mb_client.get_release("abc-123-uuid")

            # Verify fmt=json was passed in params
            call_args = mock_client.request.call_args
            assert call_args.kwargs["params"]["fmt"] == "json"

    async def test_get_release_always_includes_release_groups(
        self, mb_client: MusicBrainzClient
    ) -> None:
        """Test that get release always includes release-groups in inc parameter."""
        mock_response = httpx.Response(200, json=SAMPLE_RELEASE_DETAILS)

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            await mb_client.get_release("abc-123-uuid")

            # Verify release-groups was included in inc parameter
            call_args = mock_client.request.call_args
            assert "release-groups" in call_args.kwargs["params"]["inc"]

    async def test_get_release_with_artist_credits_includes_both(
        self, mb_client: MusicBrainzClient
    ) -> None:
        """Test that get release with artist credits includes both in inc parameter."""
        mock_response = httpx.Response(200, json=SAMPLE_RELEASE_DETAILS)

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            await mb_client.get_release("abc-123-uuid", include_artist_credits=True)

            # Verify both release-groups and artist-credits were included
            call_args = mock_client.request.call_args
            inc_param = call_args.kwargs["params"]["inc"]
            assert "release-groups" in inc_param
            assert "artist-credits" in inc_param

    async def test_get_release_parses_release_group(self, mb_client: MusicBrainzClient) -> None:
        """Test that get release correctly parses release-group data."""
        mock_response = httpx.Response(200, json=SAMPLE_RELEASE_DETAILS)

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await mb_client.get_release("abc-123-uuid")

            assert result.release_group is not None
            assert result.release_group.id == "rg-789-uuid"
            assert result.release_group.title == "The Dark Side of the Moon"
            assert result.release_group.primary_type == "Album"

    async def test_get_release_not_found(self, mb_client: MusicBrainzClient) -> None:
        """Test release details fetch for non-existent release."""
        mock_response = httpx.Response(404, json={"error": "Not Found"})

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            with pytest.raises(NotFoundError):
                await mb_client.get_release("invalid-uuid")

    async def test_get_release_or_none_returns_none(self, mb_client: MusicBrainzClient) -> None:
        """Test get_release_or_none returns None for non-existent release."""
        mock_response = httpx.Response(404, json={"error": "Not Found"})

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await mb_client.get_release_or_none("invalid-uuid")

            assert result is None

    async def test_get_release_or_none_returns_release(self, mb_client: MusicBrainzClient) -> None:
        """Test get_release_or_none returns release when found."""
        mock_response = httpx.Response(200, json=SAMPLE_RELEASE_DETAILS)

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await mb_client.get_release_or_none("abc-123-uuid")

            assert result is not None
            assert result.id == "abc-123-uuid"


class TestRateLimitHandling:
    """Tests for rate limit handling."""

    async def test_rate_limit_error(self, mb_client: MusicBrainzClient) -> None:
        """Test that rate limit response raises RateLimitError."""
        mock_response = httpx.Response(
            429,
            headers={"Retry-After": "60"},
            json={"error": "Rate limit exceeded"},
        )

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            with pytest.raises(RateLimitError) as exc_info:
                await mb_client.search_releases("test")

            assert exc_info.value.retry_after == 60


class TestCoverArtURLGeneration:
    """Tests for Cover Art Archive URL generation methods."""

    def test_get_cover_art_url(self, mb_client: MusicBrainzClient) -> None:
        """Test cover art URL generation."""
        url = mb_client.get_cover_art_url("abc-123-uuid")
        assert url == "https://coverartarchive.org/release/abc-123-uuid"

    def test_get_cover_art_front_url(self, mb_client: MusicBrainzClient) -> None:
        """Test front cover art URL generation."""
        url = mb_client.get_cover_art_front_url("abc-123-uuid")
        assert url == "https://coverartarchive.org/release/abc-123-uuid/front"

    def test_get_cover_art_release_group_url(self, mb_client: MusicBrainzClient) -> None:
        """Test release-group cover art URL generation."""
        url = mb_client.get_cover_art_release_group_url("rg-456-uuid")
        assert url == "https://coverartarchive.org/release-group/rg-456-uuid/front"


class TestCoverArtValidation:
    """Tests for cover art validation methods."""

    async def test_check_cover_art_exists_returns_true_on_307(
        self, mb_client: MusicBrainzClient
    ) -> None:
        """Test that 307 redirect means cover art exists."""
        mock_response = httpx.Response(307, headers={"Location": "https://example.com/image.jpg"})

        with patch("wrong_opinions.services.musicbrainz.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.head = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await mb_client._check_cover_art_exists(
                "https://coverartarchive.org/release/abc-123/front"
            )
            assert result is True

    async def test_check_cover_art_exists_returns_true_on_200(
        self, mb_client: MusicBrainzClient
    ) -> None:
        """Test that 200 response means cover art exists."""
        mock_response = httpx.Response(200)

        with patch("wrong_opinions.services.musicbrainz.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.head = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await mb_client._check_cover_art_exists(
                "https://coverartarchive.org/release/abc-123/front"
            )
            assert result is True

    async def test_check_cover_art_exists_returns_false_on_404(
        self, mb_client: MusicBrainzClient
    ) -> None:
        """Test that 404 means no cover art."""
        mock_response = httpx.Response(404)

        with patch("wrong_opinions.services.musicbrainz.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.head = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await mb_client._check_cover_art_exists(
                "https://coverartarchive.org/release/abc-123/front"
            )
            assert result is False

    async def test_check_cover_art_exists_returns_false_on_request_error(
        self, mb_client: MusicBrainzClient
    ) -> None:
        """Test that request errors return False gracefully."""
        with patch("wrong_opinions.services.musicbrainz.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.head = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await mb_client._check_cover_art_exists(
                "https://coverartarchive.org/release/abc-123/front"
            )
            assert result is False

    async def test_get_validated_cover_art_url_release_exists(
        self, mb_client: MusicBrainzClient
    ) -> None:
        """Test validated URL returns release URL when exists."""
        with patch.object(mb_client, "_check_cover_art_exists", return_value=True) as mock_check:
            result = await mb_client.get_validated_cover_art_url("abc-123", "rg-456")

            assert result == "https://coverartarchive.org/release/abc-123/front"
            mock_check.assert_called_once_with("https://coverartarchive.org/release/abc-123/front")

    async def test_get_validated_cover_art_url_falls_back_to_release_group(
        self, mb_client: MusicBrainzClient
    ) -> None:
        """Test fallback to release-group when release has no cover art."""
        with patch.object(mb_client, "_check_cover_art_exists") as mock_check:
            # First call (release) returns False, second (release-group) returns True
            mock_check.side_effect = [False, True]

            result = await mb_client.get_validated_cover_art_url("abc-123", "rg-456")

            assert result == "https://coverartarchive.org/release-group/rg-456/front"
            assert mock_check.call_count == 2
            mock_check.assert_any_call("https://coverartarchive.org/release/abc-123/front")
            mock_check.assert_any_call("https://coverartarchive.org/release-group/rg-456/front")

    async def test_get_validated_cover_art_url_returns_none_when_no_art(
        self, mb_client: MusicBrainzClient
    ) -> None:
        """Test returns None when neither release nor release-group has art."""
        with patch.object(mb_client, "_check_cover_art_exists", return_value=False) as mock_check:
            result = await mb_client.get_validated_cover_art_url("abc-123", "rg-456")

            assert result is None
            assert mock_check.call_count == 2

    async def test_get_validated_cover_art_url_without_release_group(
        self, mb_client: MusicBrainzClient
    ) -> None:
        """Test validation without release-group ID."""
        with patch.object(mb_client, "_check_cover_art_exists", return_value=False) as mock_check:
            result = await mb_client.get_validated_cover_art_url("abc-123", None)

            assert result is None
            # Only checks release, not release-group
            mock_check.assert_called_once_with("https://coverartarchive.org/release/abc-123/front")

    async def test_get_validated_cover_art_url_no_release_group_with_release_art(
        self, mb_client: MusicBrainzClient
    ) -> None:
        """Test validation returns release URL when release-group is None but release has art."""
        with patch.object(mb_client, "_check_cover_art_exists", return_value=True) as mock_check:
            result = await mb_client.get_validated_cover_art_url("abc-123", None)

            assert result == "https://coverartarchive.org/release/abc-123/front"
            mock_check.assert_called_once()


class TestContextManager:
    """Tests for async context manager functionality."""

    async def test_context_manager(self, mock_settings) -> None:  # noqa: ARG002
        """Test client can be used as async context manager."""
        async with MusicBrainzClient() as client:
            assert client._client is not None

        # Client should be closed after exiting context
        assert client._client is None or client._client.is_closed


class TestAPIErrorHandling:
    """Tests for API error handling."""

    async def test_api_error_on_server_error(self, mb_client: MusicBrainzClient) -> None:
        """Test that server errors raise APIError."""
        mock_response = httpx.Response(500, text="Internal Server Error")

        with patch.object(mb_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            with pytest.raises(APIError) as exc_info:
                await mb_client.search_releases("test")

            assert exc_info.value.status_code == 500
