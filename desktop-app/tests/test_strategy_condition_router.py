"""
Test Suite for Strategy Condition Router Engine
Tests condition evaluation, signal routing, and strategy module integration
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

from strategy_condition_router import (
    StrategyConditionRouter, ConditionRule, RoutingRule, ConditionType,
    ConditionOperator, RouteAction, MarketState, RouteDecision
)

class TestStrategyConditionRouter(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "strategy_condition_router": {
                "enabled": True,
                "monitoring_interval": 0.1,  # Fast for testing
                "market_state_update_interval": 1.0,
                "enable_fallback_routing": True,
                "default_action": "process_normal",
                "max_routing_depth": 2,
                "routing_rules": [
                    {
                        "rule_id": "test_volatility_rule",
                        "name": "Test High Volatility Rule",
                        "conditions": [
                            {
                                "rule_id": "vol_cond",
                                "name": "High Volatility",
                                "condition_type": "volatility",
                                "operator": "greater_than",
                                "value": 2.0,
                                "enabled": True,
                                "priority": 1
                            }
                        ],
                        "condition_logic": "AND",
                        "target_action": "route_to_reverse",
                        "enabled": True,
                        "priority": 1
                    },
                    {
                        "rule_id": "test_confidence_rule",
                        "name": "Test Low Confidence Rule",
                        "conditions": [
                            {
                                "rule_id": "conf_cond",
                                "name": "Low Confidence",
                                "condition_type": "confidence",
                                "operator": "less_than",
                                "value": 0.5,
                                "enabled": True,
                                "priority": 1
                            }
                        ],
                        "condition_logic": "AND",
                        "target_action": "block_signal",
                        "enabled": True,
                        "priority": 2
                    }
                ],
                "market_sessions": {
                    "asian": {"start": "21:00", "end": "06:00"},
                    "european": {"start": "07:00", "end": "16:00"},
                    "american": {"start": "13:00", "end": "22:00"}
                },
                "symbol_classifications": {
                    "major_pairs": ["EURUSD", "GBPUSD"],
                    "commodities": ["XAUUSD"],
                    "crypto": ["BTCUSD"]
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize strategy condition router
        self.router = StrategyConditionRouter(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
    def tearDown(self):
        """Clean up test environment"""
        self.router.stop_monitoring()
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
        # Clean up data file if created
        routing_file = self.temp_log.name.replace('.log', '_routing.json')
        if os.path.exists(routing_file):
            os.unlink(routing_file)

class TestBasicFunctionality(TestStrategyConditionRouter):
    """Test basic strategy condition router functionality"""
    
    def test_initialization(self):
        """Test strategy condition router initialization"""
        self.assertTrue(self.router.config['enabled'])
        self.assertEqual(self.router.config['default_action'], 'process_normal')
        self.assertEqual(len(self.router.routing_rules), 2)
        
    def test_routing_rules_loading(self):
        """Test loading of routing rules from configuration"""
        rules = self.router.routing_rules
        
        # Check that rules are sorted by priority
        self.assertEqual(rules[0].rule_id, "test_volatility_rule")
        self.assertEqual(rules[0].priority, 1)
        
        # Check rule properties
        volatility_rule = rules[0]
        self.assertEqual(volatility_rule.target_action, RouteAction.ROUTE_TO_REVERSE)
        self.assertTrue(volatility_rule.enabled)
        self.assertEqual(len(volatility_rule.conditions), 1)
        
        # Check condition properties
        condition = volatility_rule.conditions[0]
        self.assertEqual(condition.condition_type, ConditionType.VOLATILITY)
        self.assertEqual(condition.operator, ConditionOperator.GREATER_THAN)
        self.assertEqual(condition.value, 2.0)
        
    def test_market_session_determination(self):
        """Test market session determination"""
        # This test depends on the current time, so we'll just check it returns a valid session
        session = self.router._get_current_market_session()
        valid_sessions = ["asian", "european", "american", "unknown"]
        self.assertIn(session, valid_sessions)
        
    def test_volatility_calculation(self):
        """Test volatility score calculation"""
        # Test known symbols
        xauusd_vol = self.router._calculate_volatility_score("XAUUSD")
        eurusd_vol = self.router._calculate_volatility_score("EURUSD")
        
        # Gold should have higher volatility than EUR/USD
        self.assertGreater(xauusd_vol, eurusd_vol)
        
        # Test unknown symbol
        unknown_vol = self.router._calculate_volatility_score("UNKNOWN")
        self.assertEqual(unknown_vol, 1.0)  # Default value

class TestConditionEvaluation(TestStrategyConditionRouter):
    """Test condition evaluation functionality"""
    
    def test_volatility_condition_evaluation(self):
        """Test volatility condition evaluation"""
        condition = ConditionRule(
            rule_id="test_vol",
            name="Test Volatility",
            condition_type=ConditionType.VOLATILITY,
            operator=ConditionOperator.GREATER_THAN,
            value=2.0,
            enabled=True
        )
        
        # Test with high volatility symbol
        signal_data = {"symbol": "XAUUSD"}
        result = self.router._evaluate_condition(condition, signal_data)
        self.assertTrue(result)  # XAUUSD volatility (2.5) > 2.0
        
        # Test with low volatility symbol
        signal_data = {"symbol": "EURUSD"}
        result = self.router._evaluate_condition(condition, signal_data)
        self.assertFalse(result)  # EURUSD volatility (1.0) < 2.0
        
    def test_confidence_condition_evaluation(self):
        """Test confidence condition evaluation"""
        condition = ConditionRule(
            rule_id="test_conf",
            name="Test Confidence",
            condition_type=ConditionType.CONFIDENCE,
            operator=ConditionOperator.GREATER_THAN,
            value=0.7,
            enabled=True
        )
        
        # Test with high confidence
        signal_data = {"confidence": 0.9}
        result = self.router._evaluate_condition(condition, signal_data)
        self.assertTrue(result)
        
        # Test with low confidence
        signal_data = {"confidence": 0.5}
        result = self.router._evaluate_condition(condition, signal_data)
        self.assertFalse(result)
        
    def test_symbol_type_condition_evaluation(self):
        """Test symbol type condition evaluation"""
        condition = ConditionRule(
            rule_id="test_symbol",
            name="Test Symbol Type",
            condition_type=ConditionType.SYMBOL_TYPE,
            operator=ConditionOperator.EQUALS,
            value="major_pairs",
            enabled=True
        )
        
        # Test with major pair
        signal_data = {"symbol": "EURUSD"}
        result = self.router._evaluate_condition(condition, signal_data)
        self.assertTrue(result)
        
        # Test with commodity
        signal_data = {"symbol": "XAUUSD"}
        result = self.router._evaluate_condition(condition, signal_data)
        self.assertFalse(result)
        
    def test_provider_condition_evaluation(self):
        """Test provider condition evaluation"""
        condition = ConditionRule(
            rule_id="test_provider",
            name="Test Provider",
            condition_type=ConditionType.PROVIDER,
            operator=ConditionOperator.EQUALS,
            value="premium_provider",
            enabled=True
        )
        
        # Test matching provider
        signal_data = {"provider_id": "premium_provider"}
        result = self.router._evaluate_condition(condition, signal_data)
        self.assertTrue(result)
        
        # Test non-matching provider
        signal_data = {"provider_id": "standard_provider"}
        result = self.router._evaluate_condition(condition, signal_data)
        self.assertFalse(result)
        
    def test_disabled_condition_evaluation(self):
        """Test that disabled conditions always pass"""
        condition = ConditionRule(
            rule_id="test_disabled",
            name="Test Disabled",
            condition_type=ConditionType.CONFIDENCE,
            operator=ConditionOperator.GREATER_THAN,
            value=0.9,
            enabled=False  # Disabled
        )
        
        # Should pass even with low confidence
        signal_data = {"confidence": 0.1}
        result = self.router._evaluate_condition(condition, signal_data)
        self.assertTrue(result)

class TestRoutingRuleEvaluation(TestStrategyConditionRouter):
    """Test routing rule evaluation"""
    
    def test_single_condition_rule_evaluation(self):
        """Test routing rule with single condition"""
        # Use the volatility rule from config
        volatility_rule = self.router.routing_rules[0]  # test_volatility_rule
        
        # Test with high volatility symbol
        signal_data = {"symbol": "XAUUSD"}
        applies, conditions_met = self.router._evaluate_routing_rule(volatility_rule, signal_data)
        
        self.assertTrue(applies)
        self.assertEqual(len(conditions_met), 1)
        self.assertIn("High Volatility", conditions_met)
        
        # Test with low volatility symbol
        signal_data = {"symbol": "EURUSD"}
        applies, conditions_met = self.router._evaluate_routing_rule(volatility_rule, signal_data)
        
        self.assertFalse(applies)
        self.assertEqual(len(conditions_met), 0)
        
    def test_multiple_condition_rule_evaluation(self):
        """Test routing rule with multiple conditions (AND logic)"""
        # Create a rule with multiple conditions
        conditions = [
            ConditionRule(
                rule_id="vol_cond",
                name="High Volatility",
                condition_type=ConditionType.VOLATILITY,
                operator=ConditionOperator.GREATER_THAN,
                value=1.5,
                enabled=True
            ),
            ConditionRule(
                rule_id="conf_cond",
                name="High Confidence",
                condition_type=ConditionType.CONFIDENCE,
                operator=ConditionOperator.GREATER_THAN,
                value=0.7,
                enabled=True
            )
        ]
        
        rule = RoutingRule(
            rule_id="test_multi",
            name="Test Multiple Conditions",
            conditions=conditions,
            condition_logic="AND",
            target_action=RouteAction.ESCALATE_PRIORITY,
            enabled=True,
            priority=1
        )
        
        # Test with both conditions met
        signal_data = {"symbol": "XAUUSD", "confidence": 0.9}
        applies, conditions_met = self.router._evaluate_routing_rule(rule, signal_data)
        
        self.assertTrue(applies)
        self.assertEqual(len(conditions_met), 2)
        
        # Test with only one condition met
        signal_data = {"symbol": "XAUUSD", "confidence": 0.5}
        applies, conditions_met = self.router._evaluate_routing_rule(rule, signal_data)
        
        self.assertFalse(applies)
        self.assertEqual(len(conditions_met), 1)
        
    def test_disabled_rule_evaluation(self):
        """Test that disabled rules don't apply"""
        rule = self.router.routing_rules[0]  # test_volatility_rule
        rule.enabled = False
        
        signal_data = {"symbol": "XAUUSD"}  # Should normally trigger the rule
        applies, conditions_met = self.router._evaluate_routing_rule(rule, signal_data)
        
        self.assertFalse(applies)
        self.assertEqual(len(conditions_met), 0)
        
        # Re-enable for other tests
        rule.enabled = True

