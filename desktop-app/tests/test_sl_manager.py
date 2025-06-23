"""
Test Suite for SL Manager Engine
Tests dynamic SL adjustments, multiple strategies, signal parsing, and integration scenarios
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

from sl_manager import (
    SLManager, SLRule, SLConfiguration, SLManagedPosition, SLAdjustment,
    SLStrategy, SLTrigger, SLAction, TradeDirection
)


class TestSLManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'sl_manager': {
                'update_interval_seconds': 5,
                'default_trailing_distance': 20.0,
                'max_sl_moves_per_day': 10,
                'min_sl_distance_pips': 5.0,
                'atr_period': 14,
                'volatility_multiplier': 2.0,
                'pip_values': {
                    'EURUSD': 0.0001,
                    'GBPUSD': 0.0001,
                    'USDJPY': 0.01,
                    'default': 0.0001
                },
                'default_sl_rules': [
                    {
                        'strategy': 'trailing',
                        'trigger': 'on_profit',
                        'action': 'trail_by_pips',
                        'value': 20.0,
                        'condition': 'profit > 15 pips',
                        'priority': 1
                    }
                ],
                'max_positions_to_monitor': 100
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        json.dump([], self.temp_log)
        self.temp_log.close()
        
        self.manager = SLManager(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
        
        # Mock MT5 bridge
        self.mock_mt5_bridge = Mock()
        self.mock_mt5_bridge.get_current_price = AsyncMock()
        self.mock_mt5_bridge.modify_position = AsyncMock()
        
        # Mock market data
        self.mock_market_data = Mock()
        self.mock_market_data.get_current_price = AsyncMock()
        self.mock_market_data.get_atr = AsyncMock()
        
        # Mock other engines
        self.mock_trailing_stop = Mock()
        self.mock_break_even = Mock()
        self.mock_tp_manager = Mock()
        self.mock_tp_manager.get_position_status = Mock()
        
        self.manager.inject_modules(
            mt5_bridge=self.mock_mt5_bridge,
            market_data=self.mock_market_data,
            trailing_stop_engine=self.mock_trailing_stop,
            break_even_engine=self.mock_break_even,
            tp_manager=self.mock_tp_manager
        )
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_parse_sl_breakeven_command(self):
        """Test parsing SL to breakeven command"""
        signal = "SL to breakeven after TP1"
        sl_rules = self.manager.parse_sl_commands_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(sl_rules), 1)
        rule = sl_rules[0]
        self.assertEqual(rule.strategy, SLStrategy.FIXED)
        self.assertEqual(rule.trigger, SLTrigger.ON_TP_HIT)
        self.assertEqual(rule.action, SLAction.MOVE_TO_BREAKEVEN)
        self.assertEqual(rule.value, 0.0)
        self.assertEqual(rule.condition, 'tp_level >= 1')
    
    def test_parse_sl_trailing_command(self):
        """Test parsing trailing SL command"""
        signal = "Trail SL by 20 pips when 15 pips profit"
        sl_rules = self.manager.parse_sl_commands_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(sl_rules), 1)
        rule = sl_rules[0]
        self.assertEqual(rule.strategy, SLStrategy.TRAILING)
        self.assertEqual(rule.trigger, SLTrigger.ON_PROFIT)
        self.assertEqual(rule.action, SLAction.TRAIL_BY_PIPS)
        self.assertEqual(rule.value, 20.0)
        self.assertEqual(rule.condition, 'profit > 15 pips')
    
    def test_parse_sl_move_to_tp_command(self):
        """Test parsing move SL to TP level command"""
        signal = "Move SL to TP1 after TP2 hit"
        sl_rules = self.manager.parse_sl_commands_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(sl_rules), 1)
        rule = sl_rules[0]
        self.assertEqual(rule.strategy, SLStrategy.FIXED)
        self.assertEqual(rule.trigger, SLTrigger.ON_TP_HIT)
        self.assertEqual(rule.action, SLAction.MOVE_TO_TP_LEVEL)
        self.assertEqual(rule.value, 1.0)  # TP1
        self.assertEqual(rule.condition, 'tp_level >= 2')  # After TP2
    
    def test_parse_sl_atr_command(self):
        """Test parsing ATR-based SL command"""
        signal = "ATR SL with 2.5x multiplier"
        sl_rules = self.manager.parse_sl_commands_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(sl_rules), 1)
        rule = sl_rules[0]
        self.assertEqual(rule.strategy, SLStrategy.ATR_BASED)
        self.assertEqual(rule.trigger, SLTrigger.ON_PROFIT)
        self.assertEqual(rule.action, SLAction.ADJUST_BY_ATR)
        self.assertEqual(rule.value, 2.5)
    
    def test_parse_sl_percentage_command(self):
        """Test parsing percentage-based SL command"""
        signal = "SL 5% below high"
        sl_rules = self.manager.parse_sl_commands_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(sl_rules), 1)
        rule = sl_rules[0]
        self.assertEqual(rule.strategy, SLStrategy.PERCENTAGE_BASED)
        self.assertEqual(rule.trigger, SLTrigger.ON_PROFIT)
        self.assertEqual(rule.action, SLAction.TRAIL_BY_PERCENTAGE)
        self.assertEqual(rule.value, 5.0)
    
    def test_create_default_sl_rules(self):
        """Test creating default SL rules from configuration"""
        default_rules = self.manager.create_default_sl_rules()
        
        self.assertEqual(len(default_rules), 1)
        rule = default_rules[0]
        self.assertEqual(rule.strategy, SLStrategy.TRAILING)
        self.assertEqual(rule.action, SLAction.TRAIL_BY_PIPS)
        self.assertEqual(rule.value, 20.0)
    
    def test_add_sl_managed_position(self):
        """Test adding position to SL management"""
        custom_rules = [
            SLRule(
                strategy=SLStrategy.TRAILING,
                trigger=SLTrigger.ON_PROFIT,
                action=SLAction.TRAIL_BY_PIPS,
                value=15.0,
                condition='profit > 10 pips'
            )
        ]
        
        success = self.manager.add_sl_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            lot_size=1.0,
            current_sl=1.1980,
            custom_rules=custom_rules
        )
        
        self.assertTrue(success)
        self.assertIn(12345, self.manager.sl_positions)
        
        position = self.manager.sl_positions[12345]
        self.assertEqual(position.symbol, "EURUSD")
        self.assertEqual(position.direction, TradeDirection.BUY)
        self.assertEqual(position.entry_price, 1.2000)
        self.assertEqual(position.current_sl, 1.1980)
        self.assertEqual(len(position.config.rules), 2)  # 1 custom + 1 default
    
    def test_remove_sl_managed_position(self):
        """Test removing position from SL management"""
        # Add position first
        self.manager.add_sl_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            lot_size=1.0
        )
        
        # Remove position
        success = self.manager.remove_sl_managed_position(12345)
        self.assertTrue(success)
        self.assertNotIn(12345, self.manager.sl_positions)
        
        # Try removing non-existent position
        success = self.manager.remove_sl_managed_position(99999)
        self.assertFalse(success)
    
    def test_evaluate_sl_rule_condition_profit(self):
        """Test evaluating SL rule condition based on profit"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980
        )
        
        rule = SLRule(
            strategy=SLStrategy.TRAILING,
            trigger=SLTrigger.ON_PROFIT,
            action=SLAction.TRAIL_BY_PIPS,
            value=20.0,
            condition='profit > 15 pips'
        )
        
        # Test with 20 pips profit (should pass)
        current_price = 1.2020  # +20 pips
        result = self.manager.evaluate_sl_rule_condition(position, rule, current_price)
        self.assertTrue(result)
        
        # Test with 10 pips profit (should fail)
        current_price = 1.2010  # +10 pips
        result = self.manager.evaluate_sl_rule_condition(position, rule, current_price)
        self.assertFalse(result)
    
    def test_evaluate_sl_rule_condition_tp_level(self):
        """Test evaluating SL rule condition based on TP level"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            tp_levels_hit=[1, 2]  # TP1 and TP2 hit
        )
        
        rule = SLRule(
            strategy=SLStrategy.FIXED,
            trigger=SLTrigger.ON_TP_HIT,
            action=SLAction.MOVE_TO_BREAKEVEN,
            value=0.0,
            condition='tp_level >= 1'
        )
        
        current_price = 1.2050
        result = self.manager.evaluate_sl_rule_condition(position, rule, current_price)
        self.assertTrue(result)
        
        # Test higher threshold
        rule.condition = 'tp_level >= 3'
        result = self.manager.evaluate_sl_rule_condition(position, rule, current_price)
        self.assertFalse(result)
    
    async def test_calculate_new_sl_breakeven(self):
        """Test calculating new SL for breakeven action"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980
        )
        
        rule = SLRule(
            strategy=SLStrategy.FIXED,
            trigger=SLTrigger.ON_TP_HIT,
            action=SLAction.MOVE_TO_BREAKEVEN,
            value=0.0
        )
        
        new_sl = await self.manager.calculate_new_sl(position, rule, 1.2050)
        self.assertEqual(new_sl, 1.2000)  # Entry price
    
    async def test_calculate_new_sl_trail_by_pips_buy(self):
        """Test calculating new SL for trailing by pips (BUY position)"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980
        )
        
        rule = SLRule(
            strategy=SLStrategy.TRAILING,
            trigger=SLTrigger.ON_PROFIT,
            action=SLAction.TRAIL_BY_PIPS,
            value=20.0  # 20 pips
        )
        
        current_price = 1.2050
        new_sl = await self.manager.calculate_new_sl(position, rule, current_price)
        expected_sl = 1.2050 - 0.0020  # 20 pips below current price
        self.assertEqual(new_sl, expected_sl)
    
    async def test_calculate_new_sl_trail_by_pips_sell(self):
        """Test calculating new SL for trailing by pips (SELL position)"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.SELL,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.2020,
            current_sl=1.2020
        )
        
        rule = SLRule(
            strategy=SLStrategy.TRAILING,
            trigger=SLTrigger.ON_PROFIT,
            action=SLAction.TRAIL_BY_PIPS,
            value=20.0  # 20 pips
        )
        
        current_price = 1.1950  # Price moved down (profit for SELL)
        new_sl = await self.manager.calculate_new_sl(position, rule, current_price)
        expected_sl = 1.1950 + 0.0020  # 20 pips above current price
        self.assertEqual(new_sl, expected_sl)
    
    async def test_calculate_new_sl_trail_by_percentage(self):
        """Test calculating new SL for trailing by percentage"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            best_price_achieved=1.2100  # High watermark
        )
        
        rule = SLRule(
            strategy=SLStrategy.PERCENTAGE_BASED,
            trigger=SLTrigger.ON_PROFIT,
            action=SLAction.TRAIL_BY_PERCENTAGE,
            value=2.0  # 2%
        )
        
        current_price = 1.2080
        new_sl = await self.manager.calculate_new_sl(position, rule, current_price)
        expected_sl = 1.2100 * 0.98  # 2% below high
        self.assertEqual(new_sl, expected_sl)
    
    async def test_calculate_new_sl_atr_based(self):
        """Test calculating new SL for ATR-based adjustment"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980
        )
        
        rule = SLRule(
            strategy=SLStrategy.ATR_BASED,
            trigger=SLTrigger.ON_PROFIT,
            action=SLAction.ADJUST_BY_ATR,
            value=2.0  # 2x ATR
        )
        
        # Mock ATR value
        self.mock_market_data.get_atr.return_value = 0.0015  # 15 pips
        
        current_price = 1.2050
        new_sl = await self.manager.calculate_new_sl(position, rule, current_price)
        expected_sl = 1.2050 - (0.0015 * 2.0)  # Current price - (2 * ATR)
        self.assertEqual(new_sl, expected_sl)
    
    async def test_calculate_new_sl_move_to_tp_level(self):
        """Test calculating new SL for moving to TP level"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980
        )
        
        rule = SLRule(
            strategy=SLStrategy.FIXED,
            trigger=SLTrigger.ON_TP_HIT,
            action=SLAction.MOVE_TO_TP_LEVEL,
            value=1.0  # TP1
        )
        
        # Mock TP manager response
        self.mock_tp_manager.get_position_status.return_value = {
            'tp_levels': [
                {'level': 1, 'price': 1.2050},
                {'level': 2, 'price': 1.2080}
            ]
        }
        
        current_price = 1.2070
        new_sl = await self.manager.calculate_new_sl(position, rule, current_price)
        self.assertEqual(new_sl, 1.2050)  # TP1 price
    
    def test_validate_new_sl_buy_position(self):
        """Test validating new SL for BUY position"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            sl_moves_today=0,
            sl_adjustments_count=0,
            config=SLConfiguration(
                max_sl_moves_per_day=10,
                min_distance_pips=5.0
            )
        )
        
        current_price = 1.2050
        
        # Valid SL (more than 5 pips below current price)
        valid_sl = 1.2040  # 10 pips below current price
        result = self.manager.validate_new_sl(position, valid_sl, current_price)
        self.assertTrue(result)
        
        # Invalid SL (too close to current price)
        invalid_sl = 1.2048  # Only 2 pips below current price
        result = self.manager.validate_new_sl(position, invalid_sl, current_price)
        self.assertFalse(result)
        
        # Invalid SL (above current price)
        invalid_sl = 1.2055  # Above current price
        result = self.manager.validate_new_sl(position, invalid_sl, current_price)
        self.assertFalse(result)
    
    def test_validate_new_sl_sell_position(self):
        """Test validating new SL for SELL position"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.SELL,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.2020,
            current_sl=1.2020,
            sl_moves_today=0,
            sl_adjustments_count=0,
            config=SLConfiguration(
                max_sl_moves_per_day=10,
                min_distance_pips=5.0
            )
        )
        
        current_price = 1.1950
        
        # Valid SL (more than 5 pips above current price)
        valid_sl = 1.1960  # 10 pips above current price
        result = self.manager.validate_new_sl(position, valid_sl, current_price)
        self.assertTrue(result)
        
        # Invalid SL (too close to current price)
        invalid_sl = 1.1952  # Only 2 pips above current price
        result = self.manager.validate_new_sl(position, invalid_sl, current_price)
        self.assertFalse(result)
    
    def test_validate_new_sl_daily_limit(self):
        """Test validating new SL with daily move limit"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            sl_moves_today=10,  # Already at limit
            sl_adjustments_count=0,
            config=SLConfiguration(
                max_sl_moves_per_day=10,
                min_distance_pips=5.0
            )
        )
        
        current_price = 1.2050
        valid_sl = 1.2040
        
        result = self.manager.validate_new_sl(position, valid_sl, current_price)
        self.assertFalse(result)  # Should fail due to daily limit
    
    async def test_execute_sl_adjustment_success(self):
        """Test successful SL adjustment execution"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            sl_moves_today=0,
            sl_adjustments_count=0,
            config=SLConfiguration()
        )
        
        rule = SLRule(
            strategy=SLStrategy.TRAILING,
            trigger=SLTrigger.ON_PROFIT,
            action=SLAction.TRAIL_BY_PIPS,
            value=20.0
        )
        
        # Mock successful MT5 modification
        self.mock_mt5_bridge.modify_position.return_value = {'success': True}
        
        new_sl = 1.2030
        current_price = 1.2050
        reason = "Trailing stop adjustment"
        
        success = await self.manager.execute_sl_adjustment(position, new_sl, rule, current_price, reason)
        
        self.assertTrue(success)
        self.assertEqual(position.current_sl, new_sl)
        self.assertEqual(position.sl_adjustments_count, 1)
        self.assertEqual(position.sl_moves_today, 1)
        
        # Verify MT5 call
        self.mock_mt5_bridge.modify_position.assert_called_once_with(
            ticket=12345,
            new_sl=new_sl
        )
        
        # Verify adjustment history
        self.assertEqual(len(self.manager.adjustment_history), 1)
        adjustment = self.manager.adjustment_history[0]
        self.assertEqual(adjustment.ticket, 12345)
        self.assertEqual(adjustment.new_sl, new_sl)
        self.assertEqual(adjustment.strategy_used, SLStrategy.TRAILING)
    
    async def test_execute_sl_adjustment_mt5_failure(self):
        """Test SL adjustment execution with MT5 failure"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            config=SLConfiguration()
        )
        
        rule = SLRule(
            strategy=SLStrategy.TRAILING,
            trigger=SLTrigger.ON_PROFIT,
            action=SLAction.TRAIL_BY_PIPS,
            value=20.0
        )
        
        # Mock failed MT5 modification
        self.mock_mt5_bridge.modify_position.return_value = {'success': False}
        
        new_sl = 1.2030
        current_price = 1.2050
        reason = "Trailing stop adjustment"
        
        success = await self.manager.execute_sl_adjustment(position, new_sl, rule, current_price, reason)
        
        self.assertFalse(success)
        self.assertEqual(position.current_sl, 1.1980)  # Unchanged
        self.assertEqual(position.sl_adjustments_count, 0)  # Unchanged
    
    async def test_process_sl_rules_priority_order(self):
        """Test that SL rules are processed in priority order"""
        rules = [
            SLRule(
                strategy=SLStrategy.TRAILING,
                trigger=SLTrigger.ON_PROFIT,
                action=SLAction.TRAIL_BY_PIPS,
                value=15.0,
                condition='profit > 10 pips',
                priority=1  # Lower priority
            ),
            SLRule(
                strategy=SLStrategy.FIXED,
                trigger=SLTrigger.ON_PROFIT,
                action=SLAction.MOVE_TO_BREAKEVEN,
                value=0.0,
                condition='profit > 5 pips',
                priority=2  # Higher priority
            )
        ]
        
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            config=SLConfiguration(rules=rules)
        )
        
        # Mock successful MT5 modification
        self.mock_mt5_bridge.modify_position.return_value = {'success': True}
        
        current_price = 1.2020  # +20 pips profit, meets both conditions
        
        await self.manager.process_sl_rules(position, current_price)
        
        # Should execute higher priority rule (move to breakeven)
        self.assertEqual(position.current_sl, 1.2000)  # Breakeven
        self.assertEqual(len(self.manager.adjustment_history), 1)
        self.assertEqual(self.manager.adjustment_history[0].action_taken, SLAction.MOVE_TO_BREAKEVEN)
    
    async def test_handle_tp_hit_notification(self):
        """Test handling TP hit notification"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            tp_levels_hit=[]
        )
        
        self.manager.sl_positions[12345] = position
        
        await self.manager.handle_tp_hit_notification(12345, 1)
        
        self.assertIn(1, position.tp_levels_hit)
        
        # Test duplicate notification (should not add again)
        await self.manager.handle_tp_hit_notification(12345, 1)
        self.assertEqual(position.tp_levels_hit.count(1), 1)
    
    async def test_handle_breakeven_notification(self):
        """Test handling breakeven notification"""
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.1980,
            breakeven_triggered=False
        )
        
        self.manager.sl_positions[12345] = position
        
        await self.manager.handle_breakeven_notification(12345)
        
        self.assertTrue(position.breakeven_triggered)
    
    def test_get_sl_statistics_empty(self):
        """Test statistics with no SL history"""
        stats = self.manager.get_sl_statistics()
        
        expected = {
            'total_positions': 0,
            'active_positions': 0,
            'total_adjustments': 0,
            'successful_adjustments': 0,
            'strategies_used': {},
            'actions_taken': {},
            'average_profit_at_adjustment': 0.0
        }
        
        self.assertEqual(stats, expected)
    
    def test_get_sl_statistics_with_data(self):
        """Test statistics with SL data"""
        # Add test position
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.2020
        )
        
        self.manager.sl_positions[12345] = position
        
        # Add test adjustment history
        adjustment = SLAdjustment(
            ticket=12345,
            old_sl=1.1980,
            new_sl=1.2020,
            adjustment_reason="Trailing stop",
            strategy_used=SLStrategy.TRAILING,
            action_taken=SLAction.TRAIL_BY_PIPS,
            market_price=1.2050,
            profit_pips=50.0,
            timestamp=datetime.now()
        )
        self.manager.adjustment_history.append(adjustment)
        
        stats = self.manager.get_sl_statistics()
        
        self.assertEqual(stats['total_positions'], 1)
        self.assertEqual(stats['active_positions'], 1)
        self.assertEqual(stats['total_adjustments'], 1)
        self.assertEqual(stats['successful_adjustments'], 1)
        self.assertEqual(stats['strategies_used'], {'trailing': 1})
        self.assertEqual(stats['actions_taken'], {'trail_by_pips': 1})
        self.assertEqual(stats['average_profit_at_adjustment'], 50.0)
    
    def test_get_position_status(self):
        """Test getting status of specific SL managed position"""
        rules = [
            SLRule(
                strategy=SLStrategy.TRAILING,
                trigger=SLTrigger.ON_PROFIT,
                action=SLAction.TRAIL_BY_PIPS,
                value=20.0,
                condition='profit > 15 pips',
                priority=1
            )
        ]
        
        position = SLManagedPosition(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            entry_time=datetime.now(),
            lot_size=1.0,
            original_sl=1.1980,
            current_sl=1.2020,
            best_price_achieved=1.2060,
            sl_adjustments_count=2,
            sl_moves_today=1,
            tp_levels_hit=[1],
            breakeven_triggered=True,
            config=SLConfiguration(rules=rules)
        )
        
        self.manager.sl_positions[12345] = position
        
        status = self.manager.get_position_status(12345)
        self.assertIsNotNone(status)
        if status:
            self.assertEqual(status['ticket'], 12345)
            self.assertEqual(status['symbol'], "EURUSD")
            self.assertEqual(status['direction'], 'buy')
            self.assertEqual(status['entry_price'], 1.2000)
            self.assertEqual(status['original_sl'], 1.1980)
            self.assertEqual(status['current_sl'], 1.2020)
            self.assertEqual(status['best_price_achieved'], 1.2060)
            self.assertEqual(status['sl_adjustments_count'], 2)
            self.assertEqual(status['sl_moves_today'], 1)
            self.assertEqual(status['tp_levels_hit'], [1])
            self.assertTrue(status['breakeven_triggered'])
            
            # Check rules status
            self.assertEqual(len(status['rules']), 1)
            self.assertEqual(status['rules'][0]['strategy'], 'trailing')
            self.assertEqual(status['rules'][0]['action'], 'trail_by_pips')
        
        # Test non-existent position
        status = self.manager.get_position_status(99999)
        self.assertIsNone(status)
    
    def test_get_recent_adjustments(self):
        """Test getting recent SL adjustments"""
        # Add multiple adjustments
        adjustments = [
            SLAdjustment(
                ticket=12345,
                old_sl=1.1980,
                new_sl=1.2000,
                adjustment_reason="Move to breakeven",
                strategy_used=SLStrategy.FIXED,
                action_taken=SLAction.MOVE_TO_BREAKEVEN,
                market_price=1.2050,
                profit_pips=50.0,
                timestamp=datetime.now()
            ),
            SLAdjustment(
                ticket=12345,
                old_sl=1.2000,
                new_sl=1.2020,
                adjustment_reason="Trailing stop",
                strategy_used=SLStrategy.TRAILING,
                action_taken=SLAction.TRAIL_BY_PIPS,
                market_price=1.2060,
                profit_pips=60.0,
                timestamp=datetime.now()
            )
        ]
        
        self.manager.adjustment_history.extend(adjustments)
        
        recent = self.manager.get_recent_adjustments(limit=5)
        
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]['ticket'], 12345)
        self.assertEqual(recent[0]['new_sl'], 1.2000)
        self.assertEqual(recent[0]['strategy_used'], 'fixed')
        self.assertEqual(recent[1]['new_sl'], 1.2020)
        self.assertEqual(recent[1]['strategy_used'], 'trailing')


class TestSLManagerIntegration(unittest.TestCase):
    """Integration tests for SL Manager functionality"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'sl_manager': {
                'update_interval_seconds': 1,
                'default_trailing_distance': 15.0,
                'max_sl_moves_per_day': 5,
                'min_sl_distance_pips': 3.0,
                'pip_values': {'EURUSD': 0.0001, 'default': 0.0001},
                'default_sl_rules': [],
                'max_positions_to_monitor': 100
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        json.dump([], self.temp_log)
        self.temp_log.close()
        
        self.manager = SLManager(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def tearDown(self):
        """Clean up integration test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_full_sl_management_cycle(self):
        """Test complete SL management cycle from parsing to execution"""
        # Parse SL commands from signal
        signal = "SL to breakeven after TP1. Trail SL by 15 pips when 10 pips profit"
        sl_rules = self.manager.parse_sl_commands_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(sl_rules), 2)
        
        # Add position to management
        success = self.manager.add_sl_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            lot_size=1.0,
            current_sl=1.1980,
            custom_rules=sl_rules
        )
        
        self.assertTrue(success)
        
        # Verify position was added with parsed rules
        position = self.manager.sl_positions[12345]
        self.assertEqual(position.symbol, "EURUSD")
        self.assertEqual(len(position.config.rules), 2)
    
    def test_complex_signal_parsing(self):
        """Test parsing complex signal with multiple SL commands"""
        signal = """
        EURUSD BUY @ 1.2000
        TP1: 1.2050 TP2: 1.2080 TP3: 1.2120
        SL to breakeven after TP1
        Trail SL by 20 pips when 15 pips profit
        ATR SL with 2x multiplier
        """
        
        sl_rules = self.manager.parse_sl_commands_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(sl_rules), 3)
        
        # Check each rule was parsed correctly
        strategies = [rule.strategy for rule in sl_rules]
        self.assertIn(SLStrategy.FIXED, strategies)
        self.assertIn(SLStrategy.TRAILING, strategies)
        self.assertIn(SLStrategy.ATR_BASED, strategies)
    
    def test_edge_case_no_sl_commands(self):
        """Test signal with no SL commands (should use defaults)"""
        signal = "EURUSD BUY @ 1.2000. TP1: 1.2050"
        sl_rules = self.manager.parse_sl_commands_from_signal(
            signal, "EURUSD", TradeDirection.BUY, 1.2000
        )
        
        self.assertEqual(len(sl_rules), 0)  # No parsed rules
        
        # Add position (should get default rules)
        success = self.manager.add_sl_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.2000,
            lot_size=1.0
        )
        
        self.assertTrue(success)
        position = self.manager.sl_positions[12345]
        # Should have default rules from config (empty in test config)
        self.assertEqual(len(position.config.rules), 0)
    
    def test_sell_position_sl_management(self):
        """Test SL management for SELL positions"""
        signal = "Trail SL by 25 pips when 20 pips profit"
        sl_rules = self.manager.parse_sl_commands_from_signal(
            signal, "EURUSD", TradeDirection.SELL, 1.2000
        )
        
        self.assertEqual(len(sl_rules), 1)
        
        success = self.manager.add_sl_managed_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.SELL,
            entry_price=1.2000,
            lot_size=1.0,
            current_sl=1.2020,  # SL above entry for SELL
            custom_rules=sl_rules
        )
        
        self.assertTrue(success)
        
        position = self.manager.sl_positions[12345]
        self.assertEqual(position.direction, TradeDirection.SELL)
        self.assertEqual(position.current_sl, 1.2020)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)