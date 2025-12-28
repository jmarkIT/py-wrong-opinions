# Wrong Opinions Backend - Architecture Plan

## Overview

Backend API for the "Wrong Opinions" web app - a platform for tracking weekly movie and music selections. Users can search for movies (via TMDB) and albums (via MusicBrainz), then associate them with specific weeks for future viewing and analysis.

## Tech Stack

### Required
- **Python 3.13+** - Runtime
- **UV** - Package management
- **FastAPI** - Web framework
- **Pydantic** - Data validation and settings management

### Recommended Additions
- **SQLite + SQLAlchemy** - Database (simple, file-based, perfect for small user base)
- **Alembic** - Database migrations
- **HTTPX** - Async HTTP client for external API calls
- **Pytest** - Testing
- **Ruff** - Linting and formatting

---

## Project Structure

```
py-wrong-opinions/
├── pyproject.toml          # UV/project configuration
├── uv.lock                  # Dependency lock file
├── alembic.ini              # Alembic configuration
├── .env.example             # Environment variable template
├── src/
│   └── wrong_opinions/
│       ├── __init__.py
│       ├── main.py          # FastAPI app entry point
│       ├── config.py        # Settings/configuration
│       ├── database.py      # Database connection setup
│       │
│       ├── models/          # SQLAlchemy ORM models
│       │   ├── __init__.py
│       │   ├── user.py
│       │   ├── week.py
│       │   ├── movie.py
│       │   └── album.py
│       │
│       ├── schemas/         # Pydantic schemas
│       │   ├── __init__.py
│       │   ├── user.py
│       │   ├── week.py
│       │   ├── movie.py
│       │   ├── album.py
│       │   └── external.py  # TMDB/MusicBrainz response schemas
│       │
│       ├── api/             # API routes
│       │   ├── __init__.py
│       │   ├── router.py    # Main router aggregation
│       │   ├── auth.py      # Authentication endpoints
│       │   ├── users.py     # User management
│       │   ├── weeks.py     # Week selection endpoints
│       │   ├── movies.py    # Movie search/management
│       │   └── albums.py    # Album search/management
│       │
│       ├── services/        # Business logic
│       │   ├── __init__.py
│       │   ├── tmdb.py      # TMDB API client
│       │   ├── musicbrainz.py  # MusicBrainz API client
│       │   └── selections.py   # Week selection logic
│       │
│       └── utils/           # Utility functions
│           ├── __init__.py
│           └── dates.py     # Week/date helpers
│
├── migrations/              # Alembic migrations
│   ├── env.py
│   └── versions/
│
└── tests/
    ├── __init__.py
    ├── conftest.py          # Pytest fixtures
    ├── test_api/
    ├── test_services/
    └── test_models/
```

---

## Data Models

### User
```python
class User:
    id: int (PK)
    username: str (unique)
    email: str (unique)
    hashed_password: str
    created_at: datetime
    is_active: bool
```

### Week
Represents a weekly selection period.
```python
class Week:
    id: int (PK)
    user_id: int (FK -> User)
    year: int
    week_number: int  # ISO week number (1-53)
    notes: str | None  # Optional commentary
    created_at: datetime
    updated_at: datetime

    # Constraints: unique(user_id, year, week_number)
```

### Movie
Cached movie data from TMDB.
```python
class Movie:
    id: int (PK)
    tmdb_id: int (unique)
    title: str
    original_title: str | None
    release_date: date | None
    poster_path: str | None
    overview: str | None
    cached_at: datetime
```

### Album
Cached album data from MusicBrainz.
```python
class Album:
    id: int (PK)
    musicbrainz_id: str (unique, UUID)
    title: str
    artist: str
    release_date: date | None
    cover_art_url: str | None
    cached_at: datetime
```

### WeekMovie (Association)
```python
class WeekMovie:
    id: int (PK)
    week_id: int (FK -> Week)
    movie_id: int (FK -> Movie)
    position: int  # 1 or 2 (first or second movie)
    added_at: datetime

    # Constraints: unique(week_id, position)
```