class TestRouteActions(TestStrategyConditionRouter):
    """Test route action execution"""
    
    def test_process_normal_action(self):
        """Test normal processing action"""
        async def run_test():
            signal_data = {"signal_id": "test_001", "symbol": "EURUSD"}
            
            result = await self.router._execute_route_action(
                RouteAction.PROCESS_NORMAL, signal_data
            )
            
            self.assertEqual(result, signal_data)  # Should pass through unchanged
            
        asyncio.run(run_test())
        
    def test_block_signal_action(self):
        """Test signal blocking action"""
        async def run_test():
            signal_data = {"signal_id": "test_002", "symbol": "EURUSD"}
            
            result = await self.router._execute_route_action(
                RouteAction.BLOCK_SIGNAL, signal_data
            )
            
            self.assertIsNone(result)  # Signal should be blocked
            
        asyncio.run(run_test())
        
    def test_escalate_priority_action(self):
        """Test priority escalation action"""
        async def run_test():
            signal_data = {
                "signal_id": "test_003",
                "symbol": "EURUSD",
                "confidence": 0.6
            }
            
            result = await self.router._execute_route_action(
                RouteAction.ESCALATE_PRIORITY, signal_data
            )
            
            self.assertIsNotNone(result)
            self.assertGreater(result['confidence'], 0.6)  # Confidence should be increased
            self.assertTrue(result['priority_escalated'])
            
        asyncio.run(run_test())
        
    def test_delay_signal_action(self):
        """Test signal delay action"""
        async def run_test():
            signal_data = {"signal_id": "test_004", "symbol": "EURUSD"}
            params = {"delay_minutes": 10}
            
            result = await self.router._execute_route_action(
                RouteAction.DELAY_SIGNAL, signal_data, params
            )
            
            self.assertIsNotNone(result)
            self.assertIn('process_after', result)
            
            # Check that delay time is set correctly
            process_after = datetime.fromisoformat(result['process_after'])
            expected_time = datetime.now() + timedelta(minutes=10)
            time_diff = abs((process_after - expected_time).total_seconds())
            self.assertLess(time_diff, 60)  # Within 1 minute tolerance
            
        asyncio.run(run_test())
        
    def test_split_signal_action(self):
        """Test signal splitting action"""
        async def run_test():
            signal_data = {
                "signal_id": "test_005",
                "symbol": "EURUSD",
                "volume": 0.4
            }
            params = {"split_count": 2}
            
            result = await self.router._execute_route_action(
                RouteAction.SPLIT_SIGNAL, signal_data, params
            )
            
            self.assertIsNotNone(result)
            self.assertEqual(result['volume'], 0.2)  # Half of original volume
            self.assertTrue(result['split_info']['is_split'])
            self.assertEqual(result['split_info']['split_count'], 2)
            self.assertEqual(result['split_info']['original_volume'], 0.4)
            
        asyncio.run(run_test())

