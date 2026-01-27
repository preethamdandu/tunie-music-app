"""
Unit Tests for Exceptions

Tests for the custom exception hierarchy.
"""

import pytest


class TestExceptionHierarchy:
    """Tests for exception class structure"""

    def test_tunegenie_error_base(self):
        """Test base TuneGenieError"""
        from src.exceptions import TuneGenieError
        
        error = TuneGenieError("Test error", details={"key": "value"})
        
        assert str(error) == "Test error | Details: {'key': 'value'}"
        assert error.message == "Test error"
        assert error.details == {"key": "value"}

    def test_spotify_error_with_status_code(self):
        """Test SpotifyError with status code"""
        from src.exceptions import SpotifyError
        
        error = SpotifyError("API failed", status_code=500)
        
        assert error.status_code == 500
        assert error.retry_after is None

    def test_spotify_rate_limit_error(self):
        """Test SpotifyRateLimitError"""
        from src.exceptions import SpotifyRateLimitError
        
        error = SpotifyRateLimitError(retry_after=30)
        
        assert error.status_code == 429
        assert error.retry_after == 30

    def test_spotify_authentication_error(self):
        """Test SpotifyAuthenticationError defaults"""
        from src.exceptions import SpotifyAuthenticationError
        
        error = SpotifyAuthenticationError()
        
        assert error.status_code == 401
        assert "authentication" in error.message.lower()

    def test_llm_timeout_error(self):
        """Test LLMTimeoutError"""
        from src.exceptions import LLMTimeoutError
        
        error = LLMTimeoutError("Request timed out after 30s")
        
        assert "timed out" in str(error)

    def test_model_not_trained_error(self):
        """Test ModelNotTrainedError"""
        from src.exceptions import ModelNotTrainedError
        
        error = ModelNotTrainedError()
        
        assert "not trained" in str(error).lower()

    def test_invalid_workflow_type_error(self):
        """Test InvalidWorkflowTypeError includes workflow type"""
        from src.exceptions import InvalidWorkflowTypeError
        
        error = InvalidWorkflowTypeError("unknown_workflow")
        
        assert "unknown_workflow" in str(error)
        assert error.details["workflow_type"] == "unknown_workflow"

    def test_workflow_execution_error_with_context(self):
        """Test WorkflowExecutionError with context"""
        from src.exceptions import WorkflowExecutionError
        
        error = WorkflowExecutionError(
            "Step failed",
            workflow_type="playlist_generation",
            step="fetch_tracks",
        )
        
        assert error.details["workflow_type"] == "playlist_generation"
        assert error.details["step"] == "fetch_tracks"

    def test_invalid_input_error(self):
        """Test InvalidInputError"""
        from src.exceptions import InvalidInputError
        
        error = InvalidInputError("playlist_size", "Must be between 1 and 250")
        
        assert "playlist_size" in str(error)
        assert error.details["field"] == "playlist_size"

    def test_missing_credentials_error(self):
        """Test MissingCredentialsError"""
        from src.exceptions import MissingCredentialsError
        
        error = MissingCredentialsError("OPENAI_API_KEY")
        
        assert "OPENAI_API_KEY" in str(error)
        assert error.details["credential"] == "OPENAI_API_KEY"


class TestExceptionInheritance:
    """Tests for exception inheritance chain"""

    def test_spotify_errors_inherit_from_tunegenie_error(self):
        """Test Spotify errors are TuneGenieErrors"""
        from src.exceptions import (
            TuneGenieError,
            SpotifyError,
            SpotifyAuthenticationError,
            SpotifyRateLimitError,
        )
        
        assert issubclass(SpotifyError, TuneGenieError)
        assert issubclass(SpotifyAuthenticationError, SpotifyError)
        assert issubclass(SpotifyRateLimitError, SpotifyError)

    def test_llm_errors_inherit_from_tunegenie_error(self):
        """Test LLM errors are TuneGenieErrors"""
        from src.exceptions import (
            TuneGenieError,
            LLMError,
            LLMConnectionError,
            LLMTimeoutError,
        )
        
        assert issubclass(LLMError, TuneGenieError)
        assert issubclass(LLMConnectionError, LLMError)
        assert issubclass(LLMTimeoutError, LLMError)

    def test_recommendation_errors_inherit_from_tunegenie_error(self):
        """Test Recommendation errors are TuneGenieErrors"""
        from src.exceptions import (
            TuneGenieError,
            RecommendationError,
            ModelNotTrainedError,
            ColdStartError,
        )
        
        assert issubclass(RecommendationError, TuneGenieError)
        assert issubclass(ModelNotTrainedError, RecommendationError)
        assert issubclass(ColdStartError, RecommendationError)

    def test_catch_all_tunegenie_errors(self):
        """Test that catching TuneGenieError catches all custom exceptions"""
        from src.exceptions import (
            TuneGenieError,
            SpotifyAuthenticationError,
            LLMTimeoutError,
            ModelNotTrainedError,
        )
        
        exceptions = [
            SpotifyAuthenticationError(),
            LLMTimeoutError(),
            ModelNotTrainedError(),
        ]
        
        for exc in exceptions:
            try:
                raise exc
            except TuneGenieError as e:
                # Should catch all
                assert isinstance(e, TuneGenieError)
