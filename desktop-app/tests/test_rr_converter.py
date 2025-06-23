"""
Test Suite for R:R Converter Engine
Comprehensive tests covering R:R calculations, price conversions, integration scenarios, and edge cases
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

from rr_converter import (
    RRConverter, RRConfiguration, RRLevel, RRPosition, RRUpdate,
    RRStrategy, RRTrigger, TradeDirection
)


class TestRRConverter(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        # Test configuration
        test_config = {
            "rr_converter": {
                "default_ratio": 2.0,
                "min_ratio": 0.5,
                "max_ratio": 5.0,
                "auto_calculate_sl": True,
                "auto_calculate_tp": True,
                "use_atr_multiplier": False,
                "atr_period": 14,
                "atr_multiplier": 1.5,
                "risk_percentage": 2.0,
                "update_interval": 5,
                "enable_progressive_rr": True,
                "progressive_ratios": [1.0, 1.5, 2.0, 3.0],
                "volatility_adjustment": True,
                "min_tp_distance_pips": 10,
                "min_sl_distance_pips": 5
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize empty log file
        json.dump({"rr_updates": []}, self.temp_log)
        self.temp_log.close()
        
        # Create RR converter instance
        self.rr_converter = RRConverter(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
        
        # Setup mock modules
        self.setup_mocks()
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def setup_mocks(self):
        """Setup mock modules for testing"""
        self.mock_mt5_bridge = Mock()
        self.mock_mt5_bridge.get_current_price = AsyncMock(return_value=1.1050)
        
        self.mock_sl_manager = Mock()
        self.mock_sl_manager.update_stop_loss = AsyncMock(return_value=True)
        
        self.mock_tp_manager = Mock()
        self.mock_tp_manager.update_take_profit = AsyncMock(return_value=True)
        
        self.mock_market_data = Mock()
        self.mock_market_data.get_current_price = AsyncMock(return_value=1.1050)
        
        # Inject mocks
        self.rr_converter.inject_modules(
            mt5_bridge=self.mock_mt5_bridge,
            market_data=self.mock_market_data,
            sl_manager=self.mock_sl_manager,
            tp_manager=self.mock_tp_manager
        )


class TestRRCalculations(TestRRConverter):
    """Test R:R calculation functionality"""
    
    def test_pip_value_calculation(self):
        """Test pip value calculation for different symbols"""
        # Test major pairs
        self.assertEqual(self.rr_converter.get_pip_value("EURUSD"), 0.0001)
        self.assertEqual(self.rr_converter.get_pip_value("GBPUSD"), 0.0001)
        self.assertEqual(self.rr_converter.get_pip_value("AUDUSD"), 0.0001)
        
        # Test JPY pairs
        self.assertEqual(self.rr_converter.get_pip_value("USDJPY"), 0.01)
        self.assertEqual(self.rr_converter.get_pip_value("EURJPY"), 0.01)
        self.assertEqual(self.rr_converter.get_pip_value("GBPJPY"), 0.01)
        
        # Test unknown symbol (should default to 0.0001)
        self.assertEqual(self.rr_converter.get_pip_value("UNKNOWN"), 0.0001)
    
    def test_pips_calculation(self):
        """Test pips calculation from price differences"""
        # Test EURUSD (4-decimal places)
        pips = self.rr_converter.calculate_pips("EURUSD", 0.0020)
        self.assertEqual(pips, 20.0)
        
        # Test USDJPY (2-decimal places)
        pips = self.rr_converter.calculate_pips("USDJPY", 0.20)
        self.assertEqual(pips, 20.0)
        
        # Test negative price difference
        pips = self.rr_converter.calculate_pips("EURUSD", -0.0015)
        self.assertEqual(pips, 15.0)
    
    def test_price_conversion_from_pips(self):
        """Test converting pips to price difference"""
        # Test EURUSD
        price_diff = self.rr_converter.pips_to_price("EURUSD", 25.0)
        self.assertEqual(price_diff, 0.0025)
        
        # Test USDJPY
        price_diff = self.rr_converter.pips_to_price("USDJPY", 30.0)
        self.assertEqual(price_diff, 0.30)
    
    def test_lot_size_calculation(self):
        """Test lot size calculation for risk management"""
        # Test with normal parameters
        lot_size = self.rr_converter.calculate_lot_size_for_risk(
            symbol="EURUSD",
            entry_price=1.1000,
            sl_price=1.0980,
            risk_amount=100.0
        )
        
        # Should return a positive lot size
        self.assertGreater(lot_size, 0)
        self.assertGreaterEqual(lot_size, 0.01)  # Minimum lot size
        
        # Test with zero SL distance (edge case)
        lot_size = self.rr_converter.calculate_lot_size_for_risk(
            symbol="EURUSD",
            entry_price=1.1000,
            sl_price=1.1000,  # Same as entry
            risk_amount=100.0
        )
        
        self.assertEqual(lot_size, 0.01)  # Should return minimum
    
    def test_rr_levels_calculation(self):
        """Test R:R levels calculation"""
        levels = self.rr_converter.calculate_rr_levels(
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            target_ratios=[1.0, 2.0, 3.0],
            risk_amount=100.0,
            sl_distance_pips=20.0
        )
        
        self.assertEqual(len(levels), 3)
        
        # Check first level (1:1 ratio)
        level1 = levels[0]
        self.assertEqual(level1.ratio, 1.0)
        self.assertEqual(level1.sl_distance_pips, 20.0)
        self.assertEqual(level1.tp_distance_pips, 20.0)  # 1:1 ratio
        self.assertEqual(level1.risk_amount, 100.0)
        self.assertEqual(level1.reward_amount, 100.0)  # 1:1 ratio
        
        # Check SL and TP prices for BUY
        self.assertEqual(level1.sl_price, 1.0980)  # Entry - 20 pips
        self.assertEqual(level1.tp_price, 1.1020)  # Entry + 20 pips
        
        # Check second level (1:2 ratio)
        level2 = levels[1]
        self.assertEqual(level2.ratio, 2.0)
        self.assertEqual(level2.tp_distance_pips, 40.0)  # 2x SL distance
        self.assertEqual(level2.reward_amount, 200.0)  # 2x risk
        self.assertEqual(level2.tp_price, 1.1040)  # Entry + 40 pips
    
    def test_rr_levels_calculation_sell(self):
        """Test R:R levels calculation for SELL positions"""
        levels = self.rr_converter.calculate_rr_levels(
            symbol="EURUSD",
            direction=TradeDirection.SELL,
            entry_price=1.1000,
            target_ratios=[1.0, 2.0],
            risk_amount=100.0,
            sl_distance_pips=15.0
        )
        
        self.assertEqual(len(levels), 2)
        
        # Check first level for SELL
        level1 = levels[0]
        self.assertEqual(level1.sl_price, 1.1015)  # Entry + 15 pips (SL above for SELL)
        self.assertEqual(level1.tp_price, 1.0985)  # Entry - 15 pips (TP below for SELL)


class TestRRPositionManagement(TestRRConverter):
    """Test R:R position management functionality"""
    
    def test_add_rr_position(self):
        """Test adding R:R position to monitoring"""
        success = self.rr_converter.add_rr_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            current_price=1.1010,
            original_sl=1.0980,
            original_tp=1.1040,
            lot_size=0.1,
            target_ratios=[1.0, 2.0, 3.0]
        )
        
        self.assertTrue(success)
        self.assertIn(12345, self.rr_converter.positions)
        
        position = self.rr_converter.positions[12345]
        self.assertEqual(position.symbol, "EURUSD")
        self.assertEqual(position.direction, TradeDirection.BUY)
        self.assertEqual(position.entry_price, 1.1000)
        self.assertEqual(len(position.calculated_levels), 3)
    
    def test_remove_rr_position(self):
        """Test removing R:R position from monitoring"""
        # First add a position
        self.rr_converter.add_rr_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            current_price=1.1010,
            original_sl=1.0980,
            original_tp=1.1040,
            lot_size=0.1
        )
        
        # Then remove it
        success = self.rr_converter.remove_rr_position(12345)
        self.assertTrue(success)
        self.assertNotIn(12345, self.rr_converter.positions)
        
        # Try to remove non-existent position
        success = self.rr_converter.remove_rr_position(99999)
        self.assertFalse(success)
    
    def test_get_position_rr_info(self):
        """Test getting R:R information for position"""
        # Add test position
        self.rr_converter.add_rr_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            current_price=1.1010,
            original_sl=1.0980,
            original_tp=1.1040,
            lot_size=0.1,
            target_ratios=[1.0, 2.0]
        )
        
        # Get position info
        info = self.rr_converter.get_position_rr_info(12345)
        
        self.assertIsNotNone(info)
        self.assertEqual(info['ticket'], 12345)
        self.assertEqual(info['symbol'], "EURUSD")
        self.assertEqual(info['direction'], "buy")
        self.assertEqual(len(info['calculated_levels']), 2)
        
        # Test non-existent position
        info = self.rr_converter.get_position_rr_info(99999)
        self.assertIsNone(info)


class TestRRIntegration(TestRRConverter):
    """Test R:R converter integration with other modules"""
    
    async def test_update_sl_tp_from_rr(self):
        """Test updating SL/TP based on R:R calculations"""
        # Add test position
        self.rr_converter.add_rr_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            current_price=1.1010,
            original_sl=1.0980,
            original_tp=1.1040,
            lot_size=0.1,
            target_ratios=[1.0, 2.0]
        )
        
        position = self.rr_converter.positions[12345]
        rr_level = position.calculated_levels[1]  # Use 1:2 ratio level
        
        # Test SL/TP update
        success = await self.rr_converter.update_sl_tp_from_rr(12345, rr_level, "Test update")
        
        self.assertTrue(success)
        self.mock_sl_manager.update_stop_loss.assert_called_once()
        self.mock_tp_manager.update_take_profit.assert_called_once()
        
        # Check that history was recorded
        self.assertEqual(len(self.rr_converter.rr_history), 1)
        update = self.rr_converter.rr_history[0]
        self.assertEqual(update.ticket, 12345)
        self.assertEqual(update.new_ratio, 2.0)
    
    async def test_optimize_rr_for_position(self):
        """Test R:R optimization based on market conditions"""
        # Add test position
        self.rr_converter.add_rr_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            current_price=1.1010,
            original_sl=1.0980,
            original_tp=1.1040,
            lot_size=0.1,
            target_ratios=[1.0, 2.0, 3.0]
        )
        
        # Mock current price showing profit
        self.mock_market_data.get_current_price.return_value = 1.1015
        
        # Test optimization
        success = await self.rr_converter.optimize_rr_for_position(12345)
        
        # Should update position current price
        position = self.rr_converter.positions[12345]
        self.assertEqual(position.current_price, 1.1015)
    
    async def test_process_rr_updates(self):
        """Test processing all R:R positions"""
        # Add multiple test positions
        for ticket in [12345, 12346, 12347]:
            self.rr_converter.add_rr_position(
                ticket=ticket,
                symbol="EURUSD",
                direction=TradeDirection.BUY,
                entry_price=1.1000,
                current_price=1.1010,
                original_sl=1.0980,
                original_tp=1.1040,
                lot_size=0.1
            )
        
        # Test batch processing
        await self.rr_converter.process_rr_updates()
        
        # Verify all positions were processed (price fetched for each)
        self.assertEqual(self.mock_market_data.get_current_price.call_count, 3)


class TestRREdgeCases(TestRRConverter):
    """Test edge cases and error handling"""
    
    def test_invalid_configuration(self):
        """Test handling of invalid configuration"""
        # Test with missing config file
        invalid_converter = RRConverter(config_file="nonexistent.json")
        self.assertIsInstance(invalid_converter.config, dict)
        self.assertIn('default_ratio', invalid_converter.config)
    
    def test_zero_risk_amount(self):
        """Test handling of zero risk amount"""
        levels = self.rr_converter.calculate_rr_levels(
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            target_ratios=[1.0, 2.0],
            risk_amount=0.0  # Zero risk
        )
        
        # Should still calculate levels with default risk
        self.assertEqual(len(levels), 2)
        for level in levels:
            self.assertGreater(level.risk_amount, 0)
    
    def test_extreme_ratios(self):
        """Test handling of extreme R:R ratios"""
        # Test very high ratio
        levels = self.rr_converter.calculate_rr_levels(
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            target_ratios=[10.0, 20.0],  # Very high ratios
            sl_distance_pips=10.0
        )
        
        self.assertEqual(len(levels), 2)
        self.assertEqual(levels[0].tp_distance_pips, 100.0)  # 10x SL distance
        self.assertEqual(levels[1].tp_distance_pips, 200.0)  # 20x SL distance
    
    def test_invalid_symbol_handling(self):
        """Test handling of invalid/unknown symbols"""
        levels = self.rr_converter.calculate_rr_levels(
            symbol="INVALID",
            direction=TradeDirection.BUY,
            entry_price=1.0000,
            target_ratios=[1.0],
            sl_distance_pips=20.0
        )
        
        # Should still work with default pip value
        self.assertEqual(len(levels), 1)
        self.assertIsNotNone(levels[0].sl_price)
        self.assertIsNotNone(levels[0].tp_price)
    
    async def test_failed_module_integration(self):
        """Test handling when integrated modules fail"""
        # Setup failing mocks
        self.mock_sl_manager.update_stop_loss.return_value = False
        self.mock_tp_manager.update_take_profit.return_value = False
        
        # Add test position
        self.rr_converter.add_rr_position(
            ticket=12345,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            current_price=1.1010,
            original_sl=1.0980,
            original_tp=1.1040,
            lot_size=0.1
        )
        
        position = self.rr_converter.positions[12345]
        rr_level = position.calculated_levels[0]
        
        # Test update with failing modules
        success = await self.rr_converter.update_sl_tp_from_rr(12345, rr_level)
        
        # Should fail when modules fail
        self.assertFalse(success)


class TestRRStatistics(TestRRConverter):
    """Test R:R statistics and reporting functionality"""
    
    def test_get_rr_statistics(self):
        """Test R:R statistics generation"""
        # Add test positions
        for ticket in [12345, 12346]:
            self.rr_converter.add_rr_position(
                ticket=ticket,
                symbol="EURUSD",
                direction=TradeDirection.BUY,
                entry_price=1.1000,
                current_price=1.1010,
                original_sl=1.0980,
                original_tp=1.1040,
                lot_size=0.1
            )
        
        # Add test history
        self.rr_converter.rr_history.append(
            RRUpdate(
                ticket=12345,
                old_ratio=1.0,
                new_ratio=2.0,
                old_sl=1.0980,
                new_sl=1.0970,
                old_tp=1.1020,
                new_tp=1.1040,
                reason="Test update"
            )
        )
        
        stats = self.rr_converter.get_rr_statistics()
        
        self.assertEqual(stats['total_positions'], 2)
        self.assertEqual(stats['active_positions'], 2)
        self.assertEqual(stats['total_updates'], 1)
        self.assertEqual(stats['average_rr_ratio'], 2.0)
        self.assertIn('config', stats)
    
    def test_get_recent_rr_updates(self):
        """Test getting recent R:R updates"""
        # Add multiple updates
        for i in range(5):
            self.rr_converter.rr_history.append(
                RRUpdate(
                    ticket=12345 + i,
                    old_ratio=1.0,
                    new_ratio=2.0 + i,
                    old_sl=1.0980,
                    new_sl=1.0970,
                    old_tp=1.1020,
                    new_tp=1.1040,
                    reason=f"Update {i}"
                )
            )
        
        recent_updates = self.rr_converter.get_recent_rr_updates(limit=3)
        
        self.assertEqual(len(recent_updates), 3)
        # Should be sorted by timestamp (most recent first)
        self.assertEqual(recent_updates[0]['new_ratio'], 6.0)  # Last added
        self.assertEqual(recent_updates[1]['new_ratio'], 5.0)
        self.assertEqual(recent_updates[2]['new_ratio'], 4.0)


def run_async_test(test_func):
    """Helper to run async test functions"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_func())
    finally:
        loop.close()


if __name__ == '__main__':
    # Configure test runner for async tests
    import inspect
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestRRCalculations,
        TestRRPositionManagement,
        TestRRIntegration,
        TestRREdgeCases,
        TestRRStatistics
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Run async tests separately
    print("\n=== Running Async Integration Tests ===")
    
    async_tests = [
        TestRRIntegration().test_update_sl_tp_from_rr,
        TestRRIntegration().test_optimize_rr_for_position,
        TestRRIntegration().test_process_rr_updates,
        TestRREdgeCases().test_failed_module_integration
    ]
    
    for async_test in async_tests:
        try:
            print(f"Running {async_test.__name__}...")
            run_async_test(async_test)
            print(f"✓ {async_test.__name__} passed")
        except Exception as e:
            print(f"✗ {async_test.__name__} failed: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")