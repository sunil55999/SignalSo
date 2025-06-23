"""
Test Suite for Trailing Stop Engine
Tests pip trailing, percentage trailing, and edge cases
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

from trailing_stop import (
    TrailingStopEngine, TrailingStopConfig, TrailingPosition, 
    TrailingMethod, TradeDirection, TrailingUpdate
)


class TestTrailingStopEngine(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'trailing_stop': {
                'update_interval_seconds': 5,
                'min_profit_to_start_pips': 5.0,
                'default_trail_distance_pips': 10.0,
                'pip_values': {
                    'EURUSD': 0.0001,
                    'GBPUSD': 0.0001,
                    'USDJPY': 0.01,
                    'default': 0.0001
                },
                'max_positions_to_trail': 50
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        json.dump([], self.temp_log)
        self.temp_log.close()
        
        self.engine = TrailingStopEngine(
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
    
    def test_add_trailing_position(self):
        """Test adding position to trailing monitoring"""
        config = TrailingStopConfig(
            method=TrailingMethod.FIXED_PIPS,
            trail_distance=10.0,
            activation_threshold=5.0
        )
        
        success = self.engine.add_trailing_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        
        self.assertTrue(success)
        self.assertIn(12345, self.engine.trailing_positions)
        
        position = self.engine.trailing_positions[12345]
        self.assertEqual(position.symbol, "EURUSD")
        self.assertEqual(position.direction, TradeDirection.BUY)
        self.assertEqual(position.entry_price, 1.2000)
        self.assertEqual(position.current_sl, 1.1980)
    
    def test_remove_trailing_position(self):
        """Test removing position from trailing monitoring"""
        # First add a position
        config = TrailingStopConfig(
            method=TrailingMethod.FIXED_PIPS,
            trail_distance=10.0,
            activation_threshold=5.0
        )
        
        self.engine.add_trailing_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        
        # Now remove it
        success = self.engine.remove_trailing_position(12345)
        self.assertTrue(success)
        self.assertNotIn(12345, self.engine.trailing_positions)
        
        # Try removing non-existent position
        success = self.engine.remove_trailing_position(99999)
        self.assertFalse(success)
    
    def test_calculate_new_trailing_sl_buy_fixed_pips(self):
        """Test trailing SL calculation for BUY positions with fixed pips"""
        config = TrailingStopConfig(
            method=TrailingMethod.FIXED_PIPS,
            trail_distance=10.0,
            activation_threshold=5.0,
            step_size=1.0
        )
        
        position = TrailingPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            original_sl=1.1980,
            current_sl=1.1980,
            lot_size=1.0,
            config=config,
            last_update=datetime.now()
        )
        
        # Test case 1: Not enough profit to start trailing
        current_price = 1.2004  # Only 4 pips profit
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        self.assertIsNone(new_sl)
        
        # Test case 2: Enough profit to start trailing
        current_price = 1.2010  # 10 pips profit
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        self.assertIsNotNone(new_sl)
        # Should be 10 pips below current price
        expected_sl = 1.2010 - 0.0010  # 1.2000
        self.assertEqual(new_sl, expected_sl)
        
        # Test case 3: Price moves higher, SL should trail
        position.highest_profit_price = 1.2010
        position.current_sl = 1.2000
        current_price = 1.2020  # Price moves up 10 more pips
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        expected_sl = 1.2020 - 0.0010  # 1.2010
        self.assertEqual(new_sl, expected_sl)
    
    def test_calculate_new_trailing_sl_sell_fixed_pips(self):
        """Test trailing SL calculation for SELL positions with fixed pips"""
        config = TrailingStopConfig(
            method=TrailingMethod.FIXED_PIPS,
            trail_distance=10.0,
            activation_threshold=5.0,
            step_size=1.0
        )
        
        position = TrailingPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.SELL,
            entry_price=1.2000,
            original_sl=1.2020,
            current_sl=1.2020,
            lot_size=1.0,
            config=config,
            last_update=datetime.now()
        )
        
        # Test case 1: Not enough profit to start trailing
        current_price = 1.1996  # Only 4 pips profit
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        self.assertIsNone(new_sl)
        
        # Test case 2: Enough profit to start trailing
        current_price = 1.1990  # 10 pips profit
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        self.assertIsNotNone(new_sl)
        # Should be 10 pips above current price
        expected_sl = 1.1990 + 0.0010  # 1.2000
        self.assertEqual(new_sl, expected_sl)
    
    def test_calculate_new_trailing_sl_percentage(self):
        """Test trailing SL calculation with percentage method"""
        config = TrailingStopConfig(
            method=TrailingMethod.PERCENTAGE,
            trail_distance=1.0,  # 1%
            activation_threshold=5.0,
            step_size=1.0
        )
        
        position = TrailingPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            original_sl=1.1980,
            current_sl=1.1980,
            lot_size=1.0,
            config=config,
            last_update=datetime.now()
        )
        
        # Test with 10 pips profit
        current_price = 1.2010
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        self.assertIsNotNone(new_sl)
        # Should be 1% below current price
        expected_sl = 1.2010 * 0.99  # 1.189
        self.assertAlmostEqual(new_sl, expected_sl, places=5)
    
    def test_calculate_new_trailing_sl_breakeven_plus(self):
        """Test trailing SL calculation with breakeven plus method"""
        config = TrailingStopConfig(
            method=TrailingMethod.BREAKEVEN_PLUS,
            trail_distance=2.0,  # 2 pips above breakeven
            activation_threshold=5.0,
            step_size=1.0
        )
        
        position = TrailingPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            original_sl=1.1980,
            current_sl=1.1980,
            lot_size=1.0,
            config=config,
            last_update=datetime.now()
        )
        
        # Test with enough profit
        current_price = 1.2010
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        self.assertIsNotNone(new_sl)
        # Should be entry price + 2 pips
        expected_sl = 1.2000 + 0.0002  # 1.2002
        self.assertEqual(new_sl, expected_sl)
    
    def test_step_size_requirement(self):
        """Test that SL only moves when step size requirement is met"""
        config = TrailingStopConfig(
            method=TrailingMethod.FIXED_PIPS,
            trail_distance=10.0,
            activation_threshold=5.0,
            step_size=5.0  # Require 5 pip minimum move
        )
        
        position = TrailingPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            original_sl=1.1980,
            current_sl=1.2000,  # Already at breakeven
            lot_size=1.0,
            config=config,
            last_update=datetime.now(),
            highest_profit_price=1.2010
        )
        
        # Small move (only 2 pips improvement)
        current_price = 1.2012
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        self.assertIsNone(new_sl)  # Should not trail due to step size
        
        # Larger move (7 pips improvement)
        current_price = 1.2017
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        self.assertIsNotNone(new_sl)  # Should trail now
    
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
    
    async def test_process_trailing_updates(self):
        """Test processing trailing updates for all positions"""
        # Add test position
        config = TrailingStopConfig(
            method=TrailingMethod.FIXED_PIPS,
            trail_distance=10.0,
            activation_threshold=5.0,
            step_size=1.0
        )
        
        self.engine.add_trailing_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        
        # Mock responses
        self.mock_market_data.get_current_price.return_value = 1.2015  # 15 pips profit
        self.mock_mt5_bridge.modify_position.return_value = {'success': True}
        
        # Process updates
        await self.engine.process_trailing_updates()
        
        # Verify position was updated
        position = self.engine.trailing_positions[12345]
        self.assertTrue(position.trailing_active)
        self.assertIsNotNone(position.current_sl)
        self.assertEqual(len(self.engine.update_history), 1)
    
    def test_get_trailing_statistics_empty(self):
        """Test statistics with no trailing history"""
        stats = self.engine.get_trailing_statistics()
        
        expected = {
            'total_updates': 0,
            'active_positions': 0,
            'average_profit_at_update': 0.0,
            'most_common_method': None,
            'total_positions_trailed': 0
        }
        
        self.assertEqual(stats, expected)
    
    def test_get_trailing_statistics_with_data(self):
        """Test statistics with trailing data"""
        # Add test position
        config = TrailingStopConfig(
            method=TrailingMethod.FIXED_PIPS,
            trail_distance=10.0,
            activation_threshold=5.0
        )
        
        self.engine.add_trailing_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        
        # Add test update history
        update = TrailingUpdate(
            ticket=12345,
            new_sl=1.2005,
            old_sl=1.1980,
            current_price=1.2015,
            profit_pips=15.0,
            trailing_distance=10.0,
            reason="Test update",
            timestamp=datetime.now()
        )
        self.engine.update_history.append(update)
        
        stats = self.engine.get_trailing_statistics()
        
        self.assertEqual(stats['total_updates'], 1)
        self.assertEqual(stats['active_positions'], 1)
        self.assertEqual(stats['average_profit_at_update'], 15.0)
        self.assertEqual(stats['most_common_method'], 'fixed_pips')
        self.assertEqual(stats['total_positions_trailed'], 1)
    
    def test_get_position_status(self):
        """Test getting status of specific position"""
        config = TrailingStopConfig(
            method=TrailingMethod.FIXED_PIPS,
            trail_distance=10.0,
            activation_threshold=5.0
        )
        
        self.engine.add_trailing_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        
        status = self.engine.get_position_status(12345)
        self.assertIsNotNone(status)
        self.assertEqual(status['ticket'], 12345)
        self.assertEqual(status['symbol'], "EURUSD")
        self.assertEqual(status['direction'], 'buy')
        self.assertEqual(status['trailing_method'], 'fixed_pips')
        
        # Test non-existent position
        status = self.engine.get_position_status(99999)
        self.assertIsNone(status)
    
    def test_get_recent_updates(self):
        """Test getting recent trailing updates"""
        # Add test updates
        for i in range(5):
            update = TrailingUpdate(
                ticket=12345 + i,
                new_sl=1.2000 + i * 0.0001,
                old_sl=1.1990 + i * 0.0001,
                current_price=1.2010 + i * 0.0001,
                profit_pips=10.0 + i,
                trailing_distance=10.0,
                reason=f"Test update {i}",
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


class TestTrailingStopIntegration(unittest.TestCase):
    """Integration tests for trailing stop functionality"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'trailing_stop': {
                'update_interval_seconds': 1,
                'min_profit_to_start_pips': 5.0,
                'default_trail_distance_pips': 10.0,
                'pip_values': {
                    'EURUSD': 0.0001,
                    'default': 0.0001
                },
                'max_positions_to_trail': 50
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        json.dump([], self.temp_log)
        self.temp_log.close()
        
        self.engine = TrailingStopEngine(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def tearDown(self):
        """Clean up integration test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_full_trailing_cycle_buy_position(self):
        """Test complete trailing cycle for BUY position"""
        config = TrailingStopConfig(
            method=TrailingMethod.FIXED_PIPS,
            trail_distance=10.0,
            activation_threshold=5.0,
            step_size=1.0,
            use_breakeven_lock=True
        )
        
        # Add position
        success = self.engine.add_trailing_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            current_sl=1.1980,
            lot_size=1.0,
            config=config
        )
        self.assertTrue(success)
        
        # Simulate price movements and calculate trailing SL
        price_movements = [
            1.2005,  # 5 pips profit - should start trailing
            1.2010,  # 10 pips profit - should trail to 1.2000
            1.2015,  # 15 pips profit - should trail to 1.2005
            1.2012,  # Price drops but SL shouldn't move backward
        ]
        
        expected_sls = [
            1.1995,  # Trail to 5 pips below 1.2005
            1.2000,  # Trail to 10 pips below 1.2010
            1.2005,  # Trail to 10 pips below 1.2015
            1.2005,  # No change (price dropped)
        ]
        
        position = self.engine.trailing_positions[12345]
        
        for price, expected_sl in zip(price_movements, expected_sls):
            new_sl = self.engine.calculate_new_trailing_sl(position, price)
            if new_sl is not None:
                # Update position manually for testing
                position.current_sl = new_sl
                if position.highest_profit_price is None or price > position.highest_profit_price:
                    position.highest_profit_price = price
            
            if expected_sl != 1.2005 or price == 1.2015:  # Expect SL update except for last case
                self.assertIsNotNone(new_sl, f"Expected SL update at price {price}")
                self.assertAlmostEqual(new_sl, expected_sl, places=4)
    
    def test_breakeven_lock_activation(self):
        """Test breakeven lock functionality"""
        config = TrailingStopConfig(
            method=TrailingMethod.FIXED_PIPS,
            trail_distance=5.0,  # Small trail distance
            activation_threshold=3.0,
            step_size=1.0,
            use_breakeven_lock=True
        )
        
        # Add position
        self.engine.add_trailing_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            current_sl=1.1990,
            lot_size=1.0,
            config=config
        )
        
        position = self.engine.trailing_positions[12345]
        
        # Move price to profitable level
        current_price = 1.2008  # 8 pips profit
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        
        # SL should be at 1.2003 (5 pips below 1.2008)
        expected_sl = 1.2003
        self.assertAlmostEqual(new_sl, expected_sl, places=4)
        
        # Update position
        position.current_sl = new_sl
        position.highest_profit_price = current_price
        
        # Check if breakeven would be locked (SL >= entry)
        self.assertGreaterEqual(new_sl, position.entry_price)
    
    def test_edge_case_very_small_moves(self):
        """Test edge case with very small price movements"""
        config = TrailingStopConfig(
            method=TrailingMethod.FIXED_PIPS,
            trail_distance=10.0,
            activation_threshold=5.0,
            step_size=5.0,  # Large step size
            use_breakeven_lock=False
        )
        
        # Add position
        self.engine.add_trailing_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            current_sl=1.1990,
            lot_size=1.0,
            config=config
        )
        
        position = self.engine.trailing_positions[12345]
        
        # Set initial trailing state
        position.current_sl = 1.2000
        position.highest_profit_price = 1.2015
        
        # Small price movement (should not trigger due to step size)
        current_price = 1.2017  # Only 2 pips better
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        self.assertIsNone(new_sl)  # Should not trail due to step size
        
        # Larger price movement (should trigger trailing)
        current_price = 1.2020  # 5 pips better
        new_sl = self.engine.calculate_new_trailing_sl(position, current_price)
        self.assertIsNotNone(new_sl)  # Should trail now


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)