"""
Unit Tests for Circuit Breaker

Tests Netflix Hystrix-style circuit breaker implementation.
"""

import time
import pytest
from unittest.mock import MagicMock


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""
    
    def test_initial_state_is_closed(self):
        """Circuit should start in closed state."""
        from src.circuit_breaker import CircuitBreaker, CircuitState
        
        circuit = CircuitBreaker("test", failure_threshold=3)
        
        assert circuit.state == CircuitState.CLOSED
        assert circuit.is_closed
        assert not circuit.is_open
    
    def test_opens_after_failure_threshold(self):
        """Circuit should open after reaching failure threshold."""
        from src.circuit_breaker import CircuitBreaker, CircuitState
        
        circuit = CircuitBreaker("test", failure_threshold=3, failure_window=60)
        
        def failing_fn():
            raise Exception("API error")
        
        # Trigger failures
        for _ in range(3):
            try:
                circuit.call(failing_fn)
            except Exception:
                pass
        
        assert circuit.state == CircuitState.OPEN
        assert circuit.is_open
    
    def test_rejects_calls_when_open(self):
        """Circuit should reject calls when open."""
        from src.circuit_breaker import CircuitBreaker, CircuitBreakerError
        
        circuit = CircuitBreaker("test", failure_threshold=1)
        
        # Force open
        try:
            circuit.call(lambda: 1/0)
        except ZeroDivisionError:
            pass
        
        # Should reject
        with pytest.raises(CircuitBreakerError) as exc_info:
            circuit.call(lambda: "hello")
        
        assert "test" in exc_info.value.circuit_name
        assert exc_info.value.retry_after > 0
    
    def test_transitions_to_half_open_after_timeout(self):
        """Circuit should transition to half-open after recovery timeout."""
        from src.circuit_breaker import CircuitBreaker, CircuitState
        
        circuit = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        
        # Force open
        try:
            circuit.call(lambda: 1/0)
        except ZeroDivisionError:
            pass
        
        assert circuit.is_open
        
        # Wait for recovery
        time.sleep(0.15)
        
        # Access state triggers transition
        assert circuit.state == CircuitState.HALF_OPEN
    
    def test_closes_on_success_in_half_open(self):
        """Circuit should close on success in half-open state."""
        from src.circuit_breaker import CircuitBreaker, CircuitState
        
        circuit = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        
        # Force open
        try:
            circuit.call(lambda: 1/0)
        except ZeroDivisionError:
            pass
        
        # Wait for half-open
        time.sleep(0.15)
        
        # Successful call should close
        result = circuit.call(lambda: "success")
        
        assert result == "success"
        assert circuit.state == CircuitState.CLOSED
    
    def test_reopens_on_failure_in_half_open(self):
        """Circuit should reopen on failure in half-open state."""
        from src.circuit_breaker import CircuitBreaker, CircuitState
        
        circuit = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        
        # Force open
        try:
            circuit.call(lambda: 1/0)
        except ZeroDivisionError:
            pass
        
        # Wait for half-open
        time.sleep(0.15)
        
        # Failed call should reopen
        try:
            circuit.call(lambda: 1/0)
        except ZeroDivisionError:
            pass
        
        assert circuit.state == CircuitState.OPEN
    
    def test_stats_tracking(self):
        """Circuit should track call statistics."""
        from src.circuit_breaker import CircuitBreaker
        
        circuit = CircuitBreaker("test", failure_threshold=5)
        
        # Successful calls
        for _ in range(3):
            circuit.call(lambda: "ok")
        
        # Failed call
        try:
            circuit.call(lambda: 1/0)
        except ZeroDivisionError:
            pass
        
        stats = circuit.stats
        assert stats.total_calls == 4
        assert stats.successful_calls == 3
        assert stats.failed_calls == 1
    
    def test_decorator_protection(self):
        """Test @circuit.protect decorator."""
        from src.circuit_breaker import CircuitBreaker
        
        circuit = CircuitBreaker("test")
        
        @circuit.protect
        def my_function():
            return 42
        
        result = my_function()
        assert result == 42
    
    def test_reset_clears_state(self):
        """Manual reset should clear circuit state."""
        from src.circuit_breaker import CircuitBreaker, CircuitState
        
        circuit = CircuitBreaker("test", failure_threshold=1)
        
        # Force open
        try:
            circuit.call(lambda: 1/0)
        except ZeroDivisionError:
            pass
        
        assert circuit.is_open
        
        circuit.reset()
        
        assert circuit.state == CircuitState.CLOSED


class TestGlobalCircuits:
    """Tests for global circuit breaker functions."""
    
    def test_get_circuit_creates_new(self):
        """get_circuit should create new circuit if not exists."""
        from src.circuit_breaker import get_circuit
        
        circuit = get_circuit("unique_test_circuit")
        
        assert circuit is not None
        assert circuit.name == "unique_test_circuit"
    
    def test_get_circuit_returns_same_instance(self):
        """get_circuit should return same instance for same name."""
        from src.circuit_breaker import get_circuit
        
        circuit1 = get_circuit("same_circuit")
        circuit2 = get_circuit("same_circuit")
        
        assert circuit1 is circuit2
    
    def test_huggingface_circuit_preconfigured(self):
        """HuggingFace circuit should be preconfigured."""
        from src.circuit_breaker import huggingface_circuit
        
        assert huggingface_circuit.name == "huggingface"
        assert huggingface_circuit.is_closed
    
    def test_openai_circuit_is_open(self):
        """OpenAI circuit should be open (disabled)."""
        from src.circuit_breaker import _openai_circuit
        
        assert _openai_circuit.name == "openai"
        assert _openai_circuit.is_open  # Disabled
