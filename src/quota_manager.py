"""
Quota Manager

Enterprise-grade quota management for API rate limiting.
Tracks hourly and daily usage to ensure we stay within free tier limits.

Used by: Salesforce, HubSpot, enterprise SaaS platforms.
"""

import time
import threading
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

from src.api_limits import (
    HUGGINGFACE_REQUESTS_PER_HOUR,
    HUGGINGFACE_REQUESTS_PER_DAY,
    QUOTA_WARNING_THRESHOLD,
    QUOTA_CRITICAL_THRESHOLD,
)

logger = logging.getLogger(__name__)


class QuotaStatus(Enum):
    """Quota status levels."""
    OK = "ok"  # Under 75%
    WARNING = "warning"  # 75-90%
    CRITICAL = "critical"  # 90-100%
    EXCEEDED = "exceeded"  # 100%+


@dataclass
class QuotaUsage:
    """Current quota usage statistics."""
    api_name: str
    hourly_used: int = 0
    hourly_limit: int = 0
    daily_used: int = 0
    daily_limit: int = 0
    last_reset_hour: int = -1
    last_reset_day: int = -1
    
    @property
    def hourly_remaining(self) -> int:
        """Remaining hourly quota."""
        return max(0, self.hourly_limit - self.hourly_used)
    
    @property
    def daily_remaining(self) -> int:
        """Remaining daily quota."""
        return max(0, self.daily_limit - self.daily_used)
    
    @property
    def hourly_percentage(self) -> float:
        """Hourly usage percentage."""
        if self.hourly_limit == 0:
            return 0.0
        return min(1.0, self.hourly_used / self.hourly_limit)
    
    @property
    def daily_percentage(self) -> float:
        """Daily usage percentage."""
        if self.daily_limit == 0:
            return 0.0
        return min(1.0, self.daily_used / self.daily_limit)
    
    @property
    def status(self) -> QuotaStatus:
        """Get current quota status based on usage."""
        max_pct = max(self.hourly_percentage, self.daily_percentage)
        
        if max_pct >= 1.0:
            return QuotaStatus.EXCEEDED
        elif max_pct >= QUOTA_CRITICAL_THRESHOLD:
            return QuotaStatus.CRITICAL
        elif max_pct >= QUOTA_WARNING_THRESHOLD:
            return QuotaStatus.WARNING
        else:
            return QuotaStatus.OK
    
    @property
    def is_available(self) -> bool:
        """Check if quota is available for more requests."""
        return self.hourly_remaining > 0 and self.daily_remaining > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "api_name": self.api_name,
            "hourly_used": self.hourly_used,
            "hourly_limit": self.hourly_limit,
            "hourly_remaining": self.hourly_remaining,
            "hourly_percentage": round(self.hourly_percentage * 100, 1),
            "daily_used": self.daily_used,
            "daily_limit": self.daily_limit,
            "daily_remaining": self.daily_remaining,
            "daily_percentage": round(self.daily_percentage * 100, 1),
            "status": self.status.value,
            "is_available": self.is_available,
        }


class QuotaExceededError(Exception):
    """Raised when API quota is exceeded."""
    
    def __init__(self, api_name: str, quota_type: str, usage: QuotaUsage):
        self.api_name = api_name
        self.quota_type = quota_type
        self.usage = usage
        super().__init__(
            f"{api_name} {quota_type} quota exceeded: "
            f"{usage.hourly_used}/{usage.hourly_limit} hourly, "
            f"{usage.daily_used}/{usage.daily_limit} daily"
        )