class TestSignalRouting(TestStrategyConditionRouter):
    """Test complete signal routing workflow"""
    
    def test_route_signal_with_matching_rule(self):
        """Test routing signal that matches a rule"""
        async def run_test():
            # Signal that should trigger volatility rule (route to reverse)
            signal_data = {
                "signal_id": "test_route_001",
                "symbol": "XAUUSD",  # High volatility
                "direction": "buy",
                "confidence": 0.8
            }
            
            result = await self.router.route_signal(signal_data)
            
            # Result depends on whether reverse strategy module is available
            # Since we don't have the actual module, it should pass through
            self.assertIsNotNone(result)
            
        asyncio.run(run_test())
        
    def test_route_signal_block(self):
        """Test routing signal that gets blocked"""
        async def run_test():
            # Signal with low confidence should be blocked
            signal_data = {
                "signal_id": "test_route_002",
                "symbol": "EURUSD",
                "direction": "buy",
                "confidence": 0.3  # Below 0.5 threshold
            }
            
            result = await self.router.route_signal(signal_data)
            
            self.assertIsNone(result)  # Should be blocked
            
        asyncio.run(run_test())
        
    def test_route_signal_no_matching_rule(self):
        """Test routing signal with no matching rule (default action)"""
        async def run_test():
            # Signal that doesn't match any rule
            signal_data = {
                "signal_id": "test_route_003",
                "symbol": "EURUSD",  # Low volatility
                "direction": "buy",
                "confidence": 0.8  # High confidence
            }
            
            result = await self.router.route_signal(signal_data)
            
            self.assertEqual(result, signal_data)  # Should pass through unchanged
            
        asyncio.run(run_test())
        
    def test_route_signal_disabled_router(self):
        """Test routing when router is disabled"""
        async def run_test():
            # Disable router
            self.router.config["enabled"] = False
            
            signal_data = {
                "signal_id": "test_route_004",
                "symbol": "XAUUSD",
                "direction": "buy",
                "confidence": 0.8
            }
            
            result = await self.router.route_signal(signal_data)
            
            self.assertEqual(result, signal_data)  # Should pass through unchanged
            
            # Re-enable for other tests
            self.router.config["enabled"] = True
            
        asyncio.run(run_test())

