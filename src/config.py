"""
TuneGenie Configuration Management

Centralized configuration using Pydantic Settings for type-safe,
validated configuration management with environment variable support.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SpotifySettings(BaseSettings):
    """Spotify API configuration"""

    model_config = SettingsConfigDict(
        env_prefix="SPOTIFY_",
        extra="ignore",
    )

    client_id: str = Field(
        default="",
        description="Spotify application client ID",
    )
    client_secret: SecretStr = Field(
        default=SecretStr(""),
        description="Spotify application client secret",
    )
    redirect_uri: str = Field(
        default="http://127.0.0.1:8501/callback",
        description="OAuth redirect URI",
    )

    @field_validator("client_id", "redirect_uri", mode="before")
    @classmethod
    def check_not_empty(cls, v: str, info) -> str:
        # Also check for SPOTIPY_ prefixed variables (spotipy library convention)
        import os
        if not v:
            alt_key = f"SPOTIPY_{info.field_name.upper()}"
            v = os.getenv(alt_key, "")
        return v

    @field_validator("client_secret", mode="before")
    @classmethod
    def check_secret_not_empty(cls, v) -> SecretStr:
        import os
        if isinstance(v, SecretStr):
            if not v.get_secret_value():
                alt = os.getenv("SPOTIPY_CLIENT_SECRET", "")
                return SecretStr(alt) if alt else v
            return v
        if not v:
            v = os.getenv("SPOTIPY_CLIENT_SECRET", "")
        return SecretStr(v) if isinstance(v, str) else v


class LLMSettings(BaseSettings):
    """LLM/AI configuration"""

    model_config = SettingsConfigDict(extra="ignore")

    openai_api_key: Optional[SecretStr] = Field(
        default=None,
        alias="OPENAI_API_KEY",
        description="OpenAI API key for GPT models",
    )
    huggingface_token: Optional[SecretStr] = Field(
        default=None,
        alias="HUGGINGFACE_TOKEN",
        description="HuggingFace API token for fallback models",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        alias="LLM_TEMPERATURE",
        description="LLM creativity/randomness (0.0-2.0)",
    )
    default_model: str = Field(
        default="gpt-3.5-turbo",
        alias="LLM_MODEL",
        description="Default OpenAI model to use",
    )

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value())

    @property
    def has_huggingface(self) -> bool:
        return bool(self.huggingface_token and self.huggingface_token.get_secret_value())

    @property
    def has_any_llm(self) -> bool:
        return self.has_openai or self.has_huggingface


class RecommenderSettings(BaseSettings):
    """Collaborative filtering configuration"""

    model_config = SettingsConfigDict(extra="ignore")

    algorithm: Literal["SVD", "KNN", "KNNWithMeans", "NMF"] = Field(
        default="SVD",
        alias="COLLABORATIVE_FILTERING_ALGORITHM",
        description="Algorithm for collaborative filtering",
    )
    n_recommendations: int = Field(
        default=20,
        ge=1,
        le=250,
        alias="RECOMMENDATION_COUNT",
        description="Default number of recommendations",
    )


class AppSettings(BaseSettings):
    """Application-level configuration"""

    model_config = SettingsConfigDict(extra="ignore")

    debug: bool = Field(
        default=False,
        alias="DEBUG",
        description="Enable debug mode",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level",
    )
    feature_flag_llm_driven: bool = Field(
        default=False,
        alias="FEATURE_FLAG_LLM_DRIVEN",
        description="Enable LLM-driven recommendation strategy",
    )


class SecuritySettings(BaseSettings):
    """Security and telemetry configuration"""

    model_config = SettingsConfigDict(
        env_prefix="TUNIE_",
        extra="ignore",
    )

    enforce_license: bool = Field(
        default=False,
        description="Require valid license to run",
    )
    license_key: Optional[SecretStr] = Field(
        default=None,
        description="License key for validation",
    )
    license_check_url: Optional[str] = Field(
        default=None,
        description="URL for license validation endpoint",
    )
    telemetry_optout: bool = Field(
        default=False,
        description="Opt out of telemetry",
    )
    telemetry_url: Optional[str] = Field(
        default=None,
        description="Telemetry endpoint URL",
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version",
    )


class DatabaseSettings(BaseSettings):
    """Database configuration"""

    model_config = SettingsConfigDict(extra="ignore")

    url: str = Field(
        default="sqlite:///./data/tunegenie.db",
        alias="DATABASE_URL",
        description="Database connection URL",
    )
    echo: bool = Field(
        default=False,
        alias="DATABASE_ECHO",
        description="Echo SQL queries (for debugging)",
    )
    pool_size: int = Field(
        default=5,
        alias="DATABASE_POOL_SIZE",
        description="Connection pool size",
    )


class Settings(BaseSettings):
    """Main settings container aggregating all configuration sections"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sub-configurations
    spotify: SpotifySettings = Field(default_factory=SpotifySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    recommender: RecommenderSettings = Field(default_factory=RecommenderSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    def validate_required(self) -> list[str]:
        """
        Validate that all required configuration is present.
        Returns a list of missing required fields.
        """
        missing = []

        # Check Spotify credentials
        if not self.spotify.client_id:
            missing.append("SPOTIFY_CLIENT_ID (or SPOTIPY_CLIENT_ID)")
        if not self.spotify.client_secret.get_secret_value():
            missing.append("SPOTIFY_CLIENT_SECRET (or SPOTIPY_CLIENT_SECRET)")
        if not self.spotify.redirect_uri:
            missing.append("SPOTIFY_REDIRECT_URI (or SPOTIPY_REDIRECT_URI)")

        # Check LLM credentials (at least one required)
        if not self.llm.has_any_llm:
            missing.append("OPENAI_API_KEY (or HUGGINGFACE_TOKEN for fallback)")

        return missing

    def is_valid(self) -> bool:
        """Check if configuration is valid for application startup"""
        return len(self.validate_required()) == 0


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once per process.
    This is safe because environment variables shouldn't change at runtime.
    
    Returns:
        Validated Settings instance
    """
    return Settings()


def validate_environment() -> None:
    """
    Validate that all required environment variables are set.
    Raises SystemExit with clear message if any are missing.
    
    This is the main entry point validation called at application startup.
    """
    settings = get_settings()
    missing = settings.validate_required()

    if missing:
        details = "\n - " + "\n - ".join(missing)
        raise SystemExit(
            f"Missing required environment variables. "
            f"Please set the following in your .env file:{details}"
        )
