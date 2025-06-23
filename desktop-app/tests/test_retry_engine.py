"""
Test suite for the Retry Engine module
Tests retry logic, configuration loading, and edge cases
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from retry_engine import RetryEngine, RetryReason, TradeRequest, RetryEntry

class TestRetryEngine(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment with temporary files"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        self.log_file = os.path.join(self.temp_dir, "test_retry_log.json")
        
        # Create test configuration
        test_config = {
            "retry_delays": {
                "mt5_disconnected": [5, 10, 20],
                "high_slippage": [2, 5, 10]
            },
            "max_attempts": {
                "mt5_disconnected": 3,
                "high_slippage": 3
            },
            "conditions": {
                "max_slippage_pips": 2.0,
                "max_spread_pips": 3.0
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
        
        self.retry_engine = RetryEngine(self.config_file, self.log_file)
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_config_loading(self):
        """Test configuration file loading"""
        self.assertIn("retry_delays", self.retry_engine.config)
        self.assertIn("max_attempts", self.retry_engine.config)
        self.assertEqual(self.retry_engine.config["max_attempts"]["mt5_disconnected"], 3)
    
    def test_add_failed_trade(self):
        """Test adding a failed trade to retry buffer"""
        trade_request = TradeRequest(
            signal_id=123,
            symbol="EURUSD",
            action="BUY",
            lot_size=0.01,
            entry_price=1.1000
        )
        
        retry_id = self.retry_engine.add_failed_trade(
            trade_request,
            RetryReason.MT5_DISCONNECTED,
            "Connection lost"
        )
        
        self.assertIn(retry_id, self.retry_engine.retry_buffer)
        entry = self.retry_engine.retry_buffer[retry_id]
        self.assertEqual(entry.trade_request.signal_id, 123)
        self.assertEqual(entry.reason, RetryReason.MT5_DISCONNECTED)
        self.assertEqual(entry.attempts, 0)
    
    def test_retry_attempt_success(self):
        """Test marking retry attempt as successful"""
        trade_request = TradeRequest(
            signal_id=456,
            symbol="GBPUSD",
            action="SELL",
            lot_size=0.02
        )
        
        retry_id = self.retry_engine.add_failed_trade(
            trade_request,
            RetryReason.HIGH_SLIPPAGE
        )
        
        # Mark as successful
        success = self.retry_engine.mark_retry_attempt(retry_id, True)
        
        self.assertTrue(success)
        self.assertNotIn(retry_id, self.retry_engine.retry_buffer)
    
    def test_retry_attempt_failure(self):
        """Test marking retry attempt as failed"""
        trade_request = TradeRequest(
            signal_id=789,
            symbol="USDJPY",
            action="BUY",
            lot_size=0.01
        )
        
        retry_id = self.retry_engine.add_failed_trade(
            trade_request,
            RetryReason.MT5_DISCONNECTED
        )
        
        initial_attempts = self.retry_engine.retry_buffer[retry_id].attempts
        
        # Mark as failed
        success = self.retry_engine.mark_retry_attempt(retry_id, False, "Still disconnected")
        
        self.assertTrue(success)
        self.assertEqual(self.retry_engine.retry_buffer[retry_id].attempts, initial_attempts + 1)
    
    def test_max_attempts_reached(self):
        """Test that entry is removed after max attempts"""
        trade_request = TradeRequest(
            signal_id=999,
            symbol="EURGBP",
            action="BUY",
            lot_size=0.01
        )
        
        retry_id = self.retry_engine.add_failed_trade(
            trade_request,
            RetryReason.HIGH_SLIPPAGE
        )
        
        # Fail 3 times (max attempts)
        for i in range(3):
            self.retry_engine.mark_retry_attempt(retry_id, False, f"Attempt {i+1} failed")
        
        # Should be removed after max attempts
        self.assertNotIn(retry_id, self.retry_engine.retry_buffer)
    
    def test_pending_retries(self):
        """Test getting pending retries"""
        trade_request = TradeRequest(
            signal_id=111,
            symbol="AUDUSD",
            action="BUY",
            lot_size=0.01
        )
        
        # Add a failed trade
        retry_id = self.retry_engine.add_failed_trade(
            trade_request,
            RetryReason.MT5_DISCONNECTED
        )
        
        # Manually set next_retry to past time to make it pending
        self.retry_engine.retry_buffer[retry_id].next_retry = datetime.now() - timedelta(minutes=1)
        
        pending = self.retry_engine.get_pending_retries()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].id, retry_id)
    
    def test_should_retry_trade_analysis(self):
        """Test MT5 result analysis for retry decisions"""
        # Test MT5 disconnection
        result = {
            "success": False,
            "error_code": 6,
            "error_message": "No connection to trade server"
        }
        reason = self.retry_engine.should_retry_trade(result)
        self.assertEqual(reason, RetryReason.MT5_DISCONNECTED)
        
        # Test market closed
        result = {
            "success": False,
            "error_code": 132,
            "error_message": "Market is closed"
        }
        reason = self.retry_engine.should_retry_trade(result)
        self.assertEqual(reason, RetryReason.MARKET_CLOSED)
        
        # Test insufficient margin
        result = {
            "success": False,
            "error_code": 134,
            "error_message": "Not enough money"
        }
        reason = self.retry_engine.should_retry_trade(result)
        self.assertEqual(reason, RetryReason.INSUFFICIENT_MARGIN)
        
        # Test successful trade (no retry needed)
        result = {"success": True}
        reason = self.retry_engine.should_retry_trade(result)
        self.assertIsNone(reason)
    
    def test_market_conditions_check(self):
        """Test market conditions analysis"""
        # Test wide spread
        reason = self.retry_engine.check_market_conditions("EURUSD", 1.1000, 5.0)
        self.assertEqual(reason, RetryReason.WIDE_SPREAD)
        
        # Test normal spread
        reason = self.retry_engine.check_market_conditions("EURUSD", 1.1000, 1.5)
        self.assertIsNone(reason)
    
    def test_retry_stats(self):
        """Test retry statistics calculation"""
        # Add some failed trades
        for i in range(3):
            trade_request = TradeRequest(
                signal_id=i,
                symbol="EURUSD",
                action="BUY",
                lot_size=0.01
            )
            self.retry_engine.add_failed_trade(
                trade_request,
                RetryReason.MT5_DISCONNECTED
            )
        
        stats = self.retry_engine.get_retry_stats()
        self.assertEqual(stats["total_pending"], 3)
        self.assertIn("mt5_disconnected", stats["by_reason"])
        self.assertEqual(stats["by_reason"]["mt5_disconnected"]["count"], 3)
    
    def test_cleanup_expired_retries(self):
        """Test cleanup of old retry entries"""
        trade_request = TradeRequest(
            signal_id=555,
            symbol="EURUSD",
            action="BUY",
            lot_size=0.01
        )
        
        retry_id = self.retry_engine.add_failed_trade(
            trade_request,
            RetryReason.MT5_DISCONNECTED
        )
        
        # Manually set creation time to 25 hours ago
        self.retry_engine.retry_buffer[retry_id].created_at = datetime.now() - timedelta(hours=25)
        
        # Cleanup entries older than 24 hours
        expired_count = self.retry_engine.cleanup_expired_retries(24)
        
        self.assertEqual(expired_count, 1)
        self.assertNotIn(retry_id, self.retry_engine.retry_buffer)
    
    def test_buffer_persistence(self):
        """Test that retry buffer is saved and loaded correctly"""
        trade_request = TradeRequest(
            signal_id=777,
            symbol="GBPUSD",
            action="SELL",
            lot_size=0.01
        )
        
        retry_id = self.retry_engine.add_failed_trade(
            trade_request,
            RetryReason.HIGH_SLIPPAGE
        )
        
        # Create new engine instance to test loading
        new_engine = RetryEngine(self.config_file, self.log_file)
        
        self.assertIn(retry_id, new_engine.retry_buffer)
        self.assertEqual(new_engine.retry_buffer[retry_id].trade_request.signal_id, 777)

class TestRetryEngineIntegration(unittest.TestCase):
    """Integration tests for retry engine with mock MT5 connections"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.json")
        self.log_file = os.path.join(self.temp_dir, "retry_log.json")
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('time.sleep')
    def test_retry_cycle_simulation(self, mock_sleep):
        """Test a complete retry cycle simulation"""
        retry_engine = RetryEngine(self.config_file, self.log_file)
        
        trade_request = TradeRequest(
            signal_id=888,
            symbol="EURUSD",
            action="BUY",
            lot_size=0.01,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050
        )
        
        # Simulate failed trade
        retry_id = retry_engine.add_failed_trade(
            trade_request,
            RetryReason.MT5_DISCONNECTED,
            "Connection timeout"
        )
        
        # Simulate retry attempts
        for attempt in range(2):
            # Make retry pending
            retry_engine.retry_buffer[retry_id].next_retry = datetime.now() - timedelta(seconds=1)
            
            pending = retry_engine.get_pending_retries()
            self.assertEqual(len(pending), 1)
            
            # Simulate failed retry
            retry_engine.mark_retry_attempt(retry_id, False, f"Retry {attempt + 1} failed")
        
        # Final successful retry
        retry_engine.retry_buffer[retry_id].next_retry = datetime.now() - timedelta(seconds=1)
        retry_engine.mark_retry_attempt(retry_id, True)
        
        # Should be removed from buffer
        self.assertNotIn(retry_id, retry_engine.retry_buffer)

if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    unittest.main(verbosity=2)