"""
API Limits Configuration

Defines all free tier limits as constants. These are conservative values
to ensure we NEVER exceed free tier limits.

Based on official documentation and tested limits as of 2024-2025.
"""

from typing import Final


# =============================================================================
# SPOTIFY WEB API - FREE UNLIMITED
# =============================================================================
# Spotify API is completely free. Only rate limits apply.
# Rolling 30-second window, approximately 180 req/min tested

SPOTIFY_REQUESTS_PER_SECOND: Final[float] = 2.5  # 150 req/min (conservative)
SPOTIFY_BURST_CAPACITY: Final[int] = 10  # Allow small bursts
SPOTIFY_RETRY_AFTER_DEFAULT: Final[int] = 5  # Default retry delay


# =============================================================================
# HUGGINGFACE INFERENCE API - FREE TIER
# =============================================================================
# Official free tier: 300 req/hour, 1000 req/day
# We use conservative limits to stay well within free tier

HUGGINGFACE_REQUESTS_PER_HOUR: Final[int] = 250  # 83% of limit
HUGGINGFACE_REQUESTS_PER_DAY: Final[int] = 800  # 80% of limit
HUGGINGFACE_REQUESTS_PER_MINUTE: Final[int] = 4  # Smooth distribution
HUGGINGFACE_BURST_CAPACITY: Final[int] = 5  # Small bursts allowed

# Model endpoints (free, small models)
HUGGINGFACE_PRIMARY_MODEL: Final[str] = "facebook/opt-125m"
HUGGINGFACE_FALLBACK_MODEL: Final[str] = "gpt2"
HUGGINGFACE_API_URL: Final[str] = "https://api-inference.huggingface.co/models"


# =============================================================================
# OPENAI API - DISABLED (NO FREE TIER)
# =============================================================================
# OpenAI has NO free tier for API. All calls cost money.
# CRITICAL: Keep these disabled to guarantee $0 cost

OPENAI_ENABLED: Final[bool] = False  # NEVER enable without explicit user consent
OPENAI_DAILY_LIMIT: Final[int] = 0  # Zero calls allowed in free mode
OPENAI_WARNING_THRESHOLD: Final[int] = 0  # Warn immediately


# =============================================================================
# CIRCUIT BREAKER CONFIGURATION
# =============================================================================
# Netflix Hystrix-style circuit breaker settings

CIRCUIT_FAILURE_THRESHOLD: Final[int] = 5  # Failures before opening circuit
CIRCUIT_FAILURE_WINDOW_SECONDS: Final[int] = 60  # Window to count failures
CIRCUIT_RECOVERY_TIMEOUT_SECONDS: Final[int] = 30  # Time before half-open
CIRCUIT_HALF_OPEN_MAX_CALLS: Final[int] = 1  # Test calls in half-open state


# =============================================================================
# QUOTA MANAGEMENT
# =============================================================================
# Warning thresholds for usage alerts

QUOTA_WARNING_THRESHOLD: Final[float] = 0.75  # Warn at 75% usage
QUOTA_CRITICAL_THRESHOLD: Final[float] = 0.90  # Critical at 90% usage
QUOTA_RESET_HOUR_UTC: Final[int] = 0  # Reset daily quota at midnight UTC


# =============================================================================
# CACHE CONFIGURATION
# =============================================================================
# Response caching to reduce API calls

CACHE_TTL_SECONDS: Final[int] = 3600  # 1 hour cache
CACHE_MAX_SIZE: Final[int] = 1000  # Maximum cached items


# =============================================================================
# FREE MODE SETTINGS
# =============================================================================

class FreeModeConfig:
    """Configuration for free-only operation mode."""
    
    # API availability
    SPOTIFY_ENABLED: bool = True  # Always free
    HUGGINGFACE_ENABLED: bool = True  # Free tier available
    OPENAI_ENABLED: bool = False  # DISABLED - costs money
    
    # Fallback behavior
    USE_CACHE_FALLBACK: bool = True  # Use cached responses when rate limited
    USE_RULE_BASED_FALLBACK: bool = True  # Use rule-based logic as last resort
    
    # User notifications
    SHOW_USAGE_DASHBOARD: bool = True  # Display API usage in UI
    WARN_ON_HIGH_USAGE: bool = True  # Show warnings near limits
    
    @classmethod
    def get_enabled_apis(cls) -> list[str]:
        """Get list of enabled APIs."""
        apis = []
        if cls.SPOTIFY_ENABLED:
            apis.append("spotify")
        if cls.HUGGINGFACE_ENABLED:
            apis.append("huggingface")
        if cls.OPENAI_ENABLED:
            apis.append("openai")
        return apis
    
    @classmethod
    def is_paid_api_enabled(cls) -> bool:
        """Check if any paid API is enabled."""
        return cls.OPENAI_ENABLED


# =============================================================================
# RATE LIMIT PRESETS
# =============================================================================

RATE_LIMIT_PRESETS = {
    "spotify": {
        "rate": SPOTIFY_REQUESTS_PER_SECOND,
        "capacity": SPOTIFY_BURST_CAPACITY,
        "description": "Spotify Web API (free, rate limited only)",
    },
    "huggingface": {
        "rate": HUGGINGFACE_REQUESTS_PER_MINUTE / 60,  # Convert to per-second
        "capacity": HUGGINGFACE_BURST_CAPACITY,
        "description": "HuggingFace Inference API (free tier)",
    },
    "openai": {
        "rate": 0,  # Disabled
        "capacity": 0,
        "description": "OpenAI API (DISABLED - no free tier)",
    },
}


# =============================================================================
# COST ESTIMATES (for reference only - we don't use paid APIs)
# =============================================================================

COST_ESTIMATES = {
    "openai_gpt35_input": 0.0005,  # $ per 1K tokens
    "openai_gpt35_output": 0.0015,  # $ per 1K tokens
    "openai_gpt4_input": 0.01,  # $ per 1K tokens
    "openai_gpt4_output": 0.03,  # $ per 1K tokens
    "huggingface_compute": 0.00012,  # $ per second (after free tier)
}
