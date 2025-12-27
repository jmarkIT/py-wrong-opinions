# CLAUDE.md - AI Assistant Guide

This document provides comprehensive guidance for AI assistants working on the Wrong Opinions backend codebase.

## Project Overview

**Wrong Opinions** is a Python backend API for a web application that tracks weekly movie and music selections. Users can:
- Search for movies via TMDB (The Movie Database) API
- Search for albums via MusicBrainz API
- Associate movies and albums with specific weeks
- Track their selections over time for future viewing and analysis

**Current Status**: Early development (Phase 2)
- Phase 1: Basic FastAPI setup, Pydantic settings - **COMPLETE**
- Phase 2: Database foundation with async SQLAlchemy - **IN PROGRESS**

**Target Users**: 2 users (small-scale personal project)

## Repository Structure

```
py-wrong-opinions/
├── src/wrong_opinions/          # Main application package
│   ├── __init__.py              # Package version
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic settings management
│   ├── database.py              # Async SQLAlchemy setup
│   ├── api/                     # API route handlers (empty, planned)
│   ├── models/                  # SQLAlchemy ORM models (empty, planned)
│   ├── schemas/                 # Pydantic request/response schemas (empty, planned)
│   ├── services/                # Business logic & external API clients (empty, planned)
│   └── utils/                   # Utility functions (empty, planned)
├── tests/                       # Test suite
│   ├── conftest.py              # Pytest fixtures (AsyncClient)
│   ├── test_api/                # API endpoint tests
│   ├── test_models/             # Model tests (empty)
│   └── test_services/           # Service tests (empty)
├── migrations/                  # Alembic database migrations
│   └── versions/                # Migration version files
├── pyproject.toml               # UV project configuration
├── uv.lock                      # Dependency lock file
├── .env.example                 # Environment variable template
├── .gitignore                   # Git ignore rules
├── ARCHITECTURE.md              # Detailed architecture plan
└── README.md                    # Basic project description
```

## Tech Stack

### Core Dependencies
- **Python 3.13+** - Required runtime version
- **UV** - Package manager (NOT pip/poetry/pipenv)
- **FastAPI 0.115+** - Web framework
- **Pydantic 2.10+** - Data validation and settings
- **SQLAlchemy 2.0+** - Async ORM
- **aiosqlite 0.20+** - SQLite async driver
- **Alembic 1.14+** - Database migrations
- **HTTPX 0.28+** - Async HTTP client for external APIs
- **Uvicorn 0.34+** - ASGI server

### Development Tools
- **Pytest 8.3+** - Testing framework (with pytest-asyncio)
- **Ruff 0.8+** - Linting and formatting (replaces black, isort, flake8)
- **pytest-cov 6.0+** - Coverage reporting

### Authentication (planned)
- **python-jose** - JWT token handling
- **passlib[bcrypt]** - Password hashing

## Development Setup

### Initial Setup
```bash
# Clone repository
git clone <repo-url>
cd py-wrong-opinions

# Install dependencies (UV will auto-create virtual environment)
uv sync

# Create .env file from template
cp .env.example .env
# Edit .env to add TMDB_API_KEY and other secrets
```

### Common Commands

```bash
# Run development server (with auto-reload)
uv run fastapi dev src/wrong_opinions/main.py

# Run tests
uv run pytest                    # All tests
uv run pytest tests/test_api/    # Specific directory
uv run pytest -v                 # Verbose output
uv run pytest --cov              # With coverage report

# Linting and formatting
uv run ruff check .              # Check for issues
uv run ruff check --fix .        # Auto-fix issues
uv run ruff format .             # Format code

# Database migrations (when Alembic is configured)
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
uv run alembic downgrade -1

# Add new dependency
uv add <package-name>
uv add --dev <package-name>      # Dev dependency
```

## Architecture Patterns

### Configuration Management
- **Pattern**: Pydantic Settings with `.env` file
- **Location**: `src/wrong_opinions/config.py`
- **Usage**: `settings = get_settings()` (cached singleton)
- **Example**:
  ```python
  from wrong_opinions.config import get_settings
  settings = get_settings()
  api_key = settings.tmdb_api_key
  ```

