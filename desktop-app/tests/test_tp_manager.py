"""
Test Suite for TP Manager Engine
Tests multiple TP levels, partial closes, dynamic adjustments, and edge cases
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

from tp_manager import (
    TPManager, TPLevel, TPConfiguration, TPManagedPosition, TPExecution,
    TPHitAction, TPStatus, TradeDirection
)


class TestTPManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'tp_manager': {
                'update_interval_seconds': 5,
                'max_tp_levels': 5,
                'default_tp_percentages': [25, 25, 25, 25],
                'auto_move_sl': True,
                'tp_buffer_pips': 2.0,
                'min_lots_remaining': 0.01,
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
        
        self.manager = TPManager(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
        
        # Mock MT5 bridge
        self.mock_mt5_bridge = Mock()
        self.mock_mt5_bridge.get_current_price = AsyncMock()
        self.mock_mt5_bridge.partial_close_position = AsyncMock()
        self.mock_mt5_bridge.modify_position = AsyncMock()
        self.mock_mt5_bridge.close_position = AsyncMock()
        
        # Mock market data
        self.mock_market_data = Mock()
        self.mock_market_data.get_current_price = AsyncMock()
        
        # Mock partial close engine
        self.mock_partial_close = Mock()
        self.mock_partial_close.execute_partial_close = AsyncMock()
        
        self.manager.inject_modules(
            mt5_bridge=self.mock_mt5_bridge,
            market_data=self.mock_market_data,
            partial_close_engine=self.mock_partial_close
        )
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_parse_tp_levels_format1(self):
        """Test parsing TP levels in TP1: price TP2: price format"""
        signal = "TP1: 1.2050 TP2: 1.2080 TP3: 1.2120"
        tp_levels = self.manager.parse_tp_levels_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(tp_levels), 3)
        
        # Check TP1
        self.assertEqual(tp_levels[0].level, 1)
        self.assertEqual(tp_levels[0].price, 1.2050)
        self.assertEqual(tp_levels[0].close_percentage, 0.25)  # 25%
        
        # Check TP2
        self.assertEqual(tp_levels[1].level, 2)
        self.assertEqual(tp_levels[1].price, 1.2080)
        self.assertEqual(tp_levels[1].close_percentage, 0.25)
        
        # Check TP3
        self.assertEqual(tp_levels[2].level, 3)
        self.assertEqual(tp_levels[2].price, 1.2120)
        self.assertEqual(tp_levels[2].close_percentage, 0.25)
    
    def test_parse_tp_levels_format2(self):
        """Test parsing TP levels in comma-separated format"""
        signal = "Take Profit 1.2050, 1.2080, 1.2120"
        tp_levels = self.manager.parse_tp_levels_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(tp_levels), 3)
        self.assertEqual(tp_levels[0].price, 1.2050)
        self.assertEqual(tp_levels[1].price, 1.2080)
        self.assertEqual(tp_levels[2].price, 1.2120)
    
    def test_parse_tp_levels_format3(self):
        """Test parsing TP levels with percentages"""
        signal = "TP 1.2050 (30%), 1.2080 (40%), 1.2120 (30%)"
        tp_levels = self.manager.parse_tp_levels_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(tp_levels), 3)
        self.assertEqual(tp_levels[0].close_percentage, 0.30)
        self.assertEqual(tp_levels[1].close_percentage, 0.40)
        self.assertEqual(tp_levels[2].close_percentage, 0.30)
    
    def test_parse_tp_levels_invalid_direction(self):
        """Test parsing TP levels with invalid direction (should filter out)"""
        # For BUY position, TP should be above entry price
        signal = "TP1: 1.1950 TP2: 1.2080"  # TP1 below entry
        tp_levels = self.manager.parse_tp_levels_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        # Should only return TP2 (valid)
        self.assertEqual(len(tp_levels), 1)
        self.assertEqual(tp_levels[0].price, 1.2080)
    
    def test_validate_tp_price_buy(self):
        """Test TP price validation for BUY positions"""
        # Valid TP for BUY (above entry)
        self.assertTrue(self.manager._validate_tp_price(1.2050, 1.2000, TradeDirection.BUY))
        
        # Invalid TP for BUY (below entry)
        self.assertFalse(self.manager._validate_tp_price(1.1950, 1.2000, TradeDirection.BUY))
    
    def test_validate_tp_price_sell(self):
        """Test TP price validation for SELL positions"""
        # Valid TP for SELL (below entry)
        self.assertTrue(self.manager._validate_tp_price(1.1950, 1.2000, TradeDirection.SELL))
        
        # Invalid TP for SELL (above entry)
        self.assertFalse(self.manager._validate_tp_price(1.2050, 1.2000, TradeDirection.SELL))
    
    def test_add_tp_managed_position(self):
        """Test adding position to TP management"""
        tp_levels = [
            TPLevel(1, 1.2050, 0.25),
            TPLevel(2, 1.2080, 0.25),
            TPLevel(3, 1.2120, 0.50)
        ]
        
        success = self.manager.add_tp_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            lot_size=1.0,
            tp_levels=tp_levels,
            current_sl=1.1980
        )
        
        self.assertTrue(success)
        self.assertIn(12345, self.manager.tp_positions)
        
        position = self.manager.tp_positions[12345]
        self.assertEqual(position.symbol, "EURUSD")
        self.assertEqual(position.direction, TradeDirection.BUY)
        self.assertEqual(position.entry_price, 1.2000)
        self.assertEqual(position.original_lot_size, 1.0)
        self.assertEqual(position.current_lot_size, 1.0)
        self.assertEqual(len(position.tp_levels), 3)
    
    def test_remove_tp_managed_position(self):
        """Test removing position from TP management"""
        # Add position first
        tp_levels = [TPLevel(1, 1.2050, 0.25)]
        self.manager.add_tp_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            lot_size=1.0,
            tp_levels=tp_levels
        )
        
        # Remove position
        success = self.manager.remove_tp_managed_position(12345)
        self.assertTrue(success)
        self.assertNotIn(12345, self.manager.tp_positions)
        
        # Try removing non-existent position
        success = self.manager.remove_tp_managed_position(99999)
        self.assertFalse(success)
    
    async def test_check_tp_levels_buy_position(self):
        """Test checking TP levels for BUY position"""
        tp_levels = [
            TPLevel(1, 1.2050, 0.25),
            TPLevel(2, 1.2080, 0.25),
            TPLevel(3, 1.2120, 0.50)
        ]
        
        position = TPManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_lot_size=1.0,
            current_lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            tp_levels=tp_levels
        )
        
        # Test price below all TPs (no hits)
        hit_tps = await self.manager.check_tp_levels(position, 1.2030)
        self.assertEqual(len(hit_tps), 0)
        
        # Test price at TP1 (TP1 hit)
        hit_tps = await self.manager.check_tp_levels(position, 1.2050)
        self.assertEqual(len(hit_tps), 1)
        self.assertEqual(hit_tps[0].level, 1)
        self.assertEqual(hit_tps[0].status, TPStatus.HIT)
        
        # Reset for next test
        tp_levels[0].status = TPStatus.PENDING
        
        # Test price at TP2 (TP1 and TP2 hit)
        hit_tps = await self.manager.check_tp_levels(position, 1.2080)
        self.assertEqual(len(hit_tps), 2)
        self.assertEqual(hit_tps[0].level, 1)
        self.assertEqual(hit_tps[1].level, 2)
    
    async def test_check_tp_levels_sell_position(self):
        """Test checking TP levels for SELL position"""
        tp_levels = [
            TPLevel(1, 1.1950, 0.25),
            TPLevel(2, 1.1920, 0.25),
            TPLevel(3, 1.1880, 0.50)
        ]
        
        position = TPManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.SELL,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_lot_size=1.0,
            current_lot_size=1.0,
            original_sl=1.2020,
            current_sl=1.2020,
            tp_levels=tp_levels
        )
        
        # Test price above all TPs (no hits)
        hit_tps = await self.manager.check_tp_levels(position, 1.1970)
        self.assertEqual(len(hit_tps), 0)
        
        # Test price at TP1 (TP1 hit)
        hit_tps = await self.manager.check_tp_levels(position, 1.1950)
        self.assertEqual(len(hit_tps), 1)
        self.assertEqual(hit_tps[0].level, 1)
    
    async def test_execute_partial_close(self):
        """Test executing partial close at TP level"""
        tp_level = TPLevel(1, 1.2050, 0.25)  # Close 25%
        
        position = TPManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_lot_size=1.0,
            current_lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            tp_levels=[tp_level]
        )
        
        # Mock successful partial close
        self.mock_partial_close.execute_partial_close.return_value = {'success': True}
        
        success = await self.manager._execute_partial_close(position, tp_level, 1.2050)
        
        self.assertTrue(success)
        
        # Verify position updates
        self.assertEqual(position.current_lot_size, 0.75)  # 1.0 - 0.25
        self.assertEqual(position.total_closed_lots, 0.25)
        self.assertEqual(tp_level.executed_lots, 0.25)
        
        # Verify partial close was called with correct parameters
        self.mock_partial_close.execute_partial_close.assert_called_once_with(
            ticket=12345,
            close_lots=0.25,
            close_price=1.2050
        )
        
        # Verify execution history was recorded
        self.assertEqual(len(self.manager.execution_history), 1)
        execution = self.manager.execution_history[0]
        self.assertEqual(execution.ticket, 12345)
        self.assertEqual(execution.tp_level, 1)
        self.assertEqual(execution.closed_lots, 0.25)
        self.assertEqual(execution.remaining_lots, 0.75)
    
    async def test_execute_partial_close_minimum_lots(self):
        """Test partial close with minimum lots handling"""
        tp_level = TPLevel(1, 1.2050, 0.95)  # Close 95%
        
        position = TPManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_lot_size=0.10,  # Small position
            current_lot_size=0.10,
            original_sl=1.1980,
            current_sl=1.1980,
            tp_levels=[tp_level],
            config=TPConfiguration(min_lots_remaining=0.01)
        )
        
        # Mock successful partial close
        self.mock_partial_close.execute_partial_close.return_value = {'success': True}
        
        success = await self.manager._execute_partial_close(position, tp_level, 1.2050)
        
        self.assertTrue(success)
        
        # Should close entire position since remaining would be < min_lots_remaining
        self.assertEqual(position.current_lot_size, 0.0)
        self.assertEqual(position.total_closed_lots, 0.10)
        self.assertTrue(position.position_closed)
    
    async def test_execute_move_sl(self):
        """Test executing stop loss move when TP is hit"""
        tp_level = TPLevel(1, 1.2050, 0.25, action=TPHitAction.MOVE_SL, move_sl_to=1.2000)
        
        position = TPManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_lot_size=1.0,
            current_lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            tp_levels=[tp_level]
        )
        
        # Mock successful SL modification
        self.mock_mt5_bridge.modify_position.return_value = {'success': True}
        
        success = await self.manager._execute_move_sl(position, tp_level, 1.2050)
        
        self.assertTrue(success)
        
        # Verify SL was updated
        self.assertEqual(position.current_sl, 1.2000)
        
        # Verify MT5 modify was called
        self.mock_mt5_bridge.modify_position.assert_called_once_with(
            ticket=12345,
            new_sl=1.2000
        )
        
        # Verify execution history
        self.assertEqual(len(self.manager.execution_history), 1)
        execution = self.manager.execution_history[0]
        self.assertEqual(execution.action_taken, TPHitAction.MOVE_SL)
        self.assertEqual(execution.new_sl, 1.2000)
    
    async def test_execute_close_all(self):
        """Test executing full position close when TP is hit"""
        tp_level = TPLevel(1, 1.2050, 1.0, action=TPHitAction.CLOSE_ALL)
        
        position = TPManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_lot_size=1.0,
            current_lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            tp_levels=[tp_level]
        )
        
        # Mock successful position close
        self.mock_mt5_bridge.close_position.return_value = {'success': True}
        
        success = await self.manager._execute_close_all(position, tp_level, 1.2050)
        
        self.assertTrue(success)
        
        # Verify position was closed
        self.assertTrue(position.position_closed)
        self.assertEqual(position.total_closed_lots, 1.0)
        
        # Verify MT5 close was called
        self.mock_mt5_bridge.close_position.assert_called_once_with(12345)
        
        # Verify execution history
        execution = self.manager.execution_history[0]
        self.assertEqual(execution.action_taken, TPHitAction.CLOSE_ALL)
        self.assertEqual(execution.closed_lots, 1.0)
        self.assertEqual(execution.remaining_lots, 0.0)
    
    def test_calculate_pips_buy(self):
        """Test pip calculation for BUY positions"""
        # Profitable BUY trade
        pips = self.manager.calculate_pips("EURUSD", 0.0050, TradeDirection.BUY)  # +50 pips
        self.assertEqual(pips, 50.0)
        
        # Losing BUY trade
        pips = self.manager.calculate_pips("EURUSD", -0.0020, TradeDirection.BUY)  # -20 pips
        self.assertEqual(pips, -20.0)
    
    def test_calculate_pips_sell(self):
        """Test pip calculation for SELL positions"""
        # Profitable SELL trade
        pips = self.manager.calculate_pips("EURUSD", -0.0030, TradeDirection.SELL)  # +30 pips
        self.assertEqual(pips, 30.0)
        
        # Losing SELL trade
        pips = self.manager.calculate_pips("EURUSD", 0.0040, TradeDirection.SELL)  # -40 pips
        self.assertEqual(pips, -40.0)
    
    def test_calculate_pips_jpy(self):
        """Test pip calculation for JPY pairs"""
        # JPY pairs have different pip value
        pips = self.manager.calculate_pips("USDJPY", 1.0, TradeDirection.BUY)  # +100 pips
        self.assertEqual(pips, 100.0)
        
        pips = self.manager.calculate_pips("USDJPY", -0.5, TradeDirection.BUY)  # -50 pips
        self.assertEqual(pips, -50.0)
    
    async def test_auto_move_sl_on_tp1(self):
        """Test automatic SL move to breakeven on TP1"""
        tp_level = TPLevel(1, 1.2050, 0.25)
        
        position = TPManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_lot_size=1.0,
            current_lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            tp_levels=[tp_level],
            config=TPConfiguration(move_sl_on_tp1=True)
        )
        
        # Mock successful SL modification
        self.mock_mt5_bridge.modify_position.return_value = {'success': True}
        
        await self.manager._auto_move_sl_on_tp(position, tp_level)
        
        # Verify SL was moved to breakeven (entry price)
        self.assertEqual(position.current_sl, 1.2000)
        self.mock_mt5_bridge.modify_position.assert_called_once_with(
            ticket=12345,
            new_sl=1.2000
        )
    
    async def test_auto_move_sl_on_tp2(self):
        """Test automatic SL move to TP1 on TP2"""
        tp1 = TPLevel(1, 1.2050, 0.25, status=TPStatus.HIT)
        tp2 = TPLevel(2, 1.2080, 0.25)
        
        position = TPManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_lot_size=1.0,
            current_lot_size=0.75,
            original_sl=1.1980,
            current_sl=1.2000,  # Already moved to breakeven
            tp_levels=[tp1, tp2],
            config=TPConfiguration(move_sl_on_tp2=True)
        )
        
        # Mock successful SL modification
        self.mock_mt5_bridge.modify_position.return_value = {'success': True}
        
        await self.manager._auto_move_sl_on_tp(position, tp2)
        
        # Verify SL was moved to TP1 price
        self.assertEqual(position.current_sl, 1.2050)
        self.mock_mt5_bridge.modify_position.assert_called_once_with(
            ticket=12345,
            new_sl=1.2050
        )
    
    def test_get_tp_statistics_empty(self):
        """Test statistics with no TP history"""
        stats = self.manager.get_tp_statistics()
        
        expected = {
            'total_positions': 0,
            'active_positions': 0,
            'closed_positions': 0,
            'total_executions': 0,
            'total_profit': 0.0,
            'average_profit_per_execution': 0.0,
            'total_volume_closed': 0.0,
            'tp_level_hit_count': {}
        }
        
        self.assertEqual(stats, expected)
    
    def test_get_tp_statistics_with_data(self):
        """Test statistics with TP data"""
        # Add test position
        tp_levels = [TPLevel(1, 1.2050, 0.25)]
        position = TPManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_lot_size=1.0,
            current_lot_size=0.75,
            original_sl=1.1980,
            current_sl=1.2000,
            tp_levels=tp_levels,
            position_closed=False
        )
        
        self.manager.tp_positions[12345] = position
        
        # Add test execution history
        execution = TPExecution(
            ticket=12345,
            tp_level=1,
            execution_price=1.2050,
            closed_lots=0.25,
            remaining_lots=0.75,
            profit_pips=50.0,
            profit_amount=125.0,
            execution_time=datetime.now(),
            action_taken=TPHitAction.PARTIAL_CLOSE
        )
        self.manager.execution_history.append(execution)
        
        stats = self.manager.get_tp_statistics()
        
        self.assertEqual(stats['total_positions'], 1)
        self.assertEqual(stats['active_positions'], 1)
        self.assertEqual(stats['closed_positions'], 0)
        self.assertEqual(stats['total_executions'], 1)
        self.assertEqual(stats['total_profit'], 125.0)
        self.assertEqual(stats['average_profit_per_execution'], 125.0)
        self.assertEqual(stats['total_volume_closed'], 0.25)
        self.assertEqual(stats['tp_level_hit_count'], {1: 1})
    
    def test_get_position_status(self):
        """Test getting status of specific TP managed position"""
        tp_levels = [
            TPLevel(1, 1.2050, 0.25, status=TPStatus.HIT, hit_time=datetime.now(), executed_lots=0.25),
            TPLevel(2, 1.2080, 0.25, status=TPStatus.PENDING),
            TPLevel(3, 1.2120, 0.50, status=TPStatus.PENDING)
        ]
        
        position = TPManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            original_lot_size=1.0,
            current_lot_size=0.75,
            original_sl=1.1980,
            current_sl=1.2000,
            tp_levels=tp_levels,
            total_closed_lots=0.25,
            realized_profit=125.0
        )
        
        self.manager.tp_positions[12345] = position
        
        status = self.manager.get_position_status(12345)
        self.assertIsNotNone(status)
        if status:
            self.assertEqual(status['ticket'], 12345)
            self.assertEqual(status['symbol'], "EURUSD")
            self.assertEqual(status['direction'], 'buy')
            self.assertEqual(status['entry_price'], 1.2000)
            self.assertEqual(status['original_lot_size'], 1.0)
            self.assertEqual(status['current_lot_size'], 0.75)
            self.assertEqual(status['total_closed_lots'], 0.25)
            self.assertEqual(status['current_sl'], 1.2000)
            self.assertFalse(status['position_closed'])
            self.assertEqual(status['realized_profit'], 125.0)
            
            # Check TP levels status
            self.assertEqual(len(status['tp_levels']), 3)
            self.assertEqual(status['tp_levels'][0]['level'], 1)
            self.assertEqual(status['tp_levels'][0]['status'], 'hit')
            self.assertEqual(status['tp_levels'][0]['executed_lots'], 0.25)
            self.assertEqual(status['tp_levels'][1]['status'], 'pending')
        
        # Test non-existent position
        status = self.manager.get_position_status(99999)
        self.assertIsNone(status)
    
    def test_get_recent_executions(self):
        """Test getting recent TP executions"""
        # Add multiple executions
        executions = [
            TPExecution(
                ticket=12345,
                tp_level=1,
                execution_price=1.2050,
                closed_lots=0.25,
                remaining_lots=0.75,
                profit_pips=50.0,
                profit_amount=125.0,
                execution_time=datetime.now(),
                action_taken=TPHitAction.PARTIAL_CLOSE
            ),
            TPExecution(
                ticket=12345,
                tp_level=2,
                execution_price=1.2080,
                closed_lots=0.25,
                remaining_lots=0.50,
                profit_pips=80.0,
                profit_amount=200.0,
                execution_time=datetime.now(),
                action_taken=TPHitAction.PARTIAL_CLOSE
            )
        ]
        
        self.manager.execution_history.extend(executions)
        
        recent = self.manager.get_recent_executions(limit=5)
        
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]['ticket'], 12345)
        self.assertEqual(recent[0]['tp_level'], 1)
        self.assertEqual(recent[0]['closed_lots'], 0.25)
        self.assertEqual(recent[1]['tp_level'], 2)
        self.assertEqual(recent[1]['closed_lots'], 0.25)


class TestTPManagerIntegration(unittest.TestCase):
    """Integration tests for TP Manager functionality"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'tp_manager': {
                'update_interval_seconds': 1,
                'max_tp_levels': 5,
                'default_tp_percentages': [30, 30, 40],
                'auto_move_sl': True,
                'tp_buffer_pips': 2.0,
                'min_lots_remaining': 0.01,
                'pip_values': {'EURUSD': 0.0001, 'default': 0.0001},
                'max_positions_to_monitor': 100
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        json.dump([], self.temp_log)
        self.temp_log.close()
        
        self.manager = TPManager(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def tearDown(self):
        """Clean up integration test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_full_tp_management_cycle(self):
        """Test complete TP management cycle from parsing to execution"""
        # Parse TP levels from signal
        signal = "TP1: 1.2050 TP2: 1.2080 TP3: 1.2120"
        tp_levels = self.manager.parse_tp_levels_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(tp_levels), 3)
        
        # Add position to management
        success = self.manager.add_tp_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            lot_size=1.0,
            tp_levels=tp_levels,
            current_sl=1.1980
        )
        
        self.assertTrue(success)
        
        # Verify position was added
        position = self.manager.tp_positions[12345]
        self.assertEqual(position.symbol, "EURUSD")
        self.assertEqual(len(position.tp_levels), 3)
        self.assertFalse(position.position_closed)
    
    def test_edge_case_very_small_position(self):
        """Test TP management with very small position size"""
        tp_levels = [TPLevel(1, 1.2050, 0.50)]  # Close 50%
        
        success = self.manager.add_tp_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            lot_size=0.02,  # Very small position
            tp_levels=tp_levels
        )
        
        self.assertTrue(success)
        
        position = self.manager.tp_positions[12345]
        self.assertEqual(position.original_lot_size, 0.02)
        self.assertEqual(position.current_lot_size, 0.02)
    
    def test_edge_case_single_tp_full_close(self):
        """Test single TP level that closes full position"""
        tp_levels = [TPLevel(1, 1.2050, 1.0, action=TPHitAction.CLOSE_ALL)]
        
        success = self.manager.add_tp_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            lot_size=1.0,
            tp_levels=tp_levels
        )
        
        self.assertTrue(success)
        
        position = self.manager.tp_positions[12345]
        self.assertEqual(len(position.tp_levels), 1)
        self.assertEqual(position.tp_levels[0].action, TPHitAction.CLOSE_ALL)
    
    def test_edge_case_many_tp_levels(self):
        """Test TP management with maximum number of TP levels"""
        tp_levels = [
            TPLevel(1, 1.2020, 0.20),
            TPLevel(2, 1.2040, 0.20),
            TPLevel(3, 1.2060, 0.20),
            TPLevel(4, 1.2080, 0.20),
            TPLevel(5, 1.2100, 0.20)
        ]
        
        success = self.manager.add_tp_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            lot_size=5.0,  # Large position to handle 5 partial closes
            tp_levels=tp_levels
        )
        
        self.assertTrue(success)
        
        position = self.manager.tp_positions[12345]
        self.assertEqual(len(position.tp_levels), 5)
        
        # Verify all TP levels are correctly configured
        for i, tp_level in enumerate(position.tp_levels):
            self.assertEqual(tp_level.level, i + 1)
            self.assertEqual(tp_level.close_percentage, 0.20)
    
    def test_sell_position_tp_management(self):
        """Test TP management for SELL positions"""
        signal = "TP1: 1.1950 TP2: 1.1920 TP3: 1.1880"
        tp_levels = self.manager.parse_tp_levels_from_signal(
            signal, "EURUSD", TradeDirection.SELL, 1.2000
        )
        
        self.assertEqual(len(tp_levels), 3)
        
        # All TP levels should be below entry price for SELL
        for tp_level in tp_levels:
            self.assertLess(tp_level.price, 1.2000)
        
        success = self.manager.add_tp_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.SELL,
            entry_price=1.2000,
            lot_size=1.0,
            tp_levels=tp_levels,
            current_sl=1.2020
        )
        
        self.assertTrue(success)
        
        position = self.manager.tp_positions[12345]
        self.assertEqual(position.direction, TradeDirection.SELL)
        self.assertEqual(position.current_sl, 1.2020)  # SL above entry for SELL


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)