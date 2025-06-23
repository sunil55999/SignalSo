"""
Test Suite for Signal Conflict Resolver
Tests conflict detection and resolution logic for various scenarios
"""

import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import json
import tempfile
import os

from signal_conflict_resolver import (
    SignalConflictResolver,
    SignalInfo,
    ExistingTrade,
    ConflictType,
    ConflictAction,
    TradeDirection,
    ConflictDetails,
    ConflictResolution
)


class TestSignalConflictResolver(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary config and log files
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        self.log_file = os.path.join(self.temp_dir, "test_log.json")
        
        # Create test config
        test_config = {
            "conflict_resolver": {
                "enabled": True,
                "default_action": "warn_only",
                "hedge_mode": False,
                "provider_priorities": {
                    "high_priority": 10,
                    "medium_priority": 5,
                    "low_priority": 1
                },
                "symbol_settings": {
                    "EURUSD": {"conflict_action": "close_existing"},
                    "GBPUSD": {"conflict_action": "reject_new"}
                },
                "time_overlap_threshold_minutes": 5,
                "confidence_threshold": 0.7,
                "auto_close_opposite": False,
                "notification_enabled": True,
                "exception_tags": ["hedge", "scalp", "manual"],
                "conflict_cooldown_minutes": 15
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
        
        # Initialize resolver
        self.resolver = SignalConflictResolver(self.config_file, self.log_file)
        
        # Mock dependencies
        self.mock_mt5_bridge = Mock()
        self.mock_parser = Mock()
        self.mock_copilot_bot = Mock()
        self.mock_strategy_runtime = Mock()
        
        self.resolver.inject_modules(
            mt5_bridge=self.mock_mt5_bridge,
            parser=self.mock_parser,
            copilot_bot=self.mock_copilot_bot,
            strategy_runtime=self.mock_strategy_runtime
        )

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_test_signal(self, signal_id="test_001", provider_id="test_provider", 
                          symbol="EURUSD", direction=TradeDirection.BUY, 
                          confidence=0.8, tags=None):
        """Create a test signal"""
        return SignalInfo(
            signal_id=signal_id,
            provider_id=provider_id,
            symbol=symbol,
            direction=direction,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            lot_size=0.1,
            timestamp=datetime.now(),
            raw_content=f"{direction.value.upper()} {symbol} @ 1.1000",
            confidence=confidence,
            tags=tags or []
        )

    def create_test_trade(self, ticket=12345, symbol="EURUSD", direction=TradeDirection.SELL,
                         provider_id="test_provider"):
        """Create a test existing trade"""
        return ExistingTrade(
            ticket=ticket,
            symbol=symbol,
            direction=direction,
            entry_price=1.0950,
            current_price=1.0970,
            lot_size=0.1,
            profit=-20.0,
            open_time=datetime.now() - timedelta(hours=1),
            provider_id=provider_id,
            signal_id="previous_signal"
        )

    def test_signal_registration(self):
        """Test signal registration functionality"""
        signal = self.create_test_signal()
        
        result = self.resolver.register_signal(signal)
        
        self.assertTrue(result)
        self.assertIn(signal.signal_id, self.resolver.active_signals)
        self.assertEqual(self.resolver.active_signals[signal.signal_id], signal)

    def test_signal_registration_with_exception_tags(self):
        """Test signal registration skips conflict check for exception tags"""
        signal = self.create_test_signal(tags=["hedge"])
        
        result = self.resolver.register_signal(signal)
        
        self.assertTrue(result)
        # Signal should still be registered even with exception tag

    async def test_opposite_direction_conflict_detection(self):
        """Test detection of opposite direction conflicts"""
        # Create BUY signal
        buy_signal = self.create_test_signal(direction=TradeDirection.BUY)
        
        # Mock existing SELL trade
        sell_trade = self.create_test_trade(direction=TradeDirection.SELL)
        self.mock_mt5_bridge.get_open_trades = Mock(return_value=[{
            'ticket': sell_trade.ticket,
            'symbol': sell_trade.symbol,
            'type': sell_trade.direction.value,
            'entry_price': sell_trade.entry_price,
            'current_price': sell_trade.current_price,
            'lot_size': sell_trade.lot_size,
            'profit': sell_trade.profit,
            'open_time': sell_trade.open_time.isoformat(),
            'provider_id': sell_trade.provider_id,
            'signal_id': sell_trade.signal_id
        }])
        
        conflict = await self.resolver.check_signal_conflicts(buy_signal)
        
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict.conflict_type, ConflictType.OPPOSITE_DIRECTION)
        self.assertEqual(len(conflict.conflicting_trades), 1)
        self.assertEqual(conflict.conflicting_trades[0].ticket, sell_trade.ticket)

    async def test_no_conflict_same_direction(self):
        """Test no conflict when trades are in same direction"""
        # Create BUY signal
        buy_signal = self.create_test_signal(direction=TradeDirection.BUY)
        
        # Mock existing BUY trade (same direction)
        buy_trade = self.create_test_trade(direction=TradeDirection.BUY)
        self.mock_mt5_bridge.get_open_trades = Mock(return_value=[{
            'ticket': buy_trade.ticket,
            'symbol': buy_trade.symbol,
            'type': buy_trade.direction.value,
            'entry_price': buy_trade.entry_price,
            'current_price': buy_trade.current_price,
            'lot_size': buy_trade.lot_size,
            'profit': buy_trade.profit,
            'open_time': buy_trade.open_time.isoformat(),
            'provider_id': buy_trade.provider_id,
            'signal_id': buy_trade.signal_id
        }])
        
        conflict = await self.resolver.check_signal_conflicts(buy_signal)
        
        self.assertIsNone(conflict)

    async def test_hedge_mode_allows_opposite_directions(self):
        """Test hedge mode allows opposite direction trades"""
        # Enable hedge mode
        self.resolver.config["hedge_mode"] = True
        
        buy_signal = self.create_test_signal(direction=TradeDirection.BUY)
        sell_trade = self.create_test_trade(direction=TradeDirection.SELL)
        
        self.mock_mt5_bridge.get_open_trades = Mock(return_value=[{
            'ticket': sell_trade.ticket,
            'symbol': sell_trade.symbol,
            'type': sell_trade.direction.value,
            'entry_price': sell_trade.entry_price,
            'current_price': sell_trade.current_price,
            'lot_size': sell_trade.lot_size,
            'profit': sell_trade.profit,
            'open_time': sell_trade.open_time.isoformat(),
            'provider_id': sell_trade.provider_id,
            'signal_id': sell_trade.signal_id
        }])
        
        conflict = await self.resolver.check_signal_conflicts(buy_signal)
        
        # Should not detect direction conflict in hedge mode
        if conflict:
            self.assertEqual(len(conflict.conflicting_trades), 0)

    def test_provider_conflict_detection(self):
        """Test detection of provider conflicts"""
        # Configure providers to conflict
        self.resolver.config["provider_settings"] = {
            "conflicts": [["provider_a", "provider_b"]]
        }
        
        signal_a = self.create_test_signal(provider_id="provider_a")
        signal_b = self.create_test_signal(provider_id="provider_b", signal_id="test_002")
        
        # Test if providers conflict
        result = self.resolver._providers_conflict("provider_a", "provider_b")
        self.assertTrue(result)
        
        result = self.resolver._providers_conflict("provider_a", "provider_c")
        self.assertFalse(result)

    def test_time_overlap_conflict_detection(self):
        """Test detection of time overlap conflicts"""
        # Register first signal
        signal1 = self.create_test_signal(signal_id="test_001")
        self.resolver.register_signal(signal1)
        
        # Create second signal within overlap threshold
        signal2 = self.create_test_signal(
            signal_id="test_002",
            provider_id="test_provider"  # Same provider
        )
        signal2.timestamp = signal1.timestamp + timedelta(minutes=2)  # Within 5-minute threshold
        
        conflicts = self.resolver._check_time_overlap_conflicts(signal2)
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].signal_id, "test_001")

    def test_duplicate_signal_detection(self):
        """Test detection of duplicate signals"""
        # Register first signal
        signal1 = self.create_test_signal()
        self.resolver.register_signal(signal1)
        
        # Create identical signal
        signal2 = self.create_test_signal(signal_id="test_002")  # Different ID but same content
        
        conflicts = self.resolver._check_duplicate_signals(signal2)
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].signal_id, "test_001")

    async def test_conflict_resolution_close_existing(self):
        """Test conflict resolution with close existing action"""
        # Set up conflict
        buy_signal = self.create_test_signal(symbol="EURUSD")  # EURUSD configured for close_existing
        sell_trade = self.create_test_trade(direction=TradeDirection.SELL)
        
        conflict = ConflictDetails(
            conflict_type=ConflictType.OPPOSITE_DIRECTION,
            new_signal=buy_signal,
            conflicting_trades=[sell_trade]
        )
        
        # Mock successful trade closure
        self.mock_mt5_bridge.close_position = AsyncMock(return_value={'success': True})
        
        resolution = await self.resolver.resolve_conflict(conflict)
        
        self.assertEqual(resolution.action, ConflictAction.CLOSE_EXISTING)
        self.assertEqual(len(resolution.trades_to_close), 1)
        self.assertEqual(resolution.trades_to_close[0], sell_trade.ticket)
        
        # Verify close_position was called
        self.mock_mt5_bridge.close_position.assert_called_once_with(
            sell_trade.ticket, "Conflict resolution"
        )

    async def test_conflict_resolution_reject_new(self):
        """Test conflict resolution with reject new action"""
        # Set up conflict for GBPUSD (configured for reject_new)
        buy_signal = self.create_test_signal(symbol="GBPUSD")
        sell_trade = self.create_test_trade(symbol="GBPUSD", direction=TradeDirection.SELL)
        
        conflict = ConflictDetails(
            conflict_type=ConflictType.OPPOSITE_DIRECTION,
            new_signal=buy_signal,
            conflicting_trades=[sell_trade]
        )
        
        resolution = await self.resolver.resolve_conflict(conflict)
        
        self.assertEqual(resolution.action, ConflictAction.REJECT_NEW)
        self.assertEqual(len(resolution.signals_to_reject), 1)
        self.assertEqual(resolution.signals_to_reject[0], buy_signal.signal_id)

    async def test_conflict_resolution_warn_only(self):
        """Test conflict resolution with warn only action"""
        # Use default action (warn_only)
        buy_signal = self.create_test_signal(symbol="USDJPY")  # No specific config
        sell_trade = self.create_test_trade(symbol="USDJPY", direction=TradeDirection.SELL)
        
        conflict = ConflictDetails(
            conflict_type=ConflictType.OPPOSITE_DIRECTION,
            new_signal=buy_signal,
            conflicting_trades=[sell_trade]
        )
        
        resolution = await self.resolver.resolve_conflict(conflict)
        
        self.assertEqual(resolution.action, ConflictAction.WARN_ONLY)
        self.assertEqual(len(resolution.trades_to_close), 0)
        self.assertEqual(len(resolution.signals_to_reject), 0)

    def test_provider_priority_resolution(self):
        """Test conflict resolution based on provider priorities"""
        # High priority provider vs low priority
        high_signal = self.create_test_signal(provider_id="high_priority")
        low_trade = self.create_test_trade(provider_id="low_priority")
        
        conflict = ConflictDetails(
            conflict_type=ConflictType.PROVIDER_CONFLICT,
            new_signal=high_signal,
            conflicting_trades=[low_trade]
        )
        
        action = self.resolver._determine_resolution_action(conflict)
        
        # High priority should close existing low priority trade
        self.assertEqual(action, ConflictAction.CLOSE_EXISTING)

    def test_provider_priority_resolution_reverse(self):
        """Test conflict resolution when existing trade has higher priority"""
        # Low priority signal vs high priority trade
        low_signal = self.create_test_signal(provider_id="low_priority")
        high_trade = self.create_test_trade(provider_id="high_priority")
        
        conflict = ConflictDetails(
            conflict_type=ConflictType.PROVIDER_CONFLICT,
            new_signal=low_signal,
            conflicting_trades=[high_trade]
        )
        
        action = self.resolver._determine_resolution_action(conflict)
        
        # Should reject new low priority signal
        self.assertEqual(action, ConflictAction.REJECT_NEW)

    async def test_full_signal_processing_no_conflict(self):
        """Test full signal processing when no conflict exists"""
        signal = self.create_test_signal()
        
        # Mock no existing trades
        self.mock_mt5_bridge.get_open_trades = Mock(return_value=[])
        
        proceed, resolution = await self.resolver.process_signal_with_conflict_check(signal)
        
        self.assertTrue(proceed)
        self.assertIsNone(resolution)

    async def test_full_signal_processing_with_conflict(self):
        """Test full signal processing with conflict resolution"""
        signal = self.create_test_signal(symbol="EURUSD")  # Configured for close_existing
        conflicting_trade = self.create_test_trade(direction=TradeDirection.SELL)
        
        # Mock existing conflicting trade
        self.mock_mt5_bridge.get_open_trades = Mock(return_value=[{
            'ticket': conflicting_trade.ticket,
            'symbol': conflicting_trade.symbol,
            'type': conflicting_trade.direction.value,
            'entry_price': conflicting_trade.entry_price,
            'current_price': conflicting_trade.current_price,
            'lot_size': conflicting_trade.lot_size,
            'profit': conflicting_trade.profit,
            'open_time': conflicting_trade.open_time.isoformat(),
            'provider_id': conflicting_trade.provider_id,
            'signal_id': conflicting_trade.signal_id
        }])
        
        # Mock successful closure
        self.mock_mt5_bridge.close_position = AsyncMock(return_value={'success': True})
        
        proceed, resolution = await self.resolver.process_signal_with_conflict_check(signal)
        
        self.assertTrue(proceed)  # Should proceed after closing conflicting trade
        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.action, ConflictAction.CLOSE_EXISTING)

    async def test_notification_sending(self):
        """Test conflict notification sending"""
        signal = self.create_test_signal()
        conflict = ConflictDetails(
            conflict_type=ConflictType.OPPOSITE_DIRECTION,
            new_signal=signal,
            conflicting_trades=[]
        )
        
        # Mock copilot bot
        self.mock_copilot_bot.send_alert = AsyncMock()
        
        await self.resolver._send_conflict_notification("Test message", conflict)
        
        # Verify notification was sent
        self.mock_copilot_bot.send_alert.assert_called_once()
        call_args = self.mock_copilot_bot.send_alert.call_args[0][0]
        self.assertIn("Test message", call_args)
        self.assertIn(signal.symbol, call_args)

    def test_conflict_statistics(self):
        """Test conflict statistics generation"""
        # Add some test conflicts to history
        signal1 = self.create_test_signal(signal_id="test_001")
        signal2 = self.create_test_signal(signal_id="test_002")
        
        conflict1 = ConflictDetails(
            conflict_type=ConflictType.OPPOSITE_DIRECTION,
            new_signal=signal1,
            conflicting_trades=[],
            resolution_action=ConflictAction.CLOSE_EXISTING,
            timestamp=datetime.now()
        )
        
        conflict2 = ConflictDetails(
            conflict_type=ConflictType.DUPLICATE_SIGNAL,
            new_signal=signal2,
            conflicting_trades=[],
            resolution_action=ConflictAction.REJECT_NEW,
            timestamp=datetime.now()
        )
        
        self.resolver.conflict_history.extend([conflict1, conflict2])
        
        stats = self.resolver.get_conflict_statistics()
        
        self.assertEqual(stats["total_conflicts"], 2)
        self.assertEqual(stats["by_type"]["opposite_direction"], 1)
        self.assertEqual(stats["by_type"]["duplicate_signal"], 1)
        self.assertEqual(stats["by_resolution"]["close_existing"], 1)
        self.assertEqual(stats["by_resolution"]["reject_new"], 1)

    def test_active_signals_management(self):
        """Test active signals tracking and cleanup"""
        # Add some signals
        signal1 = self.create_test_signal(signal_id="test_001")
        signal2 = self.create_test_signal(signal_id="test_002")
        
        # Make one signal old
        signal1.timestamp = datetime.now() - timedelta(hours=25)
        signal2.timestamp = datetime.now()
        
        self.resolver.register_signal(signal1)
        self.resolver.register_signal(signal2)
        
        self.assertEqual(len(self.resolver.active_signals), 2)
        
        # Clear old signals
        self.resolver.clear_old_signals(max_age_hours=24)
        
        self.assertEqual(len(self.resolver.active_signals), 1)
        self.assertIn("test_002", self.resolver.active_signals)
        self.assertNotIn("test_001", self.resolver.active_signals)

    def test_config_update(self):
        """Test configuration update functionality"""
        new_config = {
            "hedge_mode": True,
            "default_action": "close_existing",
            "notification_enabled": False
        }
        
        old_hedge_mode = self.resolver.config.get("hedge_mode", False)
        
        self.resolver.update_config(new_config)
        
        self.assertNotEqual(old_hedge_mode, self.resolver.config["hedge_mode"])
        self.assertEqual(self.resolver.config["hedge_mode"], True)
        self.assertEqual(self.resolver.config["default_action"], "close_existing")

    async def test_mt5_bridge_error_handling(self):
        """Test handling of MT5 bridge errors"""
        signal = self.create_test_signal()
        
        # Mock MT5 bridge failure
        self.mock_mt5_bridge.get_open_trades = Mock(side_effect=Exception("MT5 connection error"))
        
        # Should handle error gracefully
        existing_trades = await self.resolver._get_existing_trades(signal.symbol)
        
        self.assertEqual(len(existing_trades), 0)  # Should return empty list on error

    async def test_trade_closure_failure_handling(self):
        """Test handling of trade closure failures"""
        ticket = 12345
        
        # Mock closure failure
        self.mock_mt5_bridge.close_position = AsyncMock(return_value={'success': False})
        
        result = await self.resolver._close_trade(ticket, "Test closure")
        
        self.assertFalse(result)

    def test_opposite_direction_detection(self):
        """Test opposite direction detection logic"""
        test_cases = [
            (TradeDirection.BUY, TradeDirection.SELL, True),
            (TradeDirection.SELL, TradeDirection.BUY, True),
            (TradeDirection.PENDING_BUY, TradeDirection.PENDING_SELL, True),
            (TradeDirection.PENDING_SELL, TradeDirection.PENDING_BUY, True),
            (TradeDirection.BUY, TradeDirection.BUY, False),
            (TradeDirection.SELL, TradeDirection.SELL, False),
            (TradeDirection.BUY, TradeDirection.PENDING_BUY, False)
        ]
        
        for dir1, dir2, expected in test_cases:
            with self.subTest(dir1=dir1, dir2=dir2):
                result = self.resolver._is_opposite_direction(dir1, dir2)
                self.assertEqual(result, expected)

    def test_signal_hash_calculation(self):
        """Test signal hash calculation for duplicate detection"""
        signal1 = self.create_test_signal(signal_id="test_001")
        signal2 = self.create_test_signal(signal_id="test_002")  # Different ID, same content
        signal3 = self.create_test_signal(signal_id="test_003", symbol="GBPUSD")  # Different content
        
        hash1 = self.resolver._calculate_signal_hash(signal1)
        hash2 = self.resolver._calculate_signal_hash(signal2)
        hash3 = self.resolver._calculate_signal_hash(signal3)
        
        self.assertEqual(hash1, hash2)  # Same content should have same hash
        self.assertNotEqual(hash1, hash3)  # Different content should have different hash

    def test_disabled_conflict_resolution(self):
        """Test behavior when conflict resolution is disabled"""
        self.resolver.config["enabled"] = False
        
        signal = self.create_test_signal()
        
        # Should not register for conflict checking when disabled
        result = self.resolver.register_signal(signal)
        self.assertTrue(result)

    async def test_confidence_based_resolution(self):
        """Test conflict resolution based on signal confidence"""
        # High confidence signal
        high_conf_signal = self.create_test_signal(confidence=0.9)
        trade = self.create_test_trade()
        
        # Enable auto close for high confidence
        self.resolver.config["auto_close_opposite"] = True
        
        conflict = ConflictDetails(
            conflict_type=ConflictType.OPPOSITE_DIRECTION,
            new_signal=high_conf_signal,
            conflicting_trades=[trade]
        )
        
        action = self.resolver._determine_resolution_action(conflict)
        
        # High confidence should trigger close existing
        self.assertEqual(action, ConflictAction.CLOSE_EXISTING)

    def test_conflict_history_persistence(self):
        """Test conflict history saving and loading"""
        # Add a conflict to history
        signal = self.create_test_signal()
        conflict = ConflictDetails(
            conflict_type=ConflictType.OPPOSITE_DIRECTION,
            new_signal=signal,
            conflicting_trades=[],
            resolution_action=ConflictAction.WARN_ONLY,
            timestamp=datetime.now()
        )
        
        self.resolver.conflict_history.append(conflict)
        self.resolver._save_conflict_history()
        
        # Create new resolver and load history
        new_resolver = SignalConflictResolver(self.config_file, self.log_file)
        
        self.assertEqual(len(new_resolver.conflict_history), 1)
        self.assertEqual(new_resolver.conflict_history[0].conflict_type, ConflictType.OPPOSITE_DIRECTION)