### WeekAlbum (Association)
```python
class WeekAlbum:
    id: int (PK)
    week_id: int (FK -> Week)
    album_id: int (FK -> Album)
    position: int  # 1 or 2 (first or second album)
    added_at: datetime

    # Constraints: unique(week_id, position)
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, return JWT token |
| POST | `/api/auth/refresh` | Refresh JWT token |
| GET | `/api/auth/me` | Get current user info |

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/{id}` | Get user profile |
| PATCH | `/api/users/{id}` | Update user profile |

### Weeks (Selections)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/weeks` | List all weeks (paginated, filterable by year) |
| POST | `/api/weeks` | Create a new week selection |
| GET | `/api/weeks/{id}` | Get week details with movies/albums |
| GET | `/api/weeks/current` | Get or create current week |
| PATCH | `/api/weeks/{id}` | Update week (notes, etc.) |
| DELETE | `/api/weeks/{id}` | Delete a week selection |

### Movies
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/movies/search` | Search TMDB for movies |
| GET | `/api/movies/{tmdb_id}` | Get movie details from TMDB |
| POST | `/api/weeks/{week_id}/movies` | Add movie to week |
| DELETE | `/api/weeks/{week_id}/movies/{position}` | Remove movie from week |

### Albums
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/albums/search` | Search MusicBrainz for albums |
| GET | `/api/albums/{musicbrainz_id}` | Get album details |
| POST | `/api/weeks/{week_id}/albums` | Add album to week |
| DELETE | `/api/weeks/{week_id}/albums/{position}` | Remove album from week |

### Analytics (Future)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats/overview` | Get selection statistics |
| GET | `/api/stats/by-year/{year}` | Get yearly breakdown |

---

## External API Integration

### TMDB API
- Base URL: `https://api.themoviedb.org/3`
- Auth: API key (Bearer token)
- Key endpoints:
  - `GET /search/movie` - Search movies
  - `GET /movie/{id}` - Get movie details
  - Image base URL: `https://image.tmdb.org/t/p/`

### MusicBrainz API
- Base URL: `https://musicbrainz.org/ws/2`
- Auth: None required (but User-Agent required)
- Format: JSON (`?fmt=json`)
- Key endpoints:
  - `GET /release?query={search}` - Search releases/albums
  - `GET /release/{mbid}` - Get release details
- Cover Art: `https://coverartarchive.org/release/{mbid}`
- Rate limit: 1 request/second (respect this!)

---

## Configuration

Environment variables (`.env`):
```
# App
SECRET_KEY=your-secret-key-here
DEBUG=false

# Database
DATABASE_URL=sqlite:///./wrong_opinions.db

# TMDB
TMDB_API_KEY=your-tmdb-api-key
TMDB_BASE_URL=https://api.themoviedb.org/3

# MusicBrainz (no key needed, but set user agent)
MUSICBRAINZ_USER_AGENT=WrongOpinions/1.0 (your-email@example.com)
```

---

## Implementation Phases

### Phase 1: Project Setup
- [x] **Step 1:** Initialize UV project with `pyproject.toml`
- [x] **Step 2:** Set up project structure (directories, `__init__.py` files)
- [x] **Step 3:** Configure FastAPI app with basic health check endpoint
- [x] **Step 4:** Set up Pydantic settings management
- [x] **Step 5:** Configure Ruff for linting/formatting
- [x] **Step 6:** Add basic pytest configuration

### Phase 2: Database Foundation
- [x] **Step 1:** Set up SQLAlchemy with async support
- [x] **Step 2:** Create all ORM models
- [x] **Step 3:** Configure Alembic for migrations
- [x] **Step 4:** Create initial migration
- [x] **Step 5:** Add database session dependency for FastAPI

### Phase 3: External API Clients
- [x] **Step 1:** Implement TMDB client service
  - [x] **Step 1a:** Movie search
  - [x] **Step 1b:** Movie details fetch
  - [x] **Step 1c:** Image URL generation
