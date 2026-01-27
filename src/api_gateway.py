"""
API Gateway

Central routing layer with fallback logic for all external API calls.
Implements graceful degradation pattern used by Uber, Lyft, and other major apps.

Fallback Chain:
1. Primary API (HuggingFace)
2. Cached responses
3. Rule-based responses (no AI)
"""

import time
import hashlib
import logging
from typing import Optional, Callable, TypeVar, Dict, Any
from functools import wraps
from dataclasses import dataclass
from enum import Enum

from src.api_limits import FreeModeConfig, CACHE_TTL_SECONDS, CACHE_MAX_SIZE
from src.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    huggingface_circuit,
    spotify_circuit,
)
from src.quota_manager import (
    QuotaManager,
    QuotaExceededError,
    huggingface_quota,
    get_all_quotas,
)
from src.rate_limiter import get_rate_limiter, RateLimiter

logger = logging.getLogger(__name__)

T = TypeVar("T")


class FallbackLevel(Enum):
    """Tracks which fallback level was used."""
    PRIMARY = "primary"  # HuggingFace API
    CACHE = "cache"  # Cached response
    RULE_BASED = "rule_based"  # Rule-based logic
    DEGRADED = "degraded"  # Minimal response


@dataclass
class APIResponse:
    """Wrapper for API responses with metadata."""
    data: Any
    fallback_level: FallbackLevel
    latency_ms: float
    cached: bool = False
    error: Optional[str] = None
    
    @property
    def is_primary(self) -> bool:
        return self.fallback_level == FallbackLevel.PRIMARY


class ResponseCache:
    """
    Simple LRU cache for API responses.
    
    Helps reduce API calls by caching similar requests.
    """
    
    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl_seconds: int = CACHE_TTL_SECONDS):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[Any, float]] = {}  # key -> (value, timestamp)
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return value
            else:
                # Expired
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        # LRU eviction
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        
        self._cache[key] = (value, time.time())
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
    
    @property
    def size(self) -> int:
        """Current cache size."""
        return len(self._cache)


# Global response cache
_response_cache = ResponseCache()


class APIGateway:
    """
    Central gateway for all external API calls.
    
    Features:
    - Circuit breaker protection
    - Quota enforcement
    - Rate limiting
    - Response caching
    - Graceful degradation
    
    Example:
        gateway = APIGateway()
        
        response = gateway.call_with_fallback(
            primary_fn=lambda: huggingface_api(prompt),
            fallback_fn=lambda: generate_rule_based(prompt),
            cache_key=f"hf_{prompt_hash}",
        )
    """
    
    def __init__(self):
        self.rate_limiter = get_rate_limiter()
        self.cache = _response_cache
        
        # Statistics
        self._stats = {
            "primary_calls": 0,
            "cache_hits": 0,
            "fallback_calls": 0,
            "failures": 0,
        }
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get gateway statistics."""
        return {
            **self._stats,
            "cache_size": self.cache.size,
            "quotas": {name: usage.to_dict() for name, usage in get_all_quotas().items()},
        }
    
    def call_with_fallback(
        self,
        primary_fn: Callable[[], T],
        fallback_fn: Optional[Callable[[], T]] = None,
        cache_key: Optional[str] = None,
        api_name: str = "huggingface",
        circuit: Optional[CircuitBreaker] = None,
        quota: Optional[QuotaManager] = None,
    ) -> APIResponse:
        """
        Call an API with full fallback chain.
        
        Args:
            primary_fn: Primary API call function
            fallback_fn: Fallback function if primary fails
            cache_key: Key for caching response
            api_name: Name of API for rate limiting
            circuit: Circuit breaker to use
            quota: Quota manager to use
            
        Returns:
            APIResponse with data and metadata
        """
        start_time = time.time()
        circuit = circuit or huggingface_circuit
        quota = quota or huggingface_quota
        
        # Level 1: Check cache first
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._stats["cache_hits"] += 1
                latency = (time.time() - start_time) * 1000
                logger.debug(f"Cache hit for key: {cache_key[:8]}...")
                return APIResponse(
                    data=cached,
                    fallback_level=FallbackLevel.CACHE,
                    latency_ms=latency,
                    cached=True,
                )
        
        # Level 2: Try primary API
        if circuit.is_closed and quota.can_consume():
            try:
                # Rate limit
                self.rate_limiter.acquire(api_name, blocking=True)
                
                # Consume quota
                quota.consume()
                
                # Make the call
                result = circuit.call(primary_fn)
                
                self._stats["primary_calls"] += 1
                latency = (time.time() - start_time) * 1000
                
                # Cache the result
                if cache_key:
                    self.cache.set(cache_key, result)
                
                return APIResponse(
                    data=result,
                    fallback_level=FallbackLevel.PRIMARY,
                    latency_ms=latency,
                )
                
            except CircuitBreakerError as e:
                logger.warning(f"Circuit breaker open: {e}")
                self._stats["failures"] += 1
                
            except QuotaExceededError as e:
                logger.warning(f"Quota exceeded: {e}")
                self._stats["failures"] += 1
                
            except Exception as e:
                logger.error(f"Primary API call failed: {e}")
                self._stats["failures"] += 1
        
        # Level 3: Use fallback function
        if fallback_fn:
            try:
                self._stats["fallback_calls"] += 1
                result = fallback_fn()
                latency = (time.time() - start_time) * 1000
                
                return APIResponse(
                    data=result,
                    fallback_level=FallbackLevel.RULE_BASED,
                    latency_ms=latency,
                )
                
            except Exception as e:
                logger.error(f"Fallback also failed: {e}")
        
        # Level 4: Return degraded response
        latency = (time.time() - start_time) * 1000
        return APIResponse(
            data=None,
            fallback_level=FallbackLevel.DEGRADED,
            latency_ms=latency,
            error="All API calls failed",
        )


# =============================================================================
# Convenience Functions
# =============================================================================

_gateway: Optional[APIGateway] = None


def get_api_gateway() -> APIGateway:
    """Get the global API gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = APIGateway()
    return _gateway


