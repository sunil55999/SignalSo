"""
Test Suite for Smart Entry Mode Engine
Tests intelligent entry execution, price monitoring, and integration with market conditions
"""

import unittest
import asyncio
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smart_entry_mode import (
    SmartEntryMode, EntryMode, EntryStatus, EntryCondition, EntryAttempt
)

class MockMT5Bridge:
    """Mock MT5 bridge for testing"""
    
    def __init__(self):
        self.mock_ticks = {}
        self.trade_results = {}
        self.connection_status = True
        
    def set_mock_tick(self, symbol: str, bid: float, ask: float, volume: float = 1000):
        """Set mock tick data for symbol"""
        self.mock_ticks[symbol] = {
            'bid': bid,
            'ask': ask,
            'last': (bid + ask) / 2,
            'volume': volume,
            'time': datetime.now(),
            'symbol': symbol
        }
        
    def get_symbol_tick(self, symbol: str):
        """Mock implementation of get_symbol_tick"""
        if not self.connection_status:
            return None
        return self.mock_ticks.get(symbol, None)
        
    async def execute_trade(self, trade_request: dict):
        """Mock trade execution"""
        symbol = trade_request.get('symbol')
        if symbol in self.trade_results:
            return self.trade_results[symbol]
        
        # Default successful execution
        return {
            'success': True,
            'ticket': 123456,
            'price': trade_request.get('price', 1.0),
            'volume': trade_request.get('volume', 0.1)
        }
        
    def set_trade_result(self, symbol: str, result: dict):
        """Set mock trade execution result"""
        self.trade_results[symbol] = result

class MockSpreadChecker:
    """Mock spread checker for testing"""
    
    def __init__(self):
        self.blocked_symbols = set()
        
    def check_spread_before_trade(self, symbol: str):
        """Mock spread check"""
        if symbol in self.blocked_symbols:
            return type('SpreadResult', (), {'value': 'blocked_high_spread'})(), None
        return type('SpreadResult', (), {'value': 'allowed'})(), None
        
    def block_symbol(self, symbol: str):
        """Block symbol for testing"""
        self.blocked_symbols.add(symbol)
        
    def unblock_symbol(self, symbol: str):
        """Unblock symbol for testing"""
        self.blocked_symbols.discard(symbol)

