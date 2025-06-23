"""
Test Suite for Edit Trade on Signal Change Engine
Comprehensive tests covering signal edit detection, trade modification, and edge cases
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

from edit_trade_on_signal_change import (
    EditTradeEngine, ChangeType, TradeStatus, SignalVersion, 
    TradeModification, EditTradeEvent
)


class TestEditTradeEngine(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create temporary config and log files
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        # Test configuration
        test_config = {
            "edit_trade_engine": {
                "enable_auto_edit": True,
                "check_interval": 30,
                "max_edit_time_window": 3600,
                "allowed_changes": ["entry_price", "stop_loss", "take_profit"],
                "require_confirmation": False,
                "min_change_threshold": {
                    "entry_price": 0.0001,
                    "stop_loss": 0.0001,
                    "take_profit": 0.0001
                },
                "max_modification_attempts": 3,
                "notification_enabled": True
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize empty log file
        json.dump({"edit_events": []}, self.temp_log)
        self.temp_log.close()
        
        # Create edit trade engine instance
        self.edit_engine = EditTradeEngine(
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
        self.mock_parser = Mock()
        self.mock_parser.parse_signal.return_value = {
            'entry_price': 1.1000,
            'stop_loss': 1.0950,
            'take_profit': 1.1050,
            'lot_size': 0.1
        }
        
        self.mock_mt5_bridge = Mock()
        self.mock_mt5_bridge.is_position_open = AsyncMock(return_value=True)
        self.mock_mt5_bridge.modify_stop_loss = AsyncMock(return_value=True)
        self.mock_mt5_bridge.modify_take_profit = AsyncMock(return_value=True)
        self.mock_mt5_bridge.modify_position_entry = AsyncMock(return_value=True)
        self.mock_mt5_bridge.modify_lot_size = AsyncMock(return_value=True)
        
        self.mock_strategy_runtime = Mock()
        
        # Inject mocks
        self.edit_engine.inject_modules(
            parser=self.mock_parser,
            mt5_bridge=self.mock_mt5_bridge,
            strategy_runtime=self.mock_strategy_runtime
        )


class TestSignalMapping(TestEditTradeEngine):
    """Test signal-trade mapping functionality"""
    
    def test_register_signal_trade_mapping(self):
        """Test registering signal-trade mapping"""
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        message_id = 12345
        trade_ticket = 67890
        
        self.edit_engine.register_signal_trade_mapping(message_id, trade_ticket, signal_content)
        
        # Check mapping was created
        self.assertIn(trade_ticket, self.edit_engine.trade_signal_mapping)
        self.assertEqual(self.edit_engine.trade_signal_mapping[trade_ticket], message_id)
        
        # Check signal version was stored
        self.assertIn(message_id, self.edit_engine.signal_versions)
        self.assertEqual(len(self.edit_engine.signal_versions[message_id]), 1)
        
        # Check edit event was created
        self.assertEqual(len(self.edit_engine.edit_events), 1)
        event = self.edit_engine.edit_events[0]
        self.assertEqual(event.message_id, message_id)
        self.assertIn(trade_ticket, event.associated_trades)
    
    def test_multiple_trades_same_signal(self):
        """Test multiple trades mapped to same signal"""
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        message_id = 12345
        
        # Register multiple trades for same signal
        for i, trade_ticket in enumerate([67890, 67891, 67892]):
            self.edit_engine.register_signal_trade_mapping(message_id, trade_ticket, signal_content)
        
        # Check all trades are mapped
        for trade_ticket in [67890, 67891, 67892]:
            self.assertIn(trade_ticket, self.edit_engine.trade_signal_mapping)
            self.assertEqual(self.edit_engine.trade_signal_mapping[trade_ticket], message_id)
        
        # Should have one event with multiple trades
        self.assertEqual(len(self.edit_engine.edit_events), 1)
        event = self.edit_engine.edit_events[0]
        self.assertEqual(len(event.associated_trades), 3)


class TestSignalParsing(TestEditTradeEngine):
    """Test signal parsing functionality"""
    
    def test_parse_signal_values_with_parser(self):
        """Test parsing signal values using injected parser"""
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        values = self.edit_engine._parse_signal_values(signal_content)
        
        self.assertEqual(values['entry_price'], 1.1000)
        self.assertEqual(values['stop_loss'], 1.0950)
        self.assertEqual(values['take_profit'], 1.1050)
        self.assertEqual(values['lot_size'], 0.1)
        
        # Verify parser was called
        self.mock_parser.parse_signal.assert_called_once_with(signal_content)
    
    def test_parse_signal_values_fallback(self):
        """Test fallback parsing when no parser is available"""
        # Remove parser to test fallback
        self.edit_engine.parser = None
        
        signal_content = "EURUSD entry: 1.1000 sl: 1.0950 tp: 1.1050 lot: 0.1"
        values = self.edit_engine._parse_signal_values(signal_content)
        
        self.assertEqual(values['entry_price'], 1.1000)
        self.assertEqual(values['stop_loss'], 1.0950)
        self.assertEqual(values['take_profit'], 1.1050)
        self.assertEqual(values['lot_size'], 0.1)
    
    def test_content_hash_calculation(self):
        """Test content hash calculation for change detection"""
        content1 = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        content2 = "EURUSD BUY 1.1000 SL 1.0940 TP 1.1050"  # Different SL
        content3 = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"  # Same as content1
        
        hash1 = self.edit_engine._calculate_content_hash(content1)
        hash2 = self.edit_engine._calculate_content_hash(content2)
        hash3 = self.edit_engine._calculate_content_hash(content3)
        
        self.assertNotEqual(hash1, hash2)  # Different content should have different hashes
        self.assertEqual(hash1, hash3)     # Same content should have same hash


class TestChangeDetection(TestEditTradeEngine):
    """Test change detection functionality"""
    
    def test_detect_stop_loss_change(self):
        """Test detecting stop loss changes"""
        old_version = SignalVersion(
            message_id=12345,
            content_hash="hash1",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            lot_size=0.1,
            timestamp=datetime.now(),
            raw_content="original"
        )
        
        new_version = SignalVersion(
            message_id=12345,
            content_hash="hash2",
            entry_price=1.1000,
            stop_loss=1.0940,  # Changed SL
            take_profit=1.1050,
            lot_size=0.1,
            timestamp=datetime.now(),
            raw_content="edited"
        )
        
        changes = self.edit_engine._detect_changes(old_version, new_version)
        
        self.assertIn(ChangeType.STOP_LOSS, changes)
        self.assertEqual(len(changes), 1)
    
    def test_detect_multiple_changes(self):
        """Test detecting multiple changes"""
        old_version = SignalVersion(
            message_id=12345,
            content_hash="hash1",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            lot_size=0.1,
            timestamp=datetime.now(),
            raw_content="original"
        )
        
        new_version = SignalVersion(
            message_id=12345,
            content_hash="hash2",
            entry_price=1.1000,
            stop_loss=1.0940,  # Changed SL
            take_profit=1.1060,  # Changed TP
            lot_size=0.1,
            timestamp=datetime.now(),
            raw_content="edited"
        )
        
        changes = self.edit_engine._detect_changes(old_version, new_version)
        
        self.assertIn(ChangeType.STOP_LOSS, changes)
        self.assertIn(ChangeType.TAKE_PROFIT, changes)
        self.assertEqual(len(changes), 2)
    
    def test_no_significant_change(self):
        """Test when changes are below threshold"""
        old_version = SignalVersion(
            message_id=12345,
            content_hash="hash1",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            lot_size=0.1,
            timestamp=datetime.now(),
            raw_content="original"
        )
        
        new_version = SignalVersion(
            message_id=12345,
            content_hash="hash2",
            entry_price=1.1000,
            stop_loss=1.09500001,  # Tiny change below threshold
            take_profit=1.1050,
            lot_size=0.1,
            timestamp=datetime.now(),
            raw_content="edited"
        )
        
        changes = self.edit_engine._detect_changes(old_version, new_version)
        
        self.assertEqual(len(changes), 0)


class TestTradeModification(TestEditTradeEngine):
    """Test trade modification functionality"""
    
    async def test_successful_stop_loss_modification(self):
        """Test successful stop loss modification"""
        # Setup signal and trade
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        message_id = 12345
        trade_ticket = 67890
        
        self.edit_engine.register_signal_trade_mapping(message_id, trade_ticket, signal_content)
        
        # Simulate signal edit
        new_content = "EURUSD BUY 1.1000 SL 1.0940 TP 1.1050"
        await self.edit_engine.on_signal_edit(message_id, new_content)
        
        # Verify MT5 bridge was called
        self.mock_mt5_bridge.modify_stop_loss.assert_called_once_with(trade_ticket, 1.0940)
        
        # Check modification was recorded
        event = self.edit_engine.edit_events[0]
        self.assertEqual(len(event.modifications), 1)
        
        modification = event.modifications[0]
        self.assertEqual(modification.change_type, ChangeType.STOP_LOSS)
        self.assertEqual(modification.old_value, 1.0950)
        self.assertEqual(modification.new_value, 1.0940)
        self.assertTrue(modification.success)
    
    async def test_failed_trade_modification(self):
        """Test handling of failed trade modification"""
        # Setup MT5 bridge to return failure
        self.mock_mt5_bridge.modify_stop_loss.return_value = False
        
        # Setup signal and trade
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        message_id = 12345
        trade_ticket = 67890
        
        self.edit_engine.register_signal_trade_mapping(message_id, trade_ticket, signal_content)
        
        # Simulate signal edit
        new_content = "EURUSD BUY 1.1000 SL 1.0940 TP 1.1050"
        await self.edit_engine.on_signal_edit(message_id, new_content)
        
        # Check modification was recorded as failed
        event = self.edit_engine.edit_events[0]
        modification = event.modifications[0]
        self.assertFalse(modification.success)
    
    async def test_closed_trade_skip(self):
        """Test skipping modification for closed trades"""
        # Setup MT5 bridge to indicate trade is closed
        self.mock_mt5_bridge.is_position_open.return_value = False
        
        # Setup signal and trade
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        message_id = 12345
        trade_ticket = 67890
        
        self.edit_engine.register_signal_trade_mapping(message_id, trade_ticket, signal_content)
        
        # Simulate signal edit
        new_content = "EURUSD BUY 1.1000 SL 1.0940 TP 1.1050"
        await self.edit_engine.on_signal_edit(message_id, new_content)
        
        # Verify no modification was attempted
        self.mock_mt5_bridge.modify_stop_loss.assert_not_called()
        
        # Should have no modifications recorded
        event = self.edit_engine.edit_events[0]
        self.assertEqual(len(event.modifications), 0)


class TestEditTimeWindow(TestEditTradeEngine):
    """Test edit time window functionality"""
    
    def test_within_edit_window(self):
        """Test edit within allowed time window"""
        recent_time = datetime.now() - timedelta(minutes=30)  # 30 minutes ago
        result = self.edit_engine._within_edit_window(recent_time)
        self.assertTrue(result)
    
    def test_outside_edit_window(self):
        """Test edit outside allowed time window"""
        old_time = datetime.now() - timedelta(hours=2)  # 2 hours ago (beyond 1 hour limit)
        result = self.edit_engine._within_edit_window(old_time)
        self.assertFalse(result)
    
    async def test_expired_edit_window_skip(self):
        """Test skipping modifications for expired edit window"""
        # Setup signal and trade with old timestamp
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        message_id = 12345
        trade_ticket = 67890
        
        self.edit_engine.register_signal_trade_mapping(message_id, trade_ticket, signal_content)
        
        # Manually set old timestamp
        event = self.edit_engine.edit_events[0]
        old_version = event.signal_versions[0]
        old_version.timestamp = datetime.now() - timedelta(hours=2)
        
        # Simulate signal edit
        new_content = "EURUSD BUY 1.1000 SL 1.0940 TP 1.1050"
        await self.edit_engine.on_signal_edit(message_id, new_content)
        
        # Verify no modification was attempted due to expired window
        self.mock_mt5_bridge.modify_stop_loss.assert_not_called()


class TestEdgeCases(TestEditTradeEngine):
    """Test edge cases and error handling"""
    
    async def test_edit_unknown_signal(self):
        """Test editing unknown signal"""
        # Try to edit a signal that wasn't registered
        unknown_message_id = 99999
        await self.edit_engine.on_signal_edit(unknown_message_id, "some content")
        
        # Should handle gracefully without errors
        # No modifications should be recorded
        self.assertEqual(len(self.edit_engine.edit_events), 0)
    
    async def test_no_content_change(self):
        """Test when signal content hasn't actually changed"""
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        message_id = 12345
        trade_ticket = 67890
        
        self.edit_engine.register_signal_trade_mapping(message_id, trade_ticket, signal_content)
        
        # "Edit" with same content
        await self.edit_engine.on_signal_edit(message_id, signal_content)
        
        # Should detect no change and not attempt modifications
        self.mock_mt5_bridge.modify_stop_loss.assert_not_called()
        
        # Should have only one signal version (no new version created)
        self.assertEqual(len(self.edit_engine.signal_versions[message_id]), 1)
    
    def test_invalid_configuration(self):
        """Test handling of invalid configuration"""
        # Test with missing config file
        invalid_engine = EditTradeEngine(config_file="nonexistent.json")
        self.assertIsInstance(invalid_engine.config, dict)
        self.assertIn('enable_auto_edit', invalid_engine.config)
    
    async def test_disallowed_change_type(self):
        """Test skipping disallowed change types"""
        # Modify config to only allow stop_loss changes
        self.edit_engine.config['allowed_changes'] = ['stop_loss']
        
        # Setup signal and trade
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        message_id = 12345
        trade_ticket = 67890
        
        self.edit_engine.register_signal_trade_mapping(message_id, trade_ticket, signal_content)
        
        # Edit take profit (not allowed)
        new_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1060"
        await self.edit_engine.on_signal_edit(message_id, new_content)
        
        # Should not modify take profit
        self.mock_mt5_bridge.modify_take_profit.assert_not_called()


