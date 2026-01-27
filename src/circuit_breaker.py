"""
Circuit Breaker Pattern Implementation

Netflix Hystrix-style circuit breaker to prevent cascading failures
and protect against API quota exhaustion.

States:
- CLOSED: Normal operation, all requests pass through
- OPEN: Circuit tripped, all requests fail fast
- HALF_OPEN: Testing recovery, limited requests allowed

Used by: Netflix, Amazon, Microsoft, and other top tech companies.
"""

import time
import threading
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, TypeVar, Optional, Any
from functools import wraps

from src.api_limits import (
    CIRCUIT_FAILURE_THRESHOLD,
    CIRCUIT_FAILURE_WINDOW_SECONDS,
    CIRCUIT_RECOVERY_TIMEOUT_SECONDS,
    CIRCUIT_HALF_OPEN_MAX_CALLS,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking all requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitStats:
    """Statistics for circuit breaker monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    current_state: CircuitState = CircuitState.CLOSED
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    
    def __init__(self, circuit_name: str, retry_after: float):
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit '{circuit_name}' is OPEN. Retry after {retry_after:.1f}s"
        )


class CircuitBreaker:
    """
    Netflix Hystrix-style circuit breaker.
    
    Prevents cascading failures by failing fast when an API is having issues.
    
    Example:
        circuit = CircuitBreaker("huggingface_api")
        
        @circuit.protect
        def call_api():
            return requests.get("https://api.example.com")
        
        try:
            result = call_api()
        except CircuitBreakerError as e:
            # Circuit is open, use fallback
            result = fallback_response()
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = CIRCUIT_FAILURE_THRESHOLD,
        failure_window: float = CIRCUIT_FAILURE_WINDOW_SECONDS,
        recovery_timeout: float = CIRCUIT_RECOVERY_TIMEOUT_SECONDS,
        half_open_max_calls: int = CIRCUIT_HALF_OPEN_MAX_CALLS,
        excluded_exceptions: tuple = (),
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Identifier for this circuit
            failure_threshold: Number of failures before opening circuit
            failure_window: Time window (seconds) to count failures
            recovery_timeout: Time (seconds) before attempting recovery
            half_open_max_calls: Max calls allowed in half-open state
            excluded_exceptions: Exceptions that don't count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.failure_window = failure_window
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.excluded_exceptions = excluded_exceptions
        
        self._state = CircuitState.CLOSED
        self._failures: list[float] = []  # Timestamps of recent failures
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        self._half_open_calls: int = 0
        self._lock = threading.RLock()
        self._stats = CircuitStats()
        
        logger.info(f"Circuit breaker '{name}' initialized (threshold={failure_threshold})")
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            self._check_state_transition()
            return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN
    
    @property
    def stats(self) -> CircuitStats:
        """Get circuit statistics."""
        with self._lock:
            self._stats.current_state = self._state
            return self._stats
    
    def _check_state_transition(self) -> None:
        """Check and perform state transitions."""
        now = time.time()
        
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._opened_at and (now - self._opened_at) >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
        
        elif self._state == CircuitState.CLOSED:
            # Clean up old failures outside the window
            self._failures = [
                t for t in self._failures
                if (now - t) < self.failure_window
            ]
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._stats.state_changes += 1
        
        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            logger.warning(f"Circuit '{self.name}' OPENED after {len(self._failures)} failures")
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            logger.info(f"Circuit '{self.name}' entering HALF-OPEN state")
        elif new_state == CircuitState.CLOSED:
            self._failures.clear()
            self._opened_at = None
            logger.info(f"Circuit '{self.name}' CLOSED (recovered)")
        
        logger.debug(f"Circuit '{self.name}': {old_state.value} -> {new_state.value}")
    
    def _record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._stats.successful_calls += 1
            self._stats.last_success_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Success in half-open state -> close circuit
                self._transition_to(CircuitState.CLOSED)
    
    def _record_failure(self, exception: Exception) -> None:
        """Record a failed call."""
        with self._lock:
            now = time.time()
            self._failures.append(now)
            self._last_failure_time = now
            self._stats.failed_calls += 1
            self._stats.last_failure_time = now
            
            if self._state == CircuitState.HALF_OPEN:
                # Failure in half-open state -> reopen circuit
                self._transition_to(CircuitState.OPEN)
            
            elif self._state == CircuitState.CLOSED:
                # Check if we've hit the failure threshold
                recent_failures = len([
                    t for t in self._failures
                    if (now - t) < self.failure_window
                ])
                
                if recent_failures >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
    
    def _should_allow_request(self) -> bool:
        """Check if a request should be allowed."""
        with self._lock:
            self._check_state_transition()
            
            if self._state == CircuitState.CLOSED:
                return True
            
            elif self._state == CircuitState.OPEN:
                return False
            
            elif self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            
            return False
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Result of function call
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        with self._lock:
            self._stats.total_calls += 1
        
        if not self._should_allow_request():
            with self._lock:
                self._stats.rejected_calls += 1
                retry_after = self.recovery_timeout
                if self._opened_at:
                    elapsed = time.time() - self._opened_at
                    retry_after = max(0, self.recovery_timeout - elapsed)
            
            raise CircuitBreakerError(self.name, retry_after)
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        
        except self.excluded_exceptions:
            # Don't count excluded exceptions as failures
            self._record_success()
            raise
        
        except Exception as e:
            self._record_failure(e)
            raise
    
    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to protect a function with this circuit breaker.
        
        Example:
            @circuit.protect
            def api_call():
                return requests.get(url)
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def reset(self) -> None:
        """Manually reset the circuit to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failures.clear()
            self._opened_at = None
            self._half_open_calls = 0
            logger.info(f"Circuit '{self.name}' manually reset to CLOSED")


# =============================================================================
# Global Circuit Breakers
# =============================================================================

_circuits: dict[str, CircuitBreaker] = {}
_circuits_lock = threading.Lock()


def get_circuit(name: str, **kwargs) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.
    
    Args:
        name: Circuit breaker name
        **kwargs: Configuration options for new circuit
        
    Returns:
        CircuitBreaker instance
    """
    with _circuits_lock:
        if name not in _circuits:
            _circuits[name] = CircuitBreaker(name, **kwargs)
        return _circuits[name]


def get_all_circuits() -> dict[str, CircuitBreaker]:
    """Get all circuit breakers."""
    with _circuits_lock:
        return dict(_circuits)


# Pre-configured circuits for our APIs

# =============================================================================
# AI Provider Circuits (Multi-Provider Strategy 2026)
# =============================================================================

# Groq - Primary AI provider (fastest)
groq_circuit = get_circuit(
    "groq",
    failure_threshold=3,
    recovery_timeout=15,  # Groq is very reliable, quick recovery
)

# Google Gemini - Backup 1
gemini_circuit = get_circuit(
    "gemini",
    failure_threshold=3,
    recovery_timeout=20,
)

# OpenRouter - Backup 2
openrouter_circuit = get_circuit(
    "openrouter",
    failure_threshold=3,
    recovery_timeout=25,
)

# DeepSeek - Backup 3
deepseek_circuit = get_circuit(
    "deepseek",
    failure_threshold=3,
    recovery_timeout=30,
)

# HuggingFace - Backup 4 (last resort before rule-based)
huggingface_circuit = get_circuit(
    "huggingface",
    failure_threshold=3,  # Lower threshold for external API
    recovery_timeout=30,
)

# =============================================================================
# Other Service Circuits
# =============================================================================

spotify_circuit = get_circuit(
    "spotify",
    failure_threshold=5,
    recovery_timeout=10,  # Spotify usually recovers quickly
)

# OpenAI circuit - always open since disabled
_openai_circuit = get_circuit(
    "openai",
    failure_threshold=1,  # Trip immediately
    recovery_timeout=86400,  # 24 hours - effectively disabled
)
# Force OpenAI circuit open
_openai_circuit._state = CircuitState.OPEN
_openai_circuit._opened_at = time.time()


# =============================================================================
# Provider Circuit Registry
# =============================================================================

AI_PROVIDER_CIRCUITS = {
    "groq": groq_circuit,
    "gemini": gemini_circuit,
    "openrouter": openrouter_circuit,
    "deepseek": deepseek_circuit,
    "huggingface": huggingface_circuit,
    "openai": _openai_circuit,
}


def get_provider_circuit(provider_name: str) -> CircuitBreaker:
    """
    Get circuit breaker for a specific AI provider.
    
    Args:
        provider_name: Name of the provider (groq, gemini, etc.)
        
    Returns:
        CircuitBreaker for the provider
    """
    return AI_PROVIDER_CIRCUITS.get(provider_name, get_circuit(provider_name))


def get_healthy_providers() -> list[str]:
    """
    Get list of AI providers with closed (healthy) circuits.
    
    Returns:
        List of provider names that are currently healthy
    """
    healthy = []
    for name, circuit in AI_PROVIDER_CIRCUITS.items():
        if name != "openai" and circuit.is_closed:
            healthy.append(name)
    return healthy


def get_provider_circuit_stats() -> dict[str, dict]:
    """
    Get circuit breaker stats for all AI providers.
    
    Returns:
        Dict mapping provider name to circuit stats
    """
    return {
        name: {
            "state": circuit.state.value,
            "is_closed": circuit.is_closed,
            "failure_rate": circuit.stats.failure_rate,
            "total_calls": circuit.stats.total_calls,
            "rejected_calls": circuit.stats.rejected_calls,
        }
        for name, circuit in AI_PROVIDER_CIRCUITS.items()
    }


def circuit_protected(circuit_name: str):
    """
    Decorator to protect a function with a named circuit breaker.
    
    Example:
        @circuit_protected("huggingface")
        def call_huggingface():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        circuit = get_circuit(circuit_name)
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return circuit.call(func, *args, **kwargs)
        
        return wrapper
    
    return decorator
