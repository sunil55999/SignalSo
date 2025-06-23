"""
Test Suite for Break Even Engine
Tests pip-based triggers, percentage triggers, buffer calculations, and edge cases
"""

import unittest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from break_even import (
    BreakEvenEngine, BreakEvenConfig, BreakEvenPosition, 
    BreakEvenTrigger, TradeDirection, BreakEvenUpdate
)


class TestBreakEvenEngine(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'break_even': {
                'update_interval_seconds': 5,
                'default_trigger_pips': 10.0,
                'default_buffer_pips': 1.0,
                'min_profit_threshold_pips': 5.0,
                'pip_values': {
                    'EURUSD': 0.0001,
                    'GBPUSD': 0.0001,
                    'USDJPY': 0.01,
                    'default': 0.0001
                },
                'max_positions_to_monitor': 100
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        json.dump([], self.temp_log)
        self.temp_log.close()
        
        self.engine = BreakEvenEngine(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
        
        # Mock MT5 bridge
        self.mock_mt5_bridge = Mock()
        self.mock_mt5_bridge.modify_position = AsyncMock()
        self.mock_mt5_bridge.get_current_price = AsyncMock()
        
        # Mock market data
        self.mock_market_data = Mock()
        self.mock_market_data.get_current_price = AsyncMock()
        
        self.engine.inject_modules(
            mt5_bridge=self.mock_mt5_bridge,
            market_data=self.mock_market_data
        )
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_pip_value_calculation(self):
        """Test pip value calculations for different symbols"""
        test_cases = [
            ('EURUSD', 0.0001),
            ('GBPUSD', 0.0001),
            ('USDJPY', 0.01),
            ('UNKNOWN', 0.0001),  # Should use default
        ]
        
        for symbol, expected_pip_value in test_cases:
            with self.subTest(symbol=symbol):
                pip_value = self.engine.get_pip_value(symbol)
                self.assertEqual(pip_value, expected_pip_value)
    
    def test_pips_calculation(self):
        """Test pips calculation from price differences"""
        test_cases = [
            ('EURUSD', 0.0010, 10.0),  # 10 pips
            ('EURUSD', 0.0050, 50.0),  # 50 pips
            ('USDJPY', 0.10, 10.0),    # 10 pips for JPY
            ('GBPUSD', 0.0025, 25.0),  # 25 pips
        ]
        
        for symbol, price_diff, expected_pips in test_cases:
            with self.subTest(symbol=symbol, price_diff=price_diff):
                pips = self.engine.calculate_pips(symbol, price_diff)
                self.assertEqual(pips, expected_pips)
    
    def test_price_to_pips_conversion(self):
        """Test conversion from pips to price difference"""
        test_cases = [
            ('EURUSD', 10.0, 0.0010),
            ('USDJPY', 20.0, 0.20),
            ('GBPUSD', 15.0, 0.0015),
        ]
        
        for symbol, pips, expected_price_diff in test_cases:
            with self.subTest(symbol=symbol, pips=pips):
                price_diff = self.engine.pips_to_price(symbol, pips)
                self.assertEqual(price_diff, expected_price_diff)
    
    def test_add_break_even_position(self):
        """Test adding position to break even monitoring"""
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.FIXED_PIPS,
            threshold_value=10.0,
            buffer_pips=1.0,
            min_profit_pips=5.0
        )
        
        success = self.engine.add_break_even_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        
        self.assertTrue(success)
        self.assertIn(12345, self.engine.break_even_positions)
        
        position = self.engine.break_even_positions[12345]
        self.assertEqual(position.symbol, "EURUSD")
        self.assertEqual(position.direction, TradeDirection.BUY)
        self.assertEqual(position.entry_price, 1.2000)
        self.assertEqual(position.current_sl, 1.1980)
        self.assertFalse(position.break_even_triggered)
    
    def test_remove_break_even_position(self):
        """Test removing position from break even monitoring"""
        # First add a position
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.FIXED_PIPS,
            threshold_value=10.0,
            buffer_pips=1.0
        )
        
        self.engine.add_break_even_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        
        # Now remove it
        success = self.engine.remove_break_even_position(12345)
        self.assertTrue(success)
        self.assertNotIn(12345, self.engine.break_even_positions)
        
        # Try removing non-existent position
        success = self.engine.remove_break_even_position(99999)
        self.assertFalse(success)
    
    def test_should_trigger_break_even_fixed_pips(self):
        """Test break even trigger logic for fixed pips"""
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.FIXED_PIPS,
            threshold_value=10.0,
            buffer_pips=1.0,
            min_profit_pips=5.0,
            only_when_profitable=True
        )
        
        position = BreakEvenPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_sl=1.1980,
            current_sl=1.1980,
            lot_size=1.0,
            config=config,
            last_update=datetime.now(),
            break_even_triggered=False
        )
        
        # Test case 1: Not enough profit
        current_price = 1.2004  # Only 4 pips profit
        should_trigger, reason = self.engine.should_trigger_break_even(position, current_price)
        self.assertFalse(should_trigger)
        self.assertIn("Insufficient profit", reason)
        
        # Test case 2: Enough profit but below threshold
        current_price = 1.2007  # 7 pips profit
        should_trigger, reason = self.engine.should_trigger_break_even(position, current_price)
        self.assertFalse(should_trigger)
        self.assertIn("Trigger conditions not met", reason)
        
        # Test case 3: Above threshold, should trigger
        current_price = 1.2010  # 10 pips profit
        should_trigger, reason = self.engine.should_trigger_break_even(position, current_price)
        self.assertTrue(should_trigger)
        self.assertIn("Fixed pips threshold reached", reason)
        
        # Test case 4: Already triggered
        position.break_even_triggered = True
        should_trigger, reason = self.engine.should_trigger_break_even(position, current_price)
        self.assertFalse(should_trigger)
        self.assertEqual(reason, "Already triggered")
    
    def test_should_trigger_break_even_percentage(self):
        """Test break even trigger logic for percentage"""
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.PERCENTAGE,
            threshold_value=0.5,  # 0.5%
            buffer_pips=1.0,
            min_profit_pips=5.0,
            only_when_profitable=True
        )
        
        position = BreakEvenPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_sl=1.1980,
            current_sl=1.1980,
            lot_size=1.0,
            config=config,
            last_update=datetime.now(),
            break_even_triggered=False
        )
        
        # Test percentage trigger
        current_price = 1.2060  # 60 pips = 0.5% of 1.2000
        should_trigger, reason = self.engine.should_trigger_break_even(position, current_price)
        self.assertTrue(should_trigger)
        self.assertIn("Percentage threshold reached", reason)
    
    def test_should_trigger_break_even_time_based(self):
        """Test break even trigger logic for time-based"""
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.TIME_BASED,
            threshold_value=30.0,  # 30 minutes
            buffer_pips=1.0,
            min_profit_pips=0.0,  # No minimum profit for time-based
            only_when_profitable=False
        )
        
        # Position opened 35 minutes ago
        entry_time = datetime.now() - timedelta(minutes=35)
        position = BreakEvenPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=entry_time,
            original_sl=1.1980,
            current_sl=1.1980,
            lot_size=1.0,
            config=config,
            last_update=datetime.now(),
            break_even_triggered=False
        )
        
        # Test time-based trigger with small profit
        current_price = 1.2002  # Small profit
        should_trigger, reason = self.engine.should_trigger_break_even(position, current_price)
        self.assertTrue(should_trigger)
        self.assertIn("Time threshold reached", reason)
    
    def test_should_trigger_break_even_ratio_based(self):
        """Test break even trigger logic for ratio-based"""
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.RATIO_BASED,
            threshold_value=2.0,  # 2:1 risk-reward ratio
            buffer_pips=1.0,
            min_profit_pips=5.0,
            only_when_profitable=True
        )
        
        position = BreakEvenPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_sl=1.1980,  # 20 pips risk
            current_sl=1.1980,
            lot_size=1.0,
            config=config,
            last_update=datetime.now(),
            break_even_triggered=False
        )
        
        # Test ratio-based trigger (40 pips profit = 2:1 ratio)
        current_price = 1.2040  # 40 pips profit
        should_trigger, reason = self.engine.should_trigger_break_even(position, current_price)
        self.assertTrue(should_trigger)
        self.assertIn("Risk-reward ratio reached", reason)
        self.assertIn("2.0:1", reason)
    
    def test_calculate_break_even_sl_buy(self):
        """Test break even SL calculation for BUY positions"""
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.FIXED_PIPS,
            threshold_value=10.0,
            buffer_pips=2.0  # 2 pips buffer
        )
        
        position = BreakEvenPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_sl=1.1980,
            current_sl=1.1980,
            lot_size=1.0,
            config=config,
            last_update=datetime.now()
        )
        
        break_even_sl = self.engine.calculate_break_even_sl(position)
        # Should be entry price + buffer (1.2000 + 0.0002)
        expected_sl = 1.2002
        self.assertEqual(break_even_sl, expected_sl)
    
    def test_calculate_break_even_sl_sell(self):
        """Test break even SL calculation for SELL positions"""
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.FIXED_PIPS,
            threshold_value=10.0,
            buffer_pips=2.0  # 2 pips buffer
        )
        
        position = BreakEvenPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.SELL,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_sl=1.2020,
            current_sl=1.2020,
            lot_size=1.0,
            config=config,
            last_update=datetime.now()
        )
        
        break_even_sl = self.engine.calculate_break_even_sl(position)
        # Should be entry price - buffer (1.2000 - 0.0002)
        expected_sl = 1.1998
        self.assertEqual(break_even_sl, expected_sl)
    
    async def test_update_stop_loss_success(self):
        """Test successful stop loss update via MT5 bridge"""
        self.mock_mt5_bridge.modify_position.return_value = {'success': True}
        
        result = await self.engine.update_stop_loss(12345, 1.2010)
        self.assertTrue(result)
        self.mock_mt5_bridge.modify_position.assert_called_once_with(
            ticket=12345,
            stop_loss=1.2010
        )
    
    async def test_update_stop_loss_failure(self):
        """Test failed stop loss update"""
        self.mock_mt5_bridge.modify_position.return_value = {'success': False, 'error': 'Invalid price'}
        
        result = await self.engine.update_stop_loss(12345, 1.2010)
        self.assertFalse(result)
    
    async def test_get_current_price(self):
        """Test getting current market price"""
        self.mock_market_data.get_current_price.return_value = 1.2015
        
        price = await self.engine.get_current_price("EURUSD")
        self.assertEqual(price, 1.2015)
        self.mock_market_data.get_current_price.assert_called_once_with("EURUSD")
    
    async def test_process_break_even_updates(self):
        """Test processing break even updates for all positions"""
        # Add test position
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.FIXED_PIPS,
            threshold_value=10.0,
            buffer_pips=1.0,
            min_profit_pips=5.0
        )
        
        self.engine.add_break_even_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        
        # Mock responses
        self.mock_market_data.get_current_price.return_value = 1.2015  # 15 pips profit
        self.mock_mt5_bridge.modify_position.return_value = {'success': True}
        
        # Process updates
        await self.engine.process_break_even_updates()
        
        # Verify position was updated
        position = self.engine.break_even_positions[12345]
        self.assertTrue(position.break_even_triggered)
        self.assertIsNotNone(position.current_sl)
        self.assertEqual(len(self.engine.update_history), 1)
        
        # Verify SL was moved to breakeven + buffer
        expected_sl = 1.2001  # Entry + 1 pip buffer
        self.assertEqual(position.current_sl, expected_sl)
    
    def test_get_break_even_statistics_empty(self):
        """Test statistics with no break even history"""
        stats = self.engine.get_break_even_statistics()
        
        expected = {
            'total_break_even_triggers': 0,
            'active_positions': 0,
            'triggered_positions': 0,
            'average_profit_at_trigger': 0.0,
            'most_common_trigger': None,
            'total_positions_monitored': 0
        }
        
        self.assertEqual(stats, expected)
    
    def test_get_break_even_statistics_with_data(self):
        """Test statistics with break even data"""
        # Add test position
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.FIXED_PIPS,
            threshold_value=10.0,
            buffer_pips=1.0
        )
        
        self.engine.add_break_even_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        
        # Mark as triggered
        position = self.engine.break_even_positions[12345]
        position.break_even_triggered = True
        
        # Add test update history
        update = BreakEvenUpdate(
            ticket=12345,
            new_sl=1.2001,
            old_sl=1.1980,
            entry_price=1.2000,
            trigger_price=1.2015,
            profit_pips=15.0,
            buffer_applied=1.0,
            trigger_reason="Test trigger",
            timestamp=datetime.now()
        )
        self.engine.update_history.append(update)
        
        stats = self.engine.get_break_even_statistics()
        
        self.assertEqual(stats['total_break_even_triggers'], 1)
        self.assertEqual(stats['active_positions'], 0)  # Position is triggered
        self.assertEqual(stats['triggered_positions'], 1)
        self.assertEqual(stats['average_profit_at_trigger'], 15.0)
        self.assertEqual(stats['most_common_trigger'], 'fixed_pips')
        self.assertEqual(stats['total_positions_monitored'], 1)
    
    def test_get_position_status(self):
        """Test getting status of specific position"""
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.FIXED_PIPS,
            threshold_value=10.0,
            buffer_pips=1.0
        )
        
        entry_time = datetime.now()
        self.engine.add_break_even_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=entry_time,
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        
        status = self.engine.get_position_status(12345)
        self.assertIsNotNone(status)
        self.assertEqual(status['ticket'], 12345)
        self.assertEqual(status['symbol'], "EURUSD")
        self.assertEqual(status['direction'], 'buy')
        self.assertEqual(status['trigger_method'], 'fixed_pips')
        self.assertEqual(status['threshold_value'], 10.0)
        self.assertEqual(status['buffer_pips'], 1.0)
        self.assertFalse(status['break_even_triggered'])
        
        # Test non-existent position
        status = self.engine.get_position_status(99999)
        self.assertIsNone(status)
    
    def test_get_recent_updates(self):
        """Test getting recent break even updates"""
        # Add test updates
        for i in range(5):
            update = BreakEvenUpdate(
                ticket=12345 + i,
                new_sl=1.2000 + i * 0.0001,
                old_sl=1.1990 + i * 0.0001,
                entry_price=1.1995 + i * 0.0001,
                trigger_price=1.2010 + i * 0.0001,
                profit_pips=10.0 + i,
                buffer_applied=1.0,
                trigger_reason=f"Test trigger {i}",
                timestamp=datetime.now()
            )
            self.engine.update_history.append(update)
        
        # Test default limit
        recent = self.engine.get_recent_updates()
        self.assertEqual(len(recent), 5)
        
        # Test custom limit
        recent = self.engine.get_recent_updates(limit=3)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0]['ticket'], 12347)  # Should be last 3


