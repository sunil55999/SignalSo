"""
Test Suite for Reverse Strategy Engine
Tests signal reversal logic, conditional reversals, and strategy integration
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reverse_strategy import (
    ReverseStrategy, ReversalRule, ReversalCondition, ReversalMode,
    OriginalSignal, SignalDirection, ReversedSignal
)

class TestReverseStrategy(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "reverse_strategy": {
                "enabled": True,
                "default_reversal_mode": "full_reverse",
                "enable_partial_reversals": True,
                "reversal_confidence_threshold": 0.7,
                "market_volatility_threshold": 2.0,
                "reversal_rules": [
                    {
                        "rule_id": "test_always_reverse",
                        "name": "Test Always Reverse",
                        "condition": "always",
                        "mode": "full_reverse",
                        "enabled": True,
                        "priority": 1,
                        "symbols": ["EURUSD"],
                        "providers": []
                    },
                    {
                        "rule_id": "test_high_volatility",
                        "name": "Test High Volatility",
                        "condition": "high_volatility",
                        "mode": "direction_only",
                        "enabled": True,
                        "priority": 2,
                        "symbols": ["XAUUSD"],
                        "market_conditions": {
                            "volatility_threshold": 2.5
                        }
                    },
                    {
                        "rule_id": "test_ignore_signal",
                        "name": "Test Ignore Signal",
                        "condition": "provider_specific",
                        "mode": "ignore_signal",
                        "enabled": True,
                        "priority": 3,
                        "providers": ["blocked_provider"]
                    }
                ],
                "symbol_settings": {
                    "EURUSD": {
                        "enable_reversal": True,
                        "reversal_strength": 1.0
                    },
                    "XAUUSD": {
                        "enable_reversal": True,
                        "reversal_strength": 1.5
                    }
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize reverse strategy
        self.strategy = ReverseStrategy(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
        # Clean up history file if created
        history_file = self.temp_log.name.replace('.log', '_history.json')
        if os.path.exists(history_file):
            os.unlink(history_file)

class TestBasicFunctionality(TestReverseStrategy):
    """Test basic reverse strategy functionality"""
    
    def test_initialization(self):
        """Test reverse strategy initialization"""
        self.assertTrue(self.strategy.config['enabled'])
        self.assertEqual(self.strategy.config['default_reversal_mode'], 'full_reverse')
        self.assertEqual(len(self.strategy.reversal_rules), 3)
        
    def test_reversal_rules_loading(self):
        """Test loading of reversal rules from configuration"""
        rules = self.strategy.reversal_rules
        
        # Check that rules are sorted by priority
        self.assertEqual(rules[0].rule_id, "test_always_reverse")
        self.assertEqual(rules[0].priority, 1)
        
        # Check rule properties
        always_rule = rules[0]
        self.assertEqual(always_rule.condition, ReversalCondition.ALWAYS)
        self.assertEqual(always_rule.mode, ReversalMode.FULL_REVERSE)
        self.assertTrue(always_rule.enabled)
        self.assertIn("EURUSD", always_rule.symbols)
        
    def test_direction_reversal(self):
        """Test basic direction reversal logic"""
        # BUY should become SELL
        reversed_buy = self.strategy._reverse_direction(SignalDirection.BUY)
        self.assertEqual(reversed_buy, SignalDirection.SELL)
        
        # SELL should become BUY
        reversed_sell = self.strategy._reverse_direction(SignalDirection.SELL)
        self.assertEqual(reversed_sell, SignalDirection.BUY)
        
        # HOLD should remain HOLD
        reversed_hold = self.strategy._reverse_direction(SignalDirection.HOLD)
        self.assertEqual(reversed_hold, SignalDirection.HOLD)

class TestReversalConditions(TestReverseStrategy):
    """Test reversal condition checking"""
    
    def test_always_condition(self):
        """Test ALWAYS reversal condition"""
        signal = OriginalSignal(
            signal_id="test_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            provider_id="test_provider",
            provider_name="Test Provider",
            timestamp=datetime.now()
        )
        
        always_rule = self.strategy.reversal_rules[0]  # test_always_reverse
        should_reverse, reason = self.strategy._check_reversal_conditions(signal, always_rule)
        
        self.assertTrue(should_reverse)
        self.assertIn("Always reverse", reason)
        
    def test_symbol_filtering(self):
        """Test symbol filtering in reversal conditions"""
        # Signal for EURUSD (in rule filter)
        eurusd_signal = OriginalSignal(
            signal_id="test_002",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            provider_id="test_provider",
            provider_name="Test Provider",
            timestamp=datetime.now()
        )
        
        always_rule = self.strategy.reversal_rules[0]  # Only applies to EURUSD
        should_reverse, reason = self.strategy._check_reversal_conditions(eurusd_signal, always_rule)
        self.assertTrue(should_reverse)
        
        # Signal for GBPUSD (not in rule filter)
        gbpusd_signal = OriginalSignal(
            signal_id="test_003",
            symbol="GBPUSD",
            direction=SignalDirection.BUY,
            entry_price=1.2500,
            stop_loss=1.2450,
            take_profit=1.2550,
            volume=0.1,
            provider_id="test_provider",
            provider_name="Test Provider",
            timestamp=datetime.now()
        )
        
        should_reverse_gbp, reason_gbp = self.strategy._check_reversal_conditions(gbpusd_signal, always_rule)
        self.assertFalse(should_reverse_gbp)
        self.assertIn("Symbol not in rule filter", reason_gbp)
        
    def test_provider_filtering(self):
        """Test provider filtering in reversal conditions"""
        signal = OriginalSignal(
            signal_id="test_004",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            provider_id="blocked_provider",
            provider_name="Blocked Provider",
            timestamp=datetime.now()
        )
        
        # Find the ignore signal rule
        ignore_rule = None
        for rule in self.strategy.reversal_rules:
            if rule.rule_id == "test_ignore_signal":
                ignore_rule = rule
                break
                
        self.assertIsNotNone(ignore_rule)
        
        should_reverse, reason = self.strategy._check_reversal_conditions(signal, ignore_rule)
        self.assertTrue(should_reverse)
        self.assertIn("Provider-specific reversal", reason)
        
    def test_high_volatility_condition(self):
        """Test high volatility reversal condition"""
        # XAUUSD signal (simulated as high volatility)
        xauusd_signal = OriginalSignal(
            signal_id="test_005",
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            entry_price=2000.0,
            stop_loss=1980.0,
            take_profit=2020.0,
            volume=0.01,
            provider_id="test_provider",
            provider_name="Test Provider",
            timestamp=datetime.now()
        )
        
        # Find high volatility rule
        volatility_rule = None
        for rule in self.strategy.reversal_rules:
            if rule.rule_id == "test_high_volatility":
                volatility_rule = rule
                break
                
        self.assertIsNotNone(volatility_rule)
        
        should_reverse, reason = self.strategy._check_reversal_conditions(xauusd_signal, volatility_rule)
        self.assertTrue(should_reverse)
        self.assertIn("High volatility detected", reason)

class TestLevelCalculations(TestReverseStrategy):
    """Test SL/TP level calculations for reversals"""
    
    def test_full_reverse_calculation_buy_to_sell(self):
        """Test full reversal calculation for BUY to SELL"""
        original_signal = OriginalSignal(
            signal_id="test_006",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,  # 50 pips below entry
            take_profit=1.1050,  # 50 pips above entry
            volume=0.1,
            provider_id="test_provider",
            provider_name="Test Provider",
            timestamp=datetime.now()
        )
        
        full_reverse_rule = ReversalRule(
            rule_id="test_full",
            name="Test Full Reverse",
            condition=ReversalCondition.ALWAYS,
            mode=ReversalMode.FULL_REVERSE
        )
        
        entry, sl, tp = self.strategy._calculate_reversed_levels(original_signal, full_reverse_rule)
        
        self.assertEqual(entry, 1.1000)  # Entry stays same
        self.assertEqual(sl, 1.1050)     # Original TP becomes new SL
        self.assertEqual(tp, 1.0950)     # Original SL becomes new TP
        
    def test_full_reverse_calculation_sell_to_buy(self):
        """Test full reversal calculation for SELL to BUY"""
        original_signal = OriginalSignal(
            signal_id="test_007",
            symbol="EURUSD",
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,    # 50 pips above entry (for SELL)
            take_profit=1.0950,  # 50 pips below entry (for SELL)
            volume=0.1,
            provider_id="test_provider",
            provider_name="Test Provider",
            timestamp=datetime.now()
        )
        
        full_reverse_rule = ReversalRule(
            rule_id="test_full",
            name="Test Full Reverse",
            condition=ReversalCondition.ALWAYS,
            mode=ReversalMode.FULL_REVERSE
        )
        
        entry, sl, tp = self.strategy._calculate_reversed_levels(original_signal, full_reverse_rule)
        
        self.assertEqual(entry, 1.1000)  # Entry stays same
        self.assertEqual(sl, 1.0950)     # Original TP becomes new SL
        self.assertEqual(tp, 1.1050)     # Original SL becomes new TP
        
    def test_direction_only_calculation(self):
        """Test direction-only reversal calculation"""
        original_signal = OriginalSignal(
            signal_id="test_008",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            provider_id="test_provider",
            provider_name="Test Provider",
            timestamp=datetime.now()
        )
        
        direction_only_rule = ReversalRule(
            rule_id="test_direction",
            name="Test Direction Only",
            condition=ReversalCondition.ALWAYS,
            mode=ReversalMode.DIRECTION_ONLY
        )
        
        entry, sl, tp = self.strategy._calculate_reversed_levels(original_signal, direction_only_rule)
        
        # All levels should remain the same
        self.assertEqual(entry, 1.1000)
        self.assertEqual(sl, 1.0950)
        self.assertEqual(tp, 1.1050)

class TestSignalProcessing(TestReverseStrategy):
    """Test complete signal processing through reversal engine"""
    
    def test_process_signal_with_reversal(self):
        """Test processing signal that gets reversed"""
        signal_data = {
            "signal_id": "test_009",
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1050,
            "volume": 0.1,
            "provider_id": "test_provider",
            "provider_name": "Test Provider",
            "confidence": 0.8
        }
        
        # Process through reversal engine
        result = self.strategy.process_signal(signal_data)
        
        # Should be reversed due to "test_always_reverse" rule
        self.assertIsNotNone(result)
        self.assertEqual(result["direction"], "sell")  # BUY -> SELL
        self.assertEqual(result["entry_price"], 1.1000)
        self.assertEqual(result["stop_loss"], 1.1050)  # Original TP
        self.assertEqual(result["take_profit"], 1.0950)  # Original SL
        self.assertTrue(result["reversal_applied"])
        self.assertEqual(result["original_direction"], "buy")
        
    def test_process_signal_no_reversal(self):
        """Test processing signal that doesn't get reversed"""
        signal_data = {
            "signal_id": "test_010",
            "symbol": "GBPUSD",  # Not in any rule filters
            "direction": "buy",
            "entry_price": 1.2500,
            "stop_loss": 1.2450,
            "take_profit": 1.2550,
            "volume": 0.1,
            "provider_id": "test_provider",
            "provider_name": "Test Provider",
            "confidence": 0.8
        }
        
        # Process through reversal engine
        result = self.strategy.process_signal(signal_data)
        
        # Should pass through unchanged
        self.assertEqual(result, signal_data)
        self.assertNotIn("reversal_applied", result)
        
    def test_process_signal_ignored(self):
        """Test processing signal that gets ignored"""
        signal_data = {
            "signal_id": "test_011",
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1050,
            "volume": 0.1,
            "provider_id": "blocked_provider",  # Matches ignore rule
            "provider_name": "Blocked Provider",
            "confidence": 0.8
        }
        
        # Process through reversal engine
        result = self.strategy.process_signal(signal_data)
        
        # Should be None (ignored)
        self.assertIsNone(result)
        
    def test_process_signal_disabled_strategy(self):
        """Test processing when strategy is disabled"""
        # Disable strategy
        self.strategy.config["enabled"] = False
        
        signal_data = {
            "signal_id": "test_012",
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1050,
            "volume": 0.1,
            "provider_id": "test_provider",
            "provider_name": "Test Provider",
            "confidence": 0.8
        }
        
        # Process through reversal engine
        result = self.strategy.process_signal(signal_data)
        
        # Should pass through unchanged when disabled
        self.assertEqual(result, signal_data)

