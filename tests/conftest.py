"""
TuneGenie Test Configuration

Shared fixtures and configuration for pytest.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    os.environ.setdefault("SPOTIFY_CLIENT_ID", "test_client_id")
    os.environ.setdefault("SPOTIFY_CLIENT_SECRET", "test_client_secret")
    os.environ.setdefault("SPOTIFY_REDIRECT_URI", "http://localhost:8501/callback")
    os.environ.setdefault("OPENAI_API_KEY", "test_openai_key")
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    yield
    # Cleanup if needed


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to mock environment variables"""
    def _set_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, value)
    return _set_env


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_spotify_client():
    """Mock Spotify client for testing without API calls"""
    mock_client = MagicMock()
    
    # Mock user profile
    mock_client.get_user_profile.return_value = {
        "id": "test_user_123",
        "display_name": "Test User",
        "email": "test@example.com",
        "country": "US",
        "product": "premium",
        "images": [{"url": "https://example.com/profile.jpg"}],
    }
    
    # Mock top tracks
    mock_client.get_user_top_tracks.return_value = [
        {
            "id": "track_1",
            "name": "Test Track 1",
            "artists": [{"name": "Test Artist 1"}],
            "album": {"name": "Test Album", "images": [{"url": "https://example.com/album.jpg"}]},
            "popularity": 75,
            "uri": "spotify:track:track_1",
            "duration_ms": 200000,
            "explicit": False,
        },
        {
            "id": "track_2",
            "name": "Test Track 2",
            "artists": [{"name": "Test Artist 2"}],
            "album": {"name": "Test Album 2", "images": []},
            "popularity": 60,
            "uri": "spotify:track:track_2",
            "duration_ms": 180000,
            "explicit": True,
        },
    ]
    
    # Mock audio features
    mock_client.get_track_features.return_value = [
        {
            "id": "track_1",
            "energy": 0.8,
            "valence": 0.7,
            "danceability": 0.75,
            "acousticness": 0.2,
            "instrumentalness": 0.0,
            "speechiness": 0.1,
            "liveness": 0.15,
            "loudness": -5.0,
            "tempo": 120.0,
        },
    ]
    
    # Mock search
    mock_client.search_tracks.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "search_track_1",
                    "name": "Search Result 1",
                    "artists": [{"name": "Search Artist"}],
                    "album": {"name": "Search Album", "images": []},
                    "popularity": 50,
                    "uri": "spotify:track:search_track_1",
                }
            ]
        }
    }
    
    mock_client.is_authenticated = True
    
    return mock_client


@pytest.fixture
def mock_llm_agent():
    """Mock LLM agent for testing without API calls"""
    mock_agent = MagicMock()
    
    mock_agent.analyze_mood.return_value = {
        "mood": "happy",
        "confidence": 0.85,
        "keywords": ["upbeat", "energetic"],
    }
    
    mock_agent.generate_playlist_recommendations.return_value = """
Here are some great tracks for your mood:
1. "Happy" by Pharrell Williams
2. "Good Vibrations" by The Beach Boys
3. "Walking on Sunshine" by Katrina and the Waves
"""
    
    mock_agent.get_music_insights.return_value = "Based on your listening history, you prefer upbeat pop music with high energy levels."
    
    return mock_agent


@pytest.fixture
def mock_recommender():
    """Mock recommender for testing"""
    mock_rec = MagicMock()
    
    mock_rec.get_recommendations.return_value = [
        {"track_id": "rec_1", "score": 0.95},
        {"track_id": "rec_2", "score": 0.88},
        {"track_id": "rec_3", "score": 0.75},
    ]
    
    mock_rec.is_trained = True
    
    return mock_rec


# ============================================================================
# Data Fixtures
# ============================================================================

@pytest.fixture
def sample_track_data():
    """Sample track data dictionary"""
    return {
        "id": "test_track_123",
        "name": "Sample Track",
        "artists": [{"name": "Sample Artist"}],
        "album": {
            "name": "Sample Album",
            "release_date": "2024-01-15",
            "images": [{"url": "https://example.com/image.jpg"}],
        },
        "popularity": 70,
        "uri": "spotify:track:test_track_123",
        "preview_url": "https://example.com/preview.mp3",
        "duration_ms": 210000,
        "explicit": False,
    }


@pytest.fixture
def sample_audio_features():
    """Sample audio features dictionary"""
    return {
        "energy": 0.75,
        "valence": 0.65,
        "danceability": 0.70,
        "acousticness": 0.15,
        "instrumentalness": 0.05,
        "speechiness": 0.08,
        "liveness": 0.12,
        "loudness": -6.5,
        "tempo": 128.0,
    }


@pytest.fixture
def sample_user_profile():
    """Sample user profile dictionary"""
    return {
        "spotify_id": "user_123",
        "display_name": "Test User",
        "email": "test@example.com",
        "country": "US",
        "product": "premium",
    }


@pytest.fixture
def sample_taste_profile():
    """Sample taste profile dictionary"""
    return {
        "top_artists": ["Artist 1", "Artist 2", "Artist 3"],
        "top_genres": ["pop", "rock", "indie"],
        "preferred_energy": 0.7,
        "preferred_valence": 0.6,
        "confidence_score": 0.85,
    }


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def test_db():
    """In-memory database for testing"""
    from src.database import DatabaseManager, Base
    
    # Create in-memory database
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    db = DatabaseManager()
    db.create_tables()
    
    yield db
    
    # Cleanup
    db.drop_tables()


# ============================================================================
# Utility Functions
# ============================================================================

def assert_valid_track(track: dict) -> None:
    """Assert that a track dictionary has required fields"""
    assert "id" in track
    assert "name" in track
    assert track["id"], "Track ID should not be empty"
    assert track["name"], "Track name should not be empty"


def assert_valid_recommendation(rec: dict) -> None:
    """Assert that a recommendation has required fields"""
    assert "track" in rec or "track_id" in rec
    assert "score" in rec
    assert 0 <= rec["score"] <= 1, "Score should be between 0 and 1"
