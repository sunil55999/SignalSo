"""
Tests for TP Adjustor module
"""

import pytest
import json
import tempfile
import os
from unittest.mock import MagicMock
from datetime import datetime
from desktop_app.tp_adjustor import TPAdjustor, TPAdjustmentType, adjust_tp


class TestTPAdjustor:
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Create test config
        test_config = {
            'tp_adjustor': {
                'enabled': True,
                'default_pip_adjustment': 5.0,
                'default_rr_ratio': 2.0,
                'override_enabled': True,
                'log_adjustments': True,
                'pip_values': {
                    'EURUSD': 0.0001,
                    'GBPUSD': 0.0001,
                    'USDJPY': 0.01,
                    'XAUUSD': 0.1,
                    'default': 0.0001
                },
                'adjustment_rules': [
                    {
                        'symbol_pattern': 'EUR*',
                        'adjustment_type': 'pips_addition',
                        'value': 10.0,
                        'enabled': True,
                        'priority': 10
                    },
                    {
                        'symbol_pattern': 'GOLD',
                        'adjustment_type': 'rr_ratio',
                        'value': 3.0,
                        'enabled': True,
                        'priority': 20
                    },
                    {
                        'symbol_pattern': 'default',
                        'adjustment_type': 'pips_addition',
                        'value': 5.0,
                        'enabled': True,
                        'priority': 0
                    }
                ]
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        self.temp_log.close()
        
        self.tp_adjustor = TPAdjustor(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def teardown_method(self):
        """Cleanup test files"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_adjust_tp_by_pips_buy(self):
        """Test TP adjustment by pips for BUY trades"""
        original_tp = 1.1050
        pips_to_add = 10.0
        symbol = "EURUSD"
        action = "BUY"
        
        adjusted_tp = self.tp_adjustor.adjust_tp_by_pips(original_tp, pips_to_add, symbol, action)
        
        expected_tp = original_tp + (10.0 * 0.0001)  # 10 pips for EURUSD
        assert abs(adjusted_tp - expected_tp) < 1e-6, f"Expected {expected_tp}, got {adjusted_tp}"
    
    def test_adjust_tp_by_pips_sell(self):
        """Test TP adjustment by pips for SELL trades"""
        original_tp = 1.1000
        pips_to_add = 10.0
        symbol = "EURUSD"
        action = "SELL"
        
        adjusted_tp = self.tp_adjustor.adjust_tp_by_pips(original_tp, pips_to_add, symbol, action)
        
        expected_tp = original_tp - (10.0 * 0.0001)  # 10 pips for EURUSD
        assert abs(adjusted_tp - expected_tp) < 1e-6, f"Expected {expected_tp}, got {adjusted_tp}"
    
    def test_adjust_tp_by_rr_ratio(self):
        """Test TP adjustment by risk-reward ratio"""
        entry_price = 1.1025
        stop_loss = 1.1000  # 25 pips risk
        rr_ratio = 2.0
        action = "BUY"
        
        adjusted_tp = self.tp_adjustor.adjust_tp_by_rr(entry_price, stop_loss, rr_ratio, action)
        
        risk_distance = abs(entry_price - stop_loss)  # 0.0025
        expected_tp = entry_price + (risk_distance * rr_ratio)  # 1.1025 + 0.005 = 1.1075
        
        assert abs(adjusted_tp - expected_tp) < 1e-6, f"Expected {expected_tp}, got {adjusted_tp}"
    
    def test_adjust_tp_by_rr_ratio_sell(self):
        """Test TP adjustment by R:R ratio for SELL trades"""
        entry_price = 1.1025
        stop_loss = 1.1050  # 25 pips risk
        rr_ratio = 2.0
        action = "SELL"
        
        adjusted_tp = self.tp_adjustor.adjust_tp_by_rr(entry_price, stop_loss, rr_ratio, action)
        
        risk_distance = abs(entry_price - stop_loss)  # 0.0025
        expected_tp = entry_price - (risk_distance * rr_ratio)  # 1.1025 - 0.005 = 1.0975
        
        assert abs(adjusted_tp - expected_tp) < 1e-6, f"Expected {expected_tp}, got {adjusted_tp}"
    
    def test_adjust_tp_by_percentage(self):
        """Test TP adjustment by percentage"""
        original_tp = 1.1100
        entry_price = 1.1000
        percentage = 20.0  # 20% increase
        action = "BUY"
        
        adjusted_tp = self.tp_adjustor.adjust_tp_by_percentage(original_tp, entry_price, percentage, action)
        
        tp_distance = abs(original_tp - entry_price)  # 0.01
        adjustment = tp_distance * (percentage / 100.0)  # 0.002
        expected_tp = original_tp + adjustment  # 1.1100 + 0.002 = 1.1120
        
        assert abs(adjusted_tp - expected_tp) < 1e-6, f"Expected {expected_tp}, got {adjusted_tp}"
    
    def test_process_tp_adjustment_pips_rule(self):
        """Test TP adjustment processing with pips rule"""
        signal_data = {
            'symbol': 'EURUSD',
            'action': 'BUY',
            'entry': 1.1000,
            'takeProfit1': 1.1050,
            'stopLoss': 1.0975
        }
        
        result = self.tp_adjustor.process_tp_adjustment(signal_data)
        
        assert result.original_tp == 1.1050
        assert result.adjustment_type == TPAdjustmentType.PIPS_ADDITION
        assert result.adjustment_pips == 10.0  # EUR* rule with 10 pips
        
        # Verify adjusted TP
        expected_tp = 1.1050 + (10.0 * 0.0001)  # Add 10 pips
        assert abs(result.adjusted_tp - expected_tp) < 1e-6
    
    def test_process_tp_adjustment_rr_rule(self):
        """Test TP adjustment processing with R:R rule"""
        signal_data = {
            'symbol': 'GOLD',
            'action': 'BUY',
            'entry': 2000.0,
            'takeProfit1': 2010.0,
            'stopLoss': 1990.0
        }
        
        result = self.tp_adjustor.process_tp_adjustment(signal_data)
        
        assert result.original_tp == 2010.0
        assert result.adjustment_type == TPAdjustmentType.RR_RATIO
        
        # GOLD rule uses 3:1 R:R ratio
        risk_distance = abs(2000.0 - 1990.0)  # 10.0
        expected_tp = 2000.0 + (risk_distance * 3.0)  # 2000 + 30 = 2030
        assert abs(result.adjusted_tp - expected_tp) < 1e-6
    
    def test_process_tp_adjustment_strategy_override(self):
        """Test TP adjustment with strategy override"""
        signal_data = {
            'symbol': 'GBPUSD',
            'action': 'BUY',
            'entry': 1.2500,
            'takeProfit1': 1.2550,
            'stopLoss': 1.2450
        }
        
        strategy_config = {
            'tp_override_enabled': True,
            'tp_override_value': 1.2600
        }
        
        result = self.tp_adjustor.process_tp_adjustment(signal_data, strategy_config)
        
        assert result.original_tp == 1.2550
        assert result.adjusted_tp == 1.2600
        assert result.adjustment_type == TPAdjustmentType.STRATEGY_OVERRIDE
        assert "override" in result.reason.lower()
    
    def test_process_tp_adjustment_no_tp_provided(self):
        """Test TP adjustment when no TP is provided"""
        signal_data = {
            'symbol': 'EURUSD',
            'action': 'BUY',
            'entry': 1.1000,
            'stopLoss': 1.0975
            # No takeProfit1
        }
        
        result = self.tp_adjustor.process_tp_adjustment(signal_data)
        
        assert result.original_tp is None
        assert result.adjusted_tp is None
        assert "No original TP provided" in result.reason
    
    def test_process_tp_adjustment_no_sl_for_rr(self):
        """Test R:R adjustment when no stop loss provided"""
        # Configure for R:R adjustment
        self.tp_adjustor.adjustment_rules[0].adjustment_type = TPAdjustmentType.RR_RATIO
        self.tp_adjustor.adjustment_rules[0].value = 2.0
        
        signal_data = {
            'symbol': 'EURUSD',
            'action': 'BUY',
            'entry': 1.1000,
            'takeProfit1': 1.1050
            # No stopLoss
        }
        
        result = self.tp_adjustor.process_tp_adjustment(signal_data)
        
        assert result.adjusted_tp == 1.1050  # Should remain unchanged
        assert "No stop loss provided" in result.reason
    
    def test_process_tp_adjustment_disabled(self):
        """Test TP adjustment when disabled"""
        self.tp_adjustor.config['enabled'] = False
        
        signal_data = {
            'symbol': 'EURUSD',
            'action': 'BUY',
            'entry': 1.1000,
            'takeProfit1': 1.1050,
            'stopLoss': 1.0975
        }
        
        result = self.tp_adjustor.process_tp_adjustment(signal_data)
        
        assert result.original_tp == 1.1050
        assert result.adjusted_tp == 1.1050  # No change
        assert result.adjustment_pips == 0.0
        assert "disabled" in result.reason.lower()
    
    def test_get_pip_value(self):
        """Test pip value calculation for different symbols"""
        assert self.tp_adjustor._get_pip_value('EURUSD') == 0.0001
        assert self.tp_adjustor._get_pip_value('USDJPY') == 0.01
        assert self.tp_adjustor._get_pip_value('XAUUSD') == 0.1
        assert self.tp_adjustor._get_pip_value('UNKNOWN') == 0.0001  # Default
    
    def test_pattern_matching(self):
        """Test symbol pattern matching"""
        # Exact match
        assert self.tp_adjustor._match_pattern('EURUSD', 'EURUSD') == True
        assert self.tp_adjustor._match_pattern('GBPUSD', 'EURUSD') == False
        
        # Wildcard patterns
        assert self.tp_adjustor._match_pattern('EURUSD', 'EUR*') == True
        assert self.tp_adjustor._match_pattern('EURJPY', 'EUR*') == True
        assert self.tp_adjustor._match_pattern('GBPUSD', 'EUR*') == False
        
        assert self.tp_adjustor._match_pattern('XAUUSD', '*USD') == True
        assert self.tp_adjustor._match_pattern('EURJPY', '*USD') == False
        
        # Default pattern
        assert self.tp_adjustor._match_pattern('ANYSYMBOL', 'DEFAULT') == True
    
    def test_rule_priority(self):
        """Test rule priority system"""
        # GOLD rule has priority 20, EUR* has priority 10
        # Test that GOLD rule takes precedence for XAUUSD (GOLD pattern)
        
        signal_data = {
            'symbol': 'XAUUSD',  # Matches both GOLD and default patterns
            'action': 'BUY',
            'entry': 2000.0,
            'takeProfit1': 2010.0,
            'stopLoss': 1990.0
        }
        
        result = self.tp_adjustor.process_tp_adjustment(signal_data)
        
        # Should use GOLD rule (R:R ratio 3.0) not default rule
        assert result.adjustment_type == TPAdjustmentType.RR_RATIO
        
        # Verify the GOLD rule was applied
        risk_distance = abs(2000.0 - 1990.0)  # 10.0
        expected_tp = 2000.0 + (risk_distance * 3.0)  # 2030.0
        assert abs(result.adjusted_tp - expected_tp) < 1e-6
    
    def test_add_adjustment_rule(self):
        """Test adding new adjustment rules"""
        initial_count = len(self.tp_adjustor.adjustment_rules)
        
        success = self.tp_adjustor.add_adjustment_rule(
            symbol_pattern="BTC*",
            adjustment_type="percentage",
            value=15.0,
            priority=50
        )
        
        assert success == True
        assert len(self.tp_adjustor.adjustment_rules) == initial_count + 1
        
        # Test the new rule
        signal_data = {
            'symbol': 'BTCUSD',
            'action': 'BUY',
            'entry': 50000.0,
            'takeProfit1': 51000.0,
            'stopLoss': 49000.0
        }
        
        result = self.tp_adjustor.process_tp_adjustment(signal_data)
        assert result.adjustment_type == TPAdjustmentType.PERCENTAGE
    
    def test_get_adjustment_statistics(self):
        """Test TP adjustment statistics"""
        # Process several adjustments
        test_signals = [
            {
                'symbol': 'EURUSD',
                'action': 'BUY',
                'entry': 1.1000,
                'takeProfit1': 1.1050,
                'stopLoss': 1.0975
            },
            {
                'symbol': 'GBPUSD',
                'action': 'SELL',
                'entry': 1.2500,
                'takeProfit1': 1.2450,
                'stopLoss': 1.2550
            },
            {
                'symbol': 'XAUUSD',
                'action': 'BUY',
                'entry': 2000.0,
                'takeProfit1': 2010.0,
                'stopLoss': 1990.0
            }
        ]
        
        for signal in test_signals:
            self.tp_adjustor.process_tp_adjustment(signal)
        
        stats = self.tp_adjustor.get_adjustment_statistics()
        
        assert stats['total_adjustments'] == 3
        assert stats['symbols_processed'] == 3
        assert 'average_adjustment_pips' in stats
        assert 'adjustment_types' in stats
        assert stats['enabled'] == True
        assert stats['active_rules'] > 0
    
    def test_convenience_function(self):
        """Test global convenience function"""
        signal_data = {
            'symbol': 'EURUSD',
            'action': 'BUY',
            'entry': 1.1000,
            'takeProfit1': 1.1050,
            'stopLoss': 1.0975
        }
        
        adjusted_tp = adjust_tp(signal_data)
        
        # Should apply EUR* rule (10 pips addition)
        expected_tp = 1.1050 + (10.0 * 0.0001)
        assert abs(adjusted_tp - expected_tp) < 1e-6
    
    def test_module_injection(self):
        """Test module injection"""
        mock_strategy_runtime = MagicMock()
        mock_parser = MagicMock()
        
        self.tp_adjustor.inject_modules(
            strategy_runtime=mock_strategy_runtime,
            parser=mock_parser
        )
        
        assert self.tp_adjustor.strategy_runtime == mock_strategy_runtime
        assert self.tp_adjustor.parser == mock_parser
    
    def test_multiple_tp_levels(self):
        """Test TP adjustment with multiple TP levels"""
        signal_data = {
            'symbol': 'EURUSD',
            'action': 'BUY',
            'entry': 1.1000,
            'takeProfit1': 1.1050,
            'takeProfit2': 1.1100,
            'takeProfit3': 1.1150,
            'stopLoss': 1.0975
        }
        
        result = self.tp_adjustor.process_tp_adjustment(signal_data)
        
        # Should adjust the first TP level
        assert result.original_tp == 1.1050
        expected_tp = 1.1050 + (10.0 * 0.0001)  # EUR* rule: +10 pips
        assert abs(result.adjusted_tp - expected_tp) < 1e-6
    
    def test_edge_cases(self):
        """Test edge cases for TP adjustment"""
        # Zero TP
        signal_zero_tp = {
            'symbol': 'EURUSD',
            'action': 'BUY',
            'entry': 1.1000,
            'takeProfit1': 0.0,
            'stopLoss': 1.0975
        }
        
        result = self.tp_adjustor.process_tp_adjustment(signal_zero_tp)
        assert result.adjusted_tp == 0.0  # Should handle zero TP
        
        # Very small TP adjustment
        small_adjustment_rule = {
            'symbol_pattern': 'TEST',
            'adjustment_type': 'pips_addition',
            'value': 0.1,
            'enabled': True,
            'priority': 100
        }
        
        self.tp_adjustor.adjustment_rules.insert(0, small_adjustment_rule)
        
        signal_small = {
            'symbol': 'TEST',
            'action': 'BUY',
            'entry': 1.1000,
            'takeProfit1': 1.1001,
            'stopLoss': 1.0999
        }
        
        # Should handle very small adjustments without errors
        result = self.tp_adjustor.process_tp_adjustment(signal_small)
        assert result.adjusted_tp is not None


if __name__ == "__main__":
    pytest.main([__file__])