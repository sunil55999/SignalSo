"""
Test Suite for TP/SL Adjustor Engine
Tests dynamic TP/SL adjustments based on spread conditions and market volatility
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

from tp_sl_adjustor import (
    TPSLAdjustor, AdjustmentType, AdjustmentReason, AdjustmentRule, 
    AdjustmentEvent, TradeInfo
)

class MockMT5Bridge:
    """Mock MT5 bridge for testing"""
    
    def __init__(self):
        self.mock_ticks = {}
        self.mock_positions = []
        self.modification_results = {}
        
    def set_mock_tick(self, symbol: str, bid: float, ask: float):
        """Set mock tick data for symbol"""
        self.mock_ticks[symbol] = {
            'bid': bid,
            'ask': ask,
            'last': (bid + ask) / 2,
            'time': datetime.now(),
            'symbol': symbol
        }
        
    def get_symbol_tick(self, symbol: str):
        """Mock implementation of get_symbol_tick"""
        return self.mock_ticks.get(symbol, None)
        
    def set_mock_positions(self, positions: list):
        """Set mock open positions"""
        self.mock_positions = positions
        
    def get_open_positions(self):
        """Mock implementation of get_open_positions"""
        return self.mock_positions
        
    async def modify_position(self, ticket: int, sl: float = None, tp: float = None):
        """Mock position modification"""
        if ticket in self.modification_results:
            return self.modification_results[ticket]
        
        # Default successful modification
        return {
            'success': True,
            'ticket': ticket,
            'sl': sl,
            'tp': tp
        }
        
    def set_modification_result(self, ticket: int, result: dict):
        """Set mock modification result"""
        self.modification_results[ticket] = result

class MockSpreadChecker:
    """Mock spread checker for testing"""
    
    def __init__(self):
        self.spread_data = {}
        
    def set_spread_data(self, symbol: str, spread_pips: float):
        """Set spread data for symbol"""
        self.spread_data[symbol] = spread_pips
        
    def check_spread_before_trade(self, symbol: str):
        """Mock spread check"""
        spread_pips = self.spread_data.get(symbol, 2.0)
        spread_info = {'spread_pips': spread_pips}
        result = type('SpreadResult', (), {'value': 'allowed'})()
        return result, spread_info

class MockTPManager:
    """Mock TP manager for testing"""
    
    def __init__(self):
        self.modification_results = {}
        
    async def modify_take_profit(self, ticket: int, new_tp: float):
        """Mock TP modification"""
        return self.modification_results.get(ticket, True)
        
    def set_modification_result(self, ticket: int, success: bool):
        """Set modification result"""
        self.modification_results[ticket] = success

class MockSLManager:
    """Mock SL manager for testing"""
    
    def __init__(self):
        self.modification_results = {}
        
    async def modify_stop_loss(self, ticket: int, new_sl: float):
        """Mock SL modification"""
        return self.modification_results.get(ticket, True)
        
    def set_modification_result(self, ticket: int, success: bool):
        """Set modification result"""
        self.modification_results[ticket] = success

class TestTPSLAdjustor(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "tp_sl_adjustor": {
                "enabled": True,
                "monitoring_interval": 0.1,  # Fast for testing
                "min_adjustment_interval": 1,  # Short for testing
                "default_spread_threshold": 3.0,
                "default_sl_buffer_pips": 2.0,
                "default_tp_buffer_pips": 2.0,
                "max_adjustment_per_session": 5.0,
                "enable_volatility_adjustments": True,
                "enable_spread_adjustments": True,
                "symbol_specific_rules": {
                    "EURUSD": {
                        "spread_threshold": 2.0,
                        "sl_buffer_pips": 1.5,
                        "tp_buffer_pips": 1.5,
                        "min_distance_pips": 10.0,
                        "max_adjustment_pips": 3.0
                    }
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize TP/SL adjustor
        self.adjustor = TPSLAdjustor(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
        # Setup mocks
        self.setup_mocks()
        
    def tearDown(self):
        """Clean up test environment"""
        self.adjustor.stop_monitoring()
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
    def setup_mocks(self):
        """Setup mock dependencies"""
        self.mock_mt5 = MockMT5Bridge()
        self.mock_spread_checker = MockSpreadChecker()
        self.mock_tp_manager = MockTPManager()
        self.mock_sl_manager = MockSLManager()
        
        self.adjustor.set_dependencies(
            mt5_bridge=self.mock_mt5,
            spread_checker=self.mock_spread_checker,
            tp_manager=self.mock_tp_manager,
            sl_manager=self.mock_sl_manager
        )

class TestBasicFunctionality(TestTPSLAdjustor):
    """Test basic TP/SL adjustor functionality"""
    
    def test_initialization(self):
        """Test TP/SL adjustor initialization"""
        self.assertTrue(self.adjustor.config['enabled'])
        self.assertEqual(self.adjustor.config['default_spread_threshold'], 3.0)
        self.assertEqual(self.adjustor.config['default_sl_buffer_pips'], 2.0)
        
    def test_pip_value_calculation(self):
        """Test pip value calculation for different symbols"""
        self.assertEqual(self.adjustor._get_pip_value('EURUSD'), 0.00001)
        self.assertEqual(self.adjustor._get_pip_value('USDJPY'), 0.001)
        self.assertEqual(self.adjustor._get_pip_value('XAUUSD'), 0.01)
        
    def test_adjustment_rules_loading(self):
        """Test loading of adjustment rules from configuration"""
        self.assertIn('EURUSD', self.adjustor.adjustment_rules)
        eurusd_rules = self.adjustor.adjustment_rules['EURUSD']
        self.assertGreater(len(eurusd_rules), 0)
        
        # Check spread-based rule
        spread_rule = None
        for rule in eurusd_rules:
            if rule.adjustment_type == AdjustmentType.SPREAD_BASED:
                spread_rule = rule
                break
                
        self.assertIsNotNone(spread_rule)
        self.assertEqual(spread_rule.trigger_condition, 2.0)  # EURUSD spread threshold
        self.assertEqual(spread_rule.sl_adjustment_pips, 1.5)

class TestMarketDataHandling(TestTPSLAdjustor):
    """Test market data handling and spread calculation"""
    
    def test_get_market_data(self):
        """Test market data retrieval"""
        # Set mock data
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0852)
        self.mock_spread_checker.set_spread_data('EURUSD', 2.0)
        
        market_data = self.adjustor._get_market_data('EURUSD')
        
        self.assertIsNotNone(market_data)
        self.assertEqual(market_data['symbol'], 'EURUSD')
        self.assertEqual(market_data['bid'], 1.0850)
        self.assertEqual(market_data['ask'], 1.0852)
        self.assertEqual(market_data['spread_pips'], 2.0)
        
    def test_market_data_caching(self):
        """Test market data caching"""
        # Set mock data
        self.mock_mt5.set_mock_tick('EURUSD', 1.0850, 1.0852)
        self.mock_spread_checker.set_spread_data('EURUSD', 2.0)
        
        # First call
        market_data1 = self.adjustor._get_market_data('EURUSD')
        
        # Second call should use cache
        market_data2 = self.adjustor._get_market_data('EURUSD')
        
        self.assertEqual(market_data1, market_data2)

class TestAdjustmentLogic(TestTPSLAdjustor):
    """Test adjustment decision logic"""
    
    def test_should_adjust_high_spread(self):
        """Test adjustment decision for high spread"""
        # Create trade info
        trade = TradeInfo(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.0900,
            current_sl=1.0850,
            current_tp=1.0950,
            volume=0.1,
            open_time=datetime.now()
        )
        
        # High spread market data
        market_data = {
            'symbol': 'EURUSD',
            'bid': 1.0895,
            'ask': 1.0905,  # 10 pip spread
            'spread_pips': 10.0,
            'time': datetime.now()
        }
        
        should_adjust, reason = self.adjustor._should_adjust_levels(trade, market_data)
        
        self.assertTrue(should_adjust)
        self.assertEqual(reason, AdjustmentReason.HIGH_SPREAD)
        
    def test_should_adjust_low_spread(self):
        """Test adjustment decision for low spread"""
        # Create trade info
        trade = TradeInfo(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.0900,
            current_sl=1.0850,
            current_tp=1.0950,
            volume=0.1,
            open_time=datetime.now()
        )
        
        # Low spread market data
        market_data = {
            'symbol': 'EURUSD',
            'bid': 1.0899,
            'ask': 1.0900,  # 1 pip spread
            'spread_pips': 1.0,
            'time': datetime.now()
        }
        
        should_adjust, reason = self.adjustor._should_adjust_levels(trade, market_data)
        
        self.assertTrue(should_adjust)
        self.assertEqual(reason, AdjustmentReason.LOW_SPREAD)
        
    def test_should_not_adjust_normal_spread(self):
        """Test no adjustment for normal spread"""
        # Create trade info
        trade = TradeInfo(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.0900,
            current_sl=1.0850,
            current_tp=1.0950,
            volume=0.1,
            open_time=datetime.now()
        )
        
        # Normal spread market data
        market_data = {
            'symbol': 'EURUSD',
            'bid': 1.0898,
            'ask': 1.0900,  # 2 pip spread (at threshold)
            'spread_pips': 2.0,
            'time': datetime.now()
        }
        
        should_adjust, reason = self.adjustor._should_adjust_levels(trade, market_data)
        
        self.assertFalse(should_adjust)

class TestLevelCalculation(TestTPSLAdjustor):
    """Test SL/TP level calculations"""
    
    def test_calculate_adjusted_levels_high_spread_buy(self):
        """Test level calculation for BUY trade with high spread"""
        # Create trade info
        trade = TradeInfo(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.0900,
            current_sl=1.0850,
            current_tp=1.0950,
            volume=0.1,
            open_time=datetime.now()
        )
        
        # Market data with current price
        market_data = {
            'bid': 1.0895,
            'ask': 1.0905,
            'spread_pips': 10.0
        }
        
        new_sl, new_tp = self.adjustor._calculate_adjusted_levels(
            trade, market_data, AdjustmentReason.HIGH_SPREAD
        )
        
        # For high spread, SL should be moved further away (lower for BUY)
        self.assertLess(new_sl, trade.current_sl)
        # TP should be moved closer (lower for BUY)
        self.assertLess(new_tp, trade.current_tp)
        
    def test_calculate_adjusted_levels_high_spread_sell(self):
        """Test level calculation for SELL trade with high spread"""
        # Create trade info
        trade = TradeInfo(
            ticket=123457,
            symbol='EURUSD',
            direction='sell',
            entry_price=1.0900,
            current_sl=1.0950,
            current_tp=1.0850,
            volume=0.1,
            open_time=datetime.now()
        )
        
        # Market data with current price
        market_data = {
            'bid': 1.0895,
            'ask': 1.0905,
            'spread_pips': 10.0
        }
        
        new_sl, new_tp = self.adjustor._calculate_adjusted_levels(
            trade, market_data, AdjustmentReason.HIGH_SPREAD
        )
        
        # For high spread, SL should be moved further away (higher for SELL)
        self.assertGreater(new_sl, trade.current_sl)
        # TP should be moved closer (higher for SELL)
        self.assertGreater(new_tp, trade.current_tp)
        
    def test_calculate_adjusted_levels_low_spread(self):
        """Test level calculation for low spread"""
        # Create trade info
        trade = TradeInfo(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.0900,
            current_sl=1.0850,
            current_tp=1.0950,
            volume=0.1,
            open_time=datetime.now()
        )
        
        # Market data with low spread
        market_data = {
            'bid': 1.0899,
            'ask': 1.0900,
            'spread_pips': 1.0
        }
        
        new_sl, new_tp = self.adjustor._calculate_adjusted_levels(
            trade, market_data, AdjustmentReason.LOW_SPREAD
        )
        
        # For low spread, SL should be moved closer (higher for BUY)
        self.assertGreater(new_sl, trade.current_sl)

class TestAdjustmentExecution(TestTPSLAdjustor):
    """Test adjustment execution"""
    
    def test_successful_adjustment_execution(self):
        """Test successful SL/TP adjustment execution"""
        async def run_test():
            # Create trade info
            trade = TradeInfo(
                ticket=123456,
                symbol='EURUSD',
                direction='buy',
                entry_price=1.0900,
                current_sl=1.0850,
                current_tp=1.0950,
                volume=0.1,
                open_time=datetime.now()
            )
            
            # Set successful modification results
            self.mock_sl_manager.set_modification_result(123456, True)
            self.mock_tp_manager.set_modification_result(123456, True)
            
            # Apply adjustments
            success = await self.adjustor._apply_adjustments(
                trade, 1.0845, 1.0945, AdjustmentReason.HIGH_SPREAD
            )
            
            self.assertTrue(success)
            self.assertGreater(len(self.adjustor.adjustment_history), 0)
            
            # Check adjustment event
            event = self.adjustor.adjustment_history[-1]
            self.assertEqual(event.ticket, 123456)
            self.assertEqual(event.new_sl, 1.0845)
            self.assertEqual(event.new_tp, 1.0945)
            self.assertTrue(event.success)
            
        asyncio.run(run_test())
        
    def test_failed_adjustment_execution(self):
        """Test failed SL/TP adjustment execution"""
        async def run_test():
            # Create trade info
            trade = TradeInfo(
                ticket=123456,
                symbol='EURUSD',
                direction='buy',
                entry_price=1.0900,
                current_sl=1.0850,
                current_tp=1.0950,
                volume=0.1,
                open_time=datetime.now()
            )
            
            # Set failed modification results
            self.mock_sl_manager.set_modification_result(123456, False)
            self.mock_tp_manager.set_modification_result(123456, False)
            
            # Apply adjustments
            success = await self.adjustor._apply_adjustments(
                trade, 1.0845, 1.0945, AdjustmentReason.HIGH_SPREAD
            )
            
            self.assertFalse(success)
            
            # Check adjustment event
            event = self.adjustor.adjustment_history[-1]
            self.assertEqual(event.ticket, 123456)
            self.assertFalse(event.success)
            self.assertIsNotNone(event.error_message)
            
        asyncio.run(run_test())

class TestManualAdjustments(TestTPSLAdjustor):
    """Test manual adjustment functionality"""
    
    def test_manual_adjust_trade(self):
        """Test manual trade adjustment"""
        async def run_test():
            # Set mock open positions
            positions = [{
                'ticket': 123456,
                'symbol': 'EURUSD',
                'type': 0,  # BUY
                'price_open': 1.0900,
                'sl': 1.0850,
                'tp': 1.0950,
                'volume': 0.1,
                'time': datetime.now()
            }]
            self.mock_mt5.set_mock_positions(positions)
            
            # Set successful modification
            self.mock_sl_manager.set_modification_result(123456, True)
            self.mock_tp_manager.set_modification_result(123456, True)
            
            # Manual adjustment
            success = await self.adjustor.manual_adjust_trade(
                ticket=123456,
                new_sl=1.0840,
                new_tp=1.0960,
                reason="Manual test adjustment"
            )
            
            self.assertTrue(success)
            
            # Check adjustment was recorded
            self.assertGreater(len(self.adjustor.adjustment_history), 0)
            event = self.adjustor.adjustment_history[-1]
            self.assertEqual(event.reason, AdjustmentReason.MANUAL_OVERRIDE)
            
        asyncio.run(run_test())

class TestRuleManagement(TestTPSLAdjustor):
    """Test adjustment rule management"""
    
    def test_add_adjustment_rule(self):
        """Test adding new adjustment rule"""
        new_rule = AdjustmentRule(
            symbol='GBPUSD',
            adjustment_type=AdjustmentType.SPREAD_BASED,
            trigger_condition=3.0,
            sl_adjustment_pips=2.5,
            tp_adjustment_pips=2.5,
            min_distance_pips=15.0,
            max_adjustment_pips=5.0
        )
        
        success = self.adjustor.add_adjustment_rule('GBPUSD', new_rule)
        
        self.assertTrue(success)
        self.assertIn('GBPUSD', self.adjustor.adjustment_rules)
        
        gbpusd_rules = self.adjustor.adjustment_rules['GBPUSD']
        self.assertGreater(len(gbpusd_rules), 0)
        
    def test_remove_adjustment_rule(self):
        """Test removing adjustment rule"""
        # First add a rule
        self.test_add_adjustment_rule()
        
        # Then remove it
        success = self.adjustor.remove_adjustment_rule('GBPUSD', AdjustmentType.SPREAD_BASED)
        
        self.assertTrue(success)
        
        gbpusd_rules = self.adjustor.adjustment_rules.get('GBPUSD', [])
        spread_rules = [r for r in gbpusd_rules if r.adjustment_type == AdjustmentType.SPREAD_BASED]
        self.assertEqual(len(spread_rules), 0)
        
    def test_get_symbol_rules(self):
        """Test getting rules for a symbol"""
        eurusd_rules = self.adjustor.get_symbol_rules('EURUSD')
        
        self.assertGreater(len(eurusd_rules), 0)
        self.assertEqual(eurusd_rules[0].symbol, 'EURUSD')

class TestStatistics(TestTPSLAdjustor):
    """Test statistics and monitoring"""
    
    def test_adjustment_statistics(self):
        """Test adjustment statistics calculation"""
        # Initially empty
        stats = self.adjustor.get_adjustment_statistics()
        self.assertEqual(stats['total_adjustments'], 0)
        self.assertEqual(stats['success_rate'], 0.0)
        
        # Add some adjustment events
        event1 = AdjustmentEvent(
            ticket=123456,
            symbol='EURUSD',
            adjustment_type=AdjustmentType.SPREAD_BASED,
            reason=AdjustmentReason.HIGH_SPREAD,
            old_sl=1.0850,
            new_sl=1.0845,
            old_tp=1.0950,
            new_tp=1.0945,
            adjustment_pips_sl=0.5,
            adjustment_pips_tp=0.5,
            timestamp=datetime.now(),
            success=True
        )
        
        event2 = AdjustmentEvent(
            ticket=123457,
            symbol='GBPUSD',
            adjustment_type=AdjustmentType.SPREAD_BASED,
            reason=AdjustmentReason.LOW_SPREAD,
            old_sl=1.2450,
            new_sl=1.2455,
            old_tp=1.2550,
            new_tp=1.2545,
            adjustment_pips_sl=0.5,
            adjustment_pips_tp=0.5,
            timestamp=datetime.now(),
            success=False,
            error_message="Broker rejection"
        )
        
        self.adjustor.adjustment_history.extend([event1, event2])
        
        # Check updated stats
        stats = self.adjustor.get_adjustment_statistics()
        self.assertEqual(stats['total_adjustments'], 2)
        self.assertEqual(stats['successful_adjustments'], 1)
        self.assertEqual(stats['success_rate'], 50.0)
        
        # Check groupings
        self.assertIn('high_spread', stats['adjustments_by_reason'])
        self.assertIn('low_spread', stats['adjustments_by_reason'])
        self.assertIn('EURUSD', stats['adjustments_by_symbol'])
        self.assertIn('GBPUSD', stats['adjustments_by_symbol'])
        
    def test_get_recent_adjustments(self):
        """Test getting recent adjustments"""
        # Add adjustment event
        event = AdjustmentEvent(
            ticket=123456,
            symbol='EURUSD',
            adjustment_type=AdjustmentType.SPREAD_BASED,
            reason=AdjustmentReason.HIGH_SPREAD,
            old_sl=1.0850,
            new_sl=1.0845,
            old_tp=1.0950,
            new_tp=1.0945,
            adjustment_pips_sl=0.5,
            adjustment_pips_tp=0.5,
            timestamp=datetime.now(),
            success=True
        )
        
        self.adjustor.adjustment_history.append(event)
        
        recent = self.adjustor.get_recent_adjustments(limit=5)
        
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]['ticket'], 123456)
        self.assertEqual(recent[0]['symbol'], 'EURUSD')

if __name__ == '__main__':
    unittest.main()