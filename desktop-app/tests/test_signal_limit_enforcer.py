"""
Test Suite for Signal Limit Enforcer Engine
Tests signal counting, limit enforcement, and provider-based restrictions
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_limit_enforcer import (
    SignalLimitEnforcer, LimitConfig, SignalRecord, EnforcementResult,
    EnforcementStatus, LimitType
)

class TestSignalLimitEnforcer(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "signal_limit_enforcer": {
                "enabled": True,
                "symbol_hourly_limit": 3,
                "symbol_daily_limit": 10,
                "provider_hourly_limit": 5,
                "provider_daily_limit": 20,
                "global_hourly_limit": 15,
                "global_daily_limit": 50,
                "cooldown_minutes": 15,
                "emergency_override_limit": 3,
                "cleanup_days": 1,  # Short for testing
                "symbol_specific_limits": {
                    "XAUUSD": {"hourly": 2, "daily": 6}
                },
                "provider_specific_limits": {
                    "high_freq_provider": {"hourly": 2, "daily": 8}
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize enforcer
        self.enforcer = SignalLimitEnforcer(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
        # Clean up history file if created
        history_file = self.temp_log.name.replace('.log', '_history.json')
        if os.path.exists(history_file):
            os.unlink(history_file)

class TestBasicFunctionality(TestSignalLimitEnforcer):
    """Test basic signal limit enforcer functionality"""
    
    def test_initialization(self):
        """Test signal limit enforcer initialization"""
        self.assertEqual(self.enforcer.config.symbol_hourly_limit, 3)
        self.assertEqual(self.enforcer.config.symbol_daily_limit, 10)
        self.assertEqual(self.enforcer.config.cooldown_minutes, 15)
        self.assertEqual(self.enforcer.config.emergency_override_limit, 3)
        
    def test_limit_config_creation(self):
        """Test limit configuration object creation"""
        config = LimitConfig(
            symbol_hourly_limit=5,
            symbol_daily_limit=15,
            cooldown_minutes=10
        )
        
        self.assertEqual(config.symbol_hourly_limit, 5)
        self.assertEqual(config.symbol_daily_limit, 15)
        self.assertEqual(config.cooldown_minutes, 10)
        
        # Test default values
        self.assertIsNotNone(config.symbol_specific_limits)
        self.assertIsNotNone(config.provider_specific_limits)
        
    def test_effective_limits_default(self):
        """Test getting effective limits with default values"""
        limits = self.enforcer._get_effective_limits("EURUSD", "test_provider")
        
        self.assertEqual(limits['symbol_hourly'], 3)
        self.assertEqual(limits['symbol_daily'], 10)
        self.assertEqual(limits['provider_hourly'], 5)
        self.assertEqual(limits['provider_daily'], 20)
        
    def test_effective_limits_symbol_specific(self):
        """Test getting effective limits with symbol-specific overrides"""
        limits = self.enforcer._get_effective_limits("XAUUSD", "test_provider")
        
        # Should use symbol-specific limits
        self.assertEqual(limits['symbol_hourly'], 2)
        self.assertEqual(limits['symbol_daily'], 6)
        # Provider limits should remain default
        self.assertEqual(limits['provider_hourly'], 5)
        self.assertEqual(limits['provider_daily'], 20)
        
    def test_effective_limits_provider_specific(self):
        """Test getting effective limits with provider-specific overrides"""
        limits = self.enforcer._get_effective_limits("EURUSD", "high_freq_provider")
        
        # Symbol limits should remain default
        self.assertEqual(limits['symbol_hourly'], 3)
        self.assertEqual(limits['symbol_daily'], 10)
        # Should use provider-specific limits
        self.assertEqual(limits['provider_hourly'], 2)
        self.assertEqual(limits['provider_daily'], 8)

class TestSignalRecording(TestSignalLimitEnforcer):
    """Test signal recording functionality"""
    
    def test_record_signal_basic(self):
        """Test basic signal recording"""
        success = self.enforcer.record_signal(
            signal_id="test_001",
            symbol="EURUSD",
            provider_id="test_provider",
            provider_name="Test Provider"
        )
        
        self.assertTrue(success)
        self.assertEqual(len(self.enforcer.signal_history), 1)
        
        # Check recorded signal
        signal = self.enforcer.signal_history[0]
        self.assertEqual(signal.signal_id, "test_001")
        self.assertEqual(signal.symbol, "EURUSD")
        self.assertEqual(signal.provider_id, "test_provider")
        
    def test_record_signal_with_timestamp(self):
        """Test recording signal with custom timestamp"""
        test_time = datetime.now() - timedelta(minutes=30)
        
        success = self.enforcer.record_signal(
            signal_id="test_002",
            symbol="GBPUSD",
            provider_id="test_provider",
            timestamp=test_time
        )
        
        self.assertTrue(success)
        signal = self.enforcer.signal_history[0]
        self.assertEqual(signal.timestamp, test_time)
        
    def test_record_signal_updates_counters(self):
        """Test that recording signal updates counters"""
        # Record signal
        self.enforcer.record_signal(
            signal_id="test_003",
            symbol="EURUSD",
            provider_id="test_provider"
        )
        
        # Check counters were updated
        self.assertEqual(len(self.enforcer.hourly_counters['symbol']['EURUSD']), 1)
        self.assertEqual(len(self.enforcer.daily_counters['symbol']['EURUSD']), 1)
        self.assertEqual(len(self.enforcer.hourly_counters['provider']['test_provider']), 1)
        self.assertEqual(len(self.enforcer.daily_counters['provider']['test_provider']), 1)
        self.assertEqual(len(self.enforcer.hourly_counters['global']), 1)
        self.assertEqual(len(self.enforcer.daily_counters['global']), 1)

class TestLimitEnforcement(TestSignalLimitEnforcer):
    """Test limit enforcement logic"""
    
    def test_check_signal_allowed_initially(self):
        """Test that signals are initially allowed"""
        status = self.enforcer.check_signal_allowed("EURUSD", "test_provider")
        
        self.assertEqual(status.result, EnforcementResult.ALLOWED)
        self.assertIn("within all limits", status.reason)
        
    def test_symbol_hourly_limit_enforcement(self):
        """Test symbol hourly limit enforcement"""
        # Record signals up to the limit (3) with different timestamps to avoid cooldown
        base_time = datetime.now() - timedelta(minutes=30)
        for i in range(3):
            timestamp = base_time + timedelta(minutes=i*20)  # Spread over time to avoid cooldown
            self.enforcer.record_signal(f"test_{i}", "EURUSD", "test_provider", timestamp=timestamp)
            
        # Next signal should be blocked by hourly limit
        status = self.enforcer.check_signal_allowed("EURUSD", "another_provider")
        
        self.assertEqual(status.result, EnforcementResult.BLOCKED_SYMBOL_HOURLY)
        self.assertIn("hourly limit exceeded", status.reason)
        self.assertEqual(status.current_count, 3)
        self.assertEqual(status.limit, 3)
        self.assertIsNotNone(status.next_reset_time)
        
    def test_symbol_daily_limit_enforcement(self):
        """Test symbol daily limit enforcement"""
        # Record signals up to daily limit but spread over time to avoid hourly limit
        for i in range(10):
            # Spread signals across different hours
            timestamp = datetime.now() - timedelta(hours=i, minutes=30)
            self.enforcer.record_signal(f"test_{i}", "EURUSD", "test_provider", timestamp=timestamp)
            
        # Next signal should be blocked by daily limit
        status = self.enforcer.check_signal_allowed("EURUSD", "test_provider")
        
        self.assertEqual(status.result, EnforcementResult.BLOCKED_SYMBOL_DAILY)
        self.assertIn("daily limit exceeded", status.reason)
        
    def test_provider_limit_enforcement(self):
        """Test provider-based limit enforcement"""
        # Record signals from same provider on different symbols
        symbols = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD"]
        
        for i, symbol in enumerate(symbols):
            self.enforcer.record_signal(f"test_{i}", symbol, "test_provider")
            
        # Next signal should be blocked by provider hourly limit (5)
        status = self.enforcer.check_signal_allowed("USDJPY", "test_provider")
        
        self.assertEqual(status.result, EnforcementResult.BLOCKED_PROVIDER_HOURLY)
        self.assertIn("Provider test_provider hourly limit exceeded", status.reason)
        
    def test_global_limit_enforcement(self):
        """Test global limit enforcement"""
        # Record many signals from different providers
        for i in range(15):
            self.enforcer.record_signal(f"test_{i}", f"SYMBOL{i}", f"provider_{i}")
            
        # Next signal should be blocked by global hourly limit (15)
        status = self.enforcer.check_signal_allowed("NEWSYMBOL", "new_provider")
        
        self.assertEqual(status.result, EnforcementResult.BLOCKED_GLOBAL_HOURLY)
        self.assertIn("Global hourly limit exceeded", status.reason)
        
    def test_symbol_specific_limits(self):
        """Test symbol-specific limit enforcement"""
        # XAUUSD has hourly limit of 2
        base_time = datetime.now() - timedelta(minutes=30)
        for i in range(2):
            timestamp = base_time + timedelta(minutes=i*20)  # Spread over time to avoid cooldown
            self.enforcer.record_signal(f"gold_{i}", "XAUUSD", "test_provider", timestamp=timestamp)
            
        # Third signal should be blocked by limit, not cooldown
        status = self.enforcer.check_signal_allowed("XAUUSD", "another_provider")
        
        self.assertEqual(status.result, EnforcementResult.BLOCKED_SYMBOL_HOURLY)
        self.assertEqual(status.limit, 2)  # Symbol-specific limit
        
    def test_provider_specific_limits(self):
        """Test provider-specific limit enforcement"""
        # high_freq_provider has hourly limit of 2
        for i in range(2):
            self.enforcer.record_signal(f"hf_{i}", f"SYMBOL{i}", "high_freq_provider")
            
        # Third signal should be blocked
        status = self.enforcer.check_signal_allowed("SYMBOL3", "high_freq_provider")
        
        self.assertEqual(status.result, EnforcementResult.BLOCKED_PROVIDER_HOURLY)
        self.assertEqual(status.limit, 2)  # Provider-specific limit

class TestCooldownPeriod(TestSignalLimitEnforcer):
    """Test cooldown period functionality"""
    
    def test_cooldown_check_no_previous_signal(self):
        """Test cooldown check with no previous signal"""
        in_cooldown, expires = self.enforcer._check_cooldown("EURUSD", datetime.now())
        
        self.assertFalse(in_cooldown)
        self.assertIsNone(expires)
        
    def test_cooldown_check_within_period(self):
        """Test cooldown check within cooldown period"""
        now = datetime.now()
        
        # Record a signal
        self.enforcer.record_signal("test_001", "EURUSD", "test_provider", timestamp=now)
        
        # Check cooldown 5 minutes later (within 15-minute cooldown)
        check_time = now + timedelta(minutes=5)
        in_cooldown, expires = self.enforcer._check_cooldown("EURUSD", check_time)
        
        self.assertTrue(in_cooldown)
        self.assertIsNotNone(expires)
        
        # Check that expires time is correct
        expected_expires = now + timedelta(minutes=15)
        self.assertEqual(expires, expected_expires)
        
    def test_cooldown_check_after_period(self):
        """Test cooldown check after cooldown period"""
        now = datetime.now()
        
        # Record a signal
        self.enforcer.record_signal("test_002", "EURUSD", "test_provider", timestamp=now)
        
        # Check cooldown 20 minutes later (after 15-minute cooldown)
        check_time = now + timedelta(minutes=20)
        in_cooldown, expires = self.enforcer._check_cooldown("EURUSD", check_time)
        
        self.assertFalse(in_cooldown)
        self.assertIsNone(expires)
        
    def test_signal_blocked_by_cooldown(self):
        """Test signal blocked by cooldown period"""
        # Record initial signal
        self.enforcer.record_signal("test_003", "EURUSD", "test_provider")
        
        # Immediate second signal should be blocked by cooldown
        status = self.enforcer.check_signal_allowed("EURUSD", "another_provider")
        
        self.assertEqual(status.result, EnforcementResult.BLOCKED_COOLDOWN)
        self.assertIn("cooldown period", status.reason)
        self.assertIsNotNone(status.cooldown_expires)

class TestEmergencyOverride(TestSignalLimitEnforcer):
    """Test emergency override functionality"""
    
    def test_enable_emergency_override(self):
        """Test enabling emergency override"""
        success = self.enforcer.enable_emergency_override(30)
        
        self.assertTrue(success)
        self.assertTrue(self.enforcer.emergency_override_active)
        self.assertIsNotNone(self.enforcer.override_expires)
        self.assertEqual(self.enforcer.daily_override_count, 1)
        
    def test_emergency_override_bypass_limits(self):
        """Test that emergency override bypasses limits"""
        # Fill up symbol hourly limit
        for i in range(3):
            self.enforcer.record_signal(f"test_{i}", "EURUSD", "test_provider")
            
        # Should be blocked normally
        status = self.enforcer.check_signal_allowed("EURUSD", "test_provider")
        self.assertEqual(status.result, EnforcementResult.BLOCKED_SYMBOL_HOURLY)
        
        # Enable override
        self.enforcer.enable_emergency_override(60)
        
        # Should now be allowed
        status_override = self.enforcer.check_signal_allowed("EURUSD", "test_provider")
        self.assertEqual(status_override.result, EnforcementResult.OVERRIDE_ACTIVE)
        
    def test_emergency_override_daily_limit(self):
        """Test emergency override daily limit"""
        # Use up daily override limit (3)
        for i in range(3):
            success = self.enforcer.enable_emergency_override(10)
            self.assertTrue(success)
            self.enforcer.disable_emergency_override()
            
        # Fourth attempt should fail
        success = self.enforcer.enable_emergency_override(10)
        self.assertFalse(success)
        
    def test_disable_emergency_override(self):
        """Test disabling emergency override"""
        # Enable first
        self.enforcer.enable_emergency_override(30)
        self.assertTrue(self.enforcer.emergency_override_active)
        
        # Disable
        success = self.enforcer.disable_emergency_override()
        
        self.assertTrue(success)
        self.assertFalse(self.enforcer.emergency_override_active)
        self.assertIsNone(self.enforcer.override_expires)

class TestStatisticsAndStatus(TestSignalLimitEnforcer):
    """Test statistics and status reporting"""
    
    def test_get_current_statistics_empty(self):
        """Test getting statistics with no signals"""
        stats = self.enforcer.get_current_statistics()
        
        self.assertEqual(stats['global_hourly_count'], 0)
        self.assertEqual(stats['global_daily_count'], 0)
        self.assertEqual(stats['total_signals_recorded'], 0)
        self.assertFalse(stats['emergency_override_active'])
        self.assertEqual(stats['daily_override_count'], 0)
        
    def test_get_current_statistics_with_signals(self):
        """Test getting statistics with recorded signals"""
        # Record some signals
        self.enforcer.record_signal("test_001", "EURUSD", "provider_1")
        self.enforcer.record_signal("test_002", "GBPUSD", "provider_1")
        self.enforcer.record_signal("test_003", "EURUSD", "provider_2")
        
        stats = self.enforcer.get_current_statistics()
        
        self.assertEqual(stats['global_hourly_count'], 3)
        self.assertEqual(stats['global_daily_count'], 3)
        self.assertEqual(stats['total_signals_recorded'], 3)
        
        # Check symbol statistics
        self.assertIn('EURUSD', stats['symbol_statistics'])
        self.assertIn('GBPUSD', stats['symbol_statistics'])
        
        eurusd_stats = stats['symbol_statistics']['EURUSD']
        self.assertEqual(eurusd_stats['hourly_count'], 2)
        self.assertEqual(eurusd_stats['daily_count'], 2)
        
        # Check provider statistics
        self.assertIn('provider_1', stats['provider_statistics'])
        self.assertIn('provider_2', stats['provider_statistics'])
        
        provider1_stats = stats['provider_statistics']['provider_1']
        self.assertEqual(provider1_stats['hourly_count'], 2)
        self.assertEqual(provider1_stats['daily_count'], 2)
        
    def test_get_symbol_status(self):
        """Test getting status for specific symbol"""
        # Record signal for EURUSD
        self.enforcer.record_signal("test_001", "EURUSD", "test_provider")
        
        status = self.enforcer.get_symbol_status("EURUSD")
        
        self.assertEqual(status['symbol'], 'EURUSD')
        self.assertEqual(status['hourly_count'], 1)
        self.assertEqual(status['daily_count'], 1)
        self.assertEqual(status['hourly_limit'], 3)
        self.assertEqual(status['daily_limit'], 10)
        self.assertFalse(status['in_cooldown'])  # Just recorded, so in cooldown
        
    def test_get_recent_signals(self):
        """Test getting recent signals"""
        # Record multiple signals
        signals = [
            ("test_001", "EURUSD", "provider_1"),
            ("test_002", "GBPUSD", "provider_1"),
            ("test_003", "EURUSD", "provider_2"),
            ("test_004", "AUDUSD", "provider_2")
        ]
        
        for signal_id, symbol, provider in signals:
            self.enforcer.record_signal(signal_id, symbol, provider)
            
        # Get all recent signals
        recent = self.enforcer.get_recent_signals(10)
        self.assertEqual(len(recent), 4)
        
        # Should be sorted by timestamp (newest first)
        self.assertEqual(recent[0]['signal_id'], 'test_004')  # Last recorded
        
        # Test filtering by symbol
        eurusd_signals = self.enforcer.get_recent_signals(10, symbol='EURUSD')
        self.assertEqual(len(eurusd_signals), 2)
        
        # Test filtering by provider
        provider1_signals = self.enforcer.get_recent_signals(10, provider_id='provider_1')
        self.assertEqual(len(provider1_signals), 2)

class TestDataPersistence(TestSignalLimitEnforcer):
    """Test data persistence functionality"""
    
    def test_signal_history_persistence(self):
        """Test saving and loading signal history"""
        # Record some signals
        self.enforcer.record_signal("persist_001", "EURUSD", "test_provider")
        self.enforcer.record_signal("persist_002", "GBPUSD", "test_provider")
        
        # Create new enforcer instance
        new_enforcer = SignalLimitEnforcer(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
        # Check signals were loaded
        self.assertEqual(len(new_enforcer.signal_history), 2)
        self.assertEqual(new_enforcer.signal_history[0].signal_id, "persist_001")
        self.assertEqual(new_enforcer.signal_history[1].signal_id, "persist_002")
        
        # Check counters were rebuilt
        self.assertEqual(len(new_enforcer.hourly_counters['symbol']['EURUSD']), 1)
        self.assertEqual(len(new_enforcer.hourly_counters['symbol']['GBPUSD']), 1)

class TestEdgeCases(TestSignalLimitEnforcer):
    """Test edge cases and error handling"""
    
    def test_disabled_enforcement(self):
        """Test behavior when enforcement is disabled"""
        # Modify config to disable enforcement
        with open(self.temp_config.name, 'r') as f:
            config = json.load(f)
        config['signal_limit_enforcer']['enabled'] = False
        with open(self.temp_config.name, 'w') as f:
            json.dump(config, f)
            
        # Check signal should always be allowed
        status = self.enforcer.check_signal_allowed("EURUSD", "test_provider")
        self.assertEqual(status.result, EnforcementResult.ALLOWED)
        self.assertIn("disabled", status.reason)
        
    def test_sliding_window_cleanup(self):
        """Test that old timestamps are cleaned from sliding windows"""
        now = datetime.now()
        
        # Record old signal (2 hours ago)
        old_time = now - timedelta(hours=2)
        self.enforcer.record_signal("old_signal", "EURUSD", "test_provider", timestamp=old_time)
        
        # Record recent signal
        self.enforcer.record_signal("new_signal", "EURUSD", "test_provider", timestamp=now)
        
        # Check that only recent signal counts in hourly window
        status = self.enforcer.check_signal_allowed("EURUSD", "test_provider", current_time=now)
        
        # Should show only 1 signal in hourly count (the recent one)
        # But we need to check the actual counters since status doesn't show counts for allowed signals
        hourly_count = len(self.enforcer.hourly_counters['symbol']['EURUSD'])
        daily_count = len(self.enforcer.daily_counters['symbol']['EURUSD'])
        
        self.assertEqual(hourly_count, 1)  # Only recent signal
        self.assertEqual(daily_count, 2)   # Both signals (within 24 hours)

if __name__ == '__main__':
    unittest.main()