### Database Sessions
- **Pattern**: Async SQLAlchemy with dependency injection
- **Location**: `src/wrong_opinions/database.py`
- **Usage**: FastAPI `Depends(get_db)` for route handlers
- **Base Class**: `Base` from `wrong_opinions.database`
- **Example**:
  ```python
  from sqlalchemy.ext.asyncio import AsyncSession
  from wrong_opinions.database import get_db

  @app.get("/items")
  async def get_items(db: AsyncSession = Depends(get_db)):
      result = await db.execute(select(Item))
      return result.scalars().all()
  ```

### Testing
- **Pattern**: Async tests with pytest-asyncio
- **Fixture**: `client` fixture provides AsyncClient for API testing
- **Location**: Test fixtures in `tests/conftest.py`
- **Example**:
  ```python
  async def test_endpoint(client: AsyncClient) -> None:
      response = await client.get("/health")
      assert response.status_code == 200
  ```

### API Route Organization (planned)
- Routes grouped by resource in `src/wrong_opinions/api/`
- Main router aggregation in `api/router.py`
- Each route file exports a router: `router = APIRouter(prefix="/movies", tags=["movies"])`

### External API Clients (planned)
- Service classes in `src/wrong_opinions/services/`
- TMDB client: `services/tmdb.py`
- MusicBrainz client: `services/musicbrainz.py`
- Must respect rate limits (MusicBrainz: 1 req/sec)

## Code Conventions

### Python Style
- **Line length**: 100 characters (Ruff configured)
- **Type hints**: Required for function signatures
- **Async/await**: Use async throughout (FastAPI, SQLAlchemy, HTTPX)
- **Imports**: Auto-sorted by Ruff (isort-compatible)
  ```python
  # Standard library
  from datetime import datetime

  # Third-party
  from fastapi import FastAPI
  from sqlalchemy import select

  # Local
  from wrong_opinions.config import get_settings
  ```

### Naming Conventions
- **Files**: Snake case (`user_service.py`, `week_schema.py`)
- **Classes**: Pascal case (`User`, `WeekSelection`, `TMDBClient`)
- **Functions/variables**: Snake case (`get_current_week`, `api_key`)
- **Constants**: Upper snake case (`MAX_MOVIES_PER_WEEK = 2`)

### Docstrings
- Required for public functions and classes
- Format: Google-style or simple one-liner
- Example:
  ```python
  async def get_current_week(db: AsyncSession) -> Week:
      """Get or create the current ISO week selection."""
      ...
  ```

### Return Type Annotations
- Always specify return types for functions
- Use `None` for functions with no return value
- Use unions for optional returns: `User | None`
- Example: `async def health_check() -> dict[str, str]:`

## Database Conventions

### Models (when created)
- Inherit from `Base` class in `wrong_opinions.database`
- Use SQLAlchemy 2.0 style (mapped_column)
- File location: `src/wrong_opinions/models/<entity>.py`
- Timestamps: `created_at`, `updated_at` where applicable
- Example structure:
  ```python
  from sqlalchemy.orm import Mapped, mapped_column
  from wrong_opinions.database import Base

  class User(Base):
      __tablename__ = "users"

      id: Mapped[int] = mapped_column(primary_key=True)
      username: Mapped[str] = mapped_column(unique=True)
      created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
  ```

### Schemas (Pydantic)
- Separate from ORM models
- File location: `src/wrong_opinions/schemas/<entity>.py`
- Naming: `UserCreate`, `UserResponse`, `UserUpdate`
- Use Pydantic v2 features (`model_config`, `ConfigDict`)

## Testing Conventions

### Test Structure
- Mirror source structure in `tests/` directory
- File naming: `test_<module>.py`
- Test naming: `test_<functionality>` (descriptive)
- Use async test functions: `async def test_something(...)`

### Test Fixtures
- Shared fixtures in `tests/conftest.py`
- Available fixture: `client` (AsyncClient for API testing)
- Database fixtures (to be added): `db_session`, `test_db`

### Test Coverage
- Aim for high coverage on business logic
- Test both success and error cases
- Example:
  ```python
  async def test_endpoint_success(client: AsyncClient) -> None:
      response = await client.get("/endpoint")
      assert response.status_code == 200

  async def test_endpoint_not_found(client: AsyncClient) -> None:
      response = await client.get("/endpoint/999")
      assert response.status_code == 404
  ```

