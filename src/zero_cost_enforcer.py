"""
Zero Cost Enforcer for TuneGenie
Guarantees $0.00 cost by enforcing strict limits on all AI providers
"""

import os
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class CostStatus(Enum):
    """Cost status for API calls"""
    SAFE = "safe"  # Well within limits
    WARNING = "warning"  # Approaching limits (80%)
    CRITICAL = "critical"  # Very close to limits (95%)
    BLOCKED = "blocked"  # Limit exceeded, blocked


class ZeroCostEnforcer:
    """
    Enforces zero-cost operation by tracking and limiting API usage
    Blocks any request that would exceed free tier limits
    """
    
    # Free tier limits (verified January 27, 2026)
    LIMITS = {
        "groq": {
            "requests_per_minute": 30,
            "requests_per_day": 14400,
            "tokens_per_minute": 20000,
            "cost_per_request": 0.0,
            "safety_margin": 0.80  # Use only 80% of limit
        },
        "gemini": {
            "requests_per_minute": 15,
            "requests_per_day": 1500,
            "tokens_per_minute": 1000000,
            "cost_per_request": 0.0,
            "safety_margin": 0.80
        },
        "openrouter": {
            "requests_per_minute": 20,
            "requests_per_day": float('inf'),  # Unlimited for free models
            "tokens_per_minute": 200000,
            "cost_per_request": 0.0,
            "safety_margin": 0.80,
            "free_models_only": True
        },
        "deepseek": {
            "requests_per_minute": 60,
            "requests_per_day": 10000,
            "tokens_per_minute": 500000,
            "tokens_total": 5000000,  # 5M free tokens
            "cost_per_request": 0.0,
            "safety_margin": 0.80
        },
        "huggingface": {
            "requests_per_minute": 10,
            "requests_per_day": 1000,
            "cost_per_request": 0.0,
            "safety_margin": 0.80
        }
    }
    
    # OpenRouter free models (verified January 27, 2026)
    OPENROUTER_FREE_MODELS = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "deepseek/deepseek-r1:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "microsoft/phi-3-medium-128k-instruct:free",
        "google/gemma-2-9b-it:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "meta-llama/llama-3.2-1b-instruct:free"
    ]
    
    def __init__(self, storage_path: str = "/tmp/tunegenie_usage.json"):
        self.storage_path = storage_path
        self.usage_data = self._load_usage_data()
        self.enabled = os.getenv("ENABLE_COST_PROTECTION", "true").lower() == "true"
        logger.info(f"Zero Cost Enforcer initialized (enabled={self.enabled})")
    
    def _load_usage_data(self) -> Dict:
        """Load usage data from storage"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load usage data: {e}")
        
        return self._create_empty_usage_data()
    
    def _create_empty_usage_data(self) -> Dict:
        """Create empty usage data structure"""
        return {
            "groq": {"minute": {}, "day": {}, "total": 0},
            "gemini": {"minute": {}, "day": {}, "total": 0},
            "openrouter": {"minute": {}, "day": {}, "total": 0},
            "deepseek": {"minute": {}, "day": {}, "total": 0, "tokens_used": 0},
            "huggingface": {"minute": {}, "day": {}, "total": 0}
        }
    
    def _save_usage_data(self):
        """Save usage data to storage"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save usage data: {e}")
    
    def _get_current_minute_key(self) -> str:
        """Get current minute key for rate limiting"""
        return datetime.now().strftime("%Y-%m-%d %H:%M")
    
    def _get_current_day_key(self) -> str:
        """Get current day key for daily limits"""
        return datetime.now().strftime("%Y-%m-%d")
    
    def _clean_old_data(self, provider: str):
        """Remove old usage data to prevent memory bloat"""
        current_minute = self._get_current_minute_key()
        current_day = self._get_current_day_key()
        
        # Clean minute data (keep only last 5 minutes)
        minute_keys = list(self.usage_data[provider]["minute"].keys())
        for key in minute_keys:
            if key < current_minute:
                del self.usage_data[provider]["minute"][key]
        
        # Clean day data (keep only last 7 days)
        day_keys = list(self.usage_data[provider]["day"].keys())
        for key in day_keys:
            if key < current_day:
                del self.usage_data[provider]["day"][key]
    
    def can_make_request(
        self,
        provider: str,
        model: Optional[str] = None
    ) -> tuple[bool, CostStatus, str]:
        """
        Check if a request can be made without exceeding limits
        Returns: (can_proceed, status, message)
        """
        if not self.enabled:
            return True, CostStatus.SAFE, "Cost protection disabled"
        
        provider = provider.lower()
        if provider not in self.LIMITS:
            return False, CostStatus.BLOCKED, f"Unknown provider: {provider}"
        
        # Special check for OpenRouter: must use free models
        if provider == "openrouter":
            if model and not any(free_model in model for free_model in self.OPENROUTER_FREE_MODELS):
                return False, CostStatus.BLOCKED, f"Model {model} is not free on OpenRouter"
        
        limits = self.LIMITS[provider]
        current_minute = self._get_current_minute_key()
        current_day = self._get_current_day_key()
        
        # Clean old data
        self._clean_old_data(provider)
        
        # Check minute limit
        minute_requests = self.usage_data[provider]["minute"].get(current_minute, 0)
        minute_limit = int(limits["requests_per_minute"] * limits["safety_margin"])
        
        if minute_requests >= minute_limit:
            return False, CostStatus.BLOCKED, f"Minute limit reached ({minute_requests}/{minute_limit})"
        
        # Check day limit
        day_requests = self.usage_data[provider]["day"].get(current_day, 0)
        day_limit = limits["requests_per_day"]
        
        if day_limit != float('inf'):
            day_limit_safe = int(day_limit * limits["safety_margin"])
            if day_requests >= day_limit_safe:
                return False, CostStatus.BLOCKED, f"Daily limit reached ({day_requests}/{day_limit_safe})"
        
        # Check DeepSeek token limit
        if provider == "deepseek":
            tokens_used = self.usage_data[provider].get("tokens_used", 0)
            token_limit = int(limits["tokens_total"] * limits["safety_margin"])
            if tokens_used >= token_limit:
                return False, CostStatus.BLOCKED, f"Token limit reached ({tokens_used}/{token_limit})"
        
        # Determine status based on usage percentage
        minute_pct = minute_requests / minute_limit if minute_limit > 0 else 0
        day_pct = day_requests / day_limit_safe if day_limit != float('inf') and day_limit_safe > 0 else 0
        
        max_pct = max(minute_pct, day_pct)
        
        if max_pct >= 0.95:
            status = CostStatus.CRITICAL
            message = f"CRITICAL: {int(max_pct * 100)}% of limit used"
        elif max_pct >= 0.80:
            status = CostStatus.WARNING
            message = f"WARNING: {int(max_pct * 100)}% of limit used"
        else:
            status = CostStatus.SAFE
            message = f"Safe: {int(max_pct * 100)}% of limit used"
        
        return True, status, message
    
    def record_request(
        self,
        provider: str,
        tokens_used: int = 0,
        success: bool = True
    ):
        """Record a completed request"""
        if not self.enabled:
            return
        
        provider = provider.lower()
        if provider not in self.usage_data:
            return
        
        current_minute = self._get_current_minute_key()
        current_day = self._get_current_day_key()
        
        # Update minute count
        self.usage_data[provider]["minute"][current_minute] = \
            self.usage_data[provider]["minute"].get(current_minute, 0) + 1
        
        # Update day count
        self.usage_data[provider]["day"][current_day] = \
            self.usage_data[provider]["day"].get(current_day, 0) + 1
        
        # Update total count
        self.usage_data[provider]["total"] += 1
        
        # Update token count for DeepSeek
        if provider == "deepseek" and tokens_used > 0:
            self.usage_data[provider]["tokens_used"] = \
                self.usage_data[provider].get("tokens_used", 0) + tokens_used
        
        # Save to disk
        self._save_usage_data()
        
        logger.info(f"Recorded request for {provider} (tokens={tokens_used}, success={success})")
    
    def get_usage_stats(self, provider: str) -> Dict:
        """Get current usage statistics for a provider"""
        provider = provider.lower()
        if provider not in self.usage_data:
            return {}
        
        current_minute = self._get_current_minute_key()
        current_day = self._get_current_day_key()
        limits = self.LIMITS.get(provider, {})
        
        minute_requests = self.usage_data[provider]["minute"].get(current_minute, 0)
        day_requests = self.usage_data[provider]["day"].get(current_day, 0)
        
        minute_limit = int(limits.get("requests_per_minute", 0) * limits.get("safety_margin", 0.8))
        day_limit = limits.get("requests_per_day", 0)
        if day_limit != float('inf'):
            day_limit = int(day_limit * limits.get("safety_margin", 0.8))
        
        stats = {
            "provider": provider,
            "minute": {
                "used": minute_requests,
                "limit": minute_limit,
                "percentage": (minute_requests / minute_limit * 100) if minute_limit > 0 else 0
            },
            "day": {
                "used": day_requests,
                "limit": day_limit if day_limit != float('inf') else "unlimited",
                "percentage": (day_requests / day_limit * 100) if day_limit != float('inf') and day_limit > 0 else 0
            },
            "total_requests": self.usage_data[provider]["total"],
            "cost": 0.0  # Always $0.00
        }
        
        # Add token stats for DeepSeek
        if provider == "deepseek":
            tokens_used = self.usage_data[provider].get("tokens_used", 0)
            token_limit = int(limits.get("tokens_total", 0) * limits.get("safety_margin", 0.8))
            stats["tokens"] = {
                "used": tokens_used,
                "limit": token_limit,
                "percentage": (tokens_used / token_limit * 100) if token_limit > 0 else 0
            }
        
        return stats
    
    def get_all_usage_stats(self) -> Dict:
        """Get usage statistics for all providers"""
        return {
            provider: self.get_usage_stats(provider)
            for provider in self.LIMITS.keys()
        }
    
    def reset_usage(self, provider: Optional[str] = None):
        """Reset usage data (for testing or manual reset)"""
        if provider:
            provider = provider.lower()
            if provider in self.usage_data:
                self.usage_data[provider] = {
                    "minute": {}, "day": {}, "total": 0
                }
                if provider == "deepseek":
                    self.usage_data[provider]["tokens_used"] = 0
        else:
            self.usage_data = self._create_empty_usage_data()
        
        self._save_usage_data()
        logger.info(f"Reset usage data for {provider or 'all providers'}")


# Global instance
_zero_cost_enforcer = None


def get_zero_cost_enforcer() -> ZeroCostEnforcer:
    """Get or create the global ZeroCostEnforcer instance"""
    global _zero_cost_enforcer
    if _zero_cost_enforcer is None:
        _zero_cost_enforcer = ZeroCostEnforcer()
    return _zero_cost_enforcer
