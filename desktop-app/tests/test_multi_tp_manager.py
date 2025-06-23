"""
Test Suite for Multi TP Manager Engine
Tests multi-level take profit management, partial closures, and SL shifting
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

from multi_tp_manager import (
    MultiTPManager, TPLevel, TPStatus, SLShiftMode, MultiTPConfig, 
    MultiTPTrade, TPHitEvent
)

class MockMT5Bridge:
    """Mock MT5 bridge for testing"""
    
    def __init__(self):
        self.mock_ticks = {}
        self.partial_close_results = {}
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
        
    async def partial_close_position(self, ticket: int, volume: float, price: float, deviation: int):
        """Mock partial close execution"""
        if ticket in self.partial_close_results:
            return self.partial_close_results[ticket]
        
        # Default successful partial close
        return {
            'success': True,
            'ticket': ticket,
            'volume': volume,
            'price': price
        }
        
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
        
    def set_partial_close_result(self, ticket: int, result: dict):
        """Set mock partial close result"""
        self.partial_close_results[ticket] = result
        
    def set_modification_result(self, ticket: int, result: dict):
        """Set mock modification result"""
        self.modification_results[ticket] = result

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

class TestMultiTPManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "multi_tp_manager": {
                "enabled": True,
                "default_monitoring_interval": 0.1,  # Fast for testing
                "default_sl_shift_mode": "break_even",
                "default_sl_buffer_pips": 2.0,
                "default_min_remaining_volume": 0.01,
                "default_max_slippage_pips": 3.0,
                "default_expire_hours": 1,  # Short for testing
                "max_tp_levels": 100,
                "enable_partial_close_notifications": True,
                "symbol_specific_settings": {
                    "EURUSD": {
                        "min_remaining_volume": 0.01,
                        "max_slippage_pips": 2.0,
                        "sl_buffer_pips": 1.5
                    }
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize multi-TP manager
        self.manager = MultiTPManager(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
        # Setup mocks
        self.setup_mocks()
        
    def tearDown(self):
        """Clean up test environment"""
        self.manager.stop_monitoring()
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
        # Clean up trades file if created
        trades_file = self.temp_log.name.replace('.log', '_trades.json')
        if os.path.exists(trades_file):
            os.unlink(trades_file)
        
    def setup_mocks(self):
        """Setup mock dependencies"""
        self.mock_mt5 = MockMT5Bridge()
        self.mock_sl_manager = MockSLManager()
        
        self.manager.set_dependencies(
            mt5_bridge=self.mock_mt5,
            sl_manager=self.mock_sl_manager
        )

class TestBasicFunctionality(TestMultiTPManager):
    """Test basic multi-TP manager functionality"""
    
    def test_initialization(self):
        """Test multi-TP manager initialization"""
        self.assertTrue(self.manager.config['enabled'])
        self.assertEqual(self.manager.config['max_tp_levels'], 100)
        self.assertEqual(self.manager.config['default_sl_shift_mode'], 'break_even')
        
    def test_pip_value_calculation(self):
        """Test pip value calculation for different symbols"""
        self.assertEqual(self.manager._get_pip_value('EURUSD'), 0.00001)
        self.assertEqual(self.manager._get_pip_value('USDJPY'), 0.001)
        self.assertEqual(self.manager._get_pip_value('XAUUSD'), 0.01)
        
    def test_add_multi_tp_trade(self):
        """Test adding a multi-TP trade"""
        tp_levels = [
            {'level': 1, 'price': 1.1050, 'percentage': 30.0},
            {'level': 2, 'price': 1.1100, 'percentage': 40.0},
            {'level': 3, 'price': 1.1150, 'percentage': 30.0}
        ]
        
        success = self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=0.3,
            tp_levels=tp_levels,
            current_sl=1.0950
        )
        
        self.assertTrue(success)
        self.assertIn(123456, self.manager.active_trades)
        
        trade = self.manager.active_trades[123456]
        self.assertEqual(trade.symbol, 'EURUSD')
        self.assertEqual(trade.direction, 'buy')
        self.assertEqual(len(trade.config.tp_levels), 3)
        self.assertEqual(trade.remaining_volume, 0.3)

class TestTPHitDetection(TestMultiTPManager):
    """Test TP hit detection logic"""
    
    def test_check_tp_hits_buy_trade(self):
        """Test TP hit detection for BUY trade"""
        # Add trade
        tp_levels = [
            {'level': 1, 'price': 1.1050, 'percentage': 50.0},
            {'level': 2, 'price': 1.1100, 'percentage': 50.0}
        ]
        
        self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=0.2,
            tp_levels=tp_levels
        )
        
        trade = self.manager.active_trades[123456]
        
        # Price below TP1 - no hits
        price_data = {'bid': 1.1040, 'ask': 1.1042}
        hit_tps = self.manager._check_tp_hits(trade, price_data)
        self.assertEqual(len(hit_tps), 0)
        
        # Price at TP1 - should hit TP1
        price_data = {'bid': 1.1048, 'ask': 1.1050}
        hit_tps = self.manager._check_tp_hits(trade, price_data)
        self.assertEqual(len(hit_tps), 1)
        self.assertEqual(hit_tps[0].level, 1)
        
        # Price above TP2 - should hit both TP1 and TP2
        price_data = {'bid': 1.1098, 'ask': 1.1100}
        hit_tps = self.manager._check_tp_hits(trade, price_data)
        self.assertEqual(len(hit_tps), 2)
        
    def test_check_tp_hits_sell_trade(self):
        """Test TP hit detection for SELL trade"""
        # Add trade
        tp_levels = [
            {'level': 1, 'price': 1.0950, 'percentage': 50.0},
            {'level': 2, 'price': 1.0900, 'percentage': 50.0}
        ]
        
        self.manager.add_multi_tp_trade(
            ticket=123457,
            symbol='EURUSD',
            direction='sell',
            entry_price=1.1000,
            volume=0.2,
            tp_levels=tp_levels
        )
        
        trade = self.manager.active_trades[123457]
        
        # Price above TP1 - no hits
        price_data = {'bid': 1.0960, 'ask': 1.0962}
        hit_tps = self.manager._check_tp_hits(trade, price_data)
        self.assertEqual(len(hit_tps), 0)
        
        # Price at TP1 - should hit TP1
        price_data = {'bid': 1.0950, 'ask': 1.0952}
        hit_tps = self.manager._check_tp_hits(trade, price_data)
        self.assertEqual(len(hit_tps), 1)
        self.assertEqual(hit_tps[0].level, 1)

class TestVolumeCalculations(TestMultiTPManager):
    """Test volume calculation logic"""
    
    def test_calculate_close_volume(self):
        """Test volume calculation for TP levels"""
        # Add trade
        tp_levels = [
            {'level': 1, 'price': 1.1050, 'percentage': 30.0},
            {'level': 2, 'price': 1.1100, 'percentage': 70.0}
        ]
        
        self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=1.0,  # 1.0 lot
            tp_levels=tp_levels
        )
        
        trade = self.manager.active_trades[123456]
        
        # TP1 should close 30% = 0.3 lots
        volume_tp1 = self.manager._calculate_close_volume(trade, trade.config.tp_levels[0])
        self.assertEqual(volume_tp1, 0.3)
        
        # TP2 should close 70% = 0.7 lots
        volume_tp2 = self.manager._calculate_close_volume(trade, trade.config.tp_levels[1])
        self.assertEqual(volume_tp2, 0.7)
        
        # Test with reduced remaining volume
        trade.remaining_volume = 0.5
        volume_tp2_reduced = self.manager._calculate_close_volume(trade, trade.config.tp_levels[1])
        self.assertEqual(volume_tp2_reduced, 0.5)  # Can't close more than remaining

class TestSLShifting(TestMultiTPManager):
    """Test stop loss shifting logic"""
    
    def test_calculate_new_sl_break_even(self):
        """Test SL calculation for break-even mode"""
        # Add trade with break-even SL shifting
        tp_levels = [
            {'level': 1, 'price': 1.1050, 'percentage': 50.0}
        ]
        
        self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=0.2,
            tp_levels=tp_levels,
            sl_shift_mode='break_even'
        )
        
        trade = self.manager.active_trades[123456]
        hit_tp = trade.config.tp_levels[0]
        
        # Calculate new SL (should be entry + buffer)
        new_sl = self.manager._calculate_new_sl(trade, hit_tp)
        
        # Entry 1.1000 + 1.5 pips buffer = 1.10015
        expected_sl = 1.1000 + (1.5 * 0.00001)  # EURUSD buffer from config
        self.assertAlmostEqual(new_sl, expected_sl, places=5)
        
    def test_calculate_new_sl_next_tp(self):
        """Test SL calculation for next TP mode"""
        # Add trade with next TP SL shifting
        tp_levels = [
            {'level': 1, 'price': 1.1050, 'percentage': 30.0},
            {'level': 2, 'price': 1.1100, 'percentage': 70.0}
        ]
        
        self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=0.3,
            tp_levels=tp_levels,
            sl_shift_mode='next_tp'
        )
        
        trade = self.manager.active_trades[123456]
        hit_tp = trade.config.tp_levels[0]  # TP1
        
        # Calculate new SL (should be next TP - buffer)
        new_sl = self.manager._calculate_new_sl(trade, hit_tp)
        
        # Next TP (1.1100) - 1.5 pips buffer = 1.10985
        expected_sl = 1.1100 - (1.5 * 0.00001)
        self.assertAlmostEqual(new_sl, expected_sl, places=5)

class TestPartialCloseExecution(TestMultiTPManager):
    """Test partial close execution"""
    
    def test_successful_partial_close(self):
        """Test successful partial close execution"""
        async def run_test():
            # Setup successful partial close result
            self.mock_mt5.set_partial_close_result(123456, {
                'success': True,
                'ticket': 123456,
                'volume': 0.15,
                'price': 1.1050
            })
            
            # Add trade
            tp_levels = [
                {'level': 1, 'price': 1.1050, 'percentage': 50.0}
            ]
            
            self.manager.add_multi_tp_trade(
                ticket=123456,
                symbol='EURUSD',
                direction='buy',
                entry_price=1.1000,
                volume=0.3,
                tp_levels=tp_levels
            )
            
            trade = self.manager.active_trades[123456]
            tp_level = trade.config.tp_levels[0]
            
            # Execute partial close
            success = await self.manager._execute_partial_close(trade, tp_level, 1.1050)
            
            self.assertTrue(success)
            self.assertEqual(tp_level.status, TPStatus.HIT)
            self.assertEqual(tp_level.actual_close_price, 1.1050)
            self.assertEqual(tp_level.closed_volume, 0.15)  # 50% of 0.3
            self.assertEqual(trade.remaining_volume, 0.15)  # 0.3 - 0.15
            self.assertEqual(trade.last_tp_hit, 1)
            
        asyncio.run(run_test())
        
    def test_failed_partial_close(self):
        """Test failed partial close execution"""
        async def run_test():
            # Setup failed partial close result
            self.mock_mt5.set_partial_close_result(123456, {
                'success': False,
                'error': 'Insufficient volume'
            })
            
            # Add trade
            tp_levels = [
                {'level': 1, 'price': 1.1050, 'percentage': 50.0}
            ]
            
            self.manager.add_multi_tp_trade(
                ticket=123456,
                symbol='EURUSD',
                direction='buy',
                entry_price=1.1000,
                volume=0.3,
                tp_levels=tp_levels
            )
            
            trade = self.manager.active_trades[123456]
            tp_level = trade.config.tp_levels[0]
            
            # Execute partial close
            success = await self.manager._execute_partial_close(trade, tp_level, 1.1050)
            
            self.assertFalse(success)
            self.assertEqual(tp_level.status, TPStatus.PENDING)  # Should remain pending
            self.assertEqual(trade.remaining_volume, 0.3)  # Should be unchanged
            
        asyncio.run(run_test())

class TestSLUpdate(TestMultiTPManager):
    """Test stop loss update functionality"""
    
    def test_successful_sl_update(self):
        """Test successful SL update"""
        async def run_test():
            # Setup successful SL modification
            self.mock_sl_manager.set_modification_result(123456, True)
            
            # Add trade
            tp_levels = [
                {'level': 1, 'price': 1.1050, 'percentage': 50.0}
            ]
            
            self.manager.add_multi_tp_trade(
                ticket=123456,
                symbol='EURUSD',
                direction='buy',
                entry_price=1.1000,
                volume=0.3,
                tp_levels=tp_levels,
                current_sl=1.0950
            )
            
            trade = self.manager.active_trades[123456]
            
            # Update SL
            success = await self.manager._update_stop_loss(trade, 1.0980)
            
            self.assertTrue(success)
            self.assertEqual(trade.current_sl, 1.0980)
            
        asyncio.run(run_test())

class TestTradeManagement(TestMultiTPManager):
    """Test trade management operations"""
    
    def test_remove_multi_tp_trade(self):
        """Test removing a multi-TP trade"""
        # Add trade
        tp_levels = [
            {'level': 1, 'price': 1.1050, 'percentage': 100.0}
        ]
        
        self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=0.2,
            tp_levels=tp_levels
        )
        
        # Verify trade exists
        self.assertIn(123456, self.manager.active_trades)
        
        # Remove trade
        success = self.manager.remove_multi_tp_trade(123456, "Test removal")
        
        self.assertTrue(success)
        self.assertNotIn(123456, self.manager.active_trades)
        
    def test_get_trade_info(self):
        """Test getting trade information"""
        # Add trade
        tp_levels = [
            {'level': 1, 'price': 1.1050, 'percentage': 100.0}
        ]
        
        self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=0.2,
            tp_levels=tp_levels
        )
        
        # Get trade info
        trade_info = self.manager.get_trade_info(123456)
        
        self.assertIsNotNone(trade_info)
        self.assertEqual(trade_info.ticket, 123456)
        self.assertEqual(trade_info.symbol, 'EURUSD')
        
        # Test non-existent trade
        non_existent = self.manager.get_trade_info(999999)
        self.assertIsNone(non_existent)

class TestStatistics(TestMultiTPManager):
    """Test statistics and monitoring"""
    
    def test_statistics_calculation(self):
        """Test statistics calculation"""
        # Initially empty
        stats = self.manager.get_statistics()
        self.assertEqual(stats['active_trades'], 0)
        self.assertEqual(stats['total_tp_hits'], 0)
        
        # Add trade
        tp_levels = [
            {'level': 1, 'price': 1.1050, 'percentage': 50.0},
            {'level': 2, 'price': 1.1100, 'percentage': 50.0}
        ]
        
        self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=0.2,
            tp_levels=tp_levels
        )
        
        # Check updated stats
        stats = self.manager.get_statistics()
        self.assertEqual(stats['active_trades'], 1)
        
        # Add TP hit event
        tp_hit = TPHitEvent(
            ticket=123456,
            tp_level=1,
            tp_price=1.1050,
            actual_price=1.1050,
            closed_volume=0.1,
            remaining_volume=0.1,
            profit=5.0,
            new_sl=1.1000,
            timestamp=datetime.now(),
            success=True
        )
        self.manager.tp_hit_history.append(tp_hit)
        
        stats = self.manager.get_statistics()
        self.assertEqual(stats['total_tp_hits'], 1)
        self.assertEqual(stats['successful_tp_hits'], 1)
        self.assertEqual(stats['tp_hit_success_rate'], 100.0)
        
    def test_trade_persistence(self):
        """Test trade persistence to file"""
        # Add trade
        tp_levels = [
            {'level': 1, 'price': 1.1050, 'percentage': 100.0}
        ]
        
        self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=0.2,
            tp_levels=tp_levels
        )
        
        # Check trades file was created
        trades_file = self.manager.log_path.replace('.log', '_trades.json')
        self.assertTrue(os.path.exists(trades_file))
        
        # Load trades in new instance
        new_manager = MultiTPManager(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
        # Check trade was loaded
        self.assertIn(123456, new_manager.active_trades)
        loaded_trade = new_manager.active_trades[123456]
        self.assertEqual(loaded_trade.symbol, 'EURUSD')
        self.assertEqual(loaded_trade.entry_price, 1.1000)

class TestErrorHandling(TestMultiTPManager):
    """Test error handling and edge cases"""
    
    def test_invalid_tp_levels(self):
        """Test handling of invalid TP levels"""
        # Test with invalid prices
        tp_levels = [
            {'level': 1, 'price': 0.0, 'percentage': 50.0},  # Invalid price
            {'level': 2, 'price': 1.1100, 'percentage': 0.0}  # Invalid percentage
        ]
        
        success = self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=0.2,
            tp_levels=tp_levels
        )
        
        self.assertFalse(success)
        self.assertNotIn(123456, self.manager.active_trades)
        
    def test_excessive_tp_percentage(self):
        """Test handling of TP percentages over 100%"""
        tp_levels = [
            {'level': 1, 'price': 1.1050, 'percentage': 60.0},
            {'level': 2, 'price': 1.1100, 'percentage': 60.0}  # Total = 120%
        ]
        
        success = self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=0.2,
            tp_levels=tp_levels
        )
        
        # Should still succeed but log a warning
        self.assertTrue(success)
        self.assertIn(123456, self.manager.active_trades)
        
    def test_duplicate_trade_ticket(self):
        """Test handling of duplicate trade tickets"""
        tp_levels = [
            {'level': 1, 'price': 1.1050, 'percentage': 100.0}
        ]
        
        # Add first trade
        success1 = self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            volume=0.2,
            tp_levels=tp_levels
        )
        
        # Try to add duplicate
        success2 = self.manager.add_multi_tp_trade(
            ticket=123456,
            symbol='GBPUSD',
            direction='sell',
            entry_price=1.2500,
            volume=0.3,
            tp_levels=tp_levels
        )
        
        self.assertTrue(success1)
        self.assertFalse(success2)
        
        # Should still have only one trade
        self.assertEqual(len(self.manager.active_trades), 1)

if __name__ == '__main__':
    unittest.main()