class TestStatisticsAndReporting(TestStrategyConditionRouter):
    """Test statistics and reporting functionality"""
    
    def test_routing_statistics_initial(self):
        """Test initial routing statistics"""
        stats = self.router.get_routing_statistics()
        
        self.assertEqual(stats['total_signals'], 0)
        self.assertEqual(stats['successful_routes'], 0)
        self.assertEqual(stats['failed_routes'], 0)
        self.assertEqual(stats['active_rules'], 2)  # Both test rules are enabled
        self.assertEqual(stats['total_rules'], 2)
        
    def test_routing_statistics_after_processing(self):
        """Test routing statistics after processing signals"""
        async def run_test():
            # Process a few signals
            signals = [
                {"signal_id": "stat_001", "symbol": "XAUUSD", "confidence": 0.8},
                {"signal_id": "stat_002", "symbol": "EURUSD", "confidence": 0.3},  # Should be blocked
                {"signal_id": "stat_003", "symbol": "EURUSD", "confidence": 0.8}
            ]
            
            for signal in signals:
                await self.router.route_signal(signal)
                
            stats = self.router.get_routing_statistics()
            
            self.assertEqual(stats['total_signals'], 3)
            self.assertGreater(stats['successful_routes'], 0)
            self.assertEqual(stats['blocked_signals'], 1)  # One signal should be blocked
            
        asyncio.run(run_test())
        
    def test_get_recent_decisions(self):
        """Test getting recent routing decisions"""
        async def run_test():
            # Process some signals to generate decisions
            signal_data = {
                "signal_id": "decision_001",
                "symbol": "XAUUSD",
                "confidence": 0.8
            }
            
            await self.router.route_signal(signal_data)
            
            decisions = self.router.get_recent_decisions(5)
            
            self.assertEqual(len(decisions), 1)
            decision = decisions[0]
            self.assertEqual(decision['signal_id'], 'decision_001')
            self.assertIn('routed_action', decision)
            self.assertIn('execution_time', decision)
            
        asyncio.run(run_test())