## Git Workflow

### Branch Naming
- Feature branches: `claude/<description>-<session-id>`
- Example: `claude/add-user-models-ABC123`
- **IMPORTANT**: Branches MUST start with `claude/` for CI/CD permissions

### Commit Messages
- Format: Clear, concise imperative mood
- Good: "Add user authentication endpoints"
- Good: "Fix database session handling in API routes"
- Bad: "Changes", "WIP", "Updates"

### Development Workflow
1. Create feature branch from main
2. Make changes and commit
3. Push to remote: `git push -u origin <branch-name>`
4. Create pull request
5. Merge after review

### Git Operations (retry logic)
- **Push failures**: Retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s)
- **Fetch/pull**: Same retry logic for network failures
- Always use: `git push -u origin <branch-name>`

## Environment Variables

Required in `.env` file:

```bash
# Application
SECRET_KEY=your-secret-key-here          # Change in production!
DEBUG=false                              # Set to true for development

# Database
DATABASE_URL=sqlite+aiosqlite:///./wrong_opinions.db  # Local SQLite file

# TMDB API
TMDB_API_KEY=<your-api-key>              # Required for movie search
TMDB_BASE_URL=https://api.themoviedb.org/3

# MusicBrainz
MUSICBRAINZ_USER_AGENT=WrongOpinions/1.0 (your-email@example.com)
```

## External API Integration

### TMDB (The Movie Database)
- **Authentication**: Bearer token (API key)
- **Base URL**: `https://api.themoviedb.org/3`
- **Key endpoints**:
  - `GET /search/movie?query={text}` - Search movies
  - `GET /movie/{id}` - Get movie details
- **Images**: `https://image.tmdb.org/t/p/{size}/{path}`
- **Rate limits**: Generous (40 requests per 10 seconds)

### MusicBrainz
- **Authentication**: None (User-Agent required in headers)
- **Base URL**: `https://musicbrainz.org/ws/2`
- **Format**: Add `?fmt=json` to all requests
- **Key endpoints**:
  - `GET /release?query={search}&fmt=json` - Search albums
  - `GET /release/{mbid}?fmt=json` - Get album details
- **Cover art**: `https://coverartarchive.org/release/{mbid}`
- **Rate limit**: **1 request per second** (MUST respect!)
- **Required header**: `User-Agent: WrongOpinions/1.0 (email@example.com)`

## Data Model Overview

See `ARCHITECTURE.md` for complete details. Key models (to be implemented):

### Core Entities
- **User**: Authentication and profile
- **Week**: Weekly selection period (ISO week number)
- **Movie**: Cached TMDB movie data
- **Album**: Cached MusicBrainz album data

### Associations
- **WeekMovie**: Links weeks to movies (max 2 per week)
- **WeekAlbum**: Links weeks to albums (max 2 per week)

### Important Constraints
- Users can have one selection per ISO week (unique constraint)
- Each week can have 1-2 movies (position 1 or 2)
- Each week can have 1-2 albums (position 1 or 2)
- External API data is cached in local database

## Common Tasks for AI Assistants

### Adding a New API Endpoint
1. Create Pydantic schemas in `schemas/`
2. Create route handler in `api/<resource>.py`
3. Add route to main router aggregation
4. Write tests in `tests/test_api/test_<resource>.py`
5. Update ARCHITECTURE.md if needed

### Adding a Database Model
1. Create model class in `models/<entity>.py`
2. Inherit from `Base` (from `wrong_opinions.database`)
3. Create Alembic migration: `uv run alembic revision --autogenerate -m "Add <entity> model"`
4. Review and apply migration: `uv run alembic upgrade head`
5. Create corresponding Pydantic schemas
6. Write model tests in `tests/test_models/`

### Adding an External API Service
1. Create service class in `services/<api_name>.py`
2. Use HTTPX AsyncClient for requests
3. Handle rate limiting (especially for MusicBrainz)
4. Implement error handling and retries
5. Add service configuration to `config.py` if needed
6. Write service tests with mocked responses

