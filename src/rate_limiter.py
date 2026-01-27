"""
TuneGenie Rate Limiter

Proactive rate limiting using Token Bucket algorithm to prevent
hitting Spotify API rate limits. Works in conjunction with the
reactive retry handler for defense in depth.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from functools import wraps
from typing import Callable, TypeVar

from .constants import (
    SPOTIFY_RATE_LIMIT_REQUESTS_PER_SECOND,
    SPOTIFY_RATE_LIMIT_BURST_CAPACITY,
)
from .logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class RateLimitStats:
    """Statistics for rate limiter monitoring"""
    total_requests: int = 0
    throttled_requests: int = 0
    total_wait_time_seconds: float = 0.0

    @property
    def throttle_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.throttled_requests / self.total_requests


class TokenBucket:
    """
    Token Bucket rate limiter implementation.
    
    Allows bursting up to `capacity` requests, then enforces
    steady-state rate of `rate` requests per second.
    
    Thread-safe implementation using locks.
    
    Example:
        limiter = TokenBucket(rate=2.5, capacity=10)
        
        if limiter.acquire():
            make_api_call()
        else:
            # Would exceed rate limit
            wait_time = limiter.wait_time()
            time.sleep(wait_time)
            limiter.acquire()
            make_api_call()
    """

    def __init__(
        self,
        rate: float = SPOTIFY_RATE_LIMIT_REQUESTS_PER_SECOND,
        capacity: int = SPOTIFY_RATE_LIMIT_BURST_CAPACITY,
    ):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens (requests) added per second
            capacity: Maximum tokens that can be stored (burst capacity)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._stats = RateLimitStats()

    def _refill(self) -> None:
        """Add tokens based on elapsed time since last refill"""
        now = time.monotonic()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def acquire(self, tokens: int = 1, blocking: bool = False) -> bool:
        """
        Attempt to acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire (typically 1 per request)
            blocking: If True, wait until tokens are available
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        with self._lock:
            self._stats.total_requests += 1
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            if blocking:
                # Calculate wait time
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.rate
                self._stats.throttled_requests += 1
                self._stats.total_wait_time_seconds += wait_time

                logger.debug(
                    f"Rate limit: waiting {wait_time:.2f}s for {tokens} tokens",
                    extra_fields={"wait_time": wait_time, "tokens_needed": tokens_needed},
                )

                # Release lock while waiting
                self._lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self._lock.acquire()

                # Refill and acquire
                self._refill()
                self.tokens -= tokens
                return True

            self._stats.throttled_requests += 1
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """
        Calculate how long to wait before tokens are available.
        
        Returns:
            Wait time in seconds (0 if tokens are available now)
        """
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                return 0.0
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.rate

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens"""
        with self._lock:
            self._refill()
            return self.tokens

    @property
    def stats(self) -> RateLimitStats:
        """Get current rate limiting statistics"""
        return self._stats

    def reset_stats(self) -> None:
        """Reset statistics counters"""
        with self._lock:
            self._stats = RateLimitStats()


class RateLimiter:
    """
    High-level rate limiter for API clients.
    
    Provides decorator and context manager interfaces for easy integration.
    Supports multiple named buckets for different API endpoints.
    """

    def __init__(self):
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def get_bucket(
        self,
        name: str = "default",
        rate: float = SPOTIFY_RATE_LIMIT_REQUESTS_PER_SECOND,
        capacity: int = SPOTIFY_RATE_LIMIT_BURST_CAPACITY,
    ) -> TokenBucket:
        """
        Get or create a named token bucket.
        
        Args:
            name: Bucket identifier
            rate: Tokens per second
            capacity: Burst capacity
            
        Returns:
            TokenBucket instance
        """
        with self._lock:
            if name not in self._buckets:
                self._buckets[name] = TokenBucket(rate=rate, capacity=capacity)
            return self._buckets[name]

    def acquire(self, name: str = "default", tokens: int = 1, blocking: bool = True) -> bool:
        """
        Acquire tokens from a named bucket.
        
        Args:
            name: Bucket identifier
            tokens: Number of tokens to acquire
            blocking: Wait for tokens if not available
            
        Returns:
            True if acquired, False if non-blocking and unavailable
        """
        bucket = self.get_bucket(name)
        return bucket.acquire(tokens=tokens, blocking=blocking)

    def rate_limited(
        self,
        bucket_name: str = "default",
        tokens: int = 1,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        Decorator for rate-limited functions.
        
        Usage:
            @rate_limiter.rate_limited("spotify_api")
            def call_spotify_api():
                ...
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                self.acquire(bucket_name, tokens=tokens, blocking=True)
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def get_all_stats(self) -> dict[str, RateLimitStats]:
        """Get statistics for all buckets"""
        with self._lock:
            return {name: bucket.stats for name, bucket in self._buckets.items()}


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limited(
    bucket_name: str = "default",
    tokens: int = 1,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Convenience decorator using global rate limiter.
    
    Usage:
        @rate_limited("spotify")
        def get_user_tracks():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            limiter = get_rate_limiter()
            limiter.acquire(bucket_name, tokens=tokens, blocking=True)
            return func(*args, **kwargs)
        return wrapper
    return decorator
