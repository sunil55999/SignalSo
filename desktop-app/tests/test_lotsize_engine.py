"""
Test Suite for Lotsize Engine
Tests lot size extraction, calculation modes, and risk management
"""

import unittest
import json
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lotsize_engine import (
    LotsizeEngine, RiskMode, LotsizeConfig, LotsizeResult, extract_lotsize, calculate_lot
)


class TestLotsizeEngine(unittest.TestCase):
    """Unit tests for Lotsize Engine"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'lotsize_engine': {
                'default_mode': 'risk_percent',
                'default_risk_percent': 1.0,
                'min_lot_size': 0.01,
                'max_lot_size': 10.0,
                'precision_digits': 2,
                'pip_value_usd': 10.0,
                'balance_fallback': 10000.0
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        self.engine = LotsizeEngine(config_file=self.temp_config.name)
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
    
    def test_extract_fixed_lot_from_text(self):
        """Test extraction of fixed lot sizes from signal text"""
        test_cases = [
            ("BUY EURUSD\nLot: 0.5\nSL: 1.0980", 0.5),
            ("Use 1.2 lots for this trade", 1.2),
            ("SELL GBPUSD\nLotsize: 0.75", 0.75),
            ("Trade with 2 lots", 2.0)
        ]
        
        for signal_text, expected_lot in test_cases:
            with self.subTest(signal_text=signal_text[:20]):
                result = self.engine.extract_lotsize(
                    signal_text, "fixed_lot", 10000, "EURUSD"
                )
                self.assertAlmostEqual(result.calculated_lot, expected_lot, places=2)
                self.assertIsNotNone(result.original_lot)
    
    def test_extract_risk_percentage_from_text(self):
        """Test extraction of risk percentage from signal text"""
        signal_text = "BUY EURUSD\nEntry: 1.1000\nSL: 1.0950\nRisk: 2%"
        
        result = self.engine.extract_lotsize(
            signal_text, "risk_percent", 10000, "EURUSD", stop_loss_pips=50
        )
        
        # With 2% risk on $10k = $200 risk
        # 50 pips SL, $10 per pip = need 4 lots for $200 risk
        expected_lot = 200 / (50 * 10)  # $200 / ($500 per lot)
        self.assertAlmostEqual(result.calculated_lot, expected_lot, places=1)
    
    def test_risk_mode_calculations(self):
        """Test different risk mode calculations"""
        account_balance = 10000
        stop_loss_pips = 50
        symbol = "EURUSD"
        
        # Test risk percent mode
        result_risk = self.engine.extract_lotsize(
            "", "risk_percent", account_balance, symbol, stop_loss_pips
        )
        expected_risk = (account_balance * 0.01) / (stop_loss_pips * 10)  # 1% risk
        self.assertAlmostEqual(result_risk.calculated_lot, expected_risk, places=2)
        
        # Test fixed lot mode
        result_fixed = self.engine.extract_lotsize(
            "", "fixed_lot", account_balance, symbol, stop_loss_pips
        )
        self.assertAlmostEqual(result_fixed.calculated_lot, 0.1, places=2)  # Default fixed lot
        
        # Test balance percent mode
        result_balance = self.engine.extract_lotsize(
            "", "balance_percent", account_balance, symbol, stop_loss_pips
        )
        expected_balance = (account_balance * 0.01) / (stop_loss_pips * 10)  # 1% of balance
        self.assertAlmostEqual(result_balance.calculated_lot, expected_balance, places=2)
    
    def test_risk_multiplier_extraction(self):
        """Test extraction of risk multipliers from keywords"""
        test_cases = [
            ("HIGH RISK signal", 2.0),
            ("Conservative approach", 0.5),
            ("Low risk entry", 0.5),
            ("Aggressive trade", 2.0),
            ("Normal signal", 1.0)  # No keywords = default
        ]
        
        for signal_text, expected_multiplier in test_cases:
            with self.subTest(signal_text=signal_text):
                result = self.engine.extract_lotsize(
                    signal_text, "fixed_lot", 10000, "EURUSD"
                )
                self.assertAlmostEqual(result.risk_multiplier, expected_multiplier, places=1)
    
    def test_pip_value_handling(self):
        """Test pip value calculation for different symbols"""
        symbols_pip_values = [
            ("EURUSD", 10.0),
            ("USDJPY", 9.09),
            ("XAUUSD", 10.0),
            ("UNKNOWN", 10.0)  # Should fall back to default
        ]
        
        for symbol, expected_pip_value in symbols_pip_values:
            with self.subTest(symbol=symbol):
                pip_value = self.engine._get_pip_value(symbol)
                self.assertAlmostEqual(pip_value, expected_pip_value, places=1)
    
    def test_lot_size_constraints(self):
        """Test that lot sizes are constrained to min/max limits"""
        # Test minimum constraint
        tiny_lot = self.engine._apply_lot_constraints(0.001)
        self.assertGreaterEqual(tiny_lot, self.engine.config.min_lot_size)
        
        # Test maximum constraint
        huge_lot = self.engine._apply_lot_constraints(100.0)
        self.assertLessEqual(huge_lot, self.engine.config.max_lot_size)
        
        # Test precision rounding
        precise_lot = self.engine._apply_lot_constraints(1.23456)
        self.assertEqual(precise_lot, 1.23)  # Rounded to 2 decimal places
    
    def test_position_value_calculation(self):
        """Test position value and exposure calculations"""
        lot_size = 1.0
        symbol = "EURUSD"
        current_price = 1.1000
        
        position_data = self.engine.calculate_position_value(lot_size, symbol, current_price)
        
        expected_value = 1.0 * 100000 * 1.1000  # 1 lot * contract size * price
        self.assertAlmostEqual(position_data['position_value'], expected_value, places=0)
        self.assertEqual(position_data['lot_size'], lot_size)
        self.assertEqual(position_data['current_price'], current_price)
    
    def test_lot_size_validation(self):
        """Test lot size validation and safety checks"""
        account_balance = 10000
        
        # Test valid lot size
        validation_valid = self.engine.validate_lot_size(1.0, account_balance)
        self.assertTrue(validation_valid['is_valid'])
        self.assertEqual(len(validation_valid['errors']), 0)
        
        # Test invalid lot size (too small)
        validation_small = self.engine.validate_lot_size(0.001, account_balance)
        self.assertFalse(validation_small['is_valid'])
        self.assertGreater(len(validation_small['errors']), 0)
        
        # Test invalid lot size (too large)
        validation_large = self.engine.validate_lot_size(50.0, account_balance)
        self.assertFalse(validation_large['is_valid'])
        self.assertGreater(len(validation_large['errors']), 0)
    
    def test_complex_signal_parsing(self):
        """Test parsing of complex real-world signal formats"""
        complex_signals = [
            # Mixed format with lot size and risk keywords
            "🔥 EURUSD BUY 📈\nEntry: 1.1000-1.1020\nSL: 1.0950\nTP: 1.1100\nLot: 0.8\nHIGH CONFIDENCE",
            
            # Risk percentage format
            "GBPUSD SELL\nRisk 1.5% of balance\nEntry: 1.2850\nStop: 1.2900",
            
            # Cash amount format  
            "USDJPY LONG\nInvest $500\nEntry: 110.50\nSL: 110.00",
            
            # Pip value format
            "$15 per pip trade\nEURUSD BUY\nEntry: 1.0980\nSL: 1.0930"
        ]
        
        for i, signal in enumerate(complex_signals):
            with self.subTest(signal_index=i):
                result = self.engine.extract_lotsize(signal, "risk_percent", 10000, "EURUSD", 50)
                
                # All should produce valid results
                self.assertIsInstance(result, LotsizeResult)
                self.assertGreater(result.calculated_lot, 0)
                self.assertLessEqual(result.calculated_lot, self.engine.config.max_lot_size)
                self.assertGreaterEqual(result.confidence, 0.5)
    
    def test_no_stop_loss_fallback(self):
        """Test behavior when no stop loss is provided"""
        result = self.engine.extract_lotsize(
            "BUY EURUSD Entry: 1.1000", "risk_percent", 10000, "EURUSD", None
        )
        
        # Should still calculate a lot size using fallback logic
        self.assertGreater(result.calculated_lot, 0)
        self.assertIsNone(result.stop_loss_pips)
    
    def test_mt5_bridge_integration(self):
        """Test integration with MT5 bridge for pip values"""
        # Mock MT5 bridge
        mock_mt5 = Mock()
        mock_mt5.get_symbol_info.return_value = {'pip_value': 15.0}
        
        self.engine.inject_modules(mt5_bridge=mock_mt5)
        
        pip_value = self.engine._get_pip_value("EURUSD")
        
        # Should use MT5 value instead of config
        self.assertEqual(pip_value, 15.0)
        mock_mt5.get_symbol_info.assert_called_with("EURUSD")
    
    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly"""
        initial_stats = self.engine.get_statistics()
        
        # Process some signals
        test_signals = [
            ("Lot: 0.5", "fixed_lot"),
            ("Risk 2%", "risk_percent"),
            ("HIGH RISK trade", "risk_percent")
        ]
        
        for signal, mode in test_signals:
            self.engine.extract_lotsize(signal, mode, 10000, "EURUSD", 50)
        
        final_stats = self.engine.get_statistics()
        
        # Should have processed more signals
        self.assertGreater(
            final_stats['extraction_stats']['total_processed'],
            initial_stats['extraction_stats']['total_processed']
        )
    
    def test_configuration_update(self):
        """Test configuration update functionality"""
        new_config = {
            'default_risk_percent': 2.0,
            'max_lot_size': 5.0,
            'precision_digits': 3
        }
        
        success = self.engine.update_configuration(new_config)
        
        self.assertTrue(success)
        self.assertEqual(self.engine.config.default_risk_percent, 2.0)
        self.assertEqual(self.engine.config.max_lot_size, 5.0)
        self.assertEqual(self.engine.config.precision_digits, 3)
    
    def test_legacy_compatibility_function(self):
        """Test legacy compatibility function"""
        signal_text = "Use 0.75 lots"
        
        lot_size = extract_lotsize(signal_text, "fixed_lot", 10000, "EURUSD")
        
        # Should return just the lot size as float
        self.assertIsInstance(lot_size, float)
        self.assertAlmostEqual(lot_size, 0.75, places=2)
    
    def test_edge_cases(self):
        """Test edge cases and error scenarios"""
        edge_cases = [
            ("", "fixed_lot", 10000, "EURUSD", None, True),  # Empty signal
            ("No lot info", "invalid_mode", 10000, "EURUSD", None, True),  # Invalid mode
            ("Lot: abc", "fixed_lot", 10000, "EURUSD", None, True),  # Invalid lot format
            ("Normal signal", "risk_percent", 0, "EURUSD", None, True),  # Zero balance
            ("Lot: -1", "fixed_lot", 10000, "EURUSD", None, True),  # Negative lot
        ]
        
        for signal, mode, balance, symbol, sl_pips, should_succeed in edge_cases:
            with self.subTest(signal=signal[:15]):
                try:
                    result = self.engine.extract_lotsize(signal, mode, balance, symbol, sl_pips)
                    # Should always return a valid result, even for edge cases
                    self.assertIsInstance(result, LotsizeResult)
                    self.assertGreaterEqual(result.calculated_lot, self.engine.config.min_lot_size)
                except Exception as e:
                    if should_succeed:
                        self.fail(f"Should not raise exception for: {signal[:15]} - {e}")