### Running Tests
```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_api/test_health.py

# With coverage
uv run pytest --cov --cov-report=html

# Watch mode (requires pytest-watch)
uv run pytest-watch
```

### Database Operations
```bash
# Create new migration after model changes
uv run alembic revision --autogenerate -m "Add user roles"

# Apply migrations
uv run alembic upgrade head

# Rollback last migration
uv run alembic downgrade -1

# View migration history
uv run alembic history
```

## Things to Avoid

### Package Management
- **DO NOT** use `pip install` - always use `uv add`
- **DO NOT** manually edit `requirements.txt` - let UV manage dependencies
- **DO NOT** commit `.env` file - only `.env.example`

### Code Style
- **DO NOT** use blocking I/O - always use async (HTTPX, not requests)
- **DO NOT** use `def` for route handlers - use `async def`
- **DO NOT** ignore Ruff warnings - fix them or explicitly ignore with `# noqa`
- **DO NOT** use bare `except:` - catch specific exceptions

### Database
- **DO NOT** use synchronous SQLAlchemy - this project uses async
- **DO NOT** commit `.db` files - they're in `.gitignore`
- **DO NOT** skip migrations - always create and apply them
- **DO NOT** use `session.commit()` directly - it's handled by `get_db` dependency

### Git
- **DO NOT** commit to main branch directly - use pull requests
- **DO NOT** commit sensitive data (API keys, secrets)
- **DO NOT** use branch names without `claude/` prefix

### Testing
- **DO NOT** skip writing tests for new features
- **DO NOT** use `sleep()` in tests - use proper async patterns
- **DO NOT** commit commented-out test code

## Key Files Reference

| File | Purpose | Key Points |
|------|---------|------------|
| `pyproject.toml` | Project config, dependencies | Python 3.13+, Ruff settings, pytest config |
| `src/wrong_opinions/main.py` | FastAPI app entry | Single health check endpoint currently |
| `src/wrong_opinions/config.py` | Settings management | Pydantic Settings, cached with `@lru_cache` |
| `src/wrong_opinions/database.py` | Database setup | Async engine, session factory, `get_db` dependency |
| `tests/conftest.py` | Test fixtures | `client` fixture for API testing |
| `ARCHITECTURE.md` | Detailed plan | Complete data models, endpoints, implementation phases |
| `.env.example` | Environment template | Copy to `.env` and fill in secrets |

## Current Implementation Status

### Completed (Phase 1 & 2)
- ✅ UV project setup with `pyproject.toml`
- ✅ Project structure (all directories created)
- ✅ FastAPI app with health check endpoint
- ✅ Pydantic settings management
- ✅ Ruff configuration for linting/formatting
- ✅ Pytest configuration with async support
- ✅ Async SQLAlchemy setup with session management

### In Progress (Phase 2)
- ⏳ ORM models creation
- ⏳ Alembic migration setup
- ⏳ Database session dependency integration

### Not Started
- ❌ External API clients (TMDB, MusicBrainz)
- ❌ API endpoints (beyond health check)
- ❌ Pydantic schemas for requests/responses
- ❌ Authentication system
- ❌ Comprehensive test coverage

## Version Information

- **Current Version**: 0.1.0
- **Python**: 3.13+
- **FastAPI**: 0.115+
- **SQLAlchemy**: 2.0+ (async)

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [TMDB API Documentation](https://developer.themoviedb.org/docs)
- [MusicBrainz API Documentation](https://musicbrainz.org/doc/MusicBrainz_API)
- [UV Documentation](https://docs.astral.sh/uv/)

## Notes for AI Assistants

1. **Always check ARCHITECTURE.md** for detailed implementation plans before making changes
2. **Run tests** after making changes: `uv run pytest`
3. **Format code** before committing: `uv run ruff format .`
4. **Use async/await consistently** - this is an async-first codebase
5. **Respect external API rate limits** - especially MusicBrainz (1 req/sec)
6. **Follow the established patterns** - review existing code before adding new features
7. **Write tests** for all new functionality
8. **Update documentation** if adding significant features or changing architecture

---

**Last Updated**: 2025-12-27
**For Questions**: Refer to ARCHITECTURE.md for detailed specifications