class TestStatistics(TestEditTradeEngine):
    """Test statistics and reporting functionality"""
    
    def test_get_edit_statistics(self):
        """Test getting edit statistics"""
        # Setup some test data
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        message_id = 12345
        trade_ticket = 67890
        
        self.edit_engine.register_signal_trade_mapping(message_id, trade_ticket, signal_content)
        
        # Add some mock modifications
        event = self.edit_engine.edit_events[0]
        modification = TradeModification(
            ticket=trade_ticket,
            change_type=ChangeType.STOP_LOSS,
            old_value=1.0950,
            new_value=1.0940,
            modification_time=datetime.now(),
            success=True
        )
        event.modifications.append(modification)
        
        stats = self.edit_engine.get_edit_statistics()
        
        self.assertEqual(stats['total_edit_events'], 1)
        self.assertEqual(stats['total_modifications'], 1)
        self.assertEqual(stats['successful_modifications'], 1)
        self.assertEqual(stats['success_rate'], 100.0)
        self.assertEqual(stats['active_signal_mappings'], 1)
        self.assertIn('stop_loss', stats['change_type_breakdown'])
    
    def test_get_trade_edit_history(self):
        """Test getting edit history for specific trade"""
        # Setup signal and trade
        signal_content = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
        message_id = 12345
        trade_ticket = 67890
        
        self.edit_engine.register_signal_trade_mapping(message_id, trade_ticket, signal_content)
        
        # Add some modifications
        event = self.edit_engine.edit_events[0]
        
        # First modification
        mod1 = TradeModification(
            ticket=trade_ticket,
            change_type=ChangeType.STOP_LOSS,
            old_value=1.0950,
            new_value=1.0940,
            modification_time=datetime.now() - timedelta(minutes=10),
            success=True
        )
        event.modifications.append(mod1)
        
        # Second modification
        mod2 = TradeModification(
            ticket=trade_ticket,
            change_type=ChangeType.TAKE_PROFIT,
            old_value=1.1050,
            new_value=1.1060,
            modification_time=datetime.now() - timedelta(minutes=5),
            success=True
        )
        event.modifications.append(mod2)
        
        history = self.edit_engine.get_trade_edit_history(trade_ticket)
        
        self.assertEqual(len(history), 2)
        # Should be sorted by time (oldest first)
        self.assertEqual(history[0]['change_type'], 'stop_loss')
        self.assertEqual(history[1]['change_type'], 'take_profit')


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
        TestSignalMapping,
        TestSignalParsing,
        TestChangeDetection,
        TestTradeModification,
        TestEditTimeWindow,
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
    print("\n=== Running Async Integration Tests ===")
    
    async_tests = [
        TestTradeModification().test_successful_stop_loss_modification,
        TestTradeModification().test_failed_trade_modification,
        TestTradeModification().test_closed_trade_skip,
        TestEditTimeWindow().test_expired_edit_window_skip,
        TestEdgeCases().test_edit_unknown_signal,
        TestEdgeCases().test_no_content_change,
        TestEdgeCases().test_disallowed_change_type
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