class TestRuleManagement(TestReverseStrategy):
    """Test reversal rule management"""
    
    def test_add_reversal_rule(self):
        """Test adding new reversal rule"""
        initial_count = len(self.strategy.reversal_rules)
        
        new_rule = ReversalRule(
            rule_id="test_new_rule",
            name="Test New Rule",
            condition=ReversalCondition.SYMBOL_SPECIFIC,
            mode=ReversalMode.MODIFY_PARAMS,
            priority=10,
            symbols=["GBPUSD"]
        )
        
        success = self.strategy.add_reversal_rule(new_rule)
        
        self.assertTrue(success)
        self.assertEqual(len(self.strategy.reversal_rules), initial_count + 1)
        
        # Check that rules are still sorted by priority
        priorities = [rule.priority for rule in self.strategy.reversal_rules]
        self.assertEqual(priorities, sorted(priorities))
        
    def test_remove_reversal_rule(self):
        """Test removing reversal rule"""
        initial_count = len(self.strategy.reversal_rules)
        
        # Remove existing rule
        success = self.strategy.remove_reversal_rule("test_always_reverse")
        
        self.assertTrue(success)
        self.assertEqual(len(self.strategy.reversal_rules), initial_count - 1)
        
        # Verify rule is gone
        rule_ids = [rule.rule_id for rule in self.strategy.reversal_rules]
        self.assertNotIn("test_always_reverse", rule_ids)
        
        # Try to remove non-existent rule
        fail_success = self.strategy.remove_reversal_rule("non_existent")
        self.assertTrue(fail_success)  # Should not fail, just do nothing
        
    def test_enable_disable_rule(self):
        """Test enabling and disabling rules"""
        # Disable a rule
        success = self.strategy.disable_rule("test_always_reverse")
        self.assertTrue(success)
        
        # Check that rule is disabled
        rule = None
        for r in self.strategy.reversal_rules:
            if r.rule_id == "test_always_reverse":
                rule = r
                break
                
        self.assertIsNotNone(rule)
        self.assertFalse(rule.enabled)
        
        # Re-enable the rule
        success = self.strategy.enable_rule("test_always_reverse")
        self.assertTrue(success)
        self.assertTrue(rule.enabled)

