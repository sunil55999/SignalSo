"""
Test Suite for Margin Filter Block
Tests margin level checking, threshold validation, and fallback handling
"""

import unittest
import json
import tempfile
import os
import time
from unittest.mock import Mock, patch
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'blocks'))

from blocks.margin_filter import MarginFilter, FilterResult, MarginThresholdType, MarginFilterConfig

class TestMarginFilter(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "margin_filter": {
                "enabled": True,
                "threshold_value": 200.0,
                "threshold_type": "percentage",
                "emergency_threshold": 100.0,
                "fallback_action": "block",
                "check_free_margin": True,
                "min_free_margin": 1000.0,
                "warning_threshold": 300.0,
                "per_strategy_overrides": {
                    "conservative": 250.0,
                    "aggressive": 150.0
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Create margin filter instance
        self.margin_filter = MarginFilter(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
        # Clean up detailed log if created
        detailed_log = self.temp_log.name.replace('.log', '_detailed.json')
        if os.path.exists(detailed_log):
            os.unlink(detailed_log)

class TestBasicFunctionality(TestMarginFilter):
    """Test basic margin filter functionality"""
    
    def test_initialization(self):
        """Test margin filter initialization"""
        self.assertTrue(self.margin_filter.config.enabled)
        self.assertEqual(self.margin_filter.config.threshold_value, 200.0)
        self.assertEqual(self.margin_filter.config.threshold_type, MarginThresholdType.PERCENTAGE)
        
    def test_config_loading(self):
        """Test configuration loading from file"""
        config = self.margin_filter.config
        
        self.assertEqual(config.threshold_value, 200.0)
        self.assertEqual(config.emergency_threshold, 100.0)
        self.assertEqual(config.warning_threshold, 300.0)
        self.assertEqual(config.fallback_action, FilterResult.BLOCK)
        
        # Test strategy overrides
        self.assertEqual(config.per_strategy_overrides["conservative"], 250.0)
        self.assertEqual(config.per_strategy_overrides["aggressive"], 150.0)

class TestMarginChecking(TestMarginFilter):
    """Test margin level checking logic"""
    
    def test_margin_above_threshold_allows_signal(self):
        """Test that margin above threshold allows signal"""
        # Mock MT5 data with good margin
        mock_margin_data = {
            "balance": 10000.0,
            "equity": 9800.0,
            "margin": 400.0,
            "free_margin": 9400.0,
            "margin_level": 2450.0,  # 245% - above 200% threshold
            "currency": "USD",
            "timestamp": time.time()
        }
        
        with patch.object(self.margin_filter, '_get_mt5_account_info', return_value=mock_margin_data):
            signal_data = {
                "signal_id": "test_001",
                "symbol": "EURUSD",
                "direction": "buy"
            }
            
            result, reason = self.margin_filter.check_signal(signal_data)
            
            self.assertEqual(result, FilterResult.ALLOW)
            self.assertIn("acceptable", reason.lower())
            self.assertIn("245", reason)
            
    def test_margin_below_threshold_blocks_signal(self):
        """Test that margin below threshold blocks signal"""
        # Mock MT5 data with low margin
        mock_margin_data = {
            "balance": 10000.0,
            "equity": 8500.0,
            "margin": 5000.0,
            "free_margin": 3500.0,
            "margin_level": 170.0,  # 170% - below 200% threshold
            "currency": "USD",
            "timestamp": time.time()
        }
        
        with patch.object(self.margin_filter, '_get_mt5_account_info', return_value=mock_margin_data):
            signal_data = {
                "signal_id": "test_002",
                "symbol": "GBPUSD",
                "direction": "sell"
            }
            
            result, reason = self.margin_filter.check_signal(signal_data)
            
            self.assertEqual(result, FilterResult.BLOCK)
            self.assertIn("too low", reason.lower())
            self.assertIn("170", reason)
            
    def test_emergency_threshold_blocks_signal(self):
        """Test that emergency threshold always blocks signal"""
        # Mock MT5 data with critical margin
        mock_margin_data = {
            "balance": 10000.0,
            "equity": 7000.0,
            "margin": 7500.0,
            "free_margin": -500.0,
            "margin_level": 93.3,  # 93.3% - below 100% emergency threshold
            "currency": "USD",
            "timestamp": time.time()
        }
        
        with patch.object(self.margin_filter, '_get_mt5_account_info', return_value=mock_margin_data):
            signal_data = {
                "signal_id": "test_003",
                "symbol": "XAUUSD",
                "direction": "buy"
            }
            
            result, reason = self.margin_filter.check_signal(signal_data)
            
            self.assertEqual(result, FilterResult.BLOCK)
            self.assertIn("emergency", reason.lower())
            self.assertIn("93.3", reason)

class TestStrategyOverrides(TestMarginFilter):
    """Test strategy-specific threshold overrides"""
    
    def test_conservative_strategy_override(self):
        """Test conservative strategy uses higher threshold"""
        # Mock margin data that would pass normal threshold but fail conservative
        mock_margin_data = {
            "balance": 10000.0,
            "equity": 9000.0,
            "margin": 4000.0,
            "free_margin": 5000.0,
            "margin_level": 225.0,  # 225% - above 200% but below 250%
            "currency": "USD",
            "timestamp": time.time()
        }
        
        with patch.object(self.margin_filter, '_get_mt5_account_info', return_value=mock_margin_data):
            signal_data = {
                "signal_id": "test_004",
                "symbol": "EURUSD",
                "direction": "buy"
            }
            
            # Test with conservative strategy
            result, reason = self.margin_filter.check_signal(signal_data, strategy_id="conservative")
            
            self.assertEqual(result, FilterResult.BLOCK)
            self.assertIn("225", reason)
            
            # Test with normal threshold (should pass)
            result, reason = self.margin_filter.check_signal(signal_data)
            
            self.assertEqual(result, FilterResult.ALLOW)
            
    def test_aggressive_strategy_override(self):
        """Test aggressive strategy uses lower threshold"""
        # Mock margin data that would fail normal threshold but pass aggressive
        mock_margin_data = {
            "balance": 10000.0,
            "equity": 8000.0,
            "margin": 4500.0,
            "free_margin": 3500.0,
            "margin_level": 177.8,  # 177.8% - below 200% but above 150%
            "currency": "USD",
            "timestamp": time.time()
        }
        
        with patch.object(self.margin_filter, '_get_mt5_account_info', return_value=mock_margin_data):
            signal_data = {
                "signal_id": "test_005",
                "symbol": "GBPUSD",
                "direction": "sell"
            }
            
            # Test with aggressive strategy
            result, reason = self.margin_filter.check_signal(signal_data, strategy_id="aggressive")
            
            self.assertEqual(result, FilterResult.ALLOW)
            self.assertIn("177.8", reason)
            
            # Test with normal threshold (should fail)
            result, reason = self.margin_filter.check_signal(signal_data)
            
            self.assertEqual(result, FilterResult.BLOCK)

class TestFallbackHandling(TestMarginFilter):
    """Test fallback behavior when MT5 data is unavailable"""
    
    def test_mt5_failure_blocks_with_block_fallback(self):
        """Test that MT5 failure blocks signal when fallback is set to block"""
        with patch.object(self.margin_filter, '_get_mt5_account_info', return_value=None):
            signal_data = {
                "signal_id": "test_006",
                "symbol": "EURUSD",
                "direction": "buy"
            }
            
            result, reason = self.margin_filter.check_signal(signal_data)
            
            self.assertEqual(result, FilterResult.BLOCK)
            self.assertIn("unavailable", reason.lower())
            self.assertIn("blocking for safety", reason.lower())
            
    def test_mt5_failure_allows_with_allow_fallback(self):
        """Test that MT5 failure allows signal when fallback is set to allow"""
        # Update config to allow on fallback
        self.margin_filter.config.fallback_action = FilterResult.ALLOW
        
        with patch.object(self.margin_filter, '_get_mt5_account_info', return_value=None):
            signal_data = {
                "signal_id": "test_007",
                "symbol": "GBPUSD",
                "direction": "sell"
            }
            
            result, reason = self.margin_filter.check_signal(signal_data)
            
            self.assertEqual(result, FilterResult.ALLOW)
            self.assertIn("unavailable", reason.lower())
            self.assertIn("allowing per fallback", reason.lower())

class TestConfigurationUpdates(TestMarginFilter):
    """Test configuration update functionality"""
    
    def test_config_update(self):
        """Test updating filter configuration"""
        new_config = {
            "threshold_value": 250.0,
            "emergency_threshold": 120.0
        }
        
        success = self.margin_filter.update_config(new_config)
        
        self.assertTrue(success)
        self.assertEqual(self.margin_filter.config.threshold_value, 250.0)
        self.assertEqual(self.margin_filter.config.emergency_threshold, 120.0)
        
    def test_strategy_override_update(self):
        """Test updating strategy-specific overrides"""
        new_config = {
            "per_strategy_overrides": {
                "conservative": 300.0,
                "aggressive": 120.0,
                "balanced": 200.0
            }
        }
        
        success = self.margin_filter.update_config(new_config)
        
        self.assertTrue(success)
        self.assertEqual(self.margin_filter.config.per_strategy_overrides["balanced"], 200.0)

class TestStatisticsAndLogging(TestMarginFilter):
    """Test statistics tracking and logging functionality"""
    
    def test_statistics_tracking(self):
        """Test that statistics are properly tracked"""
        # Mock margin data
        mock_margin_data = {
            "balance": 10000.0,
            "equity": 9500.0,
            "margin": 2000.0,
            "free_margin": 7500.0,
            "margin_level": 475.0,
            "currency": "USD",
            "timestamp": time.time()
        }
        
        with patch.object(self.margin_filter, '_get_mt5_account_info', return_value=mock_margin_data):
            # Process several signals
            signals = [
                {"signal_id": "stat_001", "symbol": "EURUSD"},
                {"signal_id": "stat_002", "symbol": "GBPUSD"},
                {"signal_id": "stat_003", "symbol": "XAUUSD"}
            ]
            
            for signal in signals:
                self.margin_filter.check_signal(signal)
                
            stats = self.margin_filter.get_statistics()
            
            self.assertEqual(stats["total_checks"], 3)
            self.assertEqual(stats["allowed_signals"], 3)
            self.assertEqual(stats["blocked_signals"], 0)
            self.assertEqual(stats["allow_rate_percent"], 100.0)
            
    def test_statistics_reset(self):
        """Test statistics reset functionality"""
        # Process a signal to generate stats
        mock_margin_data = {
            "margin_level": 300.0,
            "free_margin": 5000.0,
            "timestamp": time.time()
        }
        
        with patch.object(self.margin_filter, '_get_mt5_account_info', return_value=mock_margin_data):
            self.margin_filter.check_signal({"signal_id": "reset_test", "symbol": "EURUSD"})
            
            # Verify stats exist
            stats = self.margin_filter.get_statistics()
            self.assertGreater(stats["total_checks"], 0)
            
            # Reset and verify
            self.margin_filter.reset_statistics()
            stats = self.margin_filter.get_statistics()
            self.assertEqual(stats["total_checks"], 0)
            
    def test_cache_functionality(self):
        """Test margin data caching"""
        mock_margin_data = {
            "margin_level": 300.0,
            "free_margin": 5000.0,
            "timestamp": time.time()
        }
        
        with patch.object(self.margin_filter, '_get_mt5_account_info', return_value=mock_margin_data) as mock_mt5:
            # First call should hit MT5
            self.margin_filter.check_signal({"signal_id": "cache_001", "symbol": "EURUSD"})
            self.assertEqual(mock_mt5.call_count, 1)
            
            # Second call within cache expiry should use cache
            self.margin_filter.check_signal({"signal_id": "cache_002", "symbol": "GBPUSD"})
            self.assertEqual(mock_mt5.call_count, 1)  # Still 1, used cache
            
            # Force cache refresh and try again
            self.margin_filter.force_cache_refresh()
            self.margin_filter.check_signal({"signal_id": "cache_003", "symbol": "XAUUSD"})
            self.assertEqual(mock_mt5.call_count, 2)  # Should hit MT5 again

class TestDisabledFilter(TestMarginFilter):
    """Test behavior when filter is disabled"""
    
    def test_disabled_filter_allows_all_signals(self):
        """Test that disabled filter allows all signals"""
        # Disable the filter
        self.margin_filter.config.enabled = False
        
        signal_data = {
            "signal_id": "disabled_test",
            "symbol": "EURUSD",
            "direction": "buy"
        }
        
        result, reason = self.margin_filter.check_signal(signal_data)
        
        self.assertEqual(result, FilterResult.ALLOW)
        self.assertIn("disabled", reason.lower())

if __name__ == '__main__':
    unittest.main()