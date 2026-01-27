"""
Unit Tests for Rate Limiter

Tests for the Token Bucket rate limiting implementation.
"""

import time
import threading
import pytest


class TestTokenBucket:
    """Tests for TokenBucket rate limiter"""

    def test_initial_capacity(self):
        """Test bucket starts with full capacity"""
        from src.rate_limiter import TokenBucket
        
        bucket = TokenBucket(rate=1.0, capacity=10)
        
        assert bucket.available_tokens == 10

    def test_acquire_reduces_tokens(self):
        """Test that acquiring tokens reduces available count"""
        from src.rate_limiter import TokenBucket
        
        bucket = TokenBucket(rate=0.0, capacity=10)  # No refill for predictable test
        
        assert bucket.acquire(tokens=3) is True
        assert bucket.available_tokens == 7

    def test_acquire_fails_when_insufficient_tokens(self):
        """Test that acquire fails when not enough tokens"""
        from src.rate_limiter import TokenBucket
        
        bucket = TokenBucket(rate=1.0, capacity=5)
        
        # Drain the bucket
        bucket.acquire(tokens=5)
        
        # Should fail
        assert bucket.acquire(tokens=1, blocking=False) is False

    def test_tokens_refill_over_time(self):
        """Test that tokens refill at the correct rate"""
        from src.rate_limiter import TokenBucket
        
        bucket = TokenBucket(rate=10.0, capacity=10)  # 10 tokens/second
        
        # Drain the bucket
        bucket.acquire(tokens=10)
        
        # Wait 0.6 seconds, should have ~6 tokens (allow margin for timing)
        time.sleep(0.6)
        
        available = bucket.available_tokens
        assert 4 <= available <= 8  # Allow wider timing tolerance

    def test_tokens_dont_exceed_capacity(self):
        """Test that tokens don't exceed capacity"""
        from src.rate_limiter import TokenBucket
        
        bucket = TokenBucket(rate=100.0, capacity=10)  # Fast refill
        
        # Wait for refill
        time.sleep(0.2)
        
        assert bucket.available_tokens <= 10

    def test_wait_time_calculation(self):
        """Test wait_time returns correct duration"""
        from src.rate_limiter import TokenBucket
        
        bucket = TokenBucket(rate=2.0, capacity=2)  # 2 tokens/second
        
        # Drain the bucket
        bucket.acquire(tokens=2)
        
        # Need 1 token, at 2/sec, should need ~0.5 seconds
        wait = bucket.wait_time(tokens=1)
        assert 0.4 <= wait <= 0.6

    def test_blocking_acquire(self):
        """Test blocking acquire waits for tokens"""
        from src.rate_limiter import TokenBucket
        
        bucket = TokenBucket(rate=10.0, capacity=1)  # 10 tokens/second
        
        # Drain the bucket
        bucket.acquire(tokens=1)
        
        start = time.time()
        result = bucket.acquire(tokens=1, blocking=True)
        elapsed = time.time() - start
        
        assert result is True
        assert elapsed >= 0.05  # Should have waited

    def test_stats_tracking(self):
        """Test that statistics are tracked correctly"""
        from src.rate_limiter import TokenBucket
        
        bucket = TokenBucket(rate=1.0, capacity=2)
        
        # Successful acquires
        bucket.acquire(tokens=1)
        bucket.acquire(tokens=1)
        
        # Failed acquire
        bucket.acquire(tokens=1, blocking=False)
        
        stats = bucket.stats
        assert stats.total_requests == 3
        assert stats.throttled_requests >= 1

    def test_thread_safety(self):
        """Test that bucket is thread-safe"""
        from src.rate_limiter import TokenBucket
        
        bucket = TokenBucket(rate=100.0, capacity=100)
        results = []
        
        def acquire_tokens():
            for _ in range(10):
                result = bucket.acquire(tokens=1)
                results.append(result)
        
        threads = [threading.Thread(target=acquire_tokens) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have 50 attempts, at least most should succeed
        assert len(results) == 50
        assert sum(results) >= 45  # Most should succeed


class TestRateLimiter:
    """Tests for the high-level RateLimiter class"""

    def test_get_bucket_creates_new_bucket(self):
        """Test getting a new bucket creates it"""
        from src.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        bucket = limiter.get_bucket("test_bucket")
        
        assert bucket is not None
        assert bucket.available_tokens > 0

    def test_get_bucket_returns_same_bucket(self):
        """Test getting same bucket name returns same instance"""
        from src.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        bucket1 = limiter.get_bucket("test_bucket")
        bucket2 = limiter.get_bucket("test_bucket")
        
        assert bucket1 is bucket2

    def test_acquire_through_limiter(self):
        """Test acquire method works through limiter"""
        from src.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        
        result = limiter.acquire("api_bucket", tokens=1, blocking=False)
        
        assert result is True

    def test_rate_limited_decorator(self):
        """Test the rate_limited decorator"""
        from src.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        call_count = 0
        
        @limiter.rate_limited("test_bucket")
        def rate_limited_function():
            nonlocal call_count
            call_count += 1
            return "result"
        
        result = rate_limited_function()
        
        assert result == "result"
        assert call_count == 1


class TestGlobalRateLimiter:
    """Tests for global rate limiter functions"""

    def test_get_rate_limiter_singleton(self):
        """Test that get_rate_limiter returns singleton"""
        from src.rate_limiter import get_rate_limiter
        
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        
        assert limiter1 is limiter2

    def test_rate_limited_global_decorator(self):
        """Test the global rate_limited decorator"""
        from src.rate_limiter import rate_limited
        
        @rate_limited("global_test")
        def my_function():
            return 42
        
        result = my_function()
        assert result == 42