class TestStatistics(TestReverseStrategy):
    """Test statistics and reporting"""
    
    def test_statistics_calculation(self):
        """Test statistics calculation"""
        # Initial statistics
        stats = self.strategy.get_statistics()
        self.assertEqual(stats["total_reversals"], 0)
        self.assertEqual(stats["successful_reversals"], 0)
        
        # Process some signals to generate statistics
        signal_data = {
            "signal_id": "test_stats",
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1050,
            "volume": 0.1,
            "provider_id": "test_provider",
            "provider_name": "Test Provider",
            "confidence": 0.8
        }
        
        # Process signal (should be reversed)
        self.strategy.process_signal(signal_data)
        
        # Check updated statistics
        updated_stats = self.strategy.get_statistics()
        self.assertEqual(updated_stats["total_reversals"], 1)
        self.assertEqual(updated_stats["successful_reversals"], 1)
        self.assertEqual(updated_stats["success_rate"], 100.0)
        
    def test_get_active_rules(self):
        """Test getting active rules list"""
        active_rules = self.strategy.get_active_rules()
        
        self.assertEqual(len(active_rules), 3)  # All test rules are enabled
        
        # Check rule structure
        first_rule = active_rules[0]
        self.assertIn("rule_id", first_rule)
        self.assertIn("name", first_rule)
        self.assertIn("condition", first_rule)
        self.assertIn("mode", first_rule)
        self.assertIn("enabled", first_rule)
        
    def test_get_recent_reversals(self):
        """Test getting recent reversal events"""
        # Initially empty
        recent = self.strategy.get_recent_reversals(5)
        self.assertEqual(len(recent), 0)
        
        # Process a signal to create reversal
        signal_data = {
            "signal_id": "test_recent",
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1050,
            "volume": 0.1,
            "provider_id": "test_provider",
            "provider_name": "Test Provider",
            "confidence": 0.8
        }
        
        self.strategy.process_signal(signal_data)
        
        # Check recent reversals
        recent = self.strategy.get_recent_reversals(5)
        self.assertEqual(len(recent), 1)
        
        reversal = recent[0]
        self.assertEqual(reversal["original_signal_id"], "test_recent")
        self.assertEqual(reversal["original_direction"], "buy")
        self.assertEqual(reversal["reversed_direction"], "sell")

if __name__ == '__main__':
    unittest.main()