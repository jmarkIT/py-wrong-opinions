"""Album API endpoints."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from wrong_opinions.database import get_db
from wrong_opinions.models.album import Album
from wrong_opinions.schemas.album import AlbumDetails, AlbumSearchResponse, AlbumSearchResult
from wrong_opinions.services.base import APIError, NotFoundError
from wrong_opinions.services.musicbrainz import MusicBrainzClient, get_musicbrainz_client

router = APIRouter(prefix="/albums", tags=["albums"])


def _parse_musicbrainz_date(date_str: str | None) -> date | None:
    """Parse a MusicBrainz date string to a date object.

    MusicBrainz dates can be YYYY, YYYY-MM, or YYYY-MM-DD.
    """
    if not date_str:
        return None

    try:
        # Try full date first
        if len(date_str) == 10:
            return date.fromisoformat(date_str)
        # Year-month only
        if len(date_str) == 7:
            return date.fromisoformat(f"{date_str}-01")
        # Year only
        if len(date_str) == 4:
            return date.fromisoformat(f"{date_str}-01-01")
    except ValueError:
        pass

    return None


@router.get("/search", response_model=AlbumSearchResponse)
async def search_albums(
    query: str = Query(..., min_length=1, description="Search query for albums"),
    limit: int = Query(25, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Result offset for pagination"),
    musicbrainz_client: MusicBrainzClient = Depends(get_musicbrainz_client),
) -> AlbumSearchResponse:
    """Search for albums using MusicBrainz.

    Returns a list of albums matching the search query.
    Note: MusicBrainz has a rate limit of 1 request per second.
    """
    try:
        response = await musicbrainz_client.search_releases(query=query, limit=limit, offset=offset)

        results = [
            AlbumSearchResult(
                musicbrainz_id=release.id,
                title=release.title,
                artist=release.artist_name,
                release_date=release.date,
                country=release.country,
                score=release.score,
                cover_art_url=musicbrainz_client.get_cover_art_front_url(release.id),
            )
            for release in response.releases
        ]

        return AlbumSearchResponse(
            count=response.count,
            offset=response.offset,
            results=results,
        )
    except APIError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    finally:
        await musicbrainz_client.close()


@router.get("/{musicbrainz_id}", response_model=AlbumDetails)
async def get_album(
    musicbrainz_id: str,
    db: AsyncSession = Depends(get_db),
    musicbrainz_client: MusicBrainzClient = Depends(get_musicbrainz_client),
) -> AlbumDetails:
    """Get detailed album information.

    First checks local cache, then fetches from MusicBrainz if not cached.
    Caches the result in the local database for future requests.
    """
    # Check local cache first
    result = await db.execute(select(Album).where(Album.musicbrainz_id == musicbrainz_id))
    cached_album = result.scalar_one_or_none()

    if cached_album:
        return AlbumDetails(
            musicbrainz_id=cached_album.musicbrainz_id,
            title=cached_album.title,
            artist=cached_album.artist,
            release_date=(
                cached_album.release_date.isoformat() if cached_album.release_date else None
            ),
            country=None,  # Not stored in cache
            status=None,  # Not stored in cache
            cover_art_url=cached_album.cover_art_url,
            cached=True,
        )

    # Fetch from MusicBrainz
    try:
        release = await musicbrainz_client.get_release(musicbrainz_id)

        # Cache the album in the database
        new_album = Album(
            musicbrainz_id=release.id,
            title=release.title,
            artist=release.artist_name or "Unknown Artist",
            release_date=_parse_musicbrainz_date(release.date),
            cover_art_url=musicbrainz_client.get_cover_art_front_url(release.id),
            cached_at=datetime.now(UTC),
        )
        db.add(new_album)
        # Note: commit happens automatically via get_db dependency

        return AlbumDetails(
            musicbrainz_id=release.id,
            title=release.title,
            artist=release.artist_name,
            release_date=release.date,
            country=release.country,
            status=release.status,
            cover_art_url=musicbrainz_client.get_cover_art_front_url(release.id),
            cached=False,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail="Album not found") from e
    except APIError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    finally:
        await musicbrainz_client.close()
