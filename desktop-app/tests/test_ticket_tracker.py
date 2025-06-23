"""
Test Suite for Ticket Tracker Engine
Comprehensive tests covering ticket registration, signal mapping, provider tracking, and edge cases
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

from ticket_tracker import (
    TicketTracker, TradeStatus, TradeDirection, SignalSource,
    TradeTicket, TicketUpdate, ProviderStats
)


class TestTicketTracker(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create temporary config and log files
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        # Test configuration
        test_config = {
            "ticket_tracker": {
                "enable_tracking": True,
                "auto_cleanup_days": 30,
                "max_history_entries": 10000,
                "provider_stats_update_interval": 300,
                "enable_telegram_notifications": True,
                "track_modifications": True,
                "backup_interval_hours": 24,
                "signal_hash_algorithm": "md5"
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize empty log file
        json.dump({"tracked_tickets": [], "ticket_updates": []}, self.temp_log)
        self.temp_log.close()
        
        # Create ticket tracker instance
        self.tracker = TicketTracker(
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
        
        self.mock_copilot_bot = Mock()
        self.mock_copilot_bot.send_trade_notification = AsyncMock()
        
        self.mock_strategy_runtime = Mock()
        
        # Inject mocks
        self.tracker.inject_modules(
            mt5_bridge=self.mock_mt5_bridge,
            copilot_bot=self.mock_copilot_bot,
            strategy_runtime=self.mock_strategy_runtime
        )


class TestTicketRegistration(TestTicketTracker):
    """Test ticket registration functionality"""
    
    def test_register_trade_ticket_basic(self):
        """Test basic trade ticket registration"""
        success = self.tracker.register_trade_ticket(
            ticket=123456,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            lot_size=0.1,
            stop_loss=1.0950,
            take_profit=1.1050,
            provider_id="goldsignals",
            provider_name="Gold Signals",
            channel_name="@GoldSignals",
            message_id=12345,
            signal_content="EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        )
        
        self.assertTrue(success)
        self.assertIn(123456, self.tracker.tracked_tickets)
        
        # Check ticket details
        ticket = self.tracker.tracked_tickets[123456]
        self.assertEqual(ticket.symbol, "EURUSD")
        self.assertEqual(ticket.direction, TradeDirection.BUY)
        self.assertEqual(ticket.entry_price, 1.1000)
        self.assertEqual(ticket.signal_source.provider_id, "goldsignals")
        self.assertEqual(ticket.signal_source.provider_name, "Gold Signals")
        self.assertEqual(ticket.status, TradeStatus.OPEN)
    
    def test_register_ticket_without_signal_content(self):
        """Test registering ticket without signal content"""
        success = self.tracker.register_trade_ticket(
            ticket=123457,
            symbol="GBPUSD",
            direction=TradeDirection.SELL,
            entry_price=1.2500,
            lot_size=0.2,
            stop_loss=1.2550,
            take_profit=1.2450,
            provider_id="forexsignals",
            provider_name="Forex Signals"
        )
        
        self.assertTrue(success)
        
        ticket = self.tracker.tracked_tickets[123457]
        self.assertIsNone(ticket.signal_source.signal_hash)
        self.assertIsNone(ticket.signal_source.message_id)
    
    def test_register_multiple_tickets_same_provider(self):
        """Test registering multiple tickets from same provider"""
        provider_id = "goldsignals"
        
        # Register first ticket
        self.tracker.register_trade_ticket(
            ticket=123456, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id=provider_id, provider_name="Gold Signals"
        )
        
        # Register second ticket
        self.tracker.register_trade_ticket(
            ticket=123457, symbol="GBPUSD", direction=TradeDirection.SELL,
            entry_price=1.2500, lot_size=0.2, stop_loss=1.2550, take_profit=1.2450,
            provider_id=provider_id, provider_name="Gold Signals"
        )
        
        # Check provider mapping
        provider_tickets = self.tracker.find_tickets_by_provider(provider_id)
        self.assertEqual(len(provider_tickets), 2)
        
        ticket_numbers = [t.ticket for t in provider_tickets]
        self.assertIn(123456, ticket_numbers)
        self.assertIn(123457, ticket_numbers)


class TestSignalMapping(TestTicketTracker):
    """Test signal hash mapping functionality"""
    
    def test_signal_hash_generation(self):
        """Test signal hash generation"""
        content1 = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        content2 = "GBPUSD SELL 1.2500 SL 1.2550 TP 1.2450"
        provider_id = "goldsignals"
        
        hash1 = self.tracker._generate_signal_hash(content1, provider_id)
        hash2 = self.tracker._generate_signal_hash(content2, provider_id)
        hash3 = self.tracker._generate_signal_hash(content1, provider_id)  # Same as hash1
        
        self.assertNotEqual(hash1, hash2)  # Different content should have different hashes
        self.assertEqual(hash1, hash3)     # Same content should have same hash
        self.assertIsInstance(hash1, str)
        self.assertTrue(len(hash1) > 0)
    
    def test_find_tickets_by_signal_hash(self):
        """Test finding tickets by signal hash"""
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        
        # Register first ticket
        self.tracker.register_trade_ticket(
            ticket=123456, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id="goldsignals", provider_name="Gold Signals",
            signal_content=signal_content
        )
        
        # Register second ticket with same signal
        self.tracker.register_trade_ticket(
            ticket=123457, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.05, stop_loss=1.0950, take_profit=1.1050,
            provider_id="goldsignals", provider_name="Gold Signals",
            signal_content=signal_content
        )
        
        # Get signal hash
        signal_hash = self.tracker._generate_signal_hash(signal_content, "goldsignals")
        
        # Find tickets by signal hash
        tickets = self.tracker.find_tickets_by_signal_hash(signal_hash)
        self.assertEqual(len(tickets), 2)
        
        ticket_numbers = [t.ticket for t in tickets]
        self.assertIn(123456, ticket_numbers)
        self.assertIn(123457, ticket_numbers)
    
    def test_different_providers_same_signal(self):
        """Test same signal content from different providers creates different hashes"""
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        
        # Register ticket from first provider
        self.tracker.register_trade_ticket(
            ticket=123456, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id="provider1", provider_name="Provider 1",
            signal_content=signal_content
        )
        
        # Register ticket from second provider with same signal content
        self.tracker.register_trade_ticket(
            ticket=123457, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id="provider2", provider_name="Provider 2",
            signal_content=signal_content
        )
        
        # Get hashes
        hash1 = self.tracker._generate_signal_hash(signal_content, "provider1")
        hash2 = self.tracker._generate_signal_hash(signal_content, "provider2")
        
        self.assertNotEqual(hash1, hash2)  # Should be different due to different providers
        
        # Each hash should only find one ticket
        tickets1 = self.tracker.find_tickets_by_signal_hash(hash1)
        tickets2 = self.tracker.find_tickets_by_signal_hash(hash2)
        
        self.assertEqual(len(tickets1), 1)
        self.assertEqual(len(tickets2), 1)
        self.assertEqual(tickets1[0].ticket, 123456)
        self.assertEqual(tickets2[0].ticket, 123457)


class TestTicketStatusUpdates(TestTicketTracker):
    """Test ticket status update functionality"""
    
    def test_update_ticket_to_closed(self):
        """Test updating ticket status to closed"""
        # Register ticket
        self.tracker.register_trade_ticket(
            ticket=123456, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id="goldsignals", provider_name="Gold Signals"
        )
        
        # Update to closed
        success = self.tracker.update_ticket_status(
            ticket=123456,
            status=TradeStatus.CLOSED,
            close_price=1.1025,
            profit=25.0,
            commission=-1.0,
            swap=0.5,
            reason="TP hit"
        )
        
        self.assertTrue(success)
        
        ticket = self.tracker.tracked_tickets[123456]
        self.assertEqual(ticket.status, TradeStatus.CLOSED)
        self.assertEqual(ticket.close_price, 1.1025)
        self.assertEqual(ticket.profit, 25.0)
        self.assertEqual(ticket.commission, -1.0)
        self.assertEqual(ticket.swap, 0.5)
        self.assertIsNotNone(ticket.close_time)
        
        # Check update was recorded
        updates = [u for u in self.tracker.ticket_updates if u.ticket == 123456]
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0].update_type, "status_change")
        self.assertEqual(updates[0].old_value, "open")
        self.assertEqual(updates[0].new_value, "closed")
    
    def test_update_nonexistent_ticket(self):
        """Test updating status of nonexistent ticket"""
        success = self.tracker.update_ticket_status(
            ticket=999999,
            status=TradeStatus.CLOSED,
            reason="Test"
        )
        
        self.assertFalse(success)
    
    def test_modify_ticket_stop_loss(self):
        """Test modifying ticket stop loss"""
        # Register ticket
        self.tracker.register_trade_ticket(
            ticket=123456, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id="goldsignals", provider_name="Gold Signals"
        )
        
        # Modify stop loss
        success = self.tracker.modify_ticket(
            ticket=123456,
            modification_type="stop_loss",
            old_value=1.0950,
            new_value=1.0970,
            reason="Move SL to breakeven"
        )
        
        self.assertTrue(success)
        
        ticket = self.tracker.tracked_tickets[123456]
        self.assertEqual(ticket.stop_loss, 1.0970)
        self.assertEqual(ticket.status, TradeStatus.MODIFIED)
        
        # Check modification was recorded
        modifications = [u for u in self.tracker.ticket_updates if u.ticket == 123456 and u.update_type == "stop_loss"]
        self.assertEqual(len(modifications), 1)
        self.assertEqual(modifications[0].old_value, 1.0950)
        self.assertEqual(modifications[0].new_value, 1.0970)


class TestTicketLookup(TestTicketTracker):
    """Test ticket lookup and search functionality"""
    
    def test_get_ticket_info(self):
        """Test getting ticket information"""
        # Register ticket
        self.tracker.register_trade_ticket(
            ticket=123456, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id="goldsignals", provider_name="Gold Signals",
            comment="Test trade"
        )
        
        # Get ticket info
        ticket_info = self.tracker.get_ticket_info(123456)
        
        self.assertIsNotNone(ticket_info)
        self.assertEqual(ticket_info.ticket, 123456)
        self.assertEqual(ticket_info.symbol, "EURUSD")
        self.assertEqual(ticket_info.comment, "Test trade")
        
        # Test nonexistent ticket
        nonexistent = self.tracker.get_ticket_info(999999)
        self.assertIsNone(nonexistent)
    
    def test_find_ticket_by_context(self):
        """Test finding ticket by trading context"""
        now = datetime.now()
        
        # Register recent ticket
        self.tracker.register_trade_ticket(
            ticket=123456, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id="goldsignals", provider_name="Gold Signals"
        )
        
        # Register old ticket (simulate)
        old_ticket = self.tracker.tracked_tickets[123456]
        old_ticket.open_time = now - timedelta(hours=2)  # 2 hours ago
        
        self.tracker.register_trade_ticket(
            ticket=123457, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1010, lot_size=0.1, stop_loss=1.0960, take_profit=1.1060,
            provider_id="goldsignals", provider_name="Gold Signals"
        )
        
        # Find by context (should return most recent)
        found_ticket = self.tracker.find_ticket_by_context(
            symbol="EURUSD",
            provider_id="goldsignals",
            direction=TradeDirection.BUY,
            recent_minutes=60
        )
        
        self.assertIsNotNone(found_ticket)
        self.assertEqual(found_ticket.ticket, 123457)  # Most recent
        
        # Test with different symbol (should find nothing)
        not_found = self.tracker.find_ticket_by_context(
            symbol="GBPUSD",
            provider_id="goldsignals",
            recent_minutes=60
        )
        
        self.assertIsNone(not_found)


class TestProviderManagement(TestTicketTracker):
    """Test provider tracking and statistics"""
    
    def test_find_tickets_by_provider(self):
        """Test finding all tickets from a specific provider"""
        provider_id = "goldsignals"
        
        # Register multiple tickets
        for i, symbol in enumerate(["EURUSD", "GBPUSD", "USDJPY"], 1):
            self.tracker.register_trade_ticket(
                ticket=123450 + i, symbol=symbol, direction=TradeDirection.BUY,
                entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
                provider_id=provider_id, provider_name="Gold Signals"
            )
        
        # Register ticket from different provider
        self.tracker.register_trade_ticket(
            ticket=123460, symbol="EURUSD", direction=TradeDirection.SELL,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.1050, take_profit=1.0950,
            provider_id="otherprovider", provider_name="Other Provider"
        )
        
        # Find tickets by provider
        provider_tickets = self.tracker.find_tickets_by_provider(provider_id)
        
        self.assertEqual(len(provider_tickets), 3)
        
        symbols = [t.symbol for t in provider_tickets]
        self.assertIn("EURUSD", symbols)
        self.assertIn("GBPUSD", symbols)
        self.assertIn("USDJPY", symbols)
        
        # All should be from same provider
        for ticket in provider_tickets:
            self.assertEqual(ticket.signal_source.provider_id, provider_id)
    
    def test_get_provider_summary(self):
        """Test getting provider summary statistics"""
        provider_id = "goldsignals"
        
        # Register and close some tickets
        # Winning trade
        self.tracker.register_trade_ticket(
            ticket=123456, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id=provider_id, provider_name="Gold Signals"
        )
        self.tracker.update_ticket_status(123456, TradeStatus.CLOSED, close_price=1.1025, profit=25.0)
        
        # Losing trade
        self.tracker.register_trade_ticket(
            ticket=123457, symbol="GBPUSD", direction=TradeDirection.SELL,
            entry_price=1.2500, lot_size=0.1, stop_loss=1.2550, take_profit=1.2450,
            provider_id=provider_id, provider_name="Gold Signals"
        )
        self.tracker.update_ticket_status(123457, TradeStatus.CLOSED, close_price=1.2540, profit=-40.0)
        
        # Open trade
        self.tracker.register_trade_ticket(
            ticket=123458, symbol="USDJPY", direction=TradeDirection.BUY,
            entry_price=110.00, lot_size=0.1, stop_loss=109.50, take_profit=110.50,
            provider_id=provider_id, provider_name="Gold Signals"
        )
        
        # Get provider summary
        summary = self.tracker.get_provider_summary(provider_id)
        
        self.assertEqual(summary['provider_id'], provider_id)
        self.assertEqual(summary['provider_name'], "Gold Signals")
        self.assertEqual(summary['total_trades'], 3)
        self.assertEqual(summary['open_trades'], 1)
        self.assertEqual(summary['closed_trades'], 2)
        self.assertEqual(summary['winning_trades'], 1)
        self.assertEqual(summary['total_profit'], -15.0)  # 25.0 - 40.0
        self.assertEqual(summary['win_rate'], 50.0)  # 1/2 * 100
        self.assertIn("USDJPY", summary['active_symbols'])
        self.assertEqual(len(summary['recent_trades']), 3)
    
    def test_empty_provider_summary(self):
        """Test getting summary for provider with no trades"""
        summary = self.tracker.get_provider_summary("nonexistent")
        
        self.assertEqual(summary['provider_id'], "nonexistent")
        self.assertEqual(summary['total_trades'], 0)
        self.assertEqual(summary['open_trades'], 0)
        self.assertEqual(summary['closed_trades'], 0)
        self.assertEqual(summary['active_symbols'], [])
        self.assertEqual(summary['recent_trades'], [])


class TestEdgeCases(TestTicketTracker):
    """Test edge cases and error scenarios"""
    
    def test_same_provider_similar_signals(self):
        """Test edge case: same provider, two signals with similar SL/TP"""
        provider_id = "goldsignals"
        
        # Register first signal
        self.tracker.register_trade_ticket(
            ticket=123456, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id=provider_id, provider_name="Gold Signals",
            signal_content="EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        )
        
        # Register very similar signal (different entry by 1 pip)
        self.tracker.register_trade_ticket(
            ticket=123457, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1001, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id=provider_id, provider_name="Gold Signals",
            signal_content="EURUSD BUY 1.1001 SL 1.0950 TP 1.1050"
        )
        
        # Should create different signal hashes
        hash1 = self.tracker.tracked_tickets[123456].signal_source.signal_hash
        hash2 = self.tracker.tracked_tickets[123457].signal_source.signal_hash
        
        self.assertNotEqual(hash1, hash2)
        
        # Each should be found by their respective hashes
        tickets1 = self.tracker.find_tickets_by_signal_hash(hash1)
        tickets2 = self.tracker.find_tickets_by_signal_hash(hash2)
        
        self.assertEqual(len(tickets1), 1)
        self.assertEqual(len(tickets2), 1)
        self.assertEqual(tickets1[0].ticket, 123456)
        self.assertEqual(tickets2[0].ticket, 123457)
    
    def test_invalid_configuration(self):
        """Test handling of invalid configuration"""
        # Test with missing config file
        invalid_tracker = TicketTracker(config_file="nonexistent.json")
        
        self.assertIsInstance(invalid_tracker.config, dict)
        self.assertIn('enable_tracking', invalid_tracker.config)
    
    def test_duplicate_ticket_registration(self):
        """Test registering same ticket number twice"""
        # Register first ticket
        success1 = self.tracker.register_trade_ticket(
            ticket=123456, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id="goldsignals", provider_name="Gold Signals"
        )
        
        # Try to register same ticket number again
        success2 = self.tracker.register_trade_ticket(
            ticket=123456, symbol="GBPUSD", direction=TradeDirection.SELL,
            entry_price=1.2500, lot_size=0.2, stop_loss=1.2550, take_profit=1.2450,
            provider_id="otherprovider", provider_name="Other Provider"
        )
        
        self.assertTrue(success1)
        self.assertTrue(success2)  # Should overwrite
        
        # Check that ticket was overwritten
        ticket = self.tracker.tracked_tickets[123456]
        self.assertEqual(ticket.symbol, "GBPUSD")  # Should be the second registration
        self.assertEqual(ticket.signal_source.provider_id, "otherprovider")
    
    async def test_cleanup_old_tickets(self):
        """Test cleanup of old closed tickets"""
        # Register and close old ticket
        self.tracker.register_trade_ticket(
            ticket=123456, symbol="EURUSD", direction=TradeDirection.BUY,
            entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
            provider_id="goldsignals", provider_name="Gold Signals"
        )
        
        # Manually set old close time
        ticket = self.tracker.tracked_tickets[123456]
        old_close_time = datetime.now() - timedelta(days=35)  # 35 days ago
        ticket.close_time = old_close_time
        ticket.status = TradeStatus.CLOSED
        
        # Register recent ticket
        self.tracker.register_trade_ticket(
            ticket=123457, symbol="GBPUSD", direction=TradeDirection.SELL,
            entry_price=1.2500, lot_size=0.1, stop_loss=1.2550, take_profit=1.2450,
            provider_id="goldsignals", provider_name="Gold Signals"
        )
        
        # Cleanup old tickets
        await self.tracker.cleanup_old_tickets()
        
        # Old ticket should be removed
        self.assertNotIn(123456, self.tracker.tracked_tickets)
        
        # Recent ticket should remain
        self.assertIn(123457, self.tracker.tracked_tickets)


class TestStatistics(TestTicketTracker):
    """Test statistics and reporting functionality"""
    
    def test_get_tracking_statistics(self):
        """Test getting overall tracking statistics"""
        # Register some tickets
        for i in range(3):
            self.tracker.register_trade_ticket(
                ticket=123456 + i, symbol="EURUSD", direction=TradeDirection.BUY,
                entry_price=1.1000, lot_size=0.1, stop_loss=1.0950, take_profit=1.1050,
                provider_id="goldsignals", provider_name="Gold Signals"
            )
        
        # Close one ticket
        self.tracker.update_ticket_status(123456, TradeStatus.CLOSED, profit=25.0)
        
        # Get statistics
        stats = self.tracker.get_tracking_statistics()
        
        self.assertEqual(stats['total_tracked_tickets'], 3)
        self.assertEqual(stats['open_tickets'], 2)
        self.assertEqual(stats['closed_tickets'], 1)
        self.assertEqual(stats['tracked_providers'], 1)
        self.assertTrue(stats['tracking_enabled'])
        self.assertIn('recent_updates_24h', stats)


def run_async_test(test_func):
    """Helper to run async test functions"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_func())
    finally:
        loop.close()


if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestTicketRegistration,
        TestSignalMapping,
        TestTicketStatusUpdates,
        TestTicketLookup,
        TestProviderManagement,
        TestEdgeCases,
        TestStatistics
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Run async tests separately
    print("\n=== Running Async Tests ===")
    
    async_tests = [
        TestEdgeCases().test_cleanup_old_tickets
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