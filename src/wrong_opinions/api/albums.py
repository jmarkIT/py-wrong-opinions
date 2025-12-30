"""Album API endpoints."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from wrong_opinions.database import get_db
from wrong_opinions.models.album import Album
from wrong_opinions.models.artist import AlbumArtist, Artist
from wrong_opinions.models.week import WeekAlbum
from wrong_opinions.schemas.album import (
    AlbumCredits,
    AlbumDetails,
    AlbumSearchResponse,
    AlbumSearchResult,
    AlbumSelectionsListResponse,
    AlbumSelectionWeek,
    AlbumWithSelections,
    ArtistCredit,
)
from wrong_opinions.services.base import NotFoundError
from wrong_opinions.services.musicbrainz import MusicBrainzClient, get_musicbrainz_client
from wrong_opinions.utils.security import CurrentUser

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
    current_user: CurrentUser,  # noqa: ARG001 - Required for auth enforcement
    query: str = Query(..., min_length=1, description="Search query for albums"),
    limit: int = Query(25, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Result offset for pagination"),
    musicbrainz_client: MusicBrainzClient = Depends(get_musicbrainz_client),
) -> AlbumSearchResponse:
    """Search for albums using MusicBrainz.

    Returns a list of albums matching the search query.
    Note: MusicBrainz has a rate limit of 1 request per second.
    Requires authentication.
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
    finally:
        await musicbrainz_client.close()


@router.get("/selections", response_model=AlbumSelectionsListResponse)
async def list_all_selected_albums(
    current_user: CurrentUser,  # noqa: ARG001 - Required for auth enforcement
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    db: AsyncSession = Depends(get_db),
) -> AlbumSelectionsListResponse:
    """List all albums that have been selected in any week.

    Returns a paginated list of albums with their week selection context.
    Sorted alphabetically by title.
    Requires authentication.
    """
    # Count total distinct albums with selections
    count_query = select(func.count(func.distinct(Album.id))).select_from(Album).join(WeekAlbum)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated albums with eager-loaded week associations
    offset = (page - 1) * page_size
    albums_query = (
        select(Album)
        .join(WeekAlbum)
        .distinct()
        .options(selectinload(Album.week_albums).selectinload(WeekAlbum.week))
        .order_by(func.lower(Album.title))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(albums_query)
    albums = result.scalars().all()

    # Build response with selection details
    results = [
        AlbumWithSelections(
            id=album.id,
            musicbrainz_id=album.musicbrainz_id,
            title=album.title,
            artist=album.artist,
            release_date=album.release_date,
            cover_art_url=album.cover_art_url,
            selections=[
                AlbumSelectionWeek(
                    week_id=wa.week.id,
                    year=wa.week.year,
                    week_number=wa.week.week_number,
                    position=wa.position,
                    added_at=wa.added_at,
                )
                for wa in album.week_albums
            ],
        )
        for album in albums
    ]

    return AlbumSelectionsListResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=results,
    )


@router.get("/{musicbrainz_id}", response_model=AlbumDetails)
async def get_album(
    musicbrainz_id: str,
    current_user: CurrentUser,  # noqa: ARG001 - Required for auth enforcement
    db: AsyncSession = Depends(get_db),
    musicbrainz_client: MusicBrainzClient = Depends(get_musicbrainz_client),
) -> AlbumDetails:
    """Get detailed album information.

    First checks local cache, then fetches from MusicBrainz if not cached.
    Caches the result in the local database for future requests.
    Requires authentication.
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
    # APIError exceptions (except NotFoundError) are handled globally
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
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Album not found") from None
    finally:
        await musicbrainz_client.close()


@router.get("/{musicbrainz_id}/credits", response_model=AlbumCredits)
async def get_album_credits(
    musicbrainz_id: str,
    current_user: CurrentUser,  # noqa: ARG001 - Required for auth enforcement
    limit: int = Query(10, ge=1, le=50, description="Max number of artists to return"),
    db: AsyncSession = Depends(get_db),
    musicbrainz_client: MusicBrainzClient = Depends(get_musicbrainz_client),
) -> AlbumCredits:
    """Get artist credits for an album.

    First checks local cache, then fetches from MusicBrainz if not cached.
    Caches the result in the local database for future requests.
    Requires authentication.
    """
    # Check if we have the album in the database
    result = await db.execute(select(Album).where(Album.musicbrainz_id == musicbrainz_id))
    cached_album = result.scalar_one_or_none()

    if cached_album:
        # Check if we have cached artist credits for this album
        artists_result = await db.execute(
            select(AlbumArtist)
            .where(AlbumArtist.album_id == cached_album.id)
            .order_by(AlbumArtist.order)
            .limit(limit)
        )
        cached_artists = artists_result.scalars().all()

        if cached_artists:
            # Load artist data
            artist_credits = []
            for aa in cached_artists:
                artist_result = await db.execute(select(Artist).where(Artist.id == aa.artist_id))
                artist = artist_result.scalar_one()
                artist_credits.append(
                    ArtistCredit(
                        musicbrainz_id=artist.musicbrainz_id,
                        name=artist.name,
                        sort_name=artist.sort_name,
                        disambiguation=artist.disambiguation,
                        artist_type=artist.artist_type,
                        country=artist.country,
                        join_phrase=aa.join_phrase,
                        order=aa.order,
                    )
                )

            return AlbumCredits(artists=artist_credits)

    # Fetch from MusicBrainz with full artist credits
    try:
        release = await musicbrainz_client.get_release(musicbrainz_id, include_artist_credits=True)

        # If album doesn't exist yet, fetch and cache it first
        if not cached_album:
            cached_album = Album(
                musicbrainz_id=release.id,
                title=release.title,
                artist=release.artist_name or "Unknown Artist",
                release_date=_parse_musicbrainz_date(release.date),
                cover_art_url=musicbrainz_client.get_cover_art_front_url(release.id),
                cached_at=datetime.now(UTC),
            )
            db.add(cached_album)
            await db.flush()  # Flush to get the album ID

        # Cache artist credits
        artist_credits = []
        for order, credit in enumerate(release.artist_credit[:limit]):
            # Skip credits without full artist info
            if not credit.artist:
                continue

            # Get or create artist
            artist_result = await db.execute(
                select(Artist).where(Artist.musicbrainz_id == credit.artist.id)
            )
            artist = artist_result.scalar_one_or_none()

            if not artist:
                artist = Artist(
                    musicbrainz_id=credit.artist.id,
                    name=credit.artist.name,
                    sort_name=credit.artist.sort_name,
                    disambiguation=credit.artist.disambiguation,
                    artist_type=credit.artist.type,
                    country=credit.artist.country,
                    cached_at=datetime.now(UTC),
                )
                db.add(artist)
                await db.flush()

            # Add album-artist association
            album_artist = AlbumArtist(
                album_id=cached_album.id,
                artist_id=artist.id,
                join_phrase=credit.joinphrase,
                order=order,
                cached_at=datetime.now(UTC),
            )
            db.add(album_artist)

            artist_credits.append(
                ArtistCredit(
                    musicbrainz_id=credit.artist.id,
                    name=credit.artist.name,
                    sort_name=credit.artist.sort_name,
                    disambiguation=credit.artist.disambiguation,
                    artist_type=credit.artist.type,
                    country=credit.artist.country,
                    join_phrase=credit.joinphrase,
                    order=order,
                )
            )

        return AlbumCredits(artists=artist_credits)

    except NotFoundError:
        raise HTTPException(status_code=404, detail="Album not found") from None
    finally:
        await musicbrainz_client.close()
