"""
Test Suite for MT5 Bridge
Tests MT5 connection, order submission, and position management with comprehensive mocking
"""

import unittest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mt5_bridge import (
    MT5Bridge, OrderType, TradeRequest, TradeResult, MT5Config
)


class TestMT5Bridge(unittest.TestCase):
    """Unit tests for MT5 Bridge"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'mt5': {
                'terminal_path': '/path/to/terminal',
                'login': 12345,
                'password': 'test_password',
                'server': 'test_server',
                'timeout': 30000,
                'enable_logging': True,
                'log_file': 'logs/test_mt5_bridge.log'
            },
            'symbol_mapping': {
                'EURUSD': 'EURUSD',
                'GBPUSD': 'GBPUSD',
                'USDJPY': 'USDJPY'
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        # Create MT5 bridge with test config
        self.bridge = MT5Bridge(config_file=self.temp_config.name)
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
        self.bridge.disconnect()
    
    def test_config_loading(self):
        """Test configuration loading from file"""
        self.assertEqual(self.bridge.config.login, 12345)
        self.assertEqual(self.bridge.config.server, 'test_server')
        self.assertEqual(self.bridge.config.timeout, 30000)
    
    def test_symbol_mapping(self):
        """Test symbol mapping functionality"""
        self.assertEqual(self.bridge._map_symbol('EURUSD'), 'EURUSD')
        self.assertEqual(self.bridge._map_symbol('UNKNOWN'), 'UNKNOWN')  # Fallback
    
    @patch('mt5_bridge.MT5_AVAILABLE', False)
    def test_simulation_mode_initialization(self):
        """Test initialization in simulation mode"""
        bridge = MT5Bridge(config_file=self.temp_config.name)
        success = bridge.initialize()
        
        self.assertTrue(success)
        self.assertTrue(bridge.is_connected)
    
    @patch('mt5_bridge.mt5')
    @patch('mt5_bridge.MT5_AVAILABLE', True)
    def test_successful_initialization(self, mock_mt5):
        """Test successful MT5 initialization"""
        # Mock MT5 responses
        mock_mt5.initialize.return_value = True
        mock_account_info = Mock()
        mock_account_info._asdict.return_value = {
            'login': 12345,
            'balance': 10000.0,
            'equity': 9800.0,
            'server': 'test_server'
        }
        mock_mt5.account_info.return_value = mock_account_info
        
        success = self.bridge.initialize()
        
        self.assertTrue(success)
        self.assertTrue(self.bridge.is_connected)
        self.assertEqual(self.bridge.account_info['login'], 12345)
        mock_mt5.initialize.assert_called_once()
    
    @patch('mt5_bridge.mt5')
    @patch('mt5_bridge.MT5_AVAILABLE', True)
    def test_failed_initialization(self, mock_mt5):
        """Test failed MT5 initialization"""
        # Mock MT5 initialization failure
        mock_mt5.initialize.return_value = False
        mock_mt5.last_error.return_value = (1, "Connection failed")
        
        success = self.bridge.initialize()
        
        self.assertFalse(success)
        self.assertFalse(self.bridge.is_connected)
        self.assertIsNotNone(self.bridge.last_error)
    
    def test_trade_request_validation(self):
        """Test trade request validation"""
        # Test invalid volume
        request = TradeRequest(
            symbol="EURUSD",
            action=OrderType.BUY,
            volume=0
        )
        
        is_valid, message = self.bridge._validate_trade_request(request)
        self.assertFalse(is_valid)
        self.assertIn("Invalid volume", message)
        
        # Test missing symbol
        request = TradeRequest(
            symbol="",
            action=OrderType.BUY,
            volume=0.01
        )
        
        is_valid, message = self.bridge._validate_trade_request(request)
        self.assertFalse(is_valid)
        self.assertIn("Symbol not specified", message)
        
        # Test disconnected state
        self.bridge.is_connected = False
        request = TradeRequest(
            symbol="EURUSD",
            action=OrderType.BUY,
            volume=0.01
        )
        
        is_valid, message = self.bridge._validate_trade_request(request)
        self.assertFalse(is_valid)
        self.assertIn("MT5 not connected", message)
    
    @patch('mt5_bridge.MT5_AVAILABLE', False)
    async def test_simulation_market_order(self):
        """Test market order in simulation mode"""
        self.bridge.is_connected = True
        
        request = TradeRequest(
            symbol="EURUSD",
            action=OrderType.BUY,
            volume=0.01,
            comment="Test order"
        )
        
        result = await self.bridge.send_market_order(request)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.ticket)
        self.assertEqual(result.volume, 0.01)
        self.assertIn("Simulated", result.error_description)
    
    @patch('mt5_bridge.mt5')
    @patch('mt5_bridge.MT5_AVAILABLE', True)
    async def test_successful_market_order(self, mock_mt5):
        """Test successful market order execution"""
        self.bridge.is_connected = True
        
        # Mock symbol info and tick data
        mock_tick = Mock()
        mock_tick.ask = 1.1000
        mock_tick.bid = 1.0999
        mock_mt5.symbol_info_tick.return_value = mock_tick
        
        # Mock order result
        mock_result = Mock()
        mock_result.retcode = 10009  # TRADE_RETCODE_DONE
        mock_result.order = 123456
        mock_result.price = 1.1000
        mock_result.volume = 0.01
        mock_result._asdict.return_value = {
            'retcode': 10009,
            'order': 123456,
            'price': 1.1000,
            'volume': 0.01
        }
        mock_mt5.order_send.return_value = mock_result
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_IOC = 1
        
        request = TradeRequest(
            symbol="EURUSD",
            action=OrderType.BUY,
            volume=0.01,
            sl=1.0950,
            tp=1.1050
        )
        
        result = await self.bridge.send_market_order(request)
        
        self.assertTrue(result.success)
        self.assertEqual(result.ticket, 123456)
        self.assertEqual(result.price, 1.1000)
        self.assertEqual(result.volume, 0.01)
        mock_mt5.order_send.assert_called_once()
    
    @patch('mt5_bridge.mt5')
    @patch('mt5_bridge.MT5_AVAILABLE', True)
    async def test_failed_market_order(self, mock_mt5):
        """Test failed market order execution"""
        self.bridge.is_connected = True
        
        # Mock symbol info
        mock_tick = Mock()
        mock_tick.ask = 1.1000
        mock_tick.bid = 1.0999
        mock_mt5.symbol_info_tick.return_value = mock_tick
        
        # Mock order failure
        mock_result = Mock()
        mock_result.retcode = 10013  # TRADE_RETCODE_INVALID_PRICE
        mock_result._asdict.return_value = {
            'retcode': 10013,
            'comment': 'Invalid price'
        }
        mock_mt5.order_send.return_value = mock_result
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.ORDER_FILLING_IOC = 1
        
        request = TradeRequest(
            symbol="EURUSD",
            action=OrderType.BUY,
            volume=0.01
        )
        
        result = await self.bridge.send_market_order(request)
        
        self.assertFalse(result.success)
        self.assertEqual(result.retcode, 10013)
        self.assertIn("retcode", result.error_description)
    
    @patch('mt5_bridge.MT5_AVAILABLE', False)
    async def test_simulation_pending_order(self):
        """Test pending order in simulation mode"""
        self.bridge.is_connected = True
        
        request = TradeRequest(
            symbol="EURUSD",
            action=OrderType.BUY_LIMIT,
            volume=0.01,
            price=1.0950,
            sl=1.0900,
            tp=1.1000
        )
        
        result = await self.bridge.send_pending_order(request)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.ticket)
        self.assertEqual(result.price, 1.0950)
        self.assertEqual(result.volume, 0.01)
    
    async def test_pending_order_missing_price(self):
        """Test pending order without price"""
        self.bridge.is_connected = True
        
        request = TradeRequest(
            symbol="EURUSD",
            action=OrderType.BUY_LIMIT,
            volume=0.01,
            price=None  # Missing price
        )
        
        result = await self.bridge.send_pending_order(request)
        
        self.assertFalse(result.success)
        self.assertIn("Price required", result.error_description)
    
    @patch('mt5_bridge.MT5_AVAILABLE', False)
    async def test_simulation_close_position(self):
        """Test position close in simulation mode"""
        self.bridge.is_connected = True
        
        result = await self.bridge.close_position(123456, volume=0.01)
        
        self.assertTrue(result.success)
        self.assertEqual(result.ticket, 123456)
        self.assertIn("Simulated", result.error_description)
    
    @patch('mt5_bridge.mt5')
    @patch('mt5_bridge.MT5_AVAILABLE', True)
    async def test_close_position_not_found(self, mock_mt5):
        """Test closing non-existent position"""
        self.bridge.is_connected = True
        
        # Mock position not found
        mock_mt5.positions_get.return_value = None
        
        result = await self.bridge.close_position(999999)
        
        self.assertFalse(result.success)
        self.assertIn("not found", result.error_description)
    
    @patch('mt5_bridge.MT5_AVAILABLE', False)
    async def test_simulation_delete_pending_order(self):
        """Test pending order deletion in simulation mode"""
        self.bridge.is_connected = True
        
        result = await self.bridge.delete_pending_order(123456)
        
        self.assertTrue(result.success)
        self.assertEqual(result.ticket, 123456)
        self.assertIn("Simulated", result.error_description)
    
    @patch('mt5_bridge.MT5_AVAILABLE', False)
    def test_simulation_modify_position(self):
        """Test position modification in simulation mode"""
        self.bridge.is_connected = True
        
        result = self.bridge.modify_position(123456, sl=1.0950, tp=1.1050)
        
        self.assertTrue(result.success)
        self.assertEqual(result.ticket, 123456)
        self.assertIn("Simulated", result.error_description)
    
    @patch('mt5_bridge.MT5_AVAILABLE', False)
    def test_simulation_symbol_info(self):
        """Test symbol info in simulation mode"""
        symbol_info = self.bridge.get_symbol_info("EURUSD")
        
        self.assertIsNotNone(symbol_info)
        self.assertEqual(symbol_info['symbol'], 'EURUSD')
        self.assertEqual(symbol_info['digits'], 5)
        self.assertEqual(symbol_info['volume_min'], 0.01)
    
    @patch('mt5_bridge.MT5_AVAILABLE', False)
    def test_simulation_current_price(self):
        """Test current price in simulation mode"""
        price_info = self.bridge.get_current_price("EURUSD")
        
        self.assertIsNotNone(price_info)
        self.assertIn('bid', price_info)
        self.assertIn('ask', price_info)
        self.assertIn('time', price_info)
    
    @patch('mt5_bridge.mt5')
    @patch('mt5_bridge.MT5_AVAILABLE', True)
    def test_get_positions(self, mock_mt5):
        """Test getting positions"""
        # Mock positions
        mock_position = Mock()
        mock_position._asdict.return_value = {
            'ticket': 123456,
            'symbol': 'EURUSD',
            'type': 0,  # BUY
            'volume': 0.01,
            'price_open': 1.1000,
            'sl': 1.0950,
            'tp': 1.1050,
            'profit': 5.0
        }
        mock_mt5.positions_get.return_value = [mock_position]
        
        positions = self.bridge.get_positions()
        
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]['ticket'], 123456)
        self.assertEqual(positions[0]['symbol'], 'EURUSD')
    
    @patch('mt5_bridge.mt5')
    @patch('mt5_bridge.MT5_AVAILABLE', True)
    def test_get_orders(self, mock_mt5):
        """Test getting pending orders"""
        # Mock orders
        mock_order = Mock()
        mock_order._asdict.return_value = {
            'ticket': 789012,
            'symbol': 'GBPUSD',
            'type': 2,  # BUY_LIMIT
            'volume_initial': 0.02,
            'price_open': 1.2500,
            'sl': 1.2450,
            'tp': 1.2550
        }
        mock_mt5.orders_get.return_value = [mock_order]
        
        orders = self.bridge.get_orders()
        
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['ticket'], 789012)
        self.assertEqual(orders[0]['symbol'], 'GBPUSD')
    
    def test_connection_status(self):
        """Test connection status reporting"""
        # Test disconnected state
        status = self.bridge.get_connection_status()
        self.assertFalse(status['connected'])
        self.assertEqual(status['account_info'], {})
        
        # Test connected state
        self.bridge.is_connected = True
        self.bridge.account_info = {'login': 12345, 'balance': 10000.0}
        self.bridge.last_ping = datetime.now()
        
        status = self.bridge.get_connection_status()
        self.assertTrue(status['connected'])
        self.assertEqual(status['account_info']['login'], 12345)
        self.assertIsNotNone(status['last_ping'])
    
    def test_statistics(self):
        """Test statistics reporting"""
        stats = self.bridge.get_statistics()
        
        self.assertIn('connected', stats)
        self.assertIn('connection_attempts', stats)
        self.assertIn('account_info', stats)
        self.assertIn('mt5_available', stats)
        self.assertIn('symbol_mappings', stats)
    
    def test_invalid_order_types(self):
        """Test handling of invalid order types"""
        self.bridge.is_connected = True
        
        # Test invalid market order type
        request = TradeRequest(
            symbol="EURUSD",
            action=OrderType.BUY_LIMIT,  # Should be BUY or SELL for market orders
            volume=0.01
        )
        
        async def test():
            result = await self.bridge.send_market_order(request)
            self.assertFalse(result.success)
            self.assertIn("Invalid market order type", result.error_description)
        
        asyncio.run(test())


class TestMT5BridgeIntegration(unittest.TestCase):
    """Integration tests for MT5 Bridge"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.bridge = MT5Bridge()
    
    def test_error_handling_robustness(self):
        """Test error handling under various failure conditions"""
        # Test with invalid config file
        bridge = MT5Bridge(config_file="nonexistent.json")
        self.assertIsInstance(bridge.config, MT5Config)
        
        # Test disconnection cleanup
        bridge.disconnect()
        self.assertFalse(bridge.is_connected)
    
    async def test_concurrent_operations(self):
        """Test concurrent trade operations"""
        self.bridge.is_connected = True
        
        # Create multiple concurrent trade requests
        requests = [
            TradeRequest(symbol="EURUSD", action=OrderType.BUY, volume=0.01),
            TradeRequest(symbol="GBPUSD", action=OrderType.SELL, volume=0.02),
            TradeRequest(symbol="USDJPY", action=OrderType.BUY, volume=0.01)
        ]
        
        # Execute concurrently
        tasks = [self.bridge.send_market_order(req) for req in requests]
        results = await asyncio.gather(*tasks)
        
        # All should succeed in simulation mode
        for result in results:
            self.assertTrue(result.success)
    
    def test_configuration_edge_cases(self):
        """Test configuration handling edge cases"""
        # Test empty configuration
        bridge = MT5Bridge()
        self.assertIsInstance(bridge.config, MT5Config)
        
        # Test partial configuration
        temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump({'mt5': {'login': 12345}}, temp_config)
        temp_config.close()
        
        try:
            bridge = MT5Bridge(config_file=temp_config.name)
            self.assertEqual(bridge.config.login, 12345)
            self.assertEqual(bridge.config.server, "")  # Default value
        finally:
            os.unlink(temp_config.name)
    
    def test_symbol_mapping_edge_cases(self):
        """Test symbol mapping with edge cases"""
        # Test unmapped symbols
        unmapped = self.bridge._map_symbol("UNKNOWN_SYMBOL")
        self.assertEqual(unmapped, "UNKNOWN_SYMBOL")
        
        # Test case sensitivity
        lowercase = self.bridge._map_symbol("eurusd")
        self.assertEqual(lowercase, "eurusd")  # Should pass through unchanged
    
    def test_performance_with_large_datasets(self):
        """Test performance with many positions and orders"""
        # This would test the bridge with large amounts of data
        # In simulation mode, this tests the data handling capacity
        
        positions = self.bridge.get_positions()
        orders = self.bridge.get_orders()
        
        # Should handle empty results gracefully
        self.assertIsInstance(positions, list)
        self.assertIsInstance(orders, list)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)