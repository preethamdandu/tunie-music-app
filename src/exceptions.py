"""
TuneGenie Custom Exceptions

Centralized exception hierarchy for consistent error handling across the application.
Each exception type provides context for debugging and appropriate error responses.
"""

from __future__ import annotations

from typing import Any


class TuneGenieError(Exception):
    """
    Base exception for all TuneGenie errors.
    
    All custom exceptions should inherit from this class to enable
    catch-all error handling when needed.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ============================================================================
# Spotify API Exceptions
# ============================================================================

class SpotifyError(TuneGenieError):
    """Base exception for Spotify API related errors"""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(message, details)


class SpotifyAuthenticationError(SpotifyError):
    """
    Raised when Spotify authentication fails.
    
    This could be due to:
    - Invalid/expired access token
    - Invalid client credentials
    - User revoked application access
    """

    def __init__(self, message: str = "Spotify authentication failed", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


class SpotifyAuthorizationError(SpotifyError):
    """
    Raised when the user hasn't granted required permissions.
    
    The user needs to re-authorize with the correct scopes.
    """

    def __init__(self, message: str = "Insufficient Spotify permissions", **kwargs):
        super().__init__(message, status_code=403, **kwargs)


class SpotifyRateLimitError(SpotifyError):
    """
    Raised when Spotify API rate limit is exceeded.
    
    The `retry_after` attribute indicates how long to wait before retrying.
    """

    def __init__(
        self,
        message: str = "Spotify API rate limit exceeded",
        retry_after: int | None = None,
        **kwargs,
    ):
        super().__init__(message, status_code=429, retry_after=retry_after, **kwargs)


class SpotifyNotFoundError(SpotifyError):
    """
    Raised when a requested Spotify resource doesn't exist.
    
    Examples: track ID not found, playlist deleted, user doesn't exist.
    """

    def __init__(self, message: str = "Spotify resource not found", **kwargs):
        super().__init__(message, status_code=404, **kwargs)


class SpotifyAPIError(SpotifyError):
    """
    Generic Spotify API error for unhandled status codes.
    
    Used as a catch-all for server errors (5xx) or unexpected responses.
    """
    pass


# ============================================================================
# LLM/AI Exceptions
# ============================================================================

class LLMError(TuneGenieError):
    """Base exception for LLM/AI related errors"""
    pass


class LLMConnectionError(LLMError):
    """
    Raised when connection to LLM service fails.
    
    This could be network issues, service downtime, or invalid endpoints.
    """

    def __init__(self, message: str = "Failed to connect to LLM service", **kwargs):
        super().__init__(message, **kwargs)


class LLMAuthenticationError(LLMError):
    """
    Raised when LLM API authentication fails.
    
    Usually indicates invalid or expired API key.
    """

    def __init__(self, message: str = "LLM API authentication failed", **kwargs):
        super().__init__(message, **kwargs)


class LLMRateLimitError(LLMError):
    """
    Raised when LLM API rate limit is exceeded.
    """

    def __init__(
        self,
        message: str = "LLM API rate limit exceeded",
        retry_after: int | None = None,
        **kwargs,
    ):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class LLMResponseError(LLMError):
    """
    Raised when LLM response is invalid or cannot be parsed.
    
    This includes malformed JSON, unexpected response format, etc.
    """

    def __init__(self, message: str = "Invalid LLM response", **kwargs):
        super().__init__(message, **kwargs)


class LLMTimeoutError(LLMError):
    """
    Raised when LLM request times out.
    """

    def __init__(self, message: str = "LLM request timed out", **kwargs):
        super().__init__(message, **kwargs)


# ============================================================================
# Recommendation Exceptions
# ============================================================================

class RecommendationError(TuneGenieError):
    """Base exception for recommendation engine errors"""
    pass


class ModelNotTrainedError(RecommendationError):
    """
    Raised when trying to get recommendations from an untrained model.
    """

    def __init__(self, message: str = "Recommendation model not trained", **kwargs):
        super().__init__(message, **kwargs)


class InsufficientDataError(RecommendationError):
    """
    Raised when there isn't enough data to generate recommendations.
    
    This could be a new user with no listening history (cold start problem).
    """

    def __init__(self, message: str = "Insufficient data for recommendations", **kwargs):
        super().__init__(message, **kwargs)


class ColdStartError(RecommendationError):
    """
    Raised when cold-start fallback also fails.
    """

    def __init__(self, message: str = "Cold-start recommendations failed", **kwargs):
        super().__init__(message, **kwargs)


# ============================================================================
# Workflow Exceptions
# ============================================================================

class WorkflowError(TuneGenieError):
    """Base exception for workflow orchestration errors"""
    pass


class WorkflowNotReadyError(WorkflowError):
    """
    Raised when workflow is executed before agents are initialized.
    """

    def __init__(self, message: str = "Workflow not ready - agents not initialized", **kwargs):
        super().__init__(message, **kwargs)


class InvalidWorkflowTypeError(WorkflowError):
    """
    Raised when an unknown workflow type is requested.
    """

    def __init__(self, workflow_type: str, **kwargs):
        message = f"Unknown workflow type: {workflow_type}"
        super().__init__(message, details={"workflow_type": workflow_type}, **kwargs)


class WorkflowExecutionError(WorkflowError):
    """
    Raised when workflow execution fails.
    
    Wraps the underlying error with workflow context.
    """

    def __init__(
        self,
        message: str,
        workflow_type: str | None = None,
        step: str | None = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if workflow_type:
            details["workflow_type"] = workflow_type
        if step:
            details["step"] = step
        super().__init__(message, details=details, **kwargs)


# ============================================================================
# Data/Validation Exceptions
# ============================================================================

class ValidationError(TuneGenieError):
    """Base exception for data validation errors"""
    pass


class InvalidInputError(ValidationError):
    """
    Raised when user input fails validation.
    """

    def __init__(self, field: str, message: str, **kwargs):
        full_message = f"Invalid input for '{field}': {message}"
        super().__init__(full_message, details={"field": field}, **kwargs)


class DataNotFoundError(TuneGenieError):
    """
    Raised when requested data cannot be found.
    
    Examples: user data file missing, cached profile not found.
    """

    def __init__(self, message: str = "Requested data not found", **kwargs):
        super().__init__(message, **kwargs)


class DataCorruptionError(TuneGenieError):
    """
    Raised when stored data is corrupted or invalid.
    """

    def __init__(self, message: str = "Data corruption detected", **kwargs):
        super().__init__(message, **kwargs)


# ============================================================================
# Configuration Exceptions
# ============================================================================

class ConfigurationError(TuneGenieError):
    """
    Raised when application configuration is invalid or missing.
    """

    def __init__(self, message: str = "Configuration error", **kwargs):
        super().__init__(message, **kwargs)


class MissingCredentialsError(ConfigurationError):
    """
    Raised when required API credentials are missing.
    """

    def __init__(self, credential_name: str, **kwargs):
        message = f"Missing required credential: {credential_name}"
        super().__init__(message, details={"credential": credential_name}, **kwargs)