class TestSmartEntryMode(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "smart_entry": {
                "enabled": True,
                "default_mode": "smart_wait",
                "default_wait_seconds": 60,  # Shorter for testing
                "default_price_tolerance_pips": 2.0,
                "max_concurrent_entries": 10,
                "price_update_interval": 0.1,  # Faster for testing
                "cleanup_completed_hours": 1,
                "require_spread_improvement": True,
                "fallback_to_immediate": True,
                "symbol_specific_settings": {
                    "EURUSD": {
                        "price_tolerance_pips": 1.5,
                        "max_wait_seconds": 30
                    }
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize smart entry mode
        self.smart_entry = SmartEntryMode(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
        # Setup mocks
        self.setup_mocks()
        
    def tearDown(self):
        """Clean up test environment"""
        self.smart_entry.stop_monitoring()
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
    def setup_mocks(self):
        """Setup mock dependencies"""
        self.mock_mt5 = MockMT5Bridge()
        self.mock_spread_checker = MockSpreadChecker()
        self.mock_strategy_runtime = Mock()
        
        self.smart_entry.set_dependencies(
            mt5_bridge=self.mock_mt5,
            spread_checker=self.mock_spread_checker,
            strategy_runtime=self.mock_strategy_runtime
        )

class TestBasicFunctionality(TestSmartEntryMode):
    """Test basic smart entry functionality"""
    
    def test_initialization(self):
        """Test smart entry mode initialization"""
        self.assertTrue(self.smart_entry.config['enabled'])
        self.assertEqual(self.smart_entry.config['default_wait_seconds'], 60)
        self.assertEqual(self.smart_entry.config['default_price_tolerance_pips'], 2.0)
        
    def test_pip_value_calculation(self):
        """Test pip value calculation for different symbols"""
        self.assertEqual(self.smart_entry._get_pip_value('EURUSD'), 0.00001)
        self.assertEqual(self.smart_entry._get_pip_value('USDJPY'), 0.001)
        self.assertEqual(self.smart_entry._get_pip_value('XAUUSD'), 0.01)
        self.assertEqual(self.smart_entry._get_pip_value('UNKNOWN'), 0.00001)
        
    def test_symbol_specific_settings(self):
        """Test symbol-specific settings retrieval"""
        eurusd_settings = self.smart_entry._get_symbol_settings('EURUSD')
        self.assertEqual(eurusd_settings['price_tolerance_pips'], 1.5)
        self.assertEqual(eurusd_settings['max_wait_seconds'], 30)
        
        # Test default settings for unknown symbol
        unknown_settings = self.smart_entry._get_symbol_settings('UNKNOWN')
        self.assertEqual(unknown_settings['price_tolerance_pips'], 2.0)
        self.assertEqual(unknown_settings['max_wait_seconds'], 60)

class TestPriceAnalysis(TestSmartEntryMode):
    """Test price analysis and favorability checks"""
    
    def test_get_current_price(self):
        """Test current price retrieval"""
        # Set mock price data
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0852, 1000)
        
        price_data = self.smart_entry._get_current_price('EURUSD')
        
        self.assertIsNotNone(price_data)
        self.assertEqual(price_data['symbol'], 'EURUSD')
        self.assertEqual(price_data['bid'], 1.0850)
        self.assertEqual(price_data['ask'], 1.0852)
        self.assertEqual(price_data['spread'], 0.0002)
        
    def test_price_favorability_buy(self):
        """Test price favorability check for BUY orders"""
        # BUY should be favorable when current price is at or below target + tolerance
        target_price = 1.1000
        tolerance_pips = 2.0
        
        # Price exactly at target - should be favorable
        self.assertTrue(self.smart_entry._is_price_favorable(1.1000, target_price, 'BUY', tolerance_pips, 'EURUSD'))
        
        # Price below target - should be favorable
        self.assertTrue(self.smart_entry._is_price_favorable(1.0998, target_price, 'BUY', tolerance_pips, 'EURUSD'))
        
        # Price within tolerance above target - should be favorable
        self.assertTrue(self.smart_entry._is_price_favorable(1.1001, target_price, 'BUY', tolerance_pips, 'EURUSD'))
        
        # Price too far above target - should not be favorable
        self.assertFalse(self.smart_entry._is_price_favorable(1.1003, target_price, 'BUY', tolerance_pips, 'EURUSD'))
        
    def test_price_favorability_sell(self):
        """Test price favorability check for SELL orders"""
        # SELL should be favorable when current price is at or above target - tolerance
        target_price = 1.1000
        tolerance_pips = 2.0
        
        # Price exactly at target - should be favorable
        self.assertTrue(self.smart_entry._is_price_favorable(1.1000, target_price, 'SELL', tolerance_pips, 'EURUSD'))
        
        # Price above target - should be favorable
        self.assertTrue(self.smart_entry._is_price_favorable(1.1002, target_price, 'SELL', tolerance_pips, 'EURUSD'))
        
        # Price within tolerance below target - should be favorable
        self.assertTrue(self.smart_entry._is_price_favorable(1.0999, target_price, 'SELL', tolerance_pips, 'EURUSD'))
        
        # Price too far below target - should not be favorable
        self.assertFalse(self.smart_entry._is_price_favorable(1.0997, target_price, 'SELL', tolerance_pips, 'EURUSD'))

class TestEntryRequests(TestSmartEntryMode):
    """Test smart entry request handling"""
    
    def test_request_smart_entry_basic(self):
        """Test basic smart entry request"""
        success = self.smart_entry.request_smart_entry(
            signal_id='test_001',
            symbol='EURUSD',
            direction='BUY',
            original_entry=1.1000,
            lot_size=0.1,
            stop_loss=1.0950,
            take_profit=1.1050
        )
        
        self.assertTrue(success)
        self.assertIn('test_001', self.smart_entry.active_entries)
        
        entry = self.smart_entry.active_entries['test_001']
        self.assertEqual(entry.symbol, 'EURUSD')
        self.assertEqual(entry.direction, 'BUY')
        self.assertEqual(entry.original_entry, 1.1000)
        self.assertEqual(entry.status, EntryStatus.WAITING)
        self.assertLess(entry.target_entry, entry.original_entry)  # BUY target should be lower
        
    def test_request_smart_entry_sell(self):
        """Test smart entry request for SELL order"""
        success = self.smart_entry.request_smart_entry(
            signal_id='test_002',
            symbol='GBPUSD',
            direction='SELL',
            original_entry=1.2500,
            lot_size=0.2
        )
        
        self.assertTrue(success)
        
        entry = self.smart_entry.active_entries['test_002']
        self.assertEqual(entry.direction, 'SELL')
        self.assertGreater(entry.target_entry, entry.original_entry)  # SELL target should be higher
        
    def test_duplicate_signal_rejection(self):
        """Test rejection of duplicate signal requests"""
        # First request should succeed
        success1 = self.smart_entry.request_smart_entry(
            signal_id='test_003',
            symbol='EURUSD',
            direction='BUY',
            original_entry=1.1000,
            lot_size=0.1
        )
        self.assertTrue(success1)
        
        # Second request with same signal ID should fail
        success2 = self.smart_entry.request_smart_entry(
            signal_id='test_003',
            symbol='GBPUSD',
            direction='SELL',
            original_entry=1.2500,
            lot_size=0.1
        )
        self.assertFalse(success2)
        
    def test_concurrent_entry_limit(self):
        """Test concurrent entry limit enforcement"""
        # Fill up to limit
        for i in range(self.smart_entry.config['max_concurrent_entries']):
            success = self.smart_entry.request_smart_entry(
                signal_id=f'test_{i}',
                symbol='EURUSD',
                direction='BUY',
                original_entry=1.1000,
                lot_size=0.1
            )
            self.assertTrue(success)
            
        # Next request should fail
        success = self.smart_entry.request_smart_entry(
            signal_id='test_overflow',
            symbol='EURUSD',
            direction='BUY',
            original_entry=1.1000,
            lot_size=0.1
        )
        self.assertFalse(success)

class TestExecutionLogic(TestSmartEntryMode):
    """Test execution decision logic"""
    
    def test_immediate_execution_conditions(self):
        """Test conditions that trigger immediate execution"""
        # Create entry attempt
        condition = EntryCondition(max_wait_seconds=60, price_tolerance_pips=2.0)
        entry = EntryAttempt(
            signal_id='test_001',
            symbol='EURUSD',
            original_entry=1.1000,
            target_entry=1.0999,
            direction='BUY',
            lot_size=0.1,
            stop_loss=1.0950,
            take_profit=1.1050,
            mode=EntryMode.SMART_WAIT,
            condition=condition,
            start_time=datetime.now()
        )
        
        # Test favorable price condition
        price_data = {'bid': 1.0850, 'ask': 1.0999, 'last': 1.08745}  # Ask at target
        should_execute, reason = self.smart_entry._should_execute_immediately(entry, price_data)
        self.assertTrue(should_execute)
        self.assertIn("Favorable price", reason)
        
        # Test timeout condition
        entry.start_time = datetime.now() - timedelta(seconds=70)  # Past timeout
        price_data = {'bid': 1.0850, 'ask': 1.1005, 'last': 1.09275}  # Price not favorable
        should_execute, reason = self.smart_entry._should_execute_immediately(entry, price_data)
        self.assertTrue(should_execute)
        self.assertIn("Maximum wait time", reason)
        
    def test_waiting_conditions(self):
        """Test conditions that keep entry in waiting state"""
        condition = EntryCondition(max_wait_seconds=60, price_tolerance_pips=1.0)
        entry = EntryAttempt(
            signal_id='test_001',
            symbol='EURUSD',
            original_entry=1.1000,
            target_entry=1.0999,
            direction='BUY',
            lot_size=0.1,
            stop_loss=1.0950,
            take_profit=1.1050,
            mode=EntryMode.SMART_WAIT,
            condition=condition,
            start_time=datetime.now()
        )
        
        # Price not favorable and within timeout
        price_data = {'bid': 1.0850, 'ask': 1.1005, 'last': 1.09275}  # Ask too high
        should_execute, reason = self.smart_entry._should_execute_immediately(entry, price_data)
        self.assertFalse(should_execute)
        self.assertIn("Waiting for better", reason)

class TestAsyncOperations(TestSmartEntryMode):
    """Test asynchronous operations"""
    
    def test_trade_execution_success(self):
        """Test successful trade execution"""
        async def run_test():
            # Setup successful trade result
            self.mock_mt5.set_trade_result('EURUSD', {
                'success': True,
                'ticket': 123456,
                'price': 1.0999
            })
            
            # Set price data
            self.mock_mt5.set_mock_tick('EURUSD', 1.0998, 1.0999)
            
            # Create entry attempt
            condition = EntryCondition(max_wait_seconds=60, price_tolerance_pips=2.0)
            entry = EntryAttempt(
                signal_id='test_001',
                symbol='EURUSD',
                original_entry=1.1000,
                target_entry=1.0999,
                direction='BUY',
                lot_size=0.1,
                stop_loss=1.0950,
                take_profit=1.1050,
                mode=EntryMode.SMART_WAIT,
                condition=condition,
                start_time=datetime.now()
            )
            
            # Execute trade
            success = await self.smart_entry._execute_trade(entry, "Test execution")
            
            self.assertTrue(success)
            self.assertEqual(entry.status, EntryStatus.EXECUTED)
            self.assertEqual(entry.execution_price, 1.0999)
            self.assertIsNotNone(entry.execution_time)
            
        asyncio.run(run_test())
        
    def test_trade_execution_failure(self):
        """Test failed trade execution"""
        async def run_test():
            # Setup failed trade result
            self.mock_mt5.set_trade_result('EURUSD', {
                'success': False,
                'error': 'Insufficient margin'
            })
            
            # Set price data
            self.mock_mt5.set_mock_tick('EURUSD', 1.0998, 1.0999)
            
            # Create entry attempt
            condition = EntryCondition(max_wait_seconds=60, price_tolerance_pips=2.0)
            entry = EntryAttempt(
                signal_id='test_001',
                symbol='EURUSD',
                original_entry=1.1000,
                target_entry=1.0999,
                direction='BUY',
                lot_size=0.1,
                stop_loss=1.0950,
                take_profit=1.1050,
                mode=EntryMode.SMART_WAIT,
                condition=condition,
                start_time=datetime.now()
            )
            
            # Execute trade
            success = await self.smart_entry._execute_trade(entry, "Test execution")
            
            self.assertFalse(success)
            self.assertEqual(entry.status, EntryStatus.WAITING)  # Status unchanged on failure
            
        asyncio.run(run_test())

class TestSpreadIntegration(TestSmartEntryMode):
    """Test integration with spread checker"""
    
    def test_spread_blocking(self):
        """Test trade blocking due to high spread"""
        # Block EURUSD in spread checker
        self.mock_spread_checker.block_symbol('EURUSD')
        
        # Create entry attempt
        condition = EntryCondition(max_wait_seconds=60, price_tolerance_pips=2.0, require_spread_improvement=True)
        entry = EntryAttempt(
            signal_id='test_001',
            symbol='EURUSD',
            original_entry=1.1000,
            target_entry=1.0999,
            direction='BUY',
            lot_size=0.1,
            stop_loss=1.0950,
            take_profit=1.1050,
            mode=EntryMode.SMART_WAIT,
            condition=condition,
            start_time=datetime.now()
        )
        
        # Test execution decision with blocked spread
        price_data = {'bid': 1.0998, 'ask': 1.0999, 'last': 1.09985}  # Favorable price
        should_execute, reason = self.smart_entry._should_execute_immediately(entry, price_data)
        
        self.assertFalse(should_execute)
        self.assertIn("Spread check failed", reason)

class TestUtilityFunctions(TestSmartEntryMode):
    """Test utility and management functions"""
    
    def test_cancel_entry_attempt(self):
        """Test cancelling an active entry attempt"""
        # Create entry
        self.smart_entry.request_smart_entry(
            signal_id='test_001',
            symbol='EURUSD',
            direction='BUY',
            original_entry=1.1000,
            lot_size=0.1
        )
        
        # Cancel entry
        success = self.smart_entry.cancel_entry_attempt('test_001', 'Test cancellation')
        
        self.assertTrue(success)
        self.assertNotIn('test_001', self.smart_entry.active_entries)
        
        # Check it moved to completed
        cancelled_entry = None
        for entry in self.smart_entry.completed_entries:
            if entry.signal_id == 'test_001':
                cancelled_entry = entry
                break
                
        self.assertIsNotNone(cancelled_entry)
        self.assertEqual(cancelled_entry.status, EntryStatus.CANCELLED)
        self.assertEqual(cancelled_entry.reason, 'Test cancellation')
        
    def test_get_entry_status(self):
        """Test entry status retrieval"""
        # Test active entry
        self.smart_entry.request_smart_entry(
            signal_id='test_001',
            symbol='EURUSD',
            direction='BUY',
            original_entry=1.1000,
            lot_size=0.1
        )
        
        status = self.smart_entry.get_entry_status('test_001')
        self.assertIsNotNone(status)
        self.assertEqual(status.status, EntryStatus.WAITING)
        
        # Test non-existent entry
        status = self.smart_entry.get_entry_status('non_existent')
        self.assertIsNone(status)
        
    def test_statistics_calculation(self):
        """Test statistics calculation"""
        # Initially empty
        stats = self.smart_entry.get_statistics()
        self.assertEqual(stats['total_attempts'], 0)
        self.assertEqual(stats['success_rate'], 0.0)
        
        # Add some completed entries
        for i, status in enumerate([EntryStatus.EXECUTED, EntryStatus.TIMEOUT, EntryStatus.CANCELLED]):
            entry = EntryAttempt(
                signal_id=f'test_{i}',
                symbol='EURUSD',
                original_entry=1.1000,
                target_entry=1.0999,
                direction='BUY',
                lot_size=0.1,
                stop_loss=1.0950,
                take_profit=1.1050,
                mode=EntryMode.SMART_WAIT,
                condition=EntryCondition(60, 2.0),
                start_time=datetime.now()
            )
            entry.status = status
            if status == EntryStatus.EXECUTED:
                entry.execution_time = datetime.now()
            self.smart_entry.completed_entries.append(entry)
            
        stats = self.smart_entry.get_statistics()
        self.assertEqual(stats['total_attempts'], 3)
        self.assertEqual(stats['successful'], 1)
        self.assertEqual(stats['timeouts'], 1)
        self.assertEqual(stats['cancelled'], 1)
        self.assertAlmostEqual(stats['success_rate'], 33.33, places=1)
        
    def test_cleanup_old_entries(self):
        """Test cleanup of old completed entries"""
        # Add old entry
        old_entry = EntryAttempt(
            signal_id='old_test',
            symbol='EURUSD',
            original_entry=1.1000,
            target_entry=1.0999,
            direction='BUY',
            lot_size=0.1,
            stop_loss=1.0950,
            take_profit=1.1050,
            mode=EntryMode.SMART_WAIT,
            condition=EntryCondition(60, 2.0),
            start_time=datetime.now() - timedelta(hours=25)  # Older than default cleanup time
        )
        old_entry.status = EntryStatus.EXECUTED
        self.smart_entry.completed_entries.append(old_entry)
        
        # Add recent entry
        recent_entry = EntryAttempt(
            signal_id='recent_test',
            symbol='EURUSD',
            original_entry=1.1000,
            target_entry=1.0999,
            direction='BUY',
            lot_size=0.1,
            stop_loss=1.0950,
            take_profit=1.1050,
            mode=EntryMode.SMART_WAIT,
            condition=EntryCondition(60, 2.0),
            start_time=datetime.now() - timedelta(hours=1)
        )
        recent_entry.status = EntryStatus.EXECUTED
        self.smart_entry.completed_entries.append(recent_entry)
        
        # Clean up
        removed_count = self.smart_entry.cleanup_old_entries()
        
        self.assertEqual(removed_count, 1)
        self.assertEqual(len(self.smart_entry.completed_entries), 1)
        self.assertEqual(self.smart_entry.completed_entries[0].signal_id, 'recent_test')

if __name__ == '__main__':
    unittest.main()