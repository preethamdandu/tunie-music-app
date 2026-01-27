"""
TuneGenie Constants

Centralized location for all magic numbers and configuration constants.
This eliminates hardcoded values scattered throughout the codebase.
"""

from typing import Final

# ============================================================================
# Spotify API Limits
# ============================================================================
SPOTIFY_MAX_TRACKS_PER_REQUEST: Final[int] = 50
SPOTIFY_MAX_ARTISTS_PER_REQUEST: Final[int] = 50
SPOTIFY_MAX_AUDIO_FEATURES_PER_REQUEST: Final[int] = 100
SPOTIFY_MAX_PLAYLIST_TRACKS_PER_REQUEST: Final[int] = 100
SPOTIFY_MAX_SEARCH_RESULTS: Final[int] = 50

# ============================================================================
# Rate Limiting
# ============================================================================
SPOTIFY_RATE_LIMIT_REQUESTS_PER_SECOND: Final[float] = 2.5
SPOTIFY_RATE_LIMIT_BURST_CAPACITY: Final[int] = 10
SPOTIFY_RETRY_MAX_ATTEMPTS: Final[int] = 3
SPOTIFY_RETRY_BASE_DELAY_SECONDS: Final[float] = 1.0

# ============================================================================
# Caching
# ============================================================================
CACHE_TTL_SECONDS: Final[int] = 900  # 15 minutes
CACHE_MAX_SIZE: Final[int] = 100
LRU_CACHE_MAX_SIZE: Final[int] = 128

# ============================================================================
# Collaborative Filtering
# ============================================================================
CF_DEFAULT_ALGORITHM: Final[str] = "SVD"
CF_SVD_N_FACTORS: Final[int] = 100
CF_SVD_N_EPOCHS: Final[int] = 20
CF_SVD_LEARNING_RATE: Final[float] = 0.005
CF_SVD_REGULARIZATION: Final[float] = 0.02
CF_KNN_K_NEIGHBORS: Final[int] = 40
CF_DEFAULT_N_RECOMMENDATIONS: Final[int] = 20
CF_RATING_SCALE_MIN: Final[float] = 1.0
CF_RATING_SCALE_MAX: Final[float] = 5.0

# ============================================================================
# LLM Configuration
# ============================================================================
LLM_DEFAULT_TEMPERATURE: Final[float] = 0.7
LLM_DEFAULT_MODEL: Final[str] = "gpt-3.5-turbo"
LLM_HUGGINGFACE_FALLBACK_MODEL: Final[str] = "facebook/opt-125m"
LLM_HUGGINGFACE_SIMPLE_FALLBACK: Final[str] = "gpt2"
LLM_REQUEST_TIMEOUT_SECONDS: Final[int] = 30

# ============================================================================
# Playlist Generation
# ============================================================================
PLAYLIST_MIN_TRACKS: Final[int] = 1
PLAYLIST_MAX_TRACKS: Final[int] = 250
PLAYLIST_DEFAULT_TRACKS: Final[int] = 20
PLAYLIST_KEYWORD_SEARCH_MULTIPLIER: Final[int] = 3

# ============================================================================
# User Data Processing
# ============================================================================
TOP_TRACK_BASE_RATING: Final[int] = 50
RECENTLY_PLAYED_RATING: Final[int] = 3
PLAYLIST_SAVED_RATING: Final[int] = 4
MAX_GENRES_IN_PROFILE: Final[int] = 5
MAX_ARTISTS_IN_CONTEXT: Final[int] = 3
MAX_THEMES_IN_PROFILE: Final[int] = 3

# ============================================================================
# Audio Feature Thresholds
# ============================================================================
class MoodProfiles:
    """Audio feature targets for different moods"""
    
    ENERGETIC = {
        "min_energy": 0.7,
        "min_danceability": 0.6,
        "min_tempo": 120,
    }
    
    CALM = {
        "max_energy": 0.4,
        "max_danceability": 0.5,
        "max_tempo": 100,
        "min_acousticness": 0.3,
    }
    
    HAPPY = {
        "min_energy": 0.5,
        "min_valence": 0.7,
        "min_danceability": 0.5,
        "min_tempo": 100,
    }
    
    SAD = {
        "max_energy": 0.4,
        "max_valence": 0.4,
        "max_tempo": 90,
        "min_acousticness": 0.2,
    }
    
    FOCUSED = {
        "max_energy": 0.6,
        "max_tempo": 110,
        "min_instrumentalness": 0.1,
        "max_speechiness": 0.3,
    }

# ============================================================================
# Progressive Relaxation (Niche Queries)
# ============================================================================
PROGRESSIVE_RELAXATION_STRICT_THRESHOLD: Final[float] = 0.8
PROGRESSIVE_RELAXATION_RELAXED_THRESHOLD: Final[float] = 0.6
PROGRESSIVE_RELAXATION_MIN_TRACKS: Final[int] = 10

# ============================================================================
# File Paths
# ============================================================================
DATA_DIRECTORY: Final[str] = "data"
MODELS_DIRECTORY: Final[str] = "models"
PROMPTS_DIRECTORY: Final[str] = "prompts"
USER_DATA_FILE: Final[str] = "user_data.json"
WORKFLOW_HISTORY_FILE: Final[str] = "workflow_history.json"
TASTE_PROFILES_FILE: Final[str] = "taste_profiles.json"

# ============================================================================
# Supported Languages
# ============================================================================
SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = (
    "Any Language",
    "English",
    "Spanish",
    "French",
    "German",
    "Italian",
    "Portuguese",
    "Japanese",
    "Korean",
    "Chinese",
    "Hindi",
    "Tamil",
    "Telugu",
    "Kannada",
    "Malayalam",
    "Bengali",
    "Punjabi",
    "Arabic",
    "Russian",
    "Turkish",
)

# ============================================================================
# Moods and Activities
# ============================================================================
SUPPORTED_MOODS: Final[tuple[str, ...]] = (
    "Happy",
    "Sad",
    "Energetic",
    "Calm",
    "Focused",
    "Romantic",
    "Melancholic",
    "Motivated",
    "Relaxed",
    "Nostalgic",
)

SUPPORTED_ACTIVITIES: Final[tuple[str, ...]] = (
    "Working",
    "Exercising",
    "Studying",
    "Commuting",
    "Cooking",
    "Relaxing",
    "Sleeping",
    "Partying",
    "Meditating",
    "Reading",
)

# ============================================================================
# Artist Normalization Map
# ============================================================================
ARTIST_NORMALIZATION: Final[dict[str, str]] = {
    "weekend": "The Weeknd",
    "weeknd": "The Weeknd",
    "the weekend": "The Weeknd",
    "the weeknd": "The Weeknd",
    "taylor swift": "Taylor Swift",
    "taylor": "Taylor Swift",
    "beatles": "The Beatles",
    "the beatles": "The Beatles",
    "led zeppelin": "Led Zeppelin",
    "pink floyd": "Pink Floyd",
    "eminem": "Eminem",
    "linkin park": "Linkin Park",
    "drake": "Drake",
    "kendrick": "Kendrick Lamar",
    "kendrick lamar": "Kendrick Lamar",
    "billie": "Billie Eilish",
    "billie eilish": "Billie Eilish",
    "ariana": "Ariana Grande",
    "ariana grande": "Ariana Grande",
    "ed sheeran": "Ed Sheeran",
    "dua lipa": "Dua Lipa",
    "post malone": "Post Malone",
}
