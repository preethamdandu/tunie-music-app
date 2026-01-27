"""
Unit Tests for API Gateway

Tests central routing with circuit breakers, quotas, and fallbacks.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestResponseCache:
    """Tests for ResponseCache class."""
    
    def test_set_and_get(self):
        """Test basic cache operations."""
        from src.api_gateway import ResponseCache
        
        cache = ResponseCache(ttl_seconds=60)
        
        cache.set("key1", "value1")
        result = cache.get("key1")
        
        assert result == "value1"
    
    def test_get_returns_none_for_missing(self):
        """Test get returns None for missing keys."""
        from src.api_gateway import ResponseCache
        
        cache = ResponseCache()
        result = cache.get("nonexistent")
        
        assert result is None
    
    def test_lru_eviction(self):
        """Test LRU eviction when full."""
        from src.api_gateway import ResponseCache
        
        cache = ResponseCache(max_size=2)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
    
    def test_clear(self):
        """Test cache clear."""
        from src.api_gateway import ResponseCache
        
        cache = ResponseCache()
        cache.set("key1", "value1")
        cache.clear()
        
        assert cache.size == 0
        assert cache.get("key1") is None


class TestAPIResponse:
    """Tests for APIResponse dataclass."""
    
    def test_is_primary_property(self):
        """Test is_primary property."""
        from src.api_gateway import APIResponse, FallbackLevel
        
        primary = APIResponse(data="data", fallback_level=FallbackLevel.PRIMARY, latency_ms=100)
        assert primary.is_primary
        
        cache = APIResponse(data="data", fallback_level=FallbackLevel.CACHE, latency_ms=10)
        assert not cache.is_primary


class TestAPIGateway:
    """Tests for APIGateway class."""
    
    def test_call_with_cache_hit(self):
        """Test cache hit returns cached response."""
        from src.api_gateway import APIGateway, FallbackLevel
        
        gateway = APIGateway()
        gateway.cache.set("test_key", "cached_value")
        
        response = gateway.call_with_fallback(
            primary_fn=lambda: "api_value",
            cache_key="test_key",
        )
        
        assert response.data == "cached_value"
        assert response.fallback_level == FallbackLevel.CACHE
        assert response.cached
    
    def test_call_primary_success(self):
        """Test successful primary API call."""
        from src.api_gateway import APIGateway, FallbackLevel
        from src.circuit_breaker import CircuitBreaker
        from src.quota_manager import QuotaManager
        import tempfile
        from pathlib import Path
        
        gateway = APIGateway()
        
        # Create fresh circuit and quota for test
        circuit = CircuitBreaker("test_primary")
        with tempfile.TemporaryDirectory() as tmpdir:
            quota = QuotaManager("test", 100, 1000, Path(tmpdir) / "q.json")
            
            response = gateway.call_with_fallback(
                primary_fn=lambda: "success",
                cache_key="unique_key_123",
                circuit=circuit,
                quota=quota,
            )
            
            assert response.data == "success"
            assert response.fallback_level == FallbackLevel.PRIMARY
    
    def test_call_uses_fallback_when_quota_exceeded(self):
        """Test fallback is used when quota exceeded."""
        from src.api_gateway import APIGateway, FallbackLevel
        from src.circuit_breaker import CircuitBreaker
        from src.quota_manager import QuotaManager
        import tempfile
        from pathlib import Path
        
        gateway = APIGateway()
        gateway.cache.clear()
        
        circuit = CircuitBreaker("test_fallback")
        with tempfile.TemporaryDirectory() as tmpdir:
            quota = QuotaManager("test", 0, 0, Path(tmpdir) / "q.json")  # No quota
            
            response = gateway.call_with_fallback(
                primary_fn=lambda: "should_not_call",
                fallback_fn=lambda: "fallback_value",
                cache_key=None,
                circuit=circuit,
                quota=quota,
            )
            
            assert response.data == "fallback_value"
            assert response.fallback_level == FallbackLevel.RULE_BASED
    
    def test_stats_tracking(self):
        """Test gateway tracks statistics."""
        from src.api_gateway import APIGateway
        from src.circuit_breaker import CircuitBreaker
        from src.quota_manager import QuotaManager
        import tempfile
        from pathlib import Path
        
        gateway = APIGateway()
        
        circuit = CircuitBreaker("test_stats")
        with tempfile.TemporaryDirectory() as tmpdir:
            quota = QuotaManager("test", 100, 1000, Path(tmpdir) / "q.json")
            
            gateway.call_with_fallback(
                primary_fn=lambda: "ok",
                circuit=circuit,
                quota=quota,
            )
            
            stats = gateway.stats
            assert stats["primary_calls"] >= 1


class TestRuleBasedFallbacks:
    """Tests for rule-based fallback functions."""
    
    def test_mood_analysis_happy(self):
        """Test rule-based mood analysis for happy."""
        from src.api_gateway import generate_rule_based_mood_analysis
        
        result = generate_rule_based_mood_analysis("happy", "party")
        
        assert "happy" in result["mood_analysis"].lower()
        assert result["music_characteristics"]["energy"] > 0.7
        assert result["source"] == "rule_based"
    
    def test_mood_analysis_sad(self):
        """Test rule-based mood analysis for sad."""
        from src.api_gateway import generate_rule_based_mood_analysis
        
        result = generate_rule_based_mood_analysis("sad", "reflection")
        
        assert result["music_characteristics"]["energy"] < 0.5
        assert result["music_characteristics"]["valence"] < 0.5
    
    def test_mood_analysis_unknown_defaults_to_calm(self):
        """Test unknown mood defaults to calm."""
        from src.api_gateway import generate_rule_based_mood_analysis
        
        result = generate_rule_based_mood_analysis("xyzabc123", "unknown")
        
        # Should default to calm
        assert result["music_characteristics"]["energy"] < 0.4
    
    def test_playlist_name_generation(self):
        """Test rule-based playlist name generation."""
        from src.api_gateway import generate_rule_based_playlist_name
        
        name = generate_rule_based_playlist_name("chill", "studying")
        
        assert "Chill" in name
        assert "Studying" in name
