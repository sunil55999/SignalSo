"""
Test Suite for Spread Checker Module
Tests spread validation, quote handling, and integration with trading systems
"""

import unittest
import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spread_checker import SpreadChecker, SpreadCheckResult, SpreadInfo

class MockMT5Bridge:
    """Mock MT5 bridge for testing"""
    
    def __init__(self):
        self.mock_ticks = {}
        self.connection_status = True
        
    def set_mock_tick(self, symbol: str, bid: float, ask: float, timestamp: datetime = None):
        """Set mock tick data for symbol"""
        if timestamp is None:
            timestamp = datetime.now()
            
        self.mock_ticks[symbol] = {
            'bid': bid,
            'ask': ask,
            'time': timestamp,
            'symbol': symbol
        }
        
    def get_symbol_tick(self, symbol: str):
        """Mock implementation of get_symbol_tick"""
        if not self.connection_status:
            return None
            
        return self.mock_ticks.get(symbol, None)
        
    def set_connection_status(self, status: bool):
        """Set mock connection status"""
        self.connection_status = status

class TestSpreadChecker(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        self.log_file = os.path.join(self.temp_dir, 'test_spread.log')
        
        # Create test config
        test_config = {
            "spread_checker": {
                "enabled": True,
                "default_max_spread_pips": 3.0,
                "symbol_specific_limits": {
                    "EURUSD": 2.0,
                    "GBPUSD": 2.5,
                    "XAUUSD": 5.0,
                    "BTCUSD": 50.0
                },
                "high_spread_overrides": {
                    "BTCUSD": True,
                    "XAUUSD": True
                },
                "stale_quote_threshold_seconds": 10,
                "enable_fallback_warning": True,
                "block_on_no_quotes": True,
                "log_all_checks": True,
                "log_blocked_only": False
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
            
        # Initialize spread checker
        self.spread_checker = SpreadChecker(self.config_file, self.log_file)
        
        # Set up mock MT5 bridge
        self.mock_mt5 = MockMT5Bridge()
        self.spread_checker.set_mt5_bridge(self.mock_mt5)
        
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_initialization(self):
        """Test spread checker initialization"""
        self.assertTrue(self.spread_checker.config['enabled'])
        self.assertEqual(self.spread_checker.config['default_max_spread_pips'], 3.0)
        self.assertEqual(self.spread_checker.config['symbol_specific_limits']['EURUSD'], 2.0)
        
    def test_acceptable_spread(self):
        """Test trade allowed with acceptable spread"""
        # Set mock tick with acceptable spread
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0852)  # 2 pips spread
        
        result, spread_info = self.spread_checker.check_spread_before_trade('EURUSD')
        
        self.assertEqual(result, SpreadCheckResult.ALLOWED)
        self.assertIsNotNone(spread_info)
        self.assertEqual(spread_info.symbol, 'EURUSD')
        self.assertAlmostEqual(spread_info.spread_pips, 2.0, places=1)
        
    def test_unacceptable_spread_blocked(self):
        """Test trade blocked with unacceptable spread"""
        # Set mock tick with high spread (3 pips > 2 pips limit for EURUSD)
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0853)  # 3 pips spread
        
        result, spread_info = self.spread_checker.check_spread_before_trade('EURUSD')
        
        self.assertEqual(result, SpreadCheckResult.BLOCKED_HIGH_SPREAD)
        self.assertIsNotNone(spread_info)
        self.assertAlmostEqual(spread_info.spread_pips, 3.0, places=1)
        
    def test_high_spread_with_override(self):
        """Test high spread allowed with override enabled"""
        # Set mock tick with very high spread for BTCUSD (which has override)
        self.mock_mt5.set_mock_tick('BTCUSD', 45000.0, 45100.0)  # 100 pips spread
        
        result, spread_info = self.spread_checker.check_spread_before_trade('BTCUSD')
        
        self.assertEqual(result, SpreadCheckResult.WARNING_FALLBACK)
        self.assertIsNotNone(spread_info)
        self.assertGreater(spread_info.spread_pips, 50.0)  # Should be > 50 pips
        
    def test_no_quotes_blocked(self):
        """Test trade blocked when no quotes available"""
        # Don't set any mock tick for EURUSD
        result, spread_info = self.spread_checker.check_spread_before_trade('EURUSD')
        
        self.assertEqual(result, SpreadCheckResult.BLOCKED_NO_QUOTES)
        self.assertIsNone(spread_info)
        
    def test_stale_quotes_blocked(self):
        """Test trade blocked with stale quotes"""
        # Set mock tick with old timestamp
        old_timestamp = datetime.now() - timedelta(seconds=15)
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0852, old_timestamp)
        
        result, spread_info = self.spread_checker.check_spread_before_trade('EURUSD')
        
        self.assertEqual(result, SpreadCheckResult.BLOCKED_STALE_QUOTES)
        self.assertIsNotNone(spread_info)
        self.assertTrue(spread_info.is_stale)
        
    def test_mt5_connection_error(self):
        """Test fallback when MT5 connection fails"""
        # Simulate MT5 disconnection
        self.mock_mt5.set_connection_status(False)
        
        result, spread_info = self.spread_checker.check_spread_before_trade('EURUSD')
        
        self.assertEqual(result, SpreadCheckResult.BLOCKED_NO_QUOTES)
        self.assertIsNone(spread_info)
        
    def test_symbol_specific_limits(self):
        """Test symbol-specific spread limits"""
        # Test EURUSD (2.0 pips limit)
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0851)  # 1 pip - should pass
        result, _ = self.spread_checker.check_spread_before_trade('EURUSD')
        self.assertEqual(result, SpreadCheckResult.ALLOWED)
        
        # Test GBPUSD (2.5 pips limit)
        self.mock_mt5.set_mock_tick('GBPUSD', 1.2500, 1.2503)  # 3 pips - should fail
        result, _ = self.spread_checker.check_spread_before_trade('GBPUSD')
        self.assertEqual(result, SpreadCheckResult.BLOCKED_HIGH_SPREAD)
        
    def test_default_spread_limit(self):
        """Test default spread limit for unknown symbols"""
        # Test unknown symbol (should use default 3.0 pips)
        self.mock_mt5.set_mock_tick('UNKNOWN', 1.0000, 1.0002)  # 2 pips - should pass
        result, _ = self.spread_checker.check_spread_before_trade('UNKNOWN')
        self.assertEqual(result, SpreadCheckResult.ALLOWED)
        
        # Test with higher spread
        self.mock_mt5.set_mock_tick('UNKNOWN', 1.0000, 1.0004)  # 4 pips - should fail
        result, _ = self.spread_checker.check_spread_before_trade('UNKNOWN')
        self.assertEqual(result, SpreadCheckResult.BLOCKED_HIGH_SPREAD)
        
    def test_pip_value_calculation(self):
        """Test pip value calculation for different symbol types"""
        # Test EURUSD (5-digit)
        self.mock_mt5.set_mock_tick('EURUSD', 1.08500, 1.08520)  # 2 pips
        _, spread_info = self.spread_checker.check_spread_before_trade('EURUSD')
        self.assertAlmostEqual(spread_info.spread_pips, 2.0, places=1)
        
        # Test USDJPY (3-digit)
        self.mock_mt5.set_mock_tick('USDJPY', 110.000, 110.020)  # 2 pips
        _, spread_info = self.spread_checker.check_spread_before_trade('USDJPY')
        self.assertAlmostEqual(spread_info.spread_pips, 2.0, places=1)
        
        # Test XAUUSD (2-digit)
        self.mock_mt5.set_mock_tick('XAUUSD', 1800.00, 1800.05)  # 5 pips
        _, spread_info = self.spread_checker.check_spread_before_trade('XAUUSD')
        self.assertAlmostEqual(spread_info.spread_pips, 5.0, places=1)
        
    def test_quote_caching(self):
        """Test quote caching mechanism"""
        # Set mock tick
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0852)
        
        # First call should hit MT5
        result1, spread_info1 = self.spread_checker.check_spread_before_trade('EURUSD')
        
        # Second call within cache duration should use cache
        result2, spread_info2 = self.spread_checker.check_spread_before_trade('EURUSD')
        
        self.assertEqual(result1, result2)
        self.assertEqual(spread_info1.spread_pips, spread_info2.spread_pips)
        
        # Check cache contains the symbol
        self.assertIn('EURUSD', self.spread_checker.quote_cache)
        
    def test_disabled_checker(self):
        """Test spread checker when disabled"""
        # Disable spread checker
        self.spread_checker.config['enabled'] = False
        
        # Should always return ALLOWED
        result, spread_info = self.spread_checker.check_spread_before_trade('EURUSD')
        self.assertEqual(result, SpreadCheckResult.ALLOWED)
        self.assertIsNone(spread_info)
        
    def test_is_trade_allowed_method(self):
        """Test simple boolean is_trade_allowed method"""
        # Acceptable spread
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0851)  # 1 pip
        self.assertTrue(self.spread_checker.is_trade_allowed('EURUSD'))
        
        # Unacceptable spread
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0853)  # 3 pips
        self.assertFalse(self.spread_checker.is_trade_allowed('EURUSD'))
        
        # High spread with override (should be allowed with warning)
        self.mock_mt5.set_mock_tick('BTCUSD', 45000.0, 45100.0)  # High spread
        self.assertTrue(self.spread_checker.is_trade_allowed('BTCUSD'))
        
    def test_update_symbol_limit(self):
        """Test updating symbol-specific limits"""
        # Update limit for EURUSD
        self.spread_checker.update_symbol_limit('EURUSD', 1.5)
        
        # Verify limit was updated
        self.assertEqual(self.spread_checker.config['symbol_specific_limits']['EURUSD'], 1.5)
        
        # Test with new limit
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0852)  # 2 pips > 1.5 limit
        result, _ = self.spread_checker.check_spread_before_trade('EURUSD')
        self.assertEqual(result, SpreadCheckResult.BLOCKED_HIGH_SPREAD)
        
    def test_enable_high_spread_override(self):
        """Test enabling/disabling high spread override"""
        # Enable override for EURUSD
        self.spread_checker.enable_high_spread_override('EURUSD', True)
        
        # Test with high spread (should be allowed with warning)
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0855)  # 5 pips > 2.0 limit
        result, _ = self.spread_checker.check_spread_before_trade('EURUSD')
        self.assertEqual(result, SpreadCheckResult.WARNING_FALLBACK)
        
        # Disable override
        self.spread_checker.enable_high_spread_override('EURUSD', False)
        
        # Should now be blocked
        result, _ = self.spread_checker.check_spread_before_trade('EURUSD')
        self.assertEqual(result, SpreadCheckResult.BLOCKED_HIGH_SPREAD)
        
    def test_get_spread_info(self):
        """Test getting spread info without trade check"""
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0852)
        
        spread_info = self.spread_checker.get_spread_info('EURUSD')
        
        self.assertIsNotNone(spread_info)
        self.assertEqual(spread_info.symbol, 'EURUSD')
        self.assertEqual(spread_info.bid, 1.0850)
        self.assertEqual(spread_info.ask, 1.0852)
        self.assertAlmostEqual(spread_info.spread_pips, 2.0, places=1)
        
    def test_get_stats(self):
        """Test getting spread checker statistics"""
        stats = self.spread_checker.get_stats()
        
        self.assertTrue(stats['enabled'])
        self.assertEqual(stats['default_max_spread'], 3.0)
        self.assertEqual(stats['symbol_count'], 4)  # EURUSD, GBPUSD, XAUUSD, BTCUSD
        self.assertEqual(stats['override_count'], 2)  # BTCUSD, XAUUSD
        
    def test_invalid_tick_data(self):
        """Test handling of invalid tick data"""
        # Test with zero bid/ask
        self.mock_mt5.set_mock_tick('EURUSD', 0.0, 0.0)
        result, spread_info = self.spread_checker.check_spread_before_trade('EURUSD')
        self.assertEqual(result, SpreadCheckResult.BLOCKED_NO_QUOTES)
        
        # Test with negative prices
        self.mock_mt5.set_mock_tick('EURUSD', -1.0, -0.5)
        result, spread_info = self.spread_checker.check_spread_before_trade('EURUSD')
        self.assertEqual(result, SpreadCheckResult.BLOCKED_NO_QUOTES)
        
    def test_signal_data_logging(self):
        """Test logging with signal data"""
        signal_data = {
            'id': 123,
            'symbol': 'EURUSD',
            'action': 'BUY',
            'provider': 'test_provider',
            'confidence': 0.85
        }
        
        # Test with high spread (should be logged with signal data)
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0853)  # 3 pips
        result, _ = self.spread_checker.check_spread_before_trade('EURUSD', signal_data)
        
        self.assertEqual(result, SpreadCheckResult.BLOCKED_HIGH_SPREAD)
        
        # Verify log file was created
        self.assertTrue(os.path.exists(self.log_file))
        
    def test_config_not_found(self):
        """Test initialization with missing config file"""
        # Create spread checker with non-existent config
        nonexistent_config = os.path.join(self.temp_dir, 'nonexistent.json')
        checker = SpreadChecker(nonexistent_config, self.log_file)
        
        # Should use default config
        self.assertTrue(checker.config['enabled'])
        self.assertEqual(checker.config['default_max_spread_pips'], 3.0)
        
    def test_malformed_config(self):
        """Test initialization with malformed config file"""
        # Create malformed config file
        malformed_config = os.path.join(self.temp_dir, 'malformed.json')
        with open(malformed_config, 'w') as f:
            f.write('{ invalid json }')
            
        checker = SpreadChecker(malformed_config, self.log_file)
        
        # Should use default config
        self.assertTrue(checker.config['enabled'])
        self.assertEqual(checker.config['default_max_spread_pips'], 3.0)

if __name__ == '__main__':
    unittest.main()