class QuotaManager:
    """
    Manages API usage quotas to stay within free tier limits.
    
    Features:
    - Hourly and daily quota tracking
    - Automatic reset at hour/day boundaries
    - Persistent storage to survive restarts
    - Thread-safe operations
    
    Example:
        quota = QuotaManager("huggingface", hourly_limit=250, daily_limit=800)
        
        if quota.can_consume():
            quota.consume()
            result = call_api()
        else:
            result = use_fallback()
    """
    
    def __init__(
        self,
        api_name: str,
        hourly_limit: int,
        daily_limit: int,
        persistence_path: Optional[Path] = None,
    ):
        """
        Initialize quota manager.
        
        Args:
            api_name: Name of the API (for logging and persistence)
            hourly_limit: Maximum requests per hour
            daily_limit: Maximum requests per day
            persistence_path: Path to persist quota state (optional)
        """
        self.api_name = api_name
        self.hourly_limit = hourly_limit
        self.daily_limit = daily_limit
        self.persistence_path = persistence_path or Path(f".quota_{api_name}.json")
        
        self._lock = threading.RLock()
        self._usage = QuotaUsage(
            api_name=api_name,
            hourly_limit=hourly_limit,
            daily_limit=daily_limit,
        )
        
        # Load persisted state
        self._load_state()
        
        # Check for resets
        self._check_resets()
        
        logger.info(
            f"QuotaManager '{api_name}' initialized: "
            f"{hourly_limit}/hr, {daily_limit}/day"
        )
    
    def _get_current_hour(self) -> int:
        """Get current hour (0-23) in UTC."""
        return datetime.now(timezone.utc).hour
    
    def _get_current_day(self) -> int:
        """Get current day of year (1-366) in UTC."""
        return datetime.now(timezone.utc).timetuple().tm_yday
    
    def _check_resets(self) -> None:
        """Check and perform quota resets if needed."""
        current_hour = self._get_current_hour()
        current_day = self._get_current_day()
        
        with self._lock:
            # Reset hourly quota
            if self._usage.last_reset_hour != current_hour:
                old_usage = self._usage.hourly_used
                self._usage.hourly_used = 0
                self._usage.last_reset_hour = current_hour
                if old_usage > 0:
                    logger.info(
                        f"QuotaManager '{self.api_name}': "
                        f"Hourly quota reset (was {old_usage})"
                    )
            
            # Reset daily quota
            if self._usage.last_reset_day != current_day:
                old_usage = self._usage.daily_used
                self._usage.daily_used = 0
                self._usage.last_reset_day = current_day
                if old_usage > 0:
                    logger.info(
                        f"QuotaManager '{self.api_name}': "
                        f"Daily quota reset (was {old_usage})"
                    )
        
        self._save_state()
    
    def _load_state(self) -> None:
        """Load persisted quota state."""
        try:
            if self.persistence_path.exists():
                with open(self.persistence_path, "r") as f:
                    data = json.load(f)
                
                self._usage.hourly_used = data.get("hourly_used", 0)
                self._usage.daily_used = data.get("daily_used", 0)
                self._usage.last_reset_hour = data.get("last_reset_hour", -1)
                self._usage.last_reset_day = data.get("last_reset_day", -1)
                
                logger.debug(f"QuotaManager '{self.api_name}': Loaded state from disk")
        except Exception as e:
            logger.warning(f"Failed to load quota state: {e}")
    
    def _save_state(self) -> None:
        """Persist quota state to disk."""
        try:
            data = {
                "hourly_used": self._usage.hourly_used,
                "daily_used": self._usage.daily_used,
                "last_reset_hour": self._usage.last_reset_hour,
                "last_reset_day": self._usage.last_reset_day,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.persistence_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save quota state: {e}")
    
    @property
    def usage(self) -> QuotaUsage:
        """Get current usage statistics."""
        self._check_resets()
        with self._lock:
            return self._usage
    
    def can_consume(self, count: int = 1) -> bool:
        """
        Check if quota is available for the requested count.
        
        Args:
            count: Number of tokens/requests to consume
            
        Returns:
            True if quota is available
        """
        self._check_resets()
        
        with self._lock:
            hourly_ok = (self._usage.hourly_used + count) <= self.hourly_limit
            daily_ok = (self._usage.daily_used + count) <= self.daily_limit
            return hourly_ok and daily_ok
    
    def consume(self, count: int = 1, force: bool = False) -> None:
        """
        Consume quota for API calls.
        
        Args:
            count: Number of tokens/requests to consume
            force: If True, consume even if over limit (for tracking)
            
        Raises:
            QuotaExceededError: If quota exceeded and force=False
        """
        self._check_resets()
        
        with self._lock:
            if not force and not self.can_consume(count):
                # Determine which quota is exceeded
                quota_type = "hourly" if self._usage.hourly_remaining < count else "daily"
                raise QuotaExceededError(self.api_name, quota_type, self._usage)
            
            self._usage.hourly_used += count
            self._usage.daily_used += count
            
            # Log warnings at thresholds
            if self._usage.status == QuotaStatus.CRITICAL:
                logger.warning(
                    f"QuotaManager '{self.api_name}': CRITICAL - "
                    f"{self._usage.hourly_used}/{self.hourly_limit} hourly, "
                    f"{self._usage.daily_used}/{self.daily_limit} daily"
                )
            elif self._usage.status == QuotaStatus.WARNING:
                logger.info(
                    f"QuotaManager '{self.api_name}': Warning - "
                    f"approaching limits"
                )
        
        self._save_state()
    
    def get_wait_time(self) -> float:
        """
        Get seconds until quota becomes available.
        
        Returns:
            Seconds to wait (0 if available now)
        """
        self._check_resets()
        
        with self._lock:
            if self.can_consume():
                return 0.0
            
            now = datetime.now(timezone.utc)
            
            # If hourly exceeded, wait until next hour
            if self._usage.hourly_remaining <= 0:
                minutes_to_next_hour = 60 - now.minute
                return minutes_to_next_hour * 60
            
            # If daily exceeded, wait until midnight UTC
            if self._usage.daily_remaining <= 0:
                hours_to_midnight = 24 - now.hour
                return hours_to_midnight * 3600
            
            return 0.0
    
    def reset(self) -> None:
        """Manually reset all quotas (for testing)."""
        with self._lock:
            self._usage.hourly_used = 0
            self._usage.daily_used = 0
            self._usage.last_reset_hour = self._get_current_hour()
            self._usage.last_reset_day = self._get_current_day()
        self._save_state()
        logger.info(f"QuotaManager '{self.api_name}': Manually reset")


# =============================================================================
# Pre-configured Quota Managers
# =============================================================================

_quota_managers: Dict[str, QuotaManager] = {}
_quota_lock = threading.Lock()


def get_quota_manager(
    api_name: str,
    hourly_limit: Optional[int] = None,
    daily_limit: Optional[int] = None,
) -> QuotaManager:
    """
    Get or create a quota manager for an API.
    
    Args:
        api_name: API name
        hourly_limit: Hourly limit (uses defaults if not specified)
        daily_limit: Daily limit (uses defaults if not specified)
        
    Returns:
        QuotaManager instance
    """
    with _quota_lock:
        if api_name not in _quota_managers:
            # Use defaults based on API name
            if api_name == "huggingface":
                hourly_limit = hourly_limit or HUGGINGFACE_REQUESTS_PER_HOUR
                daily_limit = daily_limit or HUGGINGFACE_REQUESTS_PER_DAY
            else:
                hourly_limit = hourly_limit or 1000
                daily_limit = daily_limit or 10000
            
            _quota_managers[api_name] = QuotaManager(
                api_name=api_name,
                hourly_limit=hourly_limit,
                daily_limit=daily_limit,
            )
        
        return _quota_managers[api_name]


def get_all_quotas() -> Dict[str, QuotaUsage]:
    """Get usage for all quota managers."""
    with _quota_lock:
        return {name: qm.usage for name, qm in _quota_managers.items()}


# Pre-initialize HuggingFace quota
huggingface_quota = get_quota_manager("huggingface")

# OpenAI quota - zero limit (disabled)
openai_quota = get_quota_manager("openai", hourly_limit=0, daily_limit=0)