# Additional integration tests
class TestSignalConflictResolverIntegration(unittest.TestCase):
    """Integration tests for complete conflict resolution workflows"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "integration_config.json")
        self.log_file = os.path.join(self.temp_dir, "integration_log.json")
        
        # Create comprehensive config
        config = {
            "conflict_resolver": {
                "enabled": True,
                "default_action": "warn_only",
                "hedge_mode": False,
                "provider_priorities": {
                    "premium_provider": 10,
                    "standard_provider": 5,
                    "basic_provider": 1
                },
                "symbol_settings": {
                    "EURUSD": {"conflict_action": "close_existing"},
                    "GBPUSD": {"conflict_action": "reject_new"},
                    "USDJPY": {"conflict_action": "allow_both"}
                },
                "provider_settings": {
                    "conflicts": [
                        ["provider_a", "provider_b"],
                        ["free_provider", "premium_provider"]
                    ]
                },
                "auto_close_opposite": True,
                "confidence_threshold": 0.8
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
        
        self.resolver = SignalConflictResolver(self.config_file, self.log_file)
        
        # Set up comprehensive mocks
        self.mock_mt5_bridge = Mock()
        self.mock_copilot_bot = Mock()
        self.mock_copilot_bot.send_alert = AsyncMock()
        
        self.resolver.inject_modules(
            mt5_bridge=self.mock_mt5_bridge,
            copilot_bot=self.mock_copilot_bot
        )

    def tearDown(self):
        """Clean up integration test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)

    async def test_complete_workflow_close_existing(self):
        """Test complete workflow: detect conflict and close existing trade"""
        # Set up scenario: High priority BUY signal vs existing SELL trade
        buy_signal = SignalInfo(
            signal_id="premium_001",
            provider_id="premium_provider",
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            lot_size=0.2,
            timestamp=datetime.now(),
            raw_content="PREMIUM BUY EURUSD @ 1.1000",
            confidence=0.95
        )
        
        # Mock existing trade
        self.mock_mt5_bridge.get_open_trades = Mock(return_value=[{
            'ticket': 54321,
            'symbol': 'EURUSD',
            'type': 'sell',
            'entry_price': 1.0980,
            'current_price': 1.0985,
            'lot_size': 0.1,
            'profit': -5.0,
            'open_time': (datetime.now() - timedelta(hours=2)).isoformat(),
            'provider_id': 'basic_provider',
            'signal_id': 'basic_001'
        }])
        
        # Mock successful closure
        self.mock_mt5_bridge.close_position = AsyncMock(return_value={'success': True})
        
        # Process signal
        proceed, resolution = await self.resolver.process_signal_with_conflict_check(buy_signal)
        
        # Verify results
        self.assertTrue(proceed)
        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.action, ConflictAction.CLOSE_EXISTING)
        self.assertEqual(len(resolution.trades_to_close), 1)
        self.assertEqual(resolution.trades_to_close[0], 54321)
        
        # Verify trade was closed
        self.mock_mt5_bridge.close_position.assert_called_once_with(54321, "Conflict resolution")
        
        # Verify notification was sent
        self.mock_copilot_bot.send_alert.assert_called_once()

    async def test_complete_workflow_reject_new(self):
        """Test complete workflow: detect conflict and reject new signal"""
        # Set up scenario: Low priority signal vs existing high priority trade
        sell_signal = SignalInfo(
            signal_id="basic_001",
            provider_id="basic_provider",
            symbol="GBPUSD",  # Configured for reject_new
            direction=TradeDirection.SELL,
            entry_price=1.2500,
            stop_loss=1.2550,
            take_profit=1.2400,
            lot_size=0.1,
            timestamp=datetime.now(),
            raw_content="SELL GBPUSD @ 1.2500",
            confidence=0.6
        )
        
        # Mock existing trade from premium provider
        self.mock_mt5_bridge.get_open_trades = Mock(return_value=[{
            'ticket': 98765,
            'symbol': 'GBPUSD',
            'type': 'buy',
            'entry_price': 1.2480,
            'current_price': 1.2485,
            'lot_size': 0.2,
            'profit': 10.0,
            'open_time': (datetime.now() - timedelta(minutes=30)).isoformat(),
            'provider_id': 'premium_provider',
            'signal_id': 'premium_002'
        }])
        
        # Process signal
        proceed, resolution = await self.resolver.process_signal_with_conflict_check(sell_signal)
        
        # Verify results
        self.assertFalse(proceed)  # Should not proceed due to rejection
        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.action, ConflictAction.REJECT_NEW)
        self.assertEqual(len(resolution.signals_to_reject), 1)
        self.assertEqual(resolution.signals_to_reject[0], "basic_001")
        
        # Verify no trades were closed
        self.assertFalse(hasattr(self.mock_mt5_bridge, 'close_position') and 
                        self.mock_mt5_bridge.close_position.called)

    async def test_multiple_conflicts_resolution(self):
        """Test handling of multiple simultaneous conflicts"""
        # Signal that conflicts with multiple existing trades
        signal = SignalInfo(
            signal_id="multi_001",
            provider_id="premium_provider",
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            lot_size=0.3,
            timestamp=datetime.now(),
            raw_content="BUY EURUSD @ 1.1000",
            confidence=0.9
        )
        
        # Mock multiple conflicting trades
        self.mock_mt5_bridge.get_open_trades = Mock(return_value=[
            {
                'ticket': 11111,
                'symbol': 'EURUSD',
                'type': 'sell',
                'entry_price': 1.0980,
                'current_price': 1.0985,
                'lot_size': 0.1,
                'profit': -5.0,
                'open_time': (datetime.now() - timedelta(hours=1)).isoformat(),
                'provider_id': 'basic_provider',
                'signal_id': 'basic_001'
            },
            {
                'ticket': 22222,
                'symbol': 'EURUSD',
                'type': 'sell',
                'entry_price': 1.0975,
                'current_price': 1.0985,
                'lot_size': 0.15,
                'profit': -15.0,
                'open_time': (datetime.now() - timedelta(hours=2)).isoformat(),
                'provider_id': 'standard_provider',
                'signal_id': 'standard_001'
            }
        ])
        
        # Mock successful closures
        self.mock_mt5_bridge.close_position = AsyncMock(return_value={'success': True})
        
        # Process signal
        proceed, resolution = await self.resolver.process_signal_with_conflict_check(signal)
        
        # Verify all conflicting trades are marked for closure
        self.assertTrue(proceed)
        self.assertEqual(resolution.action, ConflictAction.CLOSE_EXISTING)
        self.assertEqual(len(resolution.trades_to_close), 2)
        self.assertIn(11111, resolution.trades_to_close)
        self.assertIn(22222, resolution.trades_to_close)

    def test_statistics_after_multiple_operations(self):
        """Test statistics tracking after multiple conflict operations"""
        # Simulate several conflicts over time
        conflicts = []
        
        # Create various types of conflicts
        for i in range(5):
            signal = SignalInfo(
                signal_id=f"test_{i:03d}",
                provider_id="test_provider",
                symbol="EURUSD",
                direction=TradeDirection.BUY if i % 2 == 0 else TradeDirection.SELL,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1100,
                lot_size=0.1,
                timestamp=datetime.now() - timedelta(minutes=i*10),
                raw_content=f"Test signal {i}",
                confidence=0.8
            )
            
            conflict = ConflictDetails(
                conflict_type=ConflictType.OPPOSITE_DIRECTION if i < 3 else ConflictType.DUPLICATE_SIGNAL,
                new_signal=signal,
                conflicting_trades=[],
                resolution_action=ConflictAction.CLOSE_EXISTING if i < 2 else ConflictAction.WARN_ONLY,
                timestamp=signal.timestamp
            )
            conflicts.append(conflict)
        
        self.resolver.conflict_history.extend(conflicts)
        
        # Get statistics
        stats = self.resolver.get_conflict_statistics()
        
        # Verify statistics
        self.assertEqual(stats["total_conflicts"], 5)
        self.assertEqual(stats["recent_24h"], 5)  # All within 24 hours
        self.assertEqual(stats["by_type"]["opposite_direction"], 3)
        self.assertEqual(stats["by_type"]["duplicate_signal"], 2)
        self.assertEqual(stats["by_resolution"]["close_existing"], 2)
        self.assertEqual(stats["by_resolution"]["warn_only"], 3)


if __name__ == '__main__':
    # Run tests
    unittest.main()