"""
Test suite for Strategy Runtime Engine
Tests strategy evaluation, rule processing, and signal modification
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from strategy_runtime import (
    StrategyRuntime, Strategy, StrategyRule, Condition, Action,
    ConditionType, ActionType, SignalContext
)

class TestStrategyRuntime(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        
        self.runtime = StrategyRuntime(self.config_file)
        
        # Sample signal for testing
        self.sample_signal = {
            "id": 123,
            "symbol": "EURUSD",
            "action": "BUY",
            "entry": 1.1000,
            "stop_loss": 1.0950,
            "take_profit_1": 1.1050,
            "take_profit_2": 1.1100,
            "lot_size": 0.01,
            "confidence": 85.5,
            "created_at": datetime.now().isoformat()
        }
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_default_strategy_creation(self):
        """Test creation of default strategy"""
        strategy = self.runtime.create_default_strategy()
        
        self.assertEqual(strategy.id, "default_conservative")
        self.assertGreater(len(strategy.rules), 0)
        self.assertEqual(self.runtime.current_strategy, strategy)
    
    def test_confidence_filter_rule(self):
        """Test confidence threshold filtering"""
        strategy = self.runtime.create_default_strategy()
        
        # Test signal with low confidence (should be skipped)
        low_confidence_signal = self.sample_signal.copy()
        low_confidence_signal["confidence"] = 50.0
        
        result = self.runtime.evaluate_signal(low_confidence_signal)
        
        self.assertEqual(result["action"], "skip_trade")
        self.assertIn("Low confidence", result["parameters"]["reason"])
    
    def test_high_confidence_signal_passes(self):
        """Test that high confidence signals pass through"""
        strategy = self.runtime.create_default_strategy()
        
        # Test signal with high confidence
        high_confidence_signal = self.sample_signal.copy()
        high_confidence_signal["confidence"] = 90.0
        
        result = self.runtime.evaluate_signal(high_confidence_signal)
        
        # Should not be skipped due to confidence
        applied_rules = [rule["rule_name"] for rule in result["applied_rules"]]
        self.assertNotIn("Confidence Filter", applied_rules)
    
    def test_time_filter_rule(self):
        """Test time-based filtering"""
        # Create strategy with specific time filter
        time_rule = StrategyRule(
            id="time_test",
            name="Time Filter Test",
            condition=Condition(
                type=ConditionType.TIME_FILTER,
                parameters={"allowed_hours": [9, 10, 11]},  # Only 9-11 AM
                description="Test time filter"
            ),
            action=Action(
                type=ActionType.EXECUTE_NORMAL,
                parameters={},
                description="Execute if time matches"
            ),
            priority=100
        )
        
        strategy = Strategy(
            id="time_test_strategy",
            name="Time Test Strategy",
            description="Test strategy for time filtering",
            rules=[time_rule],
            global_settings={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.runtime.current_strategy = strategy
        
        # Mock datetime to test specific hours
        # This would require more complex mocking in a real test
        result = self.runtime.evaluate_signal(self.sample_signal)
        
        # Should evaluate the time rule
        self.assertIsNotNone(result)
    
    def test_lot_size_scaling(self):
        """Test lot size scaling action"""
        # Create strategy with lot size scaling
        scaling_rule = StrategyRule(
            id="scale_test",
            name="Scale Lot Size",
            condition=Condition(
                type=ConditionType.CONFIDENCE_THRESHOLD,
                parameters={"min_confidence": 0.0},  # Always true
                description="Always scale"
            ),
            action=Action(
                type=ActionType.SCALE_LOT_SIZE,
                parameters={"scale_factor": 0.5},
                description="Scale lot size by 50%"
            ),
            priority=100
        )
        
        strategy = Strategy(
            id="scale_test_strategy",
            name="Scale Test Strategy",
            description="Test strategy for lot scaling",
            rules=[scaling_rule],
            global_settings={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.runtime.current_strategy = strategy
        
        result = self.runtime.evaluate_signal(self.sample_signal)
        
        # Check that lot size was scaled
        original_lot = self.sample_signal["lot_size"]
        scaled_lot = result["signal"]["lot_size"]
        self.assertEqual(scaled_lot, original_lot * 0.5)
    
    def test_symbol_filter(self):
        """Test symbol filtering"""
        # Create strategy that blocks EURUSD
        symbol_rule = StrategyRule(
            id="symbol_test",
            name="Symbol Filter",
            condition=Condition(
                type=ConditionType.SYMBOL_FILTER,
                parameters={"blocked_symbols": ["EURUSD"]},
                description="Block EURUSD"
            ),
            action=Action(
                type=ActionType.SKIP_TRADE,
                parameters={"reason": "Symbol blocked"},
                description="Skip blocked symbol"
            ),
            priority=100
        )
        
        strategy = Strategy(
            id="symbol_test_strategy",
            name="Symbol Test Strategy",
            description="Test strategy for symbol filtering",
            rules=[symbol_rule],
            global_settings={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.runtime.current_strategy = strategy
        
        result = self.runtime.evaluate_signal(self.sample_signal)
        
        # EURUSD should be blocked
        self.assertEqual(result["action"], "skip_trade")
    
    def test_risk_management_rule(self):
        """Test risk management calculations"""
        context = SignalContext(
            signal_data=self.sample_signal,
            account_info={"balance": 1000}  # Small balance for high risk
        )
        
        # Create risk management rule
        risk_rule = StrategyRule(
            id="risk_test",
            name="Risk Management",
            condition=Condition(
                type=ConditionType.RISK_MANAGEMENT,
                parameters={"max_risk_percent": 1.0},  # Very low risk tolerance
                description="Limit risk to 1%"
            ),
            action=Action(
                type=ActionType.SCALE_LOT_SIZE,
                parameters={"scale_factor": 0.1},
                description="Reduce lot size for high risk"
            ),
            priority=100
        )
        
        strategy = Strategy(
            id="risk_test_strategy",
            name="Risk Test Strategy",
            description="Test strategy for risk management",
            rules=[risk_rule],
            global_settings={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.runtime.current_strategy = strategy
        
        result = self.runtime.evaluate_signal(self.sample_signal, context)
        
        # Should apply risk management
        self.assertIn("Risk Management", [rule["rule_name"] for rule in result["applied_rules"]])
    
    def test_move_sl_to_entry_action(self):
        """Test moving stop loss to entry"""
        # Create rule that moves SL to entry
        sl_rule = StrategyRule(
            id="sl_test",
            name="Move SL to Entry",
            condition=Condition(
                type=ConditionType.CONFIDENCE_THRESHOLD,
                parameters={"min_confidence": 0.0},  # Always true
                description="Always move SL"
            ),
            action=Action(
                type=ActionType.MOVE_SL_TO_ENTRY,
                parameters={},
                description="Move SL to break-even"
            ),
            priority=100
        )
        
        strategy = Strategy(
            id="sl_test_strategy",
            name="SL Test Strategy",
            description="Test strategy for SL movement",
            rules=[sl_rule],
            global_settings={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.runtime.current_strategy = strategy
        
        result = self.runtime.evaluate_signal(self.sample_signal)
        
        # Stop loss should be moved to entry price
        self.assertEqual(result["signal"]["stop_loss"], self.sample_signal["entry"])
    
    def test_custom_logic_condition(self):
        """Test custom logic evaluation"""
        # Create rule with custom logic
        custom_rule = StrategyRule(
            id="custom_test",
            name="Custom Logic Test",
            condition=Condition(
                type=ConditionType.CUSTOM_LOGIC,
                parameters={"code": "signal['confidence'] > 80 and signal['symbol'] == 'EURUSD'"},
                description="Custom condition"
            ),
            action=Action(
                type=ActionType.EXECUTE_NORMAL,
                parameters={},
                description="Execute if custom condition met"
            ),
            priority=100
        )
        
        strategy = Strategy(
            id="custom_test_strategy",
            name="Custom Test Strategy",
            description="Test strategy for custom logic",
            rules=[custom_rule],
            global_settings={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.runtime.current_strategy = strategy
        
        # Test with matching signal
        matching_signal = self.sample_signal.copy()
        matching_signal["confidence"] = 85.0
        matching_signal["symbol"] = "EURUSD"
        
        result = self.runtime.evaluate_signal(matching_signal)
        
        # Custom rule should be applied
        applied_rules = [rule["rule_name"] for rule in result["applied_rules"]]
        self.assertIn("Custom Logic Test", applied_rules)
    
    def test_rule_priority_ordering(self):
        """Test that rules are executed in priority order"""
        # Create two rules with different priorities
        low_priority_rule = StrategyRule(
            id="low_priority",
            name="Low Priority Rule",
            condition=Condition(
                type=ConditionType.CONFIDENCE_THRESHOLD,
                parameters={"min_confidence": 0.0},
                description="Always true"
            ),
            action=Action(
                type=ActionType.SCALE_LOT_SIZE,
                parameters={"scale_factor": 2.0},
                description="Double lot size"
            ),
            priority=10
        )
        
        high_priority_rule = StrategyRule(
            id="high_priority",
            name="High Priority Rule",
            condition=Condition(
                type=ConditionType.CONFIDENCE_THRESHOLD,
                parameters={"min_confidence": 0.0},
                description="Always true"
            ),
            action=Action(
                type=ActionType.SCALE_LOT_SIZE,
                parameters={"scale_factor": 0.5},
                description="Half lot size"
            ),
            priority=100
        )
        
        strategy = Strategy(
            id="priority_test_strategy",
            name="Priority Test Strategy",
            description="Test strategy for rule priority",
            rules=[low_priority_rule, high_priority_rule],  # Order shouldn't matter
            global_settings={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.runtime.current_strategy = strategy
        
        result = self.runtime.evaluate_signal(self.sample_signal)
        
        # High priority rule should be applied first, then low priority
        # Final lot size should be: 0.01 * 0.5 * 2.0 = 0.01
        expected_lot = self.sample_signal["lot_size"] * 0.5 * 2.0
        self.assertEqual(result["signal"]["lot_size"], expected_lot)
    
    def test_strategy_export_import(self):
        """Test strategy export and import"""
        strategy = self.runtime.create_default_strategy()
        
        # Export strategy
        exported_json = self.runtime.export_strategy(strategy)
        self.assertIsInstance(exported_json, str)
        
        # Import strategy
        imported_strategy = self.runtime.import_strategy(exported_json)
        
        self.assertEqual(imported_strategy.id, strategy.id)
        self.assertEqual(imported_strategy.name, strategy.name)
        self.assertEqual(len(imported_strategy.rules), len(strategy.rules))
    
    def test_strategy_performance_tracking(self):
        """Test strategy performance metrics"""
        strategy = self.runtime.create_default_strategy()
        
        # Process several signals
        for i in range(5):
            test_signal = self.sample_signal.copy()
            test_signal["id"] = i
            self.runtime.evaluate_signal(test_signal)
        
        performance = self.runtime.get_strategy_performance()
        
        self.assertEqual(performance["total_signals"], 5)
        self.assertIn("actions_taken", performance)
        self.assertEqual(performance["strategy_id"], strategy.id)

class TestSignalContext(unittest.TestCase):
    """Test SignalContext functionality"""
    
    def test_signal_context_creation(self):
        """Test creating signal context with different data"""
        signal_data = {"symbol": "EURUSD", "action": "BUY"}
        market_data = {"current_price": 1.1000, "spread": 1.5}
        account_info = {"balance": 10000, "equity": 9800}
        
        context = SignalContext(
            signal_data=signal_data,
            market_data=market_data,
            account_info=account_info
        )
        
        self.assertEqual(context.signal_data, signal_data)
        self.assertEqual(context.market_data, market_data)
        self.assertEqual(context.account_info, account_info)

if __name__ == '__main__':
    unittest.main(verbosity=2)