class TestRuleManagement(TestStrategyConditionRouter):
    """Test routing rule management"""
    
    def test_add_routing_rule(self):
        """Test adding new routing rule"""
        initial_count = len(self.router.routing_rules)
        
        # Create new rule
        condition = ConditionRule(
            rule_id="new_cond",
            name="New Condition",
            condition_type=ConditionType.VOLUME,
            operator=ConditionOperator.GREATER_THAN,
            value=0.5,
            enabled=True
        )
        
        new_rule = RoutingRule(
            rule_id="new_rule",
            name="New Test Rule",
            conditions=[condition],
            target_action=RouteAction.ESCALATE_PRIORITY,
            enabled=True,
            priority=10
        )
        
        success = self.router.add_routing_rule(new_rule)
        
        self.assertTrue(success)
        self.assertEqual(len(self.router.routing_rules), initial_count + 1)
        
        # Check that rules are still sorted by priority
        priorities = [rule.priority for rule in self.router.routing_rules]
        self.assertEqual(priorities, sorted(priorities))
        
    def test_remove_routing_rule(self):
        """Test removing routing rule"""
        initial_count = len(self.router.routing_rules)
        
        # Remove existing rule
        success = self.router.remove_routing_rule("test_volatility_rule")
        
        self.assertTrue(success)
        self.assertEqual(len(self.router.routing_rules), initial_count - 1)
        
        # Verify rule is gone
        rule_ids = [rule.rule_id for rule in self.router.routing_rules]
        self.assertNotIn("test_volatility_rule", rule_ids)

if __name__ == '__main__':
    unittest.main()