def call_huggingface_with_fallback(
    primary_fn: Callable[[], T],
    fallback_fn: Optional[Callable[[], T]] = None,
    cache_key: Optional[str] = None,
) -> APIResponse:
    """
    Convenience function for HuggingFace API calls.
    
    Example:
        response = call_huggingface_with_fallback(
            primary_fn=lambda: hf_api.complete(prompt),
            fallback_fn=lambda: simple_response(prompt),
            cache_key=f"complete_{hash(prompt)}",
        )
        
        if response.is_primary:
            print("Got AI response")
        else:
            print(f"Using {response.fallback_level.value}")
    """
    gateway = get_api_gateway()
    return gateway.call_with_fallback(
        primary_fn=primary_fn,
        fallback_fn=fallback_fn,
        cache_key=cache_key,
        api_name="huggingface",
        circuit=huggingface_circuit,
        quota=huggingface_quota,
    )


def with_api_protection(api_name: str = "huggingface"):
    """
    Decorator to add API protection to a function.
    
    Adds:
    - Rate limiting
    - Circuit breaker
    - Quota tracking
    
    Example:
        @with_api_protection("huggingface")
        def call_ai(prompt: str) -> str:
            return requests.post(API_URL, json={"prompt": prompt})
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            gateway = get_api_gateway()
            
            # Check quota first
            quota = huggingface_quota if api_name == "huggingface" else None
            if quota and not quota.can_consume():
                raise QuotaExceededError(api_name, "hourly/daily", quota.usage)
            
            # Rate limit
            gateway.rate_limiter.acquire(api_name, blocking=True)
            
            # Get circuit
            circuit = huggingface_circuit if api_name == "huggingface" else spotify_circuit
            
            try:
                if quota:
                    quota.consume()
                return circuit.call(func, *args, **kwargs)
            except Exception:
                raise
        
        return wrapper
    
    return decorator


# =============================================================================
# Rule-Based Fallbacks for Music Recommendations
# =============================================================================

def generate_rule_based_mood_analysis(mood: str, activity: str) -> Dict[str, Any]:
    """
    Rule-based mood analysis when AI is unavailable.
    
    Returns reasonable defaults based on common mood patterns.
    """
    mood_profiles = {
        "happy": {"energy": 0.8, "valence": 0.9, "tempo": 120, "genres": ["pop", "dance"]},
        "sad": {"energy": 0.3, "valence": 0.2, "tempo": 70, "genres": ["acoustic", "indie"]},
        "energetic": {"energy": 0.9, "valence": 0.7, "tempo": 140, "genres": ["electronic", "rock"]},
        "calm": {"energy": 0.2, "valence": 0.5, "tempo": 60, "genres": ["ambient", "classical"]},
        "focused": {"energy": 0.4, "valence": 0.5, "tempo": 90, "genres": ["lo-fi", "instrumental"]},
        "workout": {"energy": 0.95, "valence": 0.7, "tempo": 150, "genres": ["edm", "hip-hop"]},
    }
    
    # Default to calm if mood not recognized
    mood_lower = mood.lower()
    profile = None
    for key in mood_profiles:
        if key in mood_lower:
            profile = mood_profiles[key]
            break
    
    if profile is None:
        profile = mood_profiles["calm"]
    
    return {
        "mood_analysis": f"You seem to be in a {mood} mood.",
        "music_characteristics": profile,
        "source": "rule_based",
    }


def generate_rule_based_playlist_name(mood: str, activity: str) -> str:
    """Generate a simple playlist name without AI."""
    if activity:
        return f"{mood.title()} {activity.title()} Mix"
    return f"{mood.title()} Vibes"
