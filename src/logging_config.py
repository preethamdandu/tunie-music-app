"""
TuneGenie Structured Logging Configuration

Provides JSON-formatted structured logging with context propagation.
Supports request tracking, user identification, and performance metrics.
"""

import logging
import sys
import json
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any
from functools import wraps
import time

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
workflow_id_var: ContextVar[str] = ContextVar("workflow_id", default="")


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter that includes contextual information in every log entry.
    
    Output format:
    {
        "timestamp": "2024-01-27T14:30:00.000Z",
        "level": "INFO",
        "logger": "src.workflow",
        "message": "Starting playlist generation",
        "request_id": "abc123",
        "user_id": "user456",
        "module": "workflow",
        "function": "execute_workflow",
        "line": 150,
        "extra": {...}
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context variables
        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            log_entry["user_id"] = user_id

        workflow_id = workflow_id_var.get()
        if workflow_id:
            log_entry["workflow_id"] = workflow_id

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add any extra fields passed to the logger
        if hasattr(record, "extra_fields"):
            log_entry["extra"] = record.extra_fields

        return json.dumps(log_entry, default=str)


class PrettyFormatter(logging.Formatter):
    """
    Human-readable formatter for development/console output.
    
    Output format:
    2024-01-27 14:30:00 | INFO | workflow:execute_workflow:150 | Starting playlist generation [req=abc123]
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        color = self.COLORS.get(level, "")

        location = f"{record.module}:{record.funcName}:{record.lineno}"
        message = record.getMessage()

        # Build context string
        context_parts = []
        request_id = request_id_var.get()
        if request_id:
            context_parts.append(f"req={request_id[:8]}")
        user_id = user_id_var.get()
        if user_id:
            context_parts.append(f"user={user_id[:8]}")
        workflow_id = workflow_id_var.get()
        if workflow_id:
            context_parts.append(f"wf={workflow_id[:8]}")

        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""

        formatted = f"{timestamp} | {color}{level:8}{self.RESET} | {location:40} | {message}{context_str}"

        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


class ContextualLogger(logging.LoggerAdapter):
    """
    Logger adapter that automatically includes extra context fields.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Processing request", extra_fields={"track_count": 20})
    """

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        extra = kwargs.get("extra", {})
        extra_fields = kwargs.pop("extra_fields", None)

        if extra_fields:
            extra["extra_fields"] = extra_fields

        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str) -> ContextualLogger:
    """
    Get a contextual logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        ContextualLogger instance with structured output
    """
    logger = logging.getLogger(name)
    return ContextualLogger(logger, {})


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: str | None = None,
) -> None:
    """
    Configure application-wide logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Use JSON format (True for production, False for development)
        log_file: Optional file path for log output
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create formatter
    if json_output:
        formatter = StructuredFormatter()
    else:
        formatter = PrettyFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())  # Always JSON for files
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("spotipy").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)


# ============================================================================
# Context Management
# ============================================================================

def set_request_context(request_id: str) -> None:
    """Set the current request ID for log context"""
    request_id_var.set(request_id)


def set_user_context(user_id: str) -> None:
    """Set the current user ID for log context"""
    user_id_var.set(user_id)


def set_workflow_context(workflow_id: str) -> None:
    """Set the current workflow ID for log context"""
    workflow_id_var.set(workflow_id)


def clear_context() -> None:
    """Clear all context variables"""
    request_id_var.set("")
    user_id_var.set("")
    workflow_id_var.set("")


# ============================================================================
# Performance Logging Decorators
# ============================================================================

def log_execution_time(logger: logging.Logger | ContextualLogger | None = None):
    """
    Decorator that logs function execution time.
    
    Usage:
        @log_execution_time()
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)

            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start_time
                logger.info(
                    f"{func.__name__} completed",
                    extra_fields={"duration_seconds": round(duration, 3)},
                )
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                logger.error(
                    f"{func.__name__} failed",
                    extra_fields={
                        "duration_seconds": round(duration, 3),
                        "error": str(e),
                    },
                )
                raise

        return wrapper
    return decorator


def log_api_call(service: str, operation: str):
    """
    Decorator for logging external API calls with timing and status.
    
    Usage:
        @log_api_call("spotify", "get_top_tracks")
        def get_top_tracks():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.perf_counter()

            logger.debug(
                f"API call started: {service}.{operation}",
                extra_fields={"service": service, "operation": operation},
            )

            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start_time
                logger.info(
                    f"API call completed: {service}.{operation}",
                    extra_fields={
                        "service": service,
                        "operation": operation,
                        "duration_seconds": round(duration, 3),
                        "status": "success",
                    },
                )
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                logger.error(
                    f"API call failed: {service}.{operation}",
                    extra_fields={
                        "service": service,
                        "operation": operation,
                        "duration_seconds": round(duration, 3),
                        "status": "error",
                        "error": str(e),
                    },
                )
                raise

        return wrapper
    return decorator