class TestBreakEvenIntegration(unittest.TestCase):
    """Integration tests for break even functionality"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'break_even': {
                'update_interval_seconds': 1,
                'default_trigger_pips': 10.0,
                'default_buffer_pips': 1.0,
                'min_profit_threshold_pips': 5.0,
                'pip_values': {
                    'EURUSD': 0.0001,
                    'default': 0.0001
                },
                'max_positions_to_monitor': 100
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        json.dump([], self.temp_log)
        self.temp_log.close()
        
        self.engine = BreakEvenEngine(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def tearDown(self):
        """Clean up integration test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_full_break_even_cycle_buy_position(self):
        """Test complete break even cycle for BUY position"""
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.FIXED_PIPS,
            threshold_value=10.0,
            buffer_pips=2.0,
            min_profit_pips=5.0,
            only_when_profitable=True
        )
        
        # Add position
        entry_time = datetime.now()
        success = self.engine.add_break_even_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=entry_time,
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        self.assertTrue(success)
        
        position = self.engine.break_even_positions[12345]
        
        # Test various price levels
        test_scenarios = [
            (1.2004, False, "Insufficient profit"),  # 4 pips - below min
            (1.2007, False, "Trigger conditions not met"),  # 7 pips - above min but below threshold
            (1.2010, True, "Fixed pips threshold reached"),  # 10 pips - should trigger
        ]
        
        for price, should_trigger_expected, reason_contains in test_scenarios:
            should_trigger, reason = self.engine.should_trigger_break_even(position, price)
            self.assertEqual(should_trigger, should_trigger_expected)
            self.assertIn(reason_contains, reason)
        
        # Test break even SL calculation
        break_even_sl = self.engine.calculate_break_even_sl(position)
        expected_sl = 1.2002  # Entry price + 2 pips buffer
        self.assertEqual(break_even_sl, expected_sl)
    
    def test_edge_case_no_buffer(self):
        """Test break even with no buffer"""
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.FIXED_PIPS,
            threshold_value=5.0,
            buffer_pips=0.0,  # No buffer
            min_profit_pips=3.0
        )
        
        # Add position
        self.engine.add_break_even_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            current_sl=1.1990,
            lot_size=1.0,
            config=config
        )
        
        position = self.engine.break_even_positions[12345]
        break_even_sl = self.engine.calculate_break_even_sl(position)
        
        # Should be exactly at entry price
        self.assertEqual(break_even_sl, 1.2000)
    
    def test_edge_case_large_buffer(self):
        """Test break even with large buffer"""
        config = BreakEvenConfig(
            trigger=BreakEvenTrigger.FIXED_PIPS,
            threshold_value=20.0,
            buffer_pips=5.0,  # Large buffer
            min_profit_pips=10.0
        )
        
        # Add SELL position
        self.engine.add_break_even_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.SELL,
            entry_price=1.2000,
            entry_time=datetime.now(),
            current_sl=1.2030,
            lot_size=1.0,
            config=config
        )
        
        position = self.engine.break_even_positions[12345]
        break_even_sl = self.engine.calculate_break_even_sl(position)
        
        # Should be entry price - 5 pips buffer
        expected_sl = 1.1995
        self.assertEqual(break_even_sl, expected_sl)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)