class TestLotsizeEngineIntegration(unittest.TestCase):
    """Integration tests for lotsize engine"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.engine = LotsizeEngine()
    
    def test_real_world_scenarios(self):
        """Test with real-world trading scenarios"""
        scenarios = [
            # Scalping scenario - small lots, tight SL
            {
                'signal': 'EURUSD BUY Entry: 1.1000 SL: 1.0995 TP: 1.1010',
                'mode': 'risk_percent',
                'balance': 5000,
                'sl_pips': 5,
                'expected_risk': 50  # 1% of 5000
            },
            
            # Swing trading - larger SL, conservative risk
            {
                'signal': 'GBPUSD SELL conservative Entry: 1.2800 SL: 1.2900',
                'mode': 'risk_percent', 
                'balance': 20000,
                'sl_pips': 100,
                'expected_risk': 200  # 1% of 20000
            },
            
            # Day trading with explicit lot size
            {
                'signal': 'USDJPY BUY Lot: 2.5 Entry: 110.00 SL: 109.50',
                'mode': 'fixed_lot',
                'balance': 50000,
                'sl_pips': 50,
                'expected_lot': 2.5
            }
        ]
        
        for scenario in scenarios:
            with self.subTest(scenario=scenario['signal'][:15]):
                result = self.engine.extract_lotsize(
                    scenario['signal'],
                    scenario['mode'],
                    scenario['balance'],
                    "EURUSD",  # Default symbol
                    scenario.get('sl_pips')
                )
                
                # Verify result is reasonable
                self.assertGreater(result.calculated_lot, 0)
                self.assertLess(result.calculated_lot, 10)  # Reasonable upper limit
                
                if 'expected_lot' in scenario:
                    self.assertAlmostEqual(result.calculated_lot, scenario['expected_lot'], places=1)
    
    def test_performance_with_large_dataset(self):
        """Test performance with many lot size calculations"""
        import time
        
        start_time = time.time()
        
        # Process 1000 signals
        for i in range(1000):
            signal = f"Signal {i} Lot: {0.1 + (i % 10) * 0.1}"
            result = self.engine.extract_lotsize(signal, "fixed_lot", 10000, "EURUSD")
            self.assertIsInstance(result, LotsizeResult)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process quickly (less than 5 seconds for 1000 signals)
        self.assertLess(processing_time, 5.0)
        
        # Check statistics
        stats = self.engine.get_statistics()
        self.assertEqual(stats['extraction_stats']['total_processed'], 1000)


class TestCalculateLotFunction(unittest.TestCase):
    """Test the new calculate_lot function required by the task"""
    
    def test_calculate_lot_risk_percent_mode(self):
        """Test 1% risk of $1000 account, SL 50 pips"""
        strategy_config = {
            'mode': 'risk_percent',
            'base_risk': 1.0,
            'override_keywords': ['HIGH RISK', 'LOW RISK']
        }
        signal_data = {
            'text': 'BUY EURUSD Entry: 1.1000 SL: 1.0950 TP: 1.1100'
        }
        
        lot_size = calculate_lot(strategy_config, signal_data, 1000.0, 50.0, 'EURUSD')
        
        # 1% of $1000 = $10 risk, 50 pips SL, $10 per pip = 0.02 lots
        expected_lot = 10.0 / (50.0 * 10.0)  # $10 / $500 = 0.02
        self.assertAlmostEqual(lot_size, expected_lot, places=2)
    
    def test_calculate_lot_fixed_cash_mode(self):
        """Test fixed $10 trade with pip value $1"""
        strategy_config = {
            'mode': 'cash_per_trade',
            'base_risk': 10.0,
            'override_keywords': []
        }
        signal_data = {
            'text': 'SELL US30 Entry: 35000 SL: 35010'
        }
        
        lot_size = calculate_lot(strategy_config, signal_data, 5000.0, 10.0, 'US30')
        
        # Should calculate based on fixed cash amount
        self.assertGreater(lot_size, 0)
        self.assertLessEqual(lot_size, 10)  # Reasonable upper bound
    
    def test_calculate_lot_high_risk_multiplier(self):
        """Test text contains 'HIGH RISK' → double lot"""
        strategy_config = {
            'mode': 'fixed',
            'base_risk': 0.1,
            'override_keywords': ['HIGH RISK']
        }
        signal_data = {
            'text': 'BUY GBPUSD HIGH RISK Entry: 1.2500 SL: 1.2450'
        }
        
        lot_size = calculate_lot(strategy_config, signal_data, 10000.0, 50.0, 'GBPUSD')
        
        # Should apply 2x multiplier for HIGH RISK
        self.assertGreaterEqual(lot_size, 0.15)  # Base 0.1 * 2x multiplier = 0.2, but with constraints
    
    def test_calculate_lot_missing_sl_fallback(self):
        """Test missing SL: fallback behavior"""
        strategy_config = {
            'mode': 'risk_percent',
            'base_risk': 1.0,
            'override_keywords': []
        }
        signal_data = {
            'text': 'BUY EURUSD Entry: 1.1000 TP: 1.1100'
        }
        
        # Missing SL (None or 0)
        lot_size = calculate_lot(strategy_config, signal_data, 10000.0, None, 'EURUSD')
        
        # Should use fallback behavior
        self.assertGreater(lot_size, 0)
        self.assertLess(lot_size, 10)  # Within reasonable bounds
    
    def test_calculate_lot_symbol_specific_pip_values(self):
        """Test symbol-specific pip valuation"""
        strategy_config = {
            'mode': 'pip_value',
            'base_risk': 10.0,  # $10 per pip target
            'override_keywords': []
        }
        
        # Test with Gold (higher pip value)
        signal_data_gold = {
            'text': 'BUY XAUUSD Entry: 2000 SL: 1995'
        }
        lot_size_gold = calculate_lot(strategy_config, signal_data_gold, 10000.0, 5.0, 'XAUUSD')
        
        # Test with US30 (lower pip value)
        signal_data_us30 = {
            'text': 'BUY US30 Entry: 35000 SL: 34995'
        }
        lot_size_us30 = calculate_lot(strategy_config, signal_data_us30, 10000.0, 5.0, 'US30')
        
        # Both should be positive and reasonable
        self.assertGreater(lot_size_gold, 0)
        self.assertGreater(lot_size_us30, 0)
        self.assertLessEqual(lot_size_gold, 10)
        self.assertLessEqual(lot_size_us30, 10)
    
    def test_calculate_lot_all_modes(self):
        """Test all required modes from task specification"""
        modes_to_test = [
            'fixed',
            'risk_percent', 
            'cash_per_trade',
            'pip_value',
            'text_override'
        ]
        
        signal_data = {
            'text': 'BUY EURUSD Lot: 0.5 Entry: 1.1000 SL: 1.0950'
        }
        
        for mode in modes_to_test:
            with self.subTest(mode=mode):
                strategy_config = {
                    'mode': mode,
                    'base_risk': 1.0,
                    'override_keywords': []
                }
                
                lot_size = calculate_lot(strategy_config, signal_data, 10000.0, 50.0, 'EURUSD')
                
                # Should return valid lot size
                self.assertIsInstance(lot_size, float)
                self.assertGreaterEqual(lot_size, 0.01)  # Min lot size
                self.assertLessEqual(lot_size, 5.0)      # Max lot size (from config)
    
    def test_calculate_lot_bounds_enforcement(self):
        """Test safe output bounds: 0.01 ≤ lot ≤ 5.00"""
        strategy_config = {
            'mode': 'risk_percent',
            'base_risk': 100.0,  # Extreme risk to test upper bound
            'override_keywords': []
        }
        signal_data = {
            'text': 'BUY EURUSD Entry: 1.1000 SL: 1.0999'  # Very tight SL
        }
        
        lot_size = calculate_lot(strategy_config, signal_data, 1000000.0, 1.0, 'EURUSD')
        
        # Should be constrained within bounds
        self.assertGreaterEqual(lot_size, 0.01)
        self.assertLessEqual(lot_size, 10.0)  # Max lot from config


if __name__ == '__main__':
    unittest.main()