"""
Unit Tests for Configuration Module

Tests the Pydantic settings and environment validation.
"""

import os
import pytest
from unittest.mock import patch


class TestSettings:
    """Tests for the Settings class and configuration management"""

    def test_settings_loads_from_environment(self, mock_env_vars):
        """Test that settings load from environment variables"""
        mock_env_vars(
            SPOTIFY_CLIENT_ID="test_id",
            SPOTIFY_CLIENT_SECRET="test_secret",
            SPOTIFY_REDIRECT_URI="http://localhost:8501/callback",
            OPENAI_API_KEY="test_openai_key",
        )
        
        # Clear cached settings
        from src.config import get_settings
        get_settings.cache_clear()
        
        settings = get_settings()
        
        assert settings.spotify.client_id == "test_id"
        assert settings.spotify.client_secret.get_secret_value() == "test_secret"
        assert settings.spotify.redirect_uri == "http://localhost:8501/callback"

    def test_settings_validation_missing_spotify_id(self, mock_env_vars):
        """Test validation catches missing Spotify client ID"""
        mock_env_vars(
            SPOTIFY_CLIENT_ID="",
            SPOTIFY_CLIENT_SECRET="test_secret",
            SPOTIFY_REDIRECT_URI="http://localhost:8501/callback",
            OPENAI_API_KEY="test_key",
        )
        
        from src.config import get_settings
        get_settings.cache_clear()
        
        settings = get_settings()
        missing = settings.validate_required()
        
        assert any("CLIENT_ID" in m for m in missing)

    def test_settings_validation_missing_llm_credentials(self, mock_env_vars):
        """Test validation catches missing LLM credentials"""
        mock_env_vars(
            SPOTIFY_CLIENT_ID="test_id",
            SPOTIFY_CLIENT_SECRET="test_secret",
            SPOTIFY_REDIRECT_URI="http://localhost:8501/callback",
            OPENAI_API_KEY="",
            HUGGINGFACE_TOKEN="",
        )
        
        from src.config import get_settings
        get_settings.cache_clear()
        
        settings = get_settings()
        missing = settings.validate_required()
        
        assert any("OPENAI" in m or "HUGGINGFACE" in m for m in missing)

    def test_settings_accepts_spotipy_prefix(self, mock_env_vars, monkeypatch):
        """Test that SPOTIPY_ prefixed variables are accepted"""
        # Clear the SPOTIFY_ vars to force fallback to SPOTIPY_ vars
        monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
        monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("SPOTIFY_REDIRECT_URI", raising=False)
        
        mock_env_vars(
            SPOTIPY_CLIENT_ID="spotipy_id",
            SPOTIPY_CLIENT_SECRET="spotipy_secret",
            SPOTIPY_REDIRECT_URI="http://localhost:8501/callback",
            OPENAI_API_KEY="test_key",
        )
        
        from src.config import get_settings
        get_settings.cache_clear()
        
        settings = get_settings()
        
        # Should fall back to SPOTIPY_ prefixed vars
        assert settings.spotify.client_id == "spotipy_id"

    def test_llm_settings_has_openai_property(self, mock_env_vars):
        """Test has_openai property"""
        mock_env_vars(
            SPOTIFY_CLIENT_ID="test_id",
            SPOTIFY_CLIENT_SECRET="test_secret",
            SPOTIFY_REDIRECT_URI="http://localhost:8501/callback",
            OPENAI_API_KEY="valid_key",
        )
        
        from src.config import get_settings
        get_settings.cache_clear()
        
        settings = get_settings()
        assert settings.llm.has_openai is True

    def test_llm_settings_has_huggingface_property(self, mock_env_vars):
        """Test has_huggingface property"""
        mock_env_vars(
            SPOTIFY_CLIENT_ID="test_id",
            SPOTIFY_CLIENT_SECRET="test_secret",
            SPOTIFY_REDIRECT_URI="http://localhost:8501/callback",
            HUGGINGFACE_TOKEN="valid_token",
        )
        
        from src.config import get_settings
        get_settings.cache_clear()
        
        settings = get_settings()
        assert settings.llm.has_huggingface is True

    def test_is_valid_returns_true_with_all_credentials(self, mock_env_vars):
        """Test is_valid returns True when all credentials present"""
        mock_env_vars(
            SPOTIFY_CLIENT_ID="test_id",
            SPOTIFY_CLIENT_SECRET="test_secret",
            SPOTIFY_REDIRECT_URI="http://localhost:8501/callback",
            OPENAI_API_KEY="valid_key",
        )
        
        from src.config import get_settings
        get_settings.cache_clear()
        
        settings = get_settings()
        assert settings.is_valid() is True


class TestValidateEnvironment:
    """Tests for the validate_environment function"""

    def test_validate_environment_raises_on_missing_vars(self, mock_env_vars):
        """Test that validate_environment raises SystemExit on missing vars"""
        mock_env_vars(
            SPOTIFY_CLIENT_ID="",
            SPOTIFY_CLIENT_SECRET="",
            SPOTIFY_REDIRECT_URI="",
            OPENAI_API_KEY="",
        )
        
        from src.config import get_settings, validate_environment
        get_settings.cache_clear()
        
        with pytest.raises(SystemExit) as exc_info:
            validate_environment()
        
        assert "Missing required environment variables" in str(exc_info.value)

    def test_validate_environment_succeeds_with_valid_vars(self, mock_env_vars):
        """Test that validate_environment passes with valid vars"""
        mock_env_vars(
            SPOTIFY_CLIENT_ID="test_id",
            SPOTIFY_CLIENT_SECRET="test_secret",
            SPOTIFY_REDIRECT_URI="http://localhost:8501/callback",
            OPENAI_API_KEY="valid_key",
        )
        
        from src.config import get_settings, validate_environment
        get_settings.cache_clear()
        
        # Should not raise
        validate_environment()
