"""
Test Suite for Entry Range Engine
Tests range validation, partial fills, scaling logic, and edge cases
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

from entry_range import (
    EntryRangeEngine, EntryRangeConfig, EntryRangePosition, EntryExecution,
    EntryRangeType, EntryLogic, TradeDirection
)


class TestEntryRangeEngine(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'entry_range': {
                'update_interval_seconds': 5,
                'default_range_pips': 20.0,
                'max_range_entries': 5,
                'default_timeout_minutes': 60,
                'pip_values': {
                    'EURUSD': 0.0001,
                    'GBPUSD': 0.0001,
                    'USDJPY': 0.01,
                    'default': 0.0001
                },
                'max_positions_to_monitor': 50
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        json.dump([], self.temp_log)
        self.temp_log.close()
        
        self.engine = EntryRangeEngine(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
        
        # Mock MT5 bridge
        self.mock_mt5_bridge = Mock()
        self.mock_mt5_bridge.place_pending_order = AsyncMock()
        self.mock_mt5_bridge.cancel_order = AsyncMock()
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
    
    def test_parse_entry_range_command_basic(self):
        """Test basic entry range command parsing"""
        test_cases = [
            ("ENTRY RANGE 1.2000-1.2020 AVERAGE", 1.2020, 1.2000, EntryLogic.AVERAGE_ENTRY),
            ("RANGE 1.1950/1.1970 SCALE", 1.1970, 1.1950, EntryLogic.SCALE_IN),
            ("BEST ENTRY 1.2010 TO 1.2030", 1.2030, 1.2010, EntryLogic.BEST_ENTRY),
            ("SECOND ENTRY 1.1980 TO 1.2000", 1.2000, 1.1980, EntryLogic.SECOND_ENTRY),
        ]
        
        for command, expected_upper, expected_lower, expected_logic in test_cases:
            with self.subTest(command=command):
                config = self.engine.parse_entry_range_command(
                    command, "EURUSD", TradeDirection.BUY, 1.0
                )
                self.assertIsNotNone(config)
                if config:
                    self.assertEqual(config.upper_bound, expected_upper)
                    self.assertEqual(config.lower_bound, expected_lower)
                    self.assertEqual(config.entry_logic, expected_logic)
                    self.assertEqual(config.total_lot_size, 1.0)
    
    def test_parse_entry_range_command_invalid(self):
        """Test parsing invalid entry range commands"""
        invalid_commands = [
            "CLOSE 50%",  # Not an entry range command
            "RANGE INVALID",  # No valid range
            "ENTRY",  # Incomplete command
            "",  # Empty string
            None,  # None value
        ]
        
        for command in invalid_commands:
            with self.subTest(command=command):
                config = self.engine.parse_entry_range_command(
                    command, "EURUSD", TradeDirection.BUY, 1.0
                )
                self.assertIsNone(config)
    
    def test_pip_calculations(self):
        """Test pip calculations for different symbols"""
        test_cases = [
            ('EURUSD', 0.0010, 10.0),  # 10 pips
            ('USDJPY', 0.10, 10.0),    # 10 pips for JPY
            ('GBPUSD', 0.0025, 25.0),  # 25 pips
        ]
        
        for symbol, price_diff, expected_pips in test_cases:
            with self.subTest(symbol=symbol):
                pips = self.engine.calculate_pips(symbol, price_diff)
                self.assertEqual(pips, expected_pips)
    
    def test_create_entry_range_position(self):
        """Test creating entry range position"""
        config = EntryRangeConfig(
            range_type=EntryRangeType.LIMIT_RANGE,
            entry_logic=EntryLogic.AVERAGE_ENTRY,
            upper_bound=1.2020,
            lower_bound=1.2000,
            total_lot_size=1.0,
            max_entries=3
        )
        
        success = self.engine.create_entry_range_position(
            signal_id=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            config=config
        )
        
        self.assertTrue(success)
        self.assertIn(12345, self.engine.entry_range_positions)
        
        position = self.engine.entry_range_positions[12345]
        self.assertEqual(position.symbol, "EURUSD")
        self.assertEqual(position.direction, TradeDirection.BUY)
        self.assertEqual(position.config.upper_bound, 1.2020)
        self.assertEqual(position.config.lower_bound, 1.2000)
        self.assertFalse(position.range_completed)
    
    async def test_place_average_entry_orders(self):
        """Test placing orders for average entry strategy"""
        config = EntryRangeConfig(
            range_type=EntryRangeType.LIMIT_RANGE,
            entry_logic=EntryLogic.AVERAGE_ENTRY,
            upper_bound=1.2020,
            lower_bound=1.2000,
            total_lot_size=1.5,
            max_entries=3
        )
        
        position = EntryRangePosition(
            signal_id=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            config=config,
            created_at=datetime.now(),
            entries=[],
            pending_orders=[]
        )
        
        # Mock current price and order placement
        self.mock_market_data.get_current_price.return_value = 1.2015
        self.mock_mt5_bridge.place_pending_order.return_value = {'success': True, 'ticket': 100001}
        
        await self.engine._place_average_entry_orders(position)
        
        # Should place 3 orders (max_entries)
        self.assertEqual(self.mock_mt5_bridge.place_pending_order.call_count, 3)
        self.assertEqual(len(position.pending_orders), 3)
        
        # Verify order parameters
        calls = self.mock_mt5_bridge.place_pending_order.call_args_list
        
        # First order should be at lower bound (1.2000)
        first_call_kwargs = calls[0][1]
        self.assertEqual(first_call_kwargs['price'], 1.2000)
        self.assertEqual(first_call_kwargs['lot_size'], 0.5)  # 1.5 / 3
        
        # Last order should be at upper bound (1.2020)
        last_call_kwargs = calls[-1][1]
        self.assertEqual(last_call_kwargs['price'], 1.2020)
        self.assertEqual(last_call_kwargs['lot_size'], 0.5)
    
    async def test_place_best_entry_orders(self):
        """Test placing orders for best entry strategy"""
        config = EntryRangeConfig(
            range_type=EntryRangeType.LIMIT_RANGE,
            entry_logic=EntryLogic.BEST_ENTRY,
            upper_bound=1.2020,
            lower_bound=1.2000,
            total_lot_size=2.0,
            max_entries=1
        )
        
        position = EntryRangePosition(
            signal_id=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            config=config,
            created_at=datetime.now(),
            entries=[],
            pending_orders=[]
        )
        
        # Mock current price and order placement
        self.mock_market_data.get_current_price.return_value = 1.2015
        self.mock_mt5_bridge.place_pending_order.return_value = {'success': True, 'ticket': 100001}
        
        await self.engine._place_best_entry_orders(position)
        
        # Should place 1 order at best price (lower bound for BUY)
        self.assertEqual(self.mock_mt5_bridge.place_pending_order.call_count, 1)
        self.assertEqual(len(position.pending_orders), 1)
        
        # Verify order parameters
        call_kwargs = self.mock_mt5_bridge.place_pending_order.call_args[1]
        self.assertEqual(call_kwargs['price'], 1.2000)  # Best price for BUY
        self.assertEqual(call_kwargs['lot_size'], 2.0)  # Full lot size
    
    async def test_place_scale_in_orders(self):
        """Test placing orders for scale-in strategy"""
        config = EntryRangeConfig(
            range_type=EntryRangeType.LIMIT_RANGE,
            entry_logic=EntryLogic.SCALE_IN,
            upper_bound=1.2020,
            lower_bound=1.2000,
            total_lot_size=3.0,
            max_entries=3,
            scale_factor=1.5
        )
        
        position = EntryRangePosition(
            signal_id=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            config=config,
            created_at=datetime.now(),
            entries=[],
            pending_orders=[]
        )
        
        # Mock current price and order placement
        self.mock_market_data.get_current_price.return_value = 1.2015
        self.mock_mt5_bridge.place_pending_order.return_value = {'success': True, 'ticket': 100001}
        
        await self.engine._place_scale_in_orders(position)
        
        # Should place 3 orders with scaled lot sizes
        self.assertEqual(self.mock_mt5_bridge.place_pending_order.call_count, 3)
        self.assertEqual(len(position.pending_orders), 3)
        
        # Verify scaled lot sizes
        calls = self.mock_mt5_bridge.place_pending_order.call_args_list
        lot_sizes = [call[1]['lot_size'] for call in calls]
        
        # With scale_factor=1.5, weights are [1.0, 1.5, 2.25], total=4.75
        # Lot sizes should be proportional to weights
        expected_first_lot = (3.0 * 1.0) / 4.75  # ≈ 0.63
        self.assertAlmostEqual(lot_sizes[0], expected_first_lot, places=2)
    
    async def test_process_order_fill(self):
        """Test processing order fills"""
        config = EntryRangeConfig(
            range_type=EntryRangeType.LIMIT_RANGE,
            entry_logic=EntryLogic.AVERAGE_ENTRY,
            upper_bound=1.2020,
            lower_bound=1.2000,
            total_lot_size=2.0,
            max_entries=2
        )
        
        position = EntryRangePosition(
            signal_id=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            config=config,
            created_at=datetime.now(),
            entries=[],
            pending_orders=[100001, 100002]
        )
        
        self.engine.entry_range_positions[12345] = position
        
        # Process first fill
        await self.engine.process_order_fill(100001, 1.2005, 1.0)
        
        # Verify position updates
        self.assertEqual(position.total_filled_lots, 1.0)
        self.assertEqual(position.average_entry_price, 1.2005)
        self.assertEqual(len(position.entries), 1)
        self.assertIn(100001, [entry['ticket'] for entry in position.entries])
        self.assertNotIn(100001, position.pending_orders)
        
        # Process second fill
        await self.engine.process_order_fill(100002, 1.2015, 1.0)
        
        # Verify updated averages
        self.assertEqual(position.total_filled_lots, 2.0)
        expected_avg = (1.2005 + 1.2015) / 2  # 1.2010
        self.assertEqual(position.average_entry_price, expected_avg)
        self.assertTrue(position.range_completed)
    
    def test_fill_quality_calculation(self):
        """Test fill quality calculation for different entry prices"""
        config = EntryRangeConfig(
            range_type=EntryRangeType.LIMIT_RANGE,
            entry_logic=EntryLogic.AVERAGE_ENTRY,
            upper_bound=1.2020,
            lower_bound=1.2000,  # 20 pip range
            total_lot_size=1.0,
            max_entries=1
        )
        
        # Test BUY position (lower price = better quality)
        position_buy = EntryRangePosition(
            signal_id=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            config=config,
            created_at=datetime.now(),
            entries=[],
            pending_orders=[100001]
        )
        
        self.engine.entry_range_positions[12345] = position_buy
        
        # Test various fill prices
        test_cases = [
            (1.2000, 1.0),  # Best price = 100% quality
            (1.2005, 0.75), # 5 pips from best = 75% quality
            (1.2010, 0.5),  # 10 pips from best = 50% quality
            (1.2020, 0.0),  # Worst price = 0% quality
        ]
        
        for fill_price, expected_quality in test_cases:
            with self.subTest(fill_price=fill_price):
                # Reset position for each test
                position_buy.entries = []
                position_buy.pending_orders = [100001]
                position_buy.total_filled_lots = 0.0
                
                asyncio.run(self.engine.process_order_fill(100001, fill_price, 1.0))
                
                if position_buy.entries:
                    actual_quality = position_buy.entries[0]['fill_quality']
                    self.assertAlmostEqual(actual_quality, expected_quality, places=2)
    
    async def test_monitor_entry_ranges_timeout(self):
        """Test monitoring for position timeouts"""
        config = EntryRangeConfig(
            range_type=EntryRangeType.LIMIT_RANGE,
            entry_logic=EntryLogic.AVERAGE_ENTRY,
            upper_bound=1.2020,
            lower_bound=1.2000,
            total_lot_size=1.0,
            timeout_minutes=1  # 1 minute timeout
        )
        
        # Create expired position
        expired_time = datetime.now() - timedelta(minutes=2)
        position = EntryRangePosition(
            signal_id=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            config=config,
            created_at=expired_time,
            entries=[],
            pending_orders=[100001, 100002]
        )
        
        self.engine.entry_range_positions[12345] = position
        
        # Mock order cancellation
        self.mock_mt5_bridge.cancel_order.return_value = {'success': True}
        
        # Monitor positions
        await self.engine.monitor_entry_ranges()
        
        # Verify position was marked as expired
        self.assertTrue(position.expired)
        
        # Verify cancel orders were called
        self.assertEqual(self.mock_mt5_bridge.cancel_order.call_count, 2)
    
    def test_get_entry_range_statistics_empty(self):
        """Test statistics with no entry range history"""
        stats = self.engine.get_entry_range_statistics()
        
        expected = {
            'total_positions': 0,
            'completed_positions': 0,
            'active_positions': 0,
            'expired_positions': 0,
            'total_executions': 0,
            'average_fill_quality': 0.0,
            'total_volume_traded': 0.0
        }
        
        self.assertEqual(stats, expected)
    
    def test_get_entry_range_statistics_with_data(self):
        """Test statistics with entry range data"""
        # Add test position
        config = EntryRangeConfig(
            range_type=EntryRangeType.LIMIT_RANGE,
            entry_logic=EntryLogic.AVERAGE_ENTRY,
            upper_bound=1.2020,
            lower_bound=1.2000,
            total_lot_size=1.0
        )
        
        position = EntryRangePosition(
            signal_id=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            config=config,
            created_at=datetime.now(),
            entries=[],
            pending_orders=[],
            range_completed=True
        )
        
        self.engine.entry_range_positions[12345] = position
        
        # Add test execution history
        execution = EntryExecution(
            ticket=100001,
            price=1.2005,
            lot_size=1.0,
            execution_time=datetime.now(),
            order_type="limit",
            fill_quality=0.8
        )
        self.engine.execution_history.append(execution)
        
        stats = self.engine.get_entry_range_statistics()
        
        self.assertEqual(stats['total_positions'], 1)
        self.assertEqual(stats['completed_positions'], 1)
        self.assertEqual(stats['active_positions'], 0)
        self.assertEqual(stats['total_executions'], 1)
        self.assertEqual(stats['average_fill_quality'], 0.8)
        self.assertEqual(stats['total_volume_traded'], 1.0)
    
    def test_get_position_status(self):
        """Test getting status of specific position"""
        config = EntryRangeConfig(
            range_type=EntryRangeType.LIMIT_RANGE,
            entry_logic=EntryLogic.BEST_ENTRY,
            upper_bound=1.2020,
            lower_bound=1.2000,
            total_lot_size=1.5
        )
        
        position = EntryRangePosition(
            signal_id=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            config=config,
            created_at=datetime.now(),
            entries=[],
            pending_orders=[100001],
            total_filled_lots=0.5,
            average_entry_price=1.2005
        )
        
        self.engine.entry_range_positions[12345] = position
        
        status = self.engine.get_position_status(12345)
        self.assertIsNotNone(status)
        if status:
            self.assertEqual(status['signal_id'], 12345)
            self.assertEqual(status['symbol'], "EURUSD")
            self.assertEqual(status['direction'], 'buy')
            self.assertEqual(status['entry_logic'], 'best_entry')
            self.assertEqual(status['upper_bound'], 1.2020)
            self.assertEqual(status['lower_bound'], 1.2000)
            self.assertEqual(status['total_lot_size'], 1.5)
            self.assertEqual(status['total_filled_lots'], 0.5)
            self.assertEqual(status['average_entry_price'], 1.2005)
            self.assertEqual(status['pending_orders'], 1)
            self.assertFalse(status['range_completed'])
        
        # Test non-existent position
        status = self.engine.get_position_status(99999)
        self.assertIsNone(status)


class TestEntryRangeIntegration(unittest.TestCase):
    """Integration tests for entry range functionality"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'entry_range': {
                'update_interval_seconds': 1,
                'default_range_pips': 20.0,
                'max_range_entries': 5,
                'default_timeout_minutes': 60,
                'pip_values': {'EURUSD': 0.0001, 'default': 0.0001},
                'max_positions_to_monitor': 50
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        json.dump([], self.temp_log)
        self.temp_log.close()
        
        self.engine = EntryRangeEngine(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def tearDown(self):
        """Clean up integration test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_full_entry_range_cycle(self):
        """Test complete entry range cycle from parsing to execution"""
        # Parse command
        command = "ENTRY RANGE 1.2000-1.2020 AVERAGE"
        config = self.engine.parse_entry_range_command(
            command, "EURUSD", TradeDirection.BUY, 3.0
        )
        
        self.assertIsNotNone(config)
        if config:
            self.assertEqual(config.entry_logic, EntryLogic.AVERAGE_ENTRY)
            self.assertEqual(config.upper_bound, 1.2020)
            self.assertEqual(config.lower_bound, 1.2000)
            self.assertEqual(config.total_lot_size, 3.0)
            
            # Create position
            success = self.engine.create_entry_range_position(
                signal_id=12345,
                symbol="EURUSD",
                direction=TradeDirection.BUY,
                config=config
            )
            self.assertTrue(success)
            
            # Verify position was created
            position = self.engine.entry_range_positions[12345]
            self.assertEqual(position.symbol, "EURUSD")
            self.assertEqual(position.direction, TradeDirection.BUY)
            self.assertFalse(position.range_completed)
    
    def test_edge_case_single_pip_range(self):
        """Test edge case with very small range"""
        command = "RANGE 1.2000/1.2001 BEST"
        config = self.engine.parse_entry_range_command(
            command, "EURUSD", TradeDirection.BUY, 1.0
        )
        
        self.assertIsNotNone(config)
        if config:
            self.assertEqual(config.upper_bound, 1.2001)
            self.assertEqual(config.lower_bound, 1.2000)
            
            # Range size is 1 pip
            range_pips = self.engine.calculate_pips("EURUSD", config.upper_bound - config.lower_bound)
            self.assertEqual(range_pips, 1.0)
    
    def test_edge_case_large_range(self):
        """Test edge case with very large range"""
        command = "SCALE ENTRY 1.1900 TO 1.2100"
        config = self.engine.parse_entry_range_command(
            command, "EURUSD", TradeDirection.BUY, 5.0
        )
        
        self.assertIsNotNone(config)
        if config:
            self.assertEqual(config.upper_bound, 1.2100)
            self.assertEqual(config.lower_bound, 1.1900)
            
            # Range size is 200 pips
            range_pips = self.engine.calculate_pips("EURUSD", config.upper_bound - config.lower_bound)
            self.assertEqual(range_pips, 200.0)
    
    def test_sell_position_range_logic(self):
        """Test entry range logic for SELL positions"""
        command = "BEST ENTRY 1.2000 TO 1.2020"
        config = self.engine.parse_entry_range_command(
            command, "EURUSD", TradeDirection.SELL, 2.0
        )
        
        self.assertIsNotNone(config)
        if config:
            # For SELL positions, best entry should be at upper bound (higher price)
            self.assertEqual(config.entry_logic, EntryLogic.BEST_ENTRY)
            self.assertEqual(config.upper_bound, 1.2020)
            self.assertEqual(config.lower_bound, 1.2000)
    
    def test_partial_fill_handling(self):
        """Test handling of partial fills within range"""
        config = EntryRangeConfig(
            range_type=EntryRangeType.LIMIT_RANGE,
            entry_logic=EntryLogic.AVERAGE_ENTRY,
            upper_bound=1.2020,
            lower_bound=1.2000,
            total_lot_size=3.0,
            max_entries=3,
            allow_partial_fills=True
        )
        
        position = EntryRangePosition(
            signal_id=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            config=config,
            created_at=datetime.now(),
            entries=[],
            pending_orders=[100001, 100002, 100003]
        )
        
        self.engine.entry_range_positions[12345] = position
        
        # Simulate partial fills
        fill_scenarios = [
            (100001, 1.2005, 0.8),  # Partial fill
            (100002, 1.2010, 1.2),  # Over-fill
            (100003, 1.2015, 1.0),  # Exact fill
        ]
        
        total_expected = 0.0
        for ticket, price, lots in fill_scenarios:
            asyncio.run(self.engine.process_order_fill(ticket, price, lots))
            total_expected += lots
        
        # Verify total fills
        self.assertEqual(position.total_filled_lots, total_expected)
        self.assertEqual(len(position.entries), 3)
        self.assertTrue(position.range_completed)  # Should complete when all orders filled


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)