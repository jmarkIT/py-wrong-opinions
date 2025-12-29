"""Tests for album API endpoints."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from wrong_opinions.database import get_db
from wrong_opinions.main import app
from wrong_opinions.schemas.external import (
    MusicBrainzReleaseDetails,
    MusicBrainzReleaseResult,
    MusicBrainzSearchResponse,
)
from wrong_opinions.services.musicbrainz import MusicBrainzClient, get_musicbrainz_client

# Sample test data - use model_validate with aliases for MusicBrainz schemas
SAMPLE_SEARCH_RESPONSE = MusicBrainzSearchResponse(
    count=2,
    offset=0,
    releases=[
        MusicBrainzReleaseResult.model_validate(
            {
                "id": "abc-123-uuid",
                "title": "The Dark Side of the Moon",
                "score": 100,
                "country": "GB",
                "status": "Official",
                "date": "1973-03-01",
                "barcode": "077774644426",
                "artist-credit": [{"name": "Pink Floyd"}],
            }
        ),
        MusicBrainzReleaseResult.model_validate(
            {
                "id": "def-456-uuid",
                "title": "The Dark Side of the Moon (Remaster)",
                "score": 95,
                "country": "US",
                "status": "Official",
                "date": "2011-09-27",
                "barcode": None,
                "artist-credit": [{"name": "Pink Floyd"}],
            }
        ),
    ],
)

SAMPLE_RELEASE_DETAILS = MusicBrainzReleaseDetails.model_validate(
    {
        "id": "abc-123-uuid",
        "title": "The Dark Side of the Moon",
        "status": "Official",
        "country": "GB",
        "date": "1973-03-01",
        "barcode": "077774644426",
        "artist-credit": [{"name": "Pink Floyd"}],
    }
)


@pytest.fixture
def mock_musicbrainz_client():
    """Create a mock MusicBrainz client."""
    mock_client = MagicMock(spec=MusicBrainzClient)
    mock_client.search_releases = AsyncMock(return_value=SAMPLE_SEARCH_RESPONSE)
    mock_client.get_release = AsyncMock(return_value=SAMPLE_RELEASE_DETAILS)
    mock_client.get_cover_art_front_url.side_effect = lambda id: (
        f"https://coverartarchive.org/release/{id}/front"
    )
    mock_client.close = AsyncMock()
    return mock_client


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = AsyncMock()
    # Result is sync, not async
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Not cached by default
    # execute is async but returns a sync Result
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    return mock_session


class TestAlbumSearch:
    """Tests for album search endpoint."""

    async def test_search_albums_success(
        self, client: AsyncClient, mock_musicbrainz_client: MagicMock
    ) -> None:
        """Test successful album search."""
        app.dependency_overrides[get_musicbrainz_client] = lambda: mock_musicbrainz_client

        try:
            response = await client.get("/api/albums/search?query=Dark Side of the Moon")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 2
            assert len(data["results"]) == 2
            assert data["results"][0]["musicbrainz_id"] == "abc-123-uuid"
            assert data["results"][0]["title"] == "The Dark Side of the Moon"
            assert data["results"][0]["artist"] == "Pink Floyd"
            assert data["results"][0]["cover_art_url"] is not None
        finally:
            app.dependency_overrides.clear()

    async def test_search_albums_with_pagination(
        self, client: AsyncClient, mock_musicbrainz_client: MagicMock
    ) -> None:
        """Test album search with pagination parameters."""
        app.dependency_overrides[get_musicbrainz_client] = lambda: mock_musicbrainz_client

        try:
            response = await client.get("/api/albums/search?query=test&limit=50&offset=25")

            assert response.status_code == 200
            mock_musicbrainz_client.search_releases.assert_called_once_with(
                query="test", limit=50, offset=25
            )
        finally:
            app.dependency_overrides.clear()

    async def test_search_albums_empty_query(self, client: AsyncClient) -> None:
        """Test album search with empty query returns 422."""
        response = await client.get("/api/albums/search?query=")

        assert response.status_code == 422

    async def test_search_albums_missing_query(self, client: AsyncClient) -> None:
        """Test album search without query parameter returns 422."""
        response = await client.get("/api/albums/search")

        assert response.status_code == 422

    async def test_search_albums_limit_validation(self, client: AsyncClient) -> None:
        """Test album search with invalid limit returns 422."""
        response = await client.get("/api/albums/search?query=test&limit=101")

        assert response.status_code == 422


class TestGetAlbum:
    """Tests for get album details endpoint."""

    async def test_get_album_success(
        self,
        client: AsyncClient,
        mock_musicbrainz_client: MagicMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test successful album details fetch from API."""

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_musicbrainz_client] = lambda: mock_musicbrainz_client
        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/albums/abc-123-uuid")

            assert response.status_code == 200
            data = response.json()
            assert data["musicbrainz_id"] == "abc-123-uuid"
            assert data["title"] == "The Dark Side of the Moon"
            assert data["artist"] == "Pink Floyd"
            assert data["cached"] is False
        finally:
            app.dependency_overrides.clear()

    async def test_get_album_from_cache(
        self,
        client: AsyncClient,
        mock_musicbrainz_client: MagicMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test album details fetch from cache."""
        # Set up cached album
        cached_album = MagicMock()
        cached_album.musicbrainz_id = "abc-123-uuid"
        cached_album.title = "The Dark Side of the Moon"
        cached_album.artist = "Pink Floyd"
        cached_album.release_date = date(1973, 3, 1)
        cached_album.cover_art_url = "https://coverartarchive.org/release/abc-123-uuid/front"

        # Result is sync, not async
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cached_album
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_musicbrainz_client] = lambda: mock_musicbrainz_client
        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/albums/abc-123-uuid")

            assert response.status_code == 200
            data = response.json()
            assert data["musicbrainz_id"] == "abc-123-uuid"
            assert data["cached"] is True
            # MusicBrainz client get_release should not be called
            mock_musicbrainz_client.get_release.assert_not_called()
        finally:
            app.dependency_overrides.clear()

    async def test_get_album_not_found(
        self,
        client: AsyncClient,
        mock_musicbrainz_client: MagicMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test album details fetch for non-existent album."""
        from wrong_opinions.services.base import NotFoundError

        mock_musicbrainz_client.get_release.side_effect = NotFoundError("Album not found")

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_musicbrainz_client] = lambda: mock_musicbrainz_client
        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/albums/invalid-uuid")

            assert response.status_code == 404
            assert response.json()["detail"] == "Album not found"
        finally:
            app.dependency_overrides.clear()


