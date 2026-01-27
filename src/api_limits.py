"""
API Limits Configuration

Defines all free tier limits as constants. These are conservative values
to ensure we NEVER exceed free tier limits.

Based on official documentation and tested limits as of 2024-2026.

MULTI-PROVIDER STRATEGY (2026):
- Primary: Groq (fastest, free tier)
- Backup 1: Google Gemini Flash (1M context, free tier)
- Backup 2: OpenRouter (multiple free models)
- Backup 3: DeepSeek (5M free tokens on signup)
- Backup 4: HuggingFace (limited free tier)
- Fallback: Rule-based (no AI, always works)
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
# GROQ API - FREE TIER (PRIMARY - FASTEST)
# =============================================================================
# Groq LPU technology - industry-leading inference speed
# Free tier: 30 RPM, no credit card required
# Models: Llama 3.3 70B, DeepSeek R1, Whisper, etc.

GROQ_ENABLED: Final[bool] = True
GROQ_REQUESTS_PER_MINUTE: Final[int] = 25  # 83% of 30 RPM limit
GROQ_REQUESTS_PER_DAY: Final[int] = 14400  # ~10 RPM sustained
GROQ_BURST_CAPACITY: Final[int] = 5
GROQ_DEFAULT_MODEL: Final[str] = "llama-3.3-70b-versatile"
GROQ_API_URL: Final[str] = "https://api.groq.com/openai/v1"


# =============================================================================
# GOOGLE GEMINI API - FREE TIER (BACKUP 1)
# =============================================================================
# Google Gemini Flash - frontier-level performance
# Free tier: 15 RPM, 1000 RPD, 1M token context
# Note: Content IS used to improve Google products on free tier

GEMINI_ENABLED: Final[bool] = True
GEMINI_REQUESTS_PER_MINUTE: Final[int] = 12  # 80% of 15 RPM limit
GEMINI_REQUESTS_PER_DAY: Final[int] = 800  # 80% of 1000 RPD limit
GEMINI_BURST_CAPACITY: Final[int] = 3
GEMINI_DEFAULT_MODEL: Final[str] = "gemini-2.0-flash"
GEMINI_API_URL: Final[str] = "https://generativelanguage.googleapis.com/v1beta"


# =============================================================================
# OPENROUTER API - FREE TIER (BACKUP 2)
# =============================================================================
# OpenRouter - access to 400+ models, 18+ completely FREE
# Free models: Llama 3.3 70B, Gemini 2.0 Flash, DeepSeek R1, etc.
# No credit card required for free models

OPENROUTER_ENABLED: Final[bool] = True
OPENROUTER_REQUESTS_PER_MINUTE: Final[int] = 15
OPENROUTER_REQUESTS_PER_DAY: Final[int] = 200
OPENROUTER_BURST_CAPACITY: Final[int] = 3
OPENROUTER_DEFAULT_MODEL: Final[str] = "meta-llama/llama-3.3-70b-instruct:free"
OPENROUTER_API_URL: Final[str] = "https://openrouter.ai/api/v1"

# Free models available on OpenRouter
OPENROUTER_FREE_MODELS: Final[list] = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "deepseek/deepseek-r1:free",
    "qwen/qwen-2.5-72b-instruct:free",
]


# =============================================================================
# DEEPSEEK API - FREE TRIAL (BACKUP 3)
# =============================================================================
# DeepSeek V3 - 90% of GPT-5 quality at 1/50th cost
# Free trial: 5M tokens on signup, no credit card required
# Features: 128K context, automatic caching (90% cost reduction)

DEEPSEEK_ENABLED: Final[bool] = True
DEEPSEEK_REQUESTS_PER_MINUTE: Final[int] = 50  # 83% of 60 RPM
DEEPSEEK_REQUESTS_PER_DAY: Final[int] = 800
DEEPSEEK_BURST_CAPACITY: Final[int] = 5
DEEPSEEK_DEFAULT_MODEL: Final[str] = "deepseek-chat"
DEEPSEEK_API_URL: Final[str] = "https://api.deepseek.com/v1"


# =============================================================================
# HUGGINGFACE INFERENCE API - FREE TIER (BACKUP 4)
# =============================================================================
# Official free tier: $0.10/month credit (VERY LIMITED)
# Use as last resort before rule-based fallback

HUGGINGFACE_ENABLED: Final[bool] = True
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
    """Configuration for free-only operation mode.
    
    Multi-Provider Strategy (2026):
    - All providers below have FREE tiers
    - Priority order: Groq > Gemini > OpenRouter > DeepSeek > HuggingFace
    - Automatic fallback if one provider fails
    """
    
    # API availability - ALL FREE PROVIDERS
    SPOTIFY_ENABLED: bool = True  # Always free
    GROQ_ENABLED: bool = True  # FREE - fastest inference
    GEMINI_ENABLED: bool = True  # FREE - 1M context
    OPENROUTER_ENABLED: bool = True  # FREE - multiple models
    DEEPSEEK_ENABLED: bool = True  # FREE - 5M tokens trial
    HUGGINGFACE_ENABLED: bool = True  # FREE - limited tier
    OPENAI_ENABLED: bool = False  # DISABLED - costs money
    
    # Provider priority order (fastest/best first)
    PROVIDER_PRIORITY: list = [
        "groq",       # Fastest - LPU technology
        "gemini",     # Best context - 1M tokens
        "openrouter", # Most flexible - 400+ models
        "deepseek",   # Best value - 90% GPT-5 quality
        "huggingface", # Last resort - very limited
    ]
    
    # Fallback behavior
    USE_CACHE_FALLBACK: bool = True  # Use cached responses when rate limited
    USE_RULE_BASED_FALLBACK: bool = True  # Use rule-based logic as last resort
    USE_MULTI_PROVIDER_FALLBACK: bool = True  # Try multiple providers before giving up
    
    # User notifications
    SHOW_USAGE_DASHBOARD: bool = True  # Display API usage in UI
    WARN_ON_HIGH_USAGE: bool = True  # Show warnings near limits
    SHOW_PROVIDER_STATUS: bool = True  # Show which provider is being used
    
    @classmethod
    def get_enabled_apis(cls) -> list[str]:
        """Get list of enabled APIs."""
        apis = []
        if cls.SPOTIFY_ENABLED:
            apis.append("spotify")
        if cls.GROQ_ENABLED:
            apis.append("groq")
        if cls.GEMINI_ENABLED:
            apis.append("gemini")
        if cls.OPENROUTER_ENABLED:
            apis.append("openrouter")
        if cls.DEEPSEEK_ENABLED:
            apis.append("deepseek")
        if cls.HUGGINGFACE_ENABLED:
            apis.append("huggingface")
        if cls.OPENAI_ENABLED:
            apis.append("openai")
        return apis
    
    @classmethod
    def get_ai_providers(cls) -> list[str]:
        """Get list of enabled AI providers (excluding Spotify)."""
        return [api for api in cls.get_enabled_apis() if api != "spotify"]
    
    @classmethod
    def is_paid_api_enabled(cls) -> bool:
        """Check if any paid API is enabled."""
        return cls.OPENAI_ENABLED
    
    @classmethod
    def get_provider_priority(cls) -> list[str]:
        """Get provider priority order for fallback chain."""
        return [p for p in cls.PROVIDER_PRIORITY if p in cls.get_ai_providers()]


# =============================================================================
# RATE LIMIT PRESETS
# =============================================================================

RATE_LIMIT_PRESETS = {
    "spotify": {
        "rate": SPOTIFY_REQUESTS_PER_SECOND,
        "capacity": SPOTIFY_BURST_CAPACITY,
        "description": "Spotify Web API (free, rate limited only)",
    },
    "groq": {
        "rate": GROQ_REQUESTS_PER_MINUTE / 60,  # Convert to per-second
        "capacity": GROQ_BURST_CAPACITY,
        "description": "Groq LPU API (FREE - fastest inference)",
    },
    "gemini": {
        "rate": GEMINI_REQUESTS_PER_MINUTE / 60,
        "capacity": GEMINI_BURST_CAPACITY,
        "description": "Google Gemini API (FREE - 1M context)",
    },
    "openrouter": {
        "rate": OPENROUTER_REQUESTS_PER_MINUTE / 60,
        "capacity": OPENROUTER_BURST_CAPACITY,
        "description": "OpenRouter API (FREE - multiple models)",
    },
    "deepseek": {
        "rate": DEEPSEEK_REQUESTS_PER_MINUTE / 60,
        "capacity": DEEPSEEK_BURST_CAPACITY,
        "description": "DeepSeek API (FREE trial - 5M tokens)",
    },
    "huggingface": {
        "rate": HUGGINGFACE_REQUESTS_PER_MINUTE / 60,  # Convert to per-second
        "capacity": HUGGINGFACE_BURST_CAPACITY,
        "description": "HuggingFace Inference API (FREE - limited)",
    },
    "openai": {
        "rate": 0,  # Disabled
        "capacity": 0,
        "description": "OpenAI API (DISABLED - no free tier)",
    },
}


# =============================================================================
# COST ESTIMATES (for reference only - we use FREE tiers)
# =============================================================================

COST_ESTIMATES = {
    # OpenAI (DISABLED - no free tier)
    "openai_gpt35_input": 0.0005,  # $ per 1K tokens
    "openai_gpt35_output": 0.0015,  # $ per 1K tokens
    "openai_gpt4_input": 0.01,  # $ per 1K tokens
    "openai_gpt4_output": 0.03,  # $ per 1K tokens
    
    # Groq (FREE tier - we use this)
    "groq_free": 0.0,  # FREE
    "groq_paid_input": 0.05,  # $ per 1M tokens (if paid)
    "groq_paid_output": 0.08,  # $ per 1M tokens (if paid)
    
    # Gemini (FREE tier - we use this)
    "gemini_free": 0.0,  # FREE
    "gemini_paid_input": 0.075,  # $ per 1M tokens (if paid)
    "gemini_paid_output": 0.30,  # $ per 1M tokens (if paid)
    
    # OpenRouter (FREE models - we use these)
    "openrouter_free": 0.0,  # FREE models
    
    # DeepSeek (FREE trial - we use this)
    "deepseek_free_trial": 0.0,  # 5M tokens free
    "deepseek_input": 0.28,  # $ per 1M tokens (after trial)
    "deepseek_output": 0.42,  # $ per 1M tokens (after trial)
    
    # HuggingFace (FREE tier - limited)
    "huggingface_free": 0.0,  # $0.10/month credit
    "huggingface_compute": 0.00012,  # $ per second (after free tier)
}


# =============================================================================
# PROVIDER ENVIRONMENT VARIABLES
# =============================================================================

PROVIDER_ENV_VARS = {
    "groq": "GROQ_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "huggingface": "HUGGINGFACE_TOKEN",
    "openai": "OPENAI_API_KEY",
}
