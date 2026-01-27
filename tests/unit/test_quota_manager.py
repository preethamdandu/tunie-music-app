"""
Unit Tests for Quota Manager

Tests enterprise-grade quota management.
"""

import time
import pytest
from pathlib import Path
from unittest.mock import patch


class TestQuotaUsage:
    """Tests for QuotaUsage dataclass."""
    
    def test_remaining_calculations(self):
        """Test remaining quota calculations."""
        from src.quota_manager import QuotaUsage
        
        usage = QuotaUsage(
            api_name="test",
            hourly_used=50,
            hourly_limit=100,
            daily_used=200,
            daily_limit=500,
        )
        
        assert usage.hourly_remaining == 50
        assert usage.daily_remaining == 300
    
    def test_percentage_calculations(self):
        """Test usage percentage calculations."""
        from src.quota_manager import QuotaUsage
        
        usage = QuotaUsage(
            api_name="test",
            hourly_used=75,
            hourly_limit=100,
            daily_used=400,
            daily_limit=500,
        )
        
        assert usage.hourly_percentage == 0.75
        assert usage.daily_percentage == 0.80
    
    def test_status_ok(self):
        """Test OK status when under threshold."""
        from src.quota_manager import QuotaUsage, QuotaStatus
        
        usage = QuotaUsage(
            api_name="test",
            hourly_used=50,
            hourly_limit=100,
            daily_used=300,
            daily_limit=500,
        )
        
        assert usage.status == QuotaStatus.OK
    
    def test_status_warning(self):
        """Test WARNING status at 75-90%."""
        from src.quota_manager import QuotaUsage, QuotaStatus
        
        usage = QuotaUsage(
            api_name="test",
            hourly_used=80,
            hourly_limit=100,
            daily_used=100,
            daily_limit=500,
        )
        
        assert usage.status == QuotaStatus.WARNING
    
    def test_status_critical(self):
        """Test CRITICAL status at 90-100%."""
        from src.quota_manager import QuotaUsage, QuotaStatus
        
        usage = QuotaUsage(
            api_name="test",
            hourly_used=95,
            hourly_limit=100,
            daily_used=100,
            daily_limit=500,
        )
        
        assert usage.status == QuotaStatus.CRITICAL
    
    def test_status_exceeded(self):
        """Test EXCEEDED status at 100%+."""
        from src.quota_manager import QuotaUsage, QuotaStatus
        
        usage = QuotaUsage(
            api_name="test",
            hourly_used=100,
            hourly_limit=100,
            daily_used=100,
            daily_limit=500,
        )
        
        assert usage.status == QuotaStatus.EXCEEDED
    
    def test_is_available(self):
        """Test availability check."""
        from src.quota_manager import QuotaUsage
        
        available = QuotaUsage(
            api_name="test",
            hourly_used=50,
            hourly_limit=100,
            daily_used=200,
            daily_limit=500,
        )
        assert available.is_available
        
        exhausted = QuotaUsage(
            api_name="test",
            hourly_used=100,
            hourly_limit=100,
            daily_used=200,
            daily_limit=500,
        )
        assert not exhausted.is_available


class TestQuotaManager:
    """Tests for QuotaManager class."""
    
    def test_initialization(self, tmp_path):
        """Test quota manager initializes correctly."""
        from src.quota_manager import QuotaManager
        
        qm = QuotaManager(
            "test",
            hourly_limit=100,
            daily_limit=500,
            persistence_path=tmp_path / "quota.json",
        )
        
        assert qm.api_name == "test"
        assert qm.hourly_limit == 100
        assert qm.daily_limit == 500
    
    def test_can_consume(self, tmp_path):
        """Test can_consume check."""
        from src.quota_manager import QuotaManager
        
        qm = QuotaManager(
            "test",
            hourly_limit=10,
            daily_limit=100,
            persistence_path=tmp_path / "quota.json",
        )
        
        assert qm.can_consume(1)
        assert qm.can_consume(10)
        assert not qm.can_consume(11)
    
    def test_consume_increases_usage(self, tmp_path):
        """Test consume increases usage counters."""
        from src.quota_manager import QuotaManager
        
        qm = QuotaManager(
            "test",
            hourly_limit=100,
            daily_limit=500,
            persistence_path=tmp_path / "quota.json",
        )
        
        initial_hourly = qm.usage.hourly_used
        initial_daily = qm.usage.daily_used
        
        qm.consume(5)
        
        assert qm.usage.hourly_used == initial_hourly + 5
        assert qm.usage.daily_used == initial_daily + 5
    
    def test_consume_raises_when_exceeded(self, tmp_path):
        """Test consume raises error when quota exceeded."""
        from src.quota_manager import QuotaManager, QuotaExceededError
        
        qm = QuotaManager(
            "test",
            hourly_limit=5,
            daily_limit=100,
            persistence_path=tmp_path / "quota.json",
        )
        
        # Use up quota
        qm.consume(5)
        
        # Should raise
        with pytest.raises(QuotaExceededError) as exc_info:
            qm.consume(1)
        
        assert "test" in str(exc_info.value)
        assert exc_info.value.api_name == "test"
    
    def test_persistence(self, tmp_path):
        """Test quota state persists to disk."""
        from src.quota_manager import QuotaManager
        
        persistence_path = tmp_path / "quota.json"
        
        # Create and use
        qm1 = QuotaManager(
            "test",
            hourly_limit=100,
            daily_limit=500,
            persistence_path=persistence_path,
        )
        qm1.consume(25)
        
        # Reload
        qm2 = QuotaManager(
            "test",
            hourly_limit=100,
            daily_limit=500,
            persistence_path=persistence_path,
        )
        
        assert qm2.usage.hourly_used == 25
        assert qm2.usage.daily_used == 25
    
    def test_reset_clears_usage(self, tmp_path):
        """Test reset clears usage counters."""
        from src.quota_manager import QuotaManager
        
        qm = QuotaManager(
            "test",
            hourly_limit=100,
            daily_limit=500,
            persistence_path=tmp_path / "quota.json",
        )
        
        qm.consume(50)
        qm.reset()
        
        assert qm.usage.hourly_used == 0
        assert qm.usage.daily_used == 0


class TestGlobalQuotas:
    """Tests for global quota functions."""
    
    def test_huggingface_quota_preconfigured(self):
        """HuggingFace quota should be preconfigured."""
        from src.quota_manager import huggingface_quota
        
        assert huggingface_quota.api_name == "huggingface"
        assert huggingface_quota.hourly_limit == 250  # Conservative
        assert huggingface_quota.daily_limit == 800
    
    def test_zero_quota_blocks_consume(self):
        """Zero quota should block all consumption."""
        from src.quota_manager import QuotaManager, QuotaExceededError
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a quota with zero limits
            quota = QuotaManager(
                "disabled_api_test",
                hourly_limit=0,
                daily_limit=0,
                persistence_path=Path(tmpdir) / "quota.json",
            )
            
            assert quota.hourly_limit == 0
            assert quota.daily_limit == 0
            assert not quota.can_consume(1)
            
            # Should raise on consume
            with pytest.raises(QuotaExceededError):
                quota.consume(1)