class TestDateParsing:
    """Tests for MusicBrainz date parsing."""

    def test_parse_full_date(self) -> None:
        """Test parsing a full YYYY-MM-DD date."""
        from wrong_opinions.api.albums import _parse_musicbrainz_date

        result = _parse_musicbrainz_date("1973-03-01")
        assert result == date(1973, 3, 1)

    def test_parse_year_month(self) -> None:
        """Test parsing a YYYY-MM date."""
        from wrong_opinions.api.albums import _parse_musicbrainz_date

        result = _parse_musicbrainz_date("1973-03")
        assert result == date(1973, 3, 1)

    def test_parse_year_only(self) -> None:
        """Test parsing a YYYY date."""
        from wrong_opinions.api.albums import _parse_musicbrainz_date

        result = _parse_musicbrainz_date("1973")
        assert result == date(1973, 1, 1)

    def test_parse_none(self) -> None:
        """Test parsing None returns None."""
        from wrong_opinions.api.albums import _parse_musicbrainz_date

        result = _parse_musicbrainz_date(None)
        assert result is None

    def test_parse_invalid_date(self) -> None:
        """Test parsing invalid date returns None."""
        from wrong_opinions.api.albums import _parse_musicbrainz_date

        result = _parse_musicbrainz_date("invalid")
        assert result is None


# Sample data for album credits tests
SAMPLE_RELEASE_WITH_CREDITS = MusicBrainzReleaseDetails.model_validate(
    {
        "id": "abc-123-uuid",
        "title": "The Dark Side of the Moon",
        "status": "Official",
        "country": "GB",
        "date": "1973-03-01",
        "barcode": "077774644426",
        "artist-credit": [
            {
                "name": "Pink Floyd",
                "joinphrase": "",
                "artist": {
                    "id": "artist-uuid-1",
                    "name": "Pink Floyd",
                    "sort-name": "Pink Floyd",
                    "disambiguation": "UK rock band",
                    "type": "Group",
                    "country": "GB",
                },
            }
        ],
    }
)

