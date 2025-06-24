"""
Test Suite for Signal Simulator
Tests dry-run signal execution, entry selection, lot calculation, and SL/TP adjustment
"""

import unittest
import json
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_simulator import (
    SignalSimulator, SimulationResult, SimulationConfig, simulate_signal
)


class TestSignalSimulator(unittest.TestCase):
    """Unit tests for Signal Simulator"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'signal_simulator': {
                'enable_logging': False,  # Disable for tests
                'shadow_mode': False,
                'default_tp_count': 2,
                'default_lot_size': 0.1,
                'validate_prices': True
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        self.simulator = SignalSimulator(config_file=self.temp_config.name)
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
    
    def test_valid_buy_signal_simulation(self):
        """Test valid BUY signal → correct simulation"""
        parsed_signal = {
            'symbol': 'EURUSD',
            'direction': 'BUY',
            'entry': [1.1000],
            'stop_loss': 1.0950,
            'take_profit': [1.1050, 1.1100],
            'lot_size': 0.5
        }
        
        strategy_config = {
            'mode': 'fixed',
            'base_risk': 1.0,
            'account_balance': 10000.0
        }
        
        result = self.simulator.simulate_signal(parsed_signal, strategy_config)
        
        self.assertIsInstance(result, SimulationResult)
        self.assertTrue(result.valid)
        self.assertEqual(result.symbol, 'EURUSD')
        self.assertEqual(result.direction, 'BUY')
        self.assertEqual(result.entry, 1.1000)
        self.assertEqual(result.sl, 1.0950)
        self.assertEqual(result.tp, [1.1050, 1.1100])
        self.assertGreater(result.lot, 0)
    
    def test_tp_override_from_strategy(self):
        """Test TP override from strategy"""
        parsed_signal = {
            'symbol': 'GBPUSD',
            'direction': 'SELL',
            'entry': [1.2500],
            'stop_loss': 1.2550,
            'take_profit': [1.2450]  # Original TP
        }
        
        strategy_config = {
            'mode': 'fixed',
            'tp_override': [1.2400, 1.2350],  # Strategy override
            'account_balance': 10000.0
        }
        
        result = self.simulator.simulate_signal(parsed_signal, strategy_config)
        
        self.assertTrue(result.valid)
        self.assertEqual(result.tp, [1.2400, 1.2350])  # Should use override
        self.assertIn("Applied TP override from strategy", result.warnings)
    
    def test_shadow_mode(self):
        """Test shadow mode (no SL shown)"""
        # Enable shadow mode in config
        self.simulator.config.shadow_mode = True
        
        parsed_signal = {
            'symbol': 'XAUUSD',
            'direction': 'BUY',
            'entry': [2000.0],
            'stop_loss': 1990.0,
            'take_profit': [2020.0]
        }
        
        strategy_config = {
            'mode': 'fixed',
            'account_balance': 10000.0
        }
        
        result = self.simulator.simulate_signal(parsed_signal, strategy_config)
        
        self.assertTrue(result.valid)
        self.assertEqual(result.mode, 'shadow')
        self.assertIsNone(result.sl)  # SL should be hidden in shadow mode
        self.assertIn("SL hidden in shadow mode", result.warnings)
    
    def test_fallback_if_config_missing(self):
        """Test fallback behavior if config missing"""
        parsed_signal = {
            'symbol': 'US30',
            'direction': 'BUY',
            'entry': [],  # No entry prices
            'stop_loss': None,  # No SL
            'take_profit': []   # No TP
        }
        
        strategy_config = {}  # Empty config
        
        result = self.simulator.simulate_signal(parsed_signal, strategy_config)
        
        # Should not crash and return a result
        self.assertIsInstance(result, SimulationResult)
        self.assertEqual(result.symbol, 'US30')
        self.assertGreater(result.entry, 0)  # Should have fallback entry
        self.assertGreater(result.lot, 0)    # Should have fallback lot
    
    def test_multiple_entry_prices_selection(self):
        """Test entry price selection with multiple entries"""
        parsed_signal = {
            'symbol': 'USDJPY',
            'direction': 'BUY',
            'entry': [110.50, 110.30, 110.70],  # Multiple entries
            'stop_loss': 110.00,
            'take_profit': [111.00]
        }
        
        strategy_config = {
            'mode': 'fixed',
            'account_balance': 10000.0
        }
        
        result = self.simulator.simulate_signal(parsed_signal, strategy_config)
        
        self.assertTrue(result.valid)
        # For BUY, should select minimum entry (best price)
        self.assertEqual(result.entry, 110.30)
    
    def test_sell_signal_entry_selection(self):
        """Test entry selection for SELL signals"""
        parsed_signal = {
            'symbol': 'AUDUSD',
            'direction': 'SELL',
            'entry': [0.7200, 0.7220, 0.7180],  # Multiple entries
            'stop_loss': 0.7250,
            'take_profit': [0.7150]
        }
        
        strategy_config = {
            'mode': 'fixed',
            'account_balance': 10000.0
        }
        
        result = self.simulator.simulate_signal(parsed_signal, strategy_config)
        
        self.assertTrue(result.valid)
        # For SELL, should select maximum entry (best price)
        self.assertEqual(result.entry, 0.7220)
    
    def test_lot_size_calculation_integration(self):
        """Test lot size calculation with different modes"""
        parsed_signal = {
            'symbol': 'EURUSD',
            'direction': 'BUY',
            'entry': [1.1000],
            'stop_loss': 1.0950,  # 50 pips SL
            'take_profit': [1.1100]
        }
        
        # Test risk_percent mode
        strategy_config = {
            'mode': 'risk_percent',
            'base_risk': 1.0,
            'account_balance': 10000.0
        }
        
        result = self.simulator.simulate_signal(parsed_signal, strategy_config)
        
        self.assertTrue(result.valid)
        self.assertGreater(result.lot, 0)
        self.assertLess(result.lot, 10)  # Reasonable range
    
    def test_price_validation(self):
        """Test price relationship validation"""
        # Invalid BUY signal (SL above entry)
        invalid_signal = {
            'symbol': 'GBPUSD',
            'direction': 'BUY',
            'entry': [1.2500],
            'stop_loss': 1.2600,  # SL above entry for BUY (invalid)
            'take_profit': [1.2600]
        }
        
        strategy_config = {
            'mode': 'fixed',
            'account_balance': 10000.0
        }
        
        result = self.simulator.simulate_signal(invalid_signal, strategy_config)
        
        self.assertFalse(result.valid)
        self.assertIn("BUY signal: SL should be below entry", result.warnings)
    
    def test_symbol_normalization(self):
        """Test symbol normalization through symbol mapper"""
        parsed_signal = {
            'symbol': 'GOLD',  # Should be normalized to XAUUSD
            'direction': 'BUY',
            'entry': [2000.0],
            'stop_loss': 1990.0,
            'take_profit': [2020.0]
        }
        
        strategy_config = {
            'mode': 'fixed',
            'account_balance': 10000.0
        }
        
        result = self.simulator.simulate_signal(parsed_signal, strategy_config)
        
        self.assertTrue(result.valid)
        self.assertEqual(result.symbol, 'XAUUSD')  # Should be normalized
    
    def test_spread_adjustment(self):
        """Test spread adjustment functionality"""
        self.simulator.config.apply_spread_adjustment = True
        
        parsed_signal = {
            'symbol': 'EURUSD',
            'direction': 'BUY',
            'entry': [1.1000],
            'stop_loss': 1.0950,
            'take_profit': [1.1050]
        }
        
        strategy_config = {
            'mode': 'fixed',
            'account_balance': 10000.0
        }
        
        result = self.simulator.simulate_signal(parsed_signal, strategy_config)
        
        self.assertTrue(result.valid)
        # Should have spread adjustment warning
        spread_warnings = [w for w in result.warnings if 'spread adjustment' in w]
        self.assertGreater(len(spread_warnings), 0)
    
    def test_tp_level_extension(self):
        """Test automatic TP level extension"""
        parsed_signal = {
            'symbol': 'USDCAD',
            'direction': 'BUY',
            'entry': [1.3000],
            'stop_loss': 1.2950,
            'take_profit': [1.3050]  # Only 1 TP, should be extended to 2
        }
        
        strategy_config = {
            'mode': 'fixed',
            'account_balance': 10000.0
        }
        
        result = self.simulator.simulate_signal(parsed_signal, strategy_config)
        
        self.assertTrue(result.valid)
        self.assertEqual(len(result.tp), 2)  # Should be extended to default count
        self.assertIn("Extended TP levels", result.warnings[0] if result.warnings else "")
    
    def test_batch_simulation(self):
        """Test batch simulation functionality"""
        signals_and_configs = [
            (
                {
                    'symbol': 'EURUSD',
                    'direction': 'BUY',
                    'entry': [1.1000],
                    'stop_loss': 1.0950,
                    'take_profit': [1.1050]
                },
                {'mode': 'fixed', 'account_balance': 10000.0}
            ),
            (
                {
                    'symbol': 'GBPUSD',
                    'direction': 'SELL',
                    'entry': [1.2500],
                    'stop_loss': 1.2550,
                    'take_profit': [1.2450]
                },
                {'mode': 'risk_percent', 'account_balance': 5000.0}
            )
        ]
        
        results = self.simulator.batch_simulate(signals_and_configs)
        
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], SimulationResult)
        self.assertIsInstance(results[1], SimulationResult)
    
    def test_simulation_statistics(self):
        """Test simulation statistics tracking"""
        # Clear stats first
        self.simulator.clear_statistics()
        
        parsed_signal = {
            'symbol': 'NZDUSD',
            'direction': 'BUY',
            'entry': [0.6500],
            'stop_loss': 0.6450,
            'take_profit': [0.6550]
        }
        
        strategy_config = {
            'mode': 'fixed',
            'account_balance': 10000.0
        }
        
        # Run a simulation
        result = self.simulator.simulate_signal(parsed_signal, strategy_config)
        
        # Check statistics
        stats = self.simulator.get_simulation_statistics()
        
        self.assertEqual(stats['stats']['total_simulations'], 1)
        if result.valid:
            self.assertEqual(stats['stats']['valid_simulations'], 1)
        else:
            self.assertEqual(stats['stats']['invalid_simulations'], 1)
        
        self.assertIn('NZDUSD', stats['stats']['symbol_frequency'])
    
    def test_error_handling(self):
        """Test error handling with malformed input"""
        # Malformed signal
        malformed_signal = {
            'symbol': None,
            'direction': 'INVALID',
            'entry': 'not_a_number',
            'stop_loss': [],
            'take_profit': None
        }
        
        strategy_config = {
            'mode': 'invalid_mode',
            'account_balance': -1000  # Negative balance
        }
        
        result = self.simulator.simulate_signal(malformed_signal, strategy_config)
        
        # Should not crash and return error result
        self.assertIsInstance(result, SimulationResult)
        self.assertFalse(result.valid)
        self.assertEqual(result.mode, 'error')
    
    def test_module_injection(self):
        """Test external module injection"""
        # Create mock modules
        mock_lotsize = Mock()
        mock_entry = Mock()
        mock_market = Mock()
        mock_spread = Mock()
        
        # Inject modules
        self.simulator.inject_modules(
            lotsize_engine=mock_lotsize,
            entry_handler=mock_entry,
            market_data=mock_market,
            spread_checker=mock_spread
        )
        
        # Verify injection
        stats = self.simulator.get_simulation_statistics()
        components = stats['components_available']
        
        self.assertTrue(components['lotsize_engine'])
        self.assertTrue(components['entry_handler'])
        self.assertTrue(components['market_data'])
        self.assertTrue(components['spread_checker'])


class TestGlobalFunctions(unittest.TestCase):
    """Test global utility functions"""
    
    def test_simulate_signal_function(self):
        """Test global simulate_signal function"""
        parsed_signal = {
            'symbol': 'CHFJPY',
            'direction': 'BUY',
            'entry': [110.50],
            'stop_loss': 110.00,
            'take_profit': [111.00]
        }
        
        strategy_config = {
            'mode': 'fixed',
            'account_balance': 10000.0
        }
        
        result = simulate_signal(parsed_signal, strategy_config)
        
        self.assertIsInstance(result, SimulationResult)
        self.assertEqual(result.symbol, 'CHFJPY')
    
    def test_simulation_result_to_dict(self):
        """Test SimulationResult to_dict conversion"""
        result = SimulationResult(
            entry=1.1000,
            sl=1.0950,
            tp=[1.1050, 1.1100],
            lot=0.5,
            mode='normal',
            valid=True,
            symbol='EURUSD',
            direction='BUY',
            reasoning='Test simulation',
            warnings=[],
            timestamp=datetime.now()
        )
        
        result_dict = result.to_dict()
        
        self.assertIsInstance(result_dict, dict)
        self.assertIn('entry', result_dict)
        self.assertIn('timestamp', result_dict)
        self.assertIsInstance(result_dict['timestamp'], str)  # Should be ISO format


if __name__ == '__main__':
    unittest.main()