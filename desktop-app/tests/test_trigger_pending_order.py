"""
Test Suite for Trigger Pending Order Engine
Tests pending order monitoring, triggering, and market condition handling
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

from trigger_pending_order import (
    TriggerPendingOrder, OrderType, OrderStatus, TriggerMode, PendingOrder, TriggerEvent
)

class MockMT5Bridge:
    """Mock MT5 bridge for testing"""
    
    def __init__(self):
        self.mock_ticks = {}
        self.trade_results = {}
        self.connection_status = True
        
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
        if not self.connection_status:
            return None
        return self.mock_ticks.get(symbol, None)
        
    async def execute_trade(self, trade_request: dict):
        """Mock trade execution"""
        symbol = trade_request.get('symbol')
        if symbol in self.trade_results:
            return self.trade_results[symbol]
        
        # Default successful execution
        return {
            'success': True,
            'ticket': 123456,
            'price': trade_request.get('price', 1.0),
            'volume': trade_request.get('volume', 0.1)
        }
        
    def set_trade_result(self, symbol: str, result: dict):
        """Set mock trade execution result"""
        self.trade_results[symbol] = result

class MockSpreadChecker:
    """Mock spread checker for testing"""
    
    def __init__(self):
        self.blocked_symbols = set()
        
    def check_spread_before_trade(self, symbol: str):
        """Mock spread check"""
        if symbol in self.blocked_symbols:
            return type('SpreadResult', (), {'value': 'blocked_high_spread'})(), None
        return type('SpreadResult', (), {'value': 'allowed'})(), None
        
    def block_symbol(self, symbol: str):
        """Block symbol for testing"""
        self.blocked_symbols.add(symbol)

class MockTicketTracker:
    """Mock ticket tracker for testing"""
    
    def __init__(self):
        self.registered_tickets = {}
        
    def register_trade_ticket(self, ticket, symbol, direction, entry_price, lot_size, 
                            stop_loss, take_profit, provider_id, provider_name, signal_content):
        """Mock ticket registration"""
        self.registered_tickets[ticket] = {
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry_price,
            'provider_id': provider_id
        }
        return True

class TestTriggerPendingOrder(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "trigger_pending_order": {
                "enabled": True,
                "default_mode": "auto",
                "price_check_interval": 0.1,  # Fast for testing
                "max_slippage_pips": 3.0,
                "max_trigger_attempts": 3,
                "order_expiry_hours": 1,  # Short for testing
                "cleanup_expired_hours": 24,
                "enable_notifications": True,
                "symbol_specific_settings": {
                    "EURUSD": {
                        "max_slippage_pips": 2.0,
                        "price_check_interval": 0.05
                    }
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize trigger pending order
        self.trigger_engine = TriggerPendingOrder(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
        # Setup mocks
        self.setup_mocks()
        
    def tearDown(self):
        """Clean up test environment"""
        self.trigger_engine.stop_monitoring()
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
        # Clean up orders file if created
        orders_file = self.temp_log.name.replace('.log', '_orders.json')
        if os.path.exists(orders_file):
            os.unlink(orders_file)
        
    def setup_mocks(self):
        """Setup mock dependencies"""
        self.mock_mt5 = MockMT5Bridge()
        self.mock_spread_checker = MockSpreadChecker()
        self.mock_ticket_tracker = MockTicketTracker()
        
        self.trigger_engine.set_dependencies(
            mt5_bridge=self.mock_mt5,
            spread_checker=self.mock_spread_checker,
            ticket_tracker=self.mock_ticket_tracker
        )

class TestBasicFunctionality(TestTriggerPendingOrder):
    """Test basic pending order functionality"""
    
    def test_initialization(self):
        """Test trigger pending order initialization"""
        self.assertTrue(self.trigger_engine.config['enabled'])
        self.assertEqual(self.trigger_engine.config['max_slippage_pips'], 3.0)
        self.assertEqual(self.trigger_engine.config['order_expiry_hours'], 1)
        
    def test_pip_value_calculation(self):
        """Test pip value calculation for different symbols"""
        self.assertEqual(self.trigger_engine._get_pip_value('EURUSD'), 0.00001)
        self.assertEqual(self.trigger_engine._get_pip_value('USDJPY'), 0.001)
        self.assertEqual(self.trigger_engine._get_pip_value('XAUUSD'), 0.01)
        
    def test_add_pending_order(self):
        """Test adding a pending order"""
        order_id = self.trigger_engine.add_pending_order(
            signal_id='test_signal_001',
            symbol='EURUSD',
            order_type=OrderType.BUY_LIMIT,
            trigger_price=1.0950,
            volume=0.1,
            stop_loss=1.0900,
            take_profit=1.1000,
            provider_id='test_provider'
        )
        
        self.assertNotEqual(order_id, "")
        self.assertIn(order_id, self.trigger_engine.pending_orders)
        
        order = self.trigger_engine.pending_orders[order_id]
        self.assertEqual(order.symbol, 'EURUSD')
        self.assertEqual(order.order_type, OrderType.BUY_LIMIT)
        self.assertEqual(order.trigger_price, 1.0950)
        self.assertEqual(order.status, OrderStatus.PENDING)

class TestOrderTriggering(TestTriggerPendingOrder):
    """Test order triggering logic"""
    
    def test_buy_limit_trigger_condition(self):
        """Test BUY LIMIT trigger conditions"""
        # Create BUY LIMIT order
        order = PendingOrder(
            order_id='test_001',
            signal_id='signal_001',
            symbol='EURUSD',
            order_type=OrderType.BUY_LIMIT,
            trigger_price=1.0950,
            volume=0.1,
            stop_loss=1.0900,
            take_profit=1.1000,
            slippage_pips=2.0,
            expiry_time=datetime.now() + timedelta(hours=1),
            status=OrderStatus.PENDING,
            created_time=datetime.now()
        )
        
        # Price above trigger - should not trigger
        price_data = {'bid': 1.0955, 'ask': 1.0958}
        should_trigger, reason = self.trigger_engine._should_trigger_order(order, price_data)
        self.assertFalse(should_trigger)
        
        # Price at trigger level - should trigger
        price_data = {'bid': 1.0948, 'ask': 1.0950}
        should_trigger, reason = self.trigger_engine._should_trigger_order(order, price_data)
        self.assertTrue(should_trigger)
        self.assertIn("BUY LIMIT triggered", reason)
        
        # Price below trigger - should trigger
        price_data = {'bid': 1.0945, 'ask': 1.0948}
        should_trigger, reason = self.trigger_engine._should_trigger_order(order, price_data)
        self.assertTrue(should_trigger)
        
    def test_sell_stop_trigger_condition(self):
        """Test SELL STOP trigger conditions"""
        # Create SELL STOP order
        order = PendingOrder(
            order_id='test_002',
            signal_id='signal_002',
            symbol='EURUSD',
            order_type=OrderType.SELL_STOP,
            trigger_price=1.0950,
            volume=0.1,
            stop_loss=1.1000,
            take_profit=1.0900,
            slippage_pips=2.0,
            expiry_time=datetime.now() + timedelta(hours=1),
            status=OrderStatus.PENDING,
            created_time=datetime.now()
        )
        
        # Price above trigger - should not trigger
        price_data = {'bid': 1.0955, 'ask': 1.0958}
        should_trigger, reason = self.trigger_engine._should_trigger_order(order, price_data)
        self.assertFalse(should_trigger)
        
        # Price at trigger level - should trigger
        price_data = {'bid': 1.0950, 'ask': 1.0952}
        should_trigger, reason = self.trigger_engine._should_trigger_order(order, price_data)
        self.assertTrue(should_trigger)
        self.assertIn("SELL STOP triggered", reason)
        
    def test_order_expiry(self):
        """Test order expiry handling"""
        # Create expired order
        order = PendingOrder(
            order_id='test_003',
            signal_id='signal_003',
            symbol='EURUSD',
            order_type=OrderType.BUY_LIMIT,
            trigger_price=1.0950,
            volume=0.1,
            stop_loss=1.0900,
            take_profit=1.1000,
            slippage_pips=2.0,
            expiry_time=datetime.now() - timedelta(minutes=1),  # Expired
            status=OrderStatus.PENDING,
            created_time=datetime.now() - timedelta(hours=2)
        )
        
        # Even with favorable price, expired order should not trigger
        price_data = {'bid': 1.0945, 'ask': 1.0948}
        should_trigger, reason = self.trigger_engine._should_trigger_order(order, price_data)
        self.assertFalse(should_trigger)
        self.assertIn("expired", reason.lower())

class TestOrderExecution(TestTriggerPendingOrder):
    """Test order execution"""
    
    def test_successful_order_execution(self):
        """Test successful pending order execution"""
        async def run_test():
            # Setup successful trade result
            self.mock_mt5.set_trade_result('EURUSD', {
                'success': True,
                'ticket': 123456,
                'price': 1.0950
            })
            
            # Create pending order
            order = PendingOrder(
                order_id='test_004',
                signal_id='signal_004',
                symbol='EURUSD',
                order_type=OrderType.BUY_LIMIT,
                trigger_price=1.0950,
                volume=0.1,
                stop_loss=1.0900,
                take_profit=1.1000,
                slippage_pips=2.0,
                expiry_time=datetime.now() + timedelta(hours=1),
                status=OrderStatus.PENDING,
                created_time=datetime.now()
            )
            
            # Execute order
            success = await self.trigger_engine._execute_pending_order(order, 1.0950, "Test execution")
            
            self.assertTrue(success)
            self.assertEqual(order.status, OrderStatus.TRIGGERED)
            self.assertEqual(order.mt5_ticket, 123456)
            self.assertIsNotNone(order.triggered_time)
            
            # Check ticket tracker registration
            self.assertIn(123456, self.mock_ticket_tracker.registered_tickets)
            
        asyncio.run(run_test())
        
    def test_failed_order_execution(self):
        """Test failed pending order execution"""
        async def run_test():
            # Setup failed trade result
            self.mock_mt5.set_trade_result('EURUSD', {
                'success': False,
                'error': 'Insufficient margin'
            })
            
            # Create pending order
            order = PendingOrder(
                order_id='test_005',
                signal_id='signal_005',
                symbol='EURUSD',
                order_type=OrderType.BUY_LIMIT,
                trigger_price=1.0950,
                volume=0.1,
                stop_loss=1.0900,
                take_profit=1.1000,
                slippage_pips=2.0,
                expiry_time=datetime.now() + timedelta(hours=1),
                status=OrderStatus.PENDING,
                created_time=datetime.now()
            )
            
            # Execute order
            success = await self.trigger_engine._execute_pending_order(order, 1.0950, "Test execution")
            
            self.assertFalse(success)
            self.assertEqual(order.status, OrderStatus.PENDING)  # Still pending after failure
            self.assertEqual(order.attempts, 1)
            self.assertIsNotNone(order.last_error)
            
        asyncio.run(run_test())

class TestOrderManagement(TestTriggerPendingOrder):
    """Test order management operations"""
    
    def test_cancel_pending_order(self):
        """Test cancelling a pending order"""
        # Add order
        order_id = self.trigger_engine.add_pending_order(
            signal_id='test_signal_006',
            symbol='EURUSD',
            order_type=OrderType.BUY_LIMIT,
            trigger_price=1.0950,
            volume=0.1
        )
        
        # Verify order is pending
        self.assertIn(order_id, self.trigger_engine.pending_orders)
        
        # Cancel order
        success = self.trigger_engine.cancel_pending_order(order_id, "Test cancellation")
        
        self.assertTrue(success)
        self.assertNotIn(order_id, self.trigger_engine.pending_orders)
        
    def test_manual_trigger_order(self):
        """Test manually triggering an order"""
        # Set mock price
        self.mock_mt5.set_mock_tick('EURUSD', 1.0948, 1.0950)
        
        # Add order
        order_id = self.trigger_engine.add_pending_order(
            signal_id='test_signal_007',
            symbol='EURUSD',
            order_type=OrderType.BUY_LIMIT,
            trigger_price=1.0950,
            volume=0.1
        )
        
        # Manual trigger
        success = self.trigger_engine.manual_trigger_order(order_id, "Manual test trigger")
        
        self.assertTrue(success)
        self.assertNotIn(order_id, self.trigger_engine.pending_orders)
        
    def test_get_pending_orders_filtered(self):
        """Test getting pending orders with filters"""
        # Add multiple orders
        order_id1 = self.trigger_engine.add_pending_order(
            signal_id='test_signal_008',
            symbol='EURUSD',
            order_type=OrderType.BUY_LIMIT,
            trigger_price=1.0950,
            volume=0.1
        )
        
        order_id2 = self.trigger_engine.add_pending_order(
            signal_id='test_signal_009',
            symbol='GBPUSD',
            order_type=OrderType.SELL_STOP,
            trigger_price=1.2500,
            volume=0.2
        )
        
        # Test filtering by symbol
        eurusd_orders = self.trigger_engine.get_pending_orders(symbol='EURUSD')
        self.assertEqual(len(eurusd_orders), 1)
        self.assertEqual(eurusd_orders[0].symbol, 'EURUSD')
        
        # Test filtering by status
        pending_orders = self.trigger_engine.get_pending_orders(status=OrderStatus.PENDING)
        self.assertEqual(len(pending_orders), 2)

class TestSpreadIntegration(TestTriggerPendingOrder):
    """Test integration with spread checker"""
    
    def test_spread_blocking_trigger(self):
        """Test trigger blocking due to high spread"""
        async def run_test():
            # Block EURUSD in spread checker
            self.mock_spread_checker.block_symbol('EURUSD')
            
            # Set price data
            self.mock_mt5.set_mock_tick('EURUSD', 1.0948, 1.0950)
            
            # Add pending order
            order_id = self.trigger_engine.add_pending_order(
                signal_id='test_signal_010',
                symbol='EURUSD',
                order_type=OrderType.BUY_LIMIT,
                trigger_price=1.0950,
                volume=0.1
            )
            
            # Simulate monitoring cycle
            order = self.trigger_engine.pending_orders[order_id]
            price_data = self.trigger_engine._get_current_price('EURUSD')
            
            should_trigger, reason = self.trigger_engine._should_trigger_order(order, price_data)
            self.assertTrue(should_trigger)  # Order should want to trigger
            
            # But spread check should block execution
            spread_result, _ = self.mock_spread_checker.check_spread_before_trade('EURUSD')
            self.assertEqual(spread_result.value, 'blocked_high_spread')
            
        asyncio.run(run_test())

class TestStatistics(TestTriggerPendingOrder):
    """Test statistics and monitoring"""
    
    def test_statistics_calculation(self):
        """Test statistics calculation"""
        # Initially empty
        stats = self.trigger_engine.get_statistics()
        self.assertEqual(stats['total_pending_orders'], 0)
        self.assertEqual(stats['total_triggered'], 0)
        
        # Add some orders
        self.trigger_engine.add_pending_order(
            signal_id='test_signal_011',
            symbol='EURUSD',
            order_type=OrderType.BUY_LIMIT,
            trigger_price=1.0950,
            volume=0.1
        )
        
        self.trigger_engine.add_pending_order(
            signal_id='test_signal_012',
            symbol='GBPUSD',
            order_type=OrderType.SELL_STOP,
            trigger_price=1.2500,
            volume=0.2
        )
        
        # Check updated stats
        stats = self.trigger_engine.get_statistics()
        self.assertEqual(stats['total_pending_orders'], 2)
        self.assertEqual(stats['active_pending'], 2)
        
        # Add some trigger events
        trigger_event = TriggerEvent(
            order_id='test_001',
            signal_id='signal_001',
            symbol='EURUSD',
            trigger_price=1.0950,
            market_price=1.0948,
            slippage_pips=2.0,
            execution_time=datetime.now(),
            success=True,
            mt5_ticket=123456
        )
        self.trigger_engine.trigger_history.append(trigger_event)
        
        stats = self.trigger_engine.get_statistics()
        self.assertEqual(stats['total_triggered'], 1)
        self.assertEqual(stats['successful_triggers'], 1)
        self.assertEqual(stats['trigger_success_rate'], 100.0)
        
    def test_order_persistence(self):
        """Test order persistence to file"""
        # Add order
        order_id = self.trigger_engine.add_pending_order(
            signal_id='test_signal_013',
            symbol='EURUSD',
            order_type=OrderType.BUY_LIMIT,
            trigger_price=1.0950,
            volume=0.1
        )
        
        # Check orders file was created
        orders_file = self.trigger_engine.log_path.replace('.log', '_orders.json')
        self.assertTrue(os.path.exists(orders_file))
        
        # Load orders in new instance
        new_trigger_engine = TriggerPendingOrder(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
        # Check order was loaded
        self.assertIn(order_id, new_trigger_engine.pending_orders)
        loaded_order = new_trigger_engine.pending_orders[order_id]
        self.assertEqual(loaded_order.symbol, 'EURUSD')
        self.assertEqual(loaded_order.trigger_price, 1.0950)

if __name__ == '__main__':
    unittest.main()