SAMPLE_RELEASE_WITH_MULTIPLE_ARTISTS = MusicBrainzReleaseDetails.model_validate(
    {
        "id": "collab-uuid",
        "title": "Watch the Throne",
        "status": "Official",
        "country": "US",
        "date": "2011-08-08",
        "barcode": None,
        "artist-credit": [
            {
                "name": "Jay-Z",
                "joinphrase": " & ",
                "artist": {
                    "id": "artist-uuid-jay",
                    "name": "Jay-Z",
                    "sort-name": "Jay-Z",
                    "disambiguation": None,
                    "type": "Person",
                    "country": "US",
                },
            },
            {
                "name": "Kanye West",
                "joinphrase": "",
                "artist": {
                    "id": "artist-uuid-kanye",
                    "name": "Kanye West",
                    "sort-name": "West, Kanye",
                    "disambiguation": None,
                    "type": "Person",
                    "country": "US",
                },
            },
        ],
    }
)


class TestGetAlbumCredits:
    """Tests for album credits endpoint."""

    async def test_get_album_credits_success(
        self,
        client: AsyncClient,
        mock_musicbrainz_client: MagicMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test successful album credits fetch from API."""
        mock_musicbrainz_client.get_release = AsyncMock(return_value=SAMPLE_RELEASE_WITH_CREDITS)

        # Mock scalars().all() to return empty list (no cached artists)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Album not cached
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.flush = AsyncMock()

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_musicbrainz_client] = lambda: mock_musicbrainz_client
        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/albums/abc-123-uuid/credits")

            assert response.status_code == 200
            data = response.json()
            assert "artists" in data
            assert len(data["artists"]) == 1
            assert data["artists"][0]["musicbrainz_id"] == "artist-uuid-1"
            assert data["artists"][0]["name"] == "Pink Floyd"
            assert data["artists"][0]["artist_type"] == "Group"
            assert data["artists"][0]["country"] == "GB"
        finally:
            app.dependency_overrides.clear()

    async def test_get_album_credits_multiple_artists(
        self,
        client: AsyncClient,
        mock_musicbrainz_client: MagicMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test album credits with multiple artists (collaboration)."""
        mock_musicbrainz_client.get_release = AsyncMock(
            return_value=SAMPLE_RELEASE_WITH_MULTIPLE_ARTISTS
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.flush = AsyncMock()

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_musicbrainz_client] = lambda: mock_musicbrainz_client
        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/albums/collab-uuid/credits")

            assert response.status_code == 200
            data = response.json()
            assert len(data["artists"]) == 2
            assert data["artists"][0]["name"] == "Jay-Z"
            assert data["artists"][0]["join_phrase"] == " & "
            assert data["artists"][0]["order"] == 0
            assert data["artists"][1]["name"] == "Kanye West"
            assert data["artists"][1]["order"] == 1
        finally:
            app.dependency_overrides.clear()

    async def test_get_album_credits_not_found(
        self,
        client: AsyncClient,
        mock_musicbrainz_client: MagicMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test album credits fetch for non-existent album."""
        from wrong_opinions.services.base import NotFoundError

        mock_musicbrainz_client.get_release.side_effect = NotFoundError("Album not found")

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_musicbrainz_client] = lambda: mock_musicbrainz_client
        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/albums/invalid-uuid/credits")

            assert response.status_code == 404
            assert response.json()["detail"] == "Album not found"
        finally:
            app.dependency_overrides.clear()

    async def test_get_album_credits_with_limit(
        self,
        client: AsyncClient,
        mock_musicbrainz_client: MagicMock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test album credits with limit parameter."""
        mock_musicbrainz_client.get_release = AsyncMock(
            return_value=SAMPLE_RELEASE_WITH_MULTIPLE_ARTISTS
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.flush = AsyncMock()

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_musicbrainz_client] = lambda: mock_musicbrainz_client
        app.dependency_overrides[get_db] = override_get_db

        try:
            response = await client.get("/api/albums/collab-uuid/credits?limit=1")

            assert response.status_code == 200
            data = response.json()
            # Only 1 artist returned due to limit
            assert len(data["artists"]) == 1
            assert data["artists"][0]["name"] == "Jay-Z"
        finally:
            app.dependency_overrides.clear()
