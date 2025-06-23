"""
Test Suite for Grid Strategy Engine
Tests grid level calculation, order placement, and position management
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

from grid_strategy import (
    GridStrategy, GridDirection, GridStatus, OrderType, GridConfiguration,
    GridLevel, GridInstance
)

class MockMT5Bridge:
    """Mock MT5 bridge for testing"""
    
    def __init__(self):
        self.mock_ticks = {}
        self.mock_orders = []
        self.mock_positions = []
        self.order_results = {}
        self.next_ticket = 10000
        
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
        
    async def place_buy_limit_order(self, symbol: str, volume: float, price: float, comment: str = ""):
        """Mock buy limit order placement"""
        ticket = self.next_ticket
        self.next_ticket += 1
        
        if ticket in self.order_results:
            return self.order_results[ticket]
            
        # Default successful order
        order = {
            'ticket': ticket,
            'symbol': symbol,
            'volume': volume,
            'price': price,
            'type': 'buy_limit',
            'comment': comment
        }
        self.mock_orders.append(order)
        
        return {
            'success': True,
            'ticket': ticket
        }
        
    async def place_sell_limit_order(self, symbol: str, volume: float, price: float, comment: str = ""):
        """Mock sell limit order placement"""
        ticket = self.next_ticket
        self.next_ticket += 1
        
        if ticket in self.order_results:
            return self.order_results[ticket]
            
        # Default successful order
        order = {
            'ticket': ticket,
            'symbol': symbol,
            'volume': volume,
            'price': price,
            'type': 'sell_limit',
            'comment': comment
        }
        self.mock_orders.append(order)
        
        return {
            'success': True,
            'ticket': ticket
        }
        
    async def get_open_orders(self):
        """Mock implementation of get_open_orders"""
        return self.mock_orders
        
    async def get_open_positions(self):
        """Mock implementation of get_open_positions"""
        return self.mock_positions
        
    async def cancel_order(self, ticket: int):
        """Mock order cancellation"""
        self.mock_orders = [order for order in self.mock_orders if order['ticket'] != ticket]
        return {'success': True}
        
    async def close_position(self, ticket: int):
        """Mock position closing"""
        self.mock_positions = [pos for pos in self.mock_positions if pos['ticket'] != ticket]
        return {'success': True}
        
    def set_order_result(self, ticket: int, result: dict):
        """Set mock order result"""
        self.order_results[ticket] = result

class MockMarginChecker:
    """Mock margin checker for testing"""
    
    def __init__(self):
        self.margin_results = {}
        
    async def check_margin_for_trade(self, symbol: str, volume: float, direction: str):
        """Mock margin check"""
        key = f"{symbol}_{volume}_{direction}"
        if key in self.margin_results:
            return self.margin_results[key]
            
        # Default allow
        return Mock(allowed=True)
        
    def set_margin_result(self, symbol: str, volume: float, direction: str, allowed: bool):
        """Set margin check result"""
        key = f"{symbol}_{volume}_{direction}"
        self.margin_results[key] = Mock(allowed=allowed)

class MockSpreadChecker:
    """Mock spread checker for testing"""
    
    def __init__(self):
        self.spread_results = {}
        
    def check_spread_before_trade(self, symbol: str):
        """Mock spread check"""
        if symbol in self.spread_results:
            return self.spread_results[symbol], {}
            
        # Default allow
        return Mock(value="allowed"), {}
        
    def set_spread_result(self, symbol: str, result_value: str):
        """Set spread check result"""
        self.spread_results[symbol] = Mock(value=result_value)

class TestGridStrategy(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "grid_strategy": {
                "enabled": True,
                "monitoring_interval": 0.1,  # Fast for testing
                "max_active_grids": 3,
                "default_grid_spacing_pips": 10.0,
                "default_profit_target_pips": 20.0,
                "max_grid_levels": 10,
                "min_account_balance": 100.0,
                "max_risk_percentage": 10.0,
                "enable_recovery_mode": True,
                "recovery_multiplier": 1.2,
                "symbol_configs": {
                    "EURUSD": {
                        "grid_spacing_pips": 8.0,
                        "max_levels": 5,
                        "base_volume": 0.01,
                        "profit_target_pips": 15.0,
                        "max_spread_pips": 2.0
                    },
                    "XAUUSD": {
                        "grid_spacing_pips": 50.0,
                        "max_levels": 3,
                        "base_volume": 0.01,
                        "profit_target_pips": 100.0,
                        "max_spread_pips": 10.0
                    }
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize grid strategy
        self.strategy = GridStrategy(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
        # Setup mocks
        self.setup_mocks()
        
    def tearDown(self):
        """Clean up test environment"""
        self.strategy.stop_monitoring()
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
        # Clean up grid file if created
        grid_file = self.temp_log.name.replace('.log', '_grids.json')
        if os.path.exists(grid_file):
            os.unlink(grid_file)
        
    def setup_mocks(self):
        """Setup mock dependencies"""
        self.mock_mt5 = MockMT5Bridge()
        self.mock_margin_checker = MockMarginChecker()
        self.mock_spread_checker = MockSpreadChecker()
        
        self.strategy.set_dependencies(
            mt5_bridge=self.mock_mt5,
            margin_checker=self.mock_margin_checker,
            spread_checker=self.mock_spread_checker
        )

class TestBasicFunctionality(TestGridStrategy):
    """Test basic grid strategy functionality"""
    
    def test_initialization(self):
        """Test grid strategy initialization"""
        self.assertTrue(self.strategy.config['enabled'])
        self.assertEqual(self.strategy.config['max_active_grids'], 3)
        self.assertEqual(self.strategy.config['default_grid_spacing_pips'], 10.0)
        
    def test_pip_value_calculation(self):
        """Test pip value calculation for different symbols"""
        self.assertEqual(self.strategy._get_pip_value('EURUSD'), 0.00001)
        self.assertEqual(self.strategy._get_pip_value('USDJPY'), 0.001)
        self.assertEqual(self.strategy._get_pip_value('XAUUSD'), 0.01)
        
    def test_symbol_config_loading(self):
        """Test loading of symbol-specific configurations"""
        eurusd_config = self.strategy._get_symbol_config('EURUSD')
        self.assertEqual(eurusd_config['grid_spacing_pips'], 8.0)
        self.assertEqual(eurusd_config['max_levels'], 5)
        self.assertEqual(eurusd_config['profit_target_pips'], 15.0)
        
        # Test default config for unknown symbol
        unknown_config = self.strategy._get_symbol_config('UNKNOWN')
        self.assertEqual(unknown_config['grid_spacing_pips'], 10.0)  # Default value
        
    def test_volatility_calculation(self):
        """Test volatility calculation for different symbols"""
        xauusd_vol = self.strategy._calculate_volatility('XAUUSD')
        eurusd_vol = self.strategy._calculate_volatility('EURUSD')
        
        # Gold should have higher volatility than EUR/USD
        self.assertGreater(xauusd_vol, eurusd_vol)
        
    def test_grid_spacing_calculation(self):
        """Test grid spacing calculation with volatility adjustment"""
        # Non-adaptive spacing
        fixed_spacing = self.strategy._calculate_grid_spacing('EURUSD', 1.5, adaptive=False)
        self.assertEqual(fixed_spacing, 8.0)  # Should use base spacing
        
        # Adaptive spacing
        adaptive_spacing = self.strategy._calculate_grid_spacing('EURUSD', 2.0, adaptive=True)
        self.assertNotEqual(adaptive_spacing, 8.0)  # Should be adjusted

class TestGridLevelCreation(TestGridStrategy):
    """Test grid level creation and configuration"""
    
    def test_position_size_calculation_basic(self):
        """Test basic position size calculation without martingale"""
        size = self.strategy._calculate_position_size('EURUSD', 1, 0.01, enable_martingale=False)
        self.assertEqual(size, 0.01)
        
        size = self.strategy._calculate_position_size('EURUSD', 5, 0.01, enable_martingale=False)
        self.assertEqual(size, 0.01)  # Should remain constant
        
    def test_position_size_calculation_martingale(self):
        """Test position size calculation with martingale"""
        # Level 1
        size1 = self.strategy._calculate_position_size('EURUSD', 1, 0.01, enable_martingale=True, multiplier=1.5)
        self.assertEqual(size1, 0.015)  # 0.01 * 1.5^1
        
        # Level 2
        size2 = self.strategy._calculate_position_size('EURUSD', 2, 0.01, enable_martingale=True, multiplier=1.5)
        self.assertEqual(size2, 0.0225)  # 0.01 * 1.5^2
        
    def test_create_grid_levels(self):
        """Test creation of grid levels"""
        config = GridConfiguration(
            symbol='EURUSD',
            direction=GridDirection.BIDIRECTIONAL,
            center_price=1.1000,
            grid_spacing_pips=10.0,
            levels_above=3,
            levels_below=3,
            base_volume=0.01
        )
        
        levels = self.strategy._create_grid_levels(config)
        
        # Should have 6 levels total (3 above + 3 below)
        self.assertEqual(len(levels), 6)
        
        # Check buy levels (below center)
        buy_levels = [l for l in levels if l.order_type == OrderType.BUY_LIMIT]
        self.assertEqual(len(buy_levels), 3)
        
        # Check sell levels (above center)
        sell_levels = [l for l in levels if l.order_type == OrderType.SELL_LIMIT]
        self.assertEqual(len(sell_levels), 3)
        
        # Check prices are correctly calculated
        pip_value = 0.00001  # EURUSD pip value
        spacing_price = 10.0 * pip_value  # 10 pips
        
        # First buy level should be center_price - spacing_price
        first_buy = next(l for l in buy_levels if l.level_id == "buy_1")
        expected_price = 1.1000 - spacing_price
        self.assertAlmostEqual(first_buy.price, expected_price, places=5)
        
        # First sell level should be center_price + spacing_price
        first_sell = next(l for l in sell_levels if l.level_id == "sell_1")
        expected_price = 1.1000 + spacing_price
        self.assertAlmostEqual(first_sell.price, expected_price, places=5)

class TestGridCreation(TestGridStrategy):
    """Test grid creation and management"""
    
    def test_create_grid_success(self):
        """Test successful grid creation"""
        async def run_test():
            # Set mock market data
            self.mock_mt5.set_mock_tick('EURUSD', 1.0995, 1.1005)
            
            # Create grid
            grid_id = await self.strategy.create_grid(
                symbol='EURUSD',
                direction=GridDirection.BIDIRECTIONAL,
                center_price=1.1000,
                levels_above=2,
                levels_below=2,
                base_volume=0.01
            )
            
            self.assertIsNotNone(grid_id)
            self.assertIn(grid_id, self.strategy.active_grids)
            
            # Check grid properties
            grid = self.strategy.active_grids[grid_id]
            self.assertEqual(grid.config.symbol, 'EURUSD')
            self.assertEqual(grid.status, GridStatus.ACTIVE)
            self.assertEqual(len(grid.levels), 4)  # 2 above + 2 below
            
        asyncio.run(run_test())
        
    def test_create_grid_insufficient_margin(self):
        """Test grid creation with insufficient margin"""
        async def run_test():
            # Set margin check to fail
            self.mock_margin_checker.set_margin_result('EURUSD', 0.04, 'buy', False)
            
            # Set mock market data
            self.mock_mt5.set_mock_tick('EURUSD', 1.0995, 1.1005)
            
            # Try to create grid
            grid_id = await self.strategy.create_grid(
                symbol='EURUSD',
                direction=GridDirection.BIDIRECTIONAL,
                center_price=1.1000,
                levels_above=2,
                levels_below=2,
                base_volume=0.01
            )
            
            self.assertIsNone(grid_id)
            self.assertEqual(len(self.strategy.active_grids), 0)
            
        asyncio.run(run_test())
        
    def test_create_grid_max_limit(self):
        """Test grid creation when maximum limit is reached"""
        async def run_test():
            # Set mock market data
            self.mock_mt5.set_mock_tick('EURUSD', 1.0995, 1.1005)
            
            # Create grids up to the limit (3)
            for i in range(3):
                grid_id = await self.strategy.create_grid(
                    symbol='EURUSD',
                    direction=GridDirection.BIDIRECTIONAL,
                    center_price=1.1000 + i * 0.001,  # Different prices
                    levels_above=1,
                    levels_below=1,
                    base_volume=0.01
                )
                self.assertIsNotNone(grid_id)
                
            # Try to create one more (should fail)
            grid_id = await self.strategy.create_grid(
                symbol='EURUSD',
                direction=GridDirection.BIDIRECTIONAL,
                center_price=1.1030,
                levels_above=1,
                levels_below=1,
                base_volume=0.01
            )
            
            self.assertIsNone(grid_id)
            self.assertEqual(len(self.strategy.active_grids), 3)
            
        asyncio.run(run_test())

class TestOrderPlacement(TestGridStrategy):
    """Test grid order placement"""
    
    def test_place_grid_order_success(self):
        """Test successful grid order placement"""
        async def run_test():
            level = GridLevel(
                level_id="test_buy_1",
                price=1.0950,
                order_type=OrderType.BUY_LIMIT,
                volume=0.01
            )
            
            success = await self.strategy._place_grid_order(level, 'EURUSD')
            
            self.assertTrue(success)
            self.assertIsNotNone(level.order_ticket)
            
            # Check that order was added to mock orders
            self.assertEqual(len(self.mock_mt5.mock_orders), 1)
            placed_order = self.mock_mt5.mock_orders[0]
            self.assertEqual(placed_order['symbol'], 'EURUSD')
            self.assertEqual(placed_order['price'], 1.0950)
            self.assertEqual(placed_order['volume'], 0.01)
            
        asyncio.run(run_test())
        
    def test_place_grid_order_failure(self):
        """Test failed grid order placement"""
        async def run_test():
            level = GridLevel(
                level_id="test_buy_1",
                price=1.0950,
                order_type=OrderType.BUY_LIMIT,
                volume=0.01
            )
            
            # Set order to fail
            self.mock_mt5.set_order_result(self.mock_mt5.next_ticket, {'success': False, 'error': 'Test error'})
            
            success = await self.strategy._place_grid_order(level, 'EURUSD')
            
            self.assertFalse(success)
            self.assertIsNone(level.order_ticket)
            
        asyncio.run(run_test())
        
    def test_place_grid_order_high_spread(self):
        """Test grid order placement blocked by high spread"""
        async def run_test():
            level = GridLevel(
                level_id="test_buy_1",
                price=1.0950,
                order_type=OrderType.BUY_LIMIT,
                volume=0.01
            )
            
            # Set spread check to block
            self.mock_spread_checker.set_spread_result('EURUSD', 'blocked')
            
            success = await self.strategy._place_grid_order(level, 'EURUSD')
            
            self.assertFalse(success)
            self.assertIsNone(level.order_ticket)
            
        asyncio.run(run_test())

class TestGridManagement(TestGridStrategy):
    """Test grid management operations"""
    
    def test_stop_grid(self):
        """Test stopping a grid"""
        async def run_test():
            # Create a grid first
            self.mock_mt5.set_mock_tick('EURUSD', 1.0995, 1.1005)
            
            grid_id = await self.strategy.create_grid(
                symbol='EURUSD',
                direction=GridDirection.BIDIRECTIONAL,
                center_price=1.1000,
                levels_above=1,
                levels_below=1,
                base_volume=0.01
            )
            
            self.assertIsNotNone(grid_id)
            self.assertEqual(len(self.strategy.active_grids), 1)
            
            # Stop the grid
            success = await self.strategy.stop_grid(grid_id, close_positions=True)
            
            self.assertTrue(success)
            self.assertEqual(len(self.strategy.active_grids), 0)
            
        asyncio.run(run_test())
        
    def test_stop_nonexistent_grid(self):
        """Test stopping a non-existent grid"""
        async def run_test():
            success = await self.strategy.stop_grid("nonexistent_grid")
            self.assertFalse(success)
            
        asyncio.run(run_test())

class TestStatisticsAndReporting(TestGridStrategy):
    """Test statistics and reporting functionality"""
    
    def test_get_active_grids_empty(self):
        """Test getting active grids when none exist"""
        active_grids = self.strategy.get_active_grids()
        self.assertEqual(len(active_grids), 0)
        
    def test_get_active_grids_with_data(self):
        """Test getting active grids with data"""
        async def run_test():
            # Create a grid
            self.mock_mt5.set_mock_tick('EURUSD', 1.0995, 1.1005)
            
            grid_id = await self.strategy.create_grid(
                symbol='EURUSD',
                direction=GridDirection.BIDIRECTIONAL,
                center_price=1.1000,
                levels_above=1,
                levels_below=1,
                base_volume=0.01
            )
            
            active_grids = self.strategy.get_active_grids()
            
            self.assertEqual(len(active_grids), 1)
            self.assertIn(grid_id, active_grids)
            
            grid_info = active_grids[grid_id]
            self.assertEqual(grid_info['symbol'], 'EURUSD')
            self.assertEqual(grid_info['status'], 'active')
            
        asyncio.run(run_test())
        
    def test_get_grid_details(self):
        """Test getting detailed grid information"""
        async def run_test():
            # Create a grid
            self.mock_mt5.set_mock_tick('EURUSD', 1.0995, 1.1005)
            
            grid_id = await self.strategy.create_grid(
                symbol='EURUSD',
                direction=GridDirection.BIDIRECTIONAL,
                center_price=1.1000,
                levels_above=1,
                levels_below=1,
                base_volume=0.01
            )
            
            details = self.strategy.get_grid_details(grid_id)
            
            self.assertIsNotNone(details)
            self.assertIn('grid_info', details)
            self.assertIn('levels', details)
            self.assertIn('config', details)
            
            # Check levels
            levels = details['levels']
            self.assertEqual(len(levels), 2)  # 1 above + 1 below
            
            # Check config
            config = details['config']
            self.assertEqual(config['symbol'], 'EURUSD')
            self.assertEqual(config['center_price'], 1.1000)
            
        asyncio.run(run_test())
        
    def test_get_statistics(self):
        """Test getting strategy statistics"""
        # Initially empty
        stats = self.strategy.get_statistics()
        self.assertEqual(stats['active_grids'], 0)
        self.assertEqual(stats['total_active_orders'], 0)
        
        async def run_test():
            # Create a grid
            self.mock_mt5.set_mock_tick('EURUSD', 1.0995, 1.1005)
            
            await self.strategy.create_grid(
                symbol='EURUSD',
                direction=GridDirection.BIDIRECTIONAL,
                center_price=1.1000,
                levels_above=1,
                levels_below=1,
                base_volume=0.01
            )
            
            # Check updated stats
            stats = self.strategy.get_statistics()
            self.assertEqual(stats['active_grids'], 1)
            self.assertGreater(stats['total_active_orders'], 0)
            
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()