- [x] **Step 2:** Implement MusicBrainz client service
  - [x] **Step 2a:** Album/release search
  - [x] **Step 2b:** Album details fetch
  - [x] **Step 2c:** Cover art URL fetching
  - [x] **Step 2d:** Rate limiting (1 req/sec)

### Phase 4: Core API - Movies & Albums
- [x] **Step 1:** Create Pydantic schemas for movies/albums
- [x] **Step 2:** Implement movie search endpoint
- [x] **Step 3:** Implement movie details endpoint
- [x] **Step 4:** Implement album search endpoint
- [x] **Step 5:** Implement album details endpoint
- [x] **Step 6:** Add caching layer for external API responses

### Phase 5: Week Selections
- [x] **Step 1:** Create week-related Pydantic schemas
- [x] **Step 2:** Implement CRUD endpoints for weeks
- [ ] **Step 3:** Implement add/remove movie to week
- [ ] **Step 4:** Implement add/remove album to week
- [ ] **Step 5:** Add validation (1-2 movies, 1-2 albums per week)
- [ ] **Step 6:** Implement "current week" helper endpoint

### Phase 6: Authentication
- [ ] **Step 1:** Implement user registration
- [ ] **Step 2:** Implement password hashing (bcrypt or argon2)
- [ ] **Step 3:** Implement JWT token generation/validation
- [ ] **Step 4:** Add auth middleware/dependencies
- [ ] **Step 5:** Protect relevant endpoints

### Phase 7: Testing & Polish
- [ ] **Step 1:** Write unit tests for services
- [ ] **Step 2:** Write integration tests for API endpoints
- [ ] **Step 3:** Add request validation error handling
- [ ] **Step 4:** Add proper HTTP error responses
- [ ] **Step 5:** API documentation (FastAPI auto-generates OpenAPI)

### Phase 8: Future Enhancements (Optional)
- [ ] **Step 1:** Movie cast & crew data - Pull and store cast/crew from TMDB (`/movie/{id}/credits`)
  - [ ] **Step 1a:** Create `Person`, `MovieCast`, `MovieCrew` models
  - [ ] **Step 1b:** Store actor names, roles, profile images
  - [ ] **Step 1c:** Store director, writer, composer, etc.
- [ ] **Step 2:** Album artist details - Pull full artist info from MusicBrainz
  - [ ] **Step 2a:** Create `Artist` model with MusicBrainz artist ID
  - [ ] **Step 2b:** Store artist bio, origin, active years
  - [ ] **Step 2c:** Link albums to multiple artists (collaborations)
- [ ] **Step 3:** Statistics/analytics endpoints
- [ ] **Step 4:** Export functionality (CSV, JSON)
- [ ] **Step 5:** Multiple users viewing each other's selections
- [ ] **Step 6:** Rating/review system for selections
- [ ] **Step 7:** Recommendations based on history

---

## Development Commands

```bash
# Install dependencies
uv sync

# Run development server
uv run fastapi dev src/wrong_opinions/main.py

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Format code
uv run ruff format .

# Create migration
uv run alembic revision --autogenerate -m "description"

# Run migrations
uv run alembic upgrade head
```

---

## Notes & Decisions

### Why SQLite?
- Only 2 users expected
- Simple deployment (single file)
- No external database server needed
- Easy to backup (just copy the file)
- Can migrate to PostgreSQL later if needed

### Why cache external API data?
- Reduce API calls to TMDB/MusicBrainz
- Faster response times for repeated queries
- Works offline for previously fetched data
- Respects rate limits (especially MusicBrainz's 1 req/sec)

### Week numbering
- Using ISO week numbers (1-53)
- Week starts on Monday
- Consistent international standard
- Python's `datetime.isocalendar()` provides this

### Authentication approach
- JWT tokens (stateless, simple)
- For a 2-user app, could simplify further
- Can add OAuth later if needed
