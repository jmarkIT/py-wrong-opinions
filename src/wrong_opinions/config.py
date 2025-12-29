"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App settings
    app_name: str = "Wrong Opinions API"
    debug: bool = False
    secret_key: str  # Required, no default

    # Database
    database_url: str = "sqlite+aiosqlite:///./wrong_opinions.db"

    # TMDB API
    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"

    # MusicBrainz
    musicbrainz_base_url: str = "https://musicbrainz.org/ws/2"
    musicbrainz_user_agent: str = "WrongOpinions/1.0 (contact@example.com)"

    # JWT Authentication
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate that secret_key is secure."""
        if not v:
            raise ValueError("SECRET_KEY is required")

        # In production mode, ensure secret key is strong
        debug = info.data.get("debug", False)
        if not debug:
            if len(v) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production mode")
            if v in ("change-me-in-production", "secret", "password", "changeme"):
                raise ValueError("SECRET_KEY must not be a common weak value")

        return v

    def validate_runtime_config(self) -> list[str]:
        """Validate runtime configuration and return warnings."""
        warnings = []

        # Check TMDB API key
        if not self.tmdb_api_key:
            warnings.append("TMDB_API_KEY is not set - movie search will not work")

        # Check MusicBrainz user agent
        if "contact@example.com" in self.musicbrainz_user_agent:
            warnings.append(
                "MUSICBRAINZ_USER_AGENT contains example email - "
                "please update with your actual contact info"
            )

        # Warn about debug mode in production
        if self.debug:
            warnings.append("DEBUG mode is enabled - should be disabled in production")

        return warnings


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
