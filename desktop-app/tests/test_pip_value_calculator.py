"""
Test Suite for Pip Value Calculator
Tests pip value calculation, symbol mapping, and configuration management
"""

import unittest
import json
import tempfile
import os
from unittest.mock import Mock, patch

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pip_value_calculator import (
    PipValueCalculator, get_pip_value, get_contract_size, add_custom_pip_value
)


class TestPipValueCalculator(unittest.TestCase):
    """Unit tests for Pip Value Calculator"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'pip_values': {
                'EURUSD': 10.0,
                'XAUUSD': 10.0,
                'US30': 1.0,
                'CUSTOM_PAIR': 15.0
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        self.calculator = PipValueCalculator(config_file=self.temp_config.name)
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
    
    def test_get_pip_value_from_config(self):
        """Test getting pip values from configuration"""
        test_cases = [
            ('EURUSD', 10.0),
            ('XAUUSD', 10.0),
            ('US30', 1.0),
            ('CUSTOM_PAIR', 15.0)
        ]
        
        for symbol, expected_value in test_cases:
            with self.subTest(symbol=symbol):
                pip_value = self.calculator.get_pip_value(symbol)
                self.assertEqual(pip_value, expected_value)
    
    def test_get_pip_value_default_values(self):
        """Test default pip values for common symbols"""
        # Test symbols not in config but should have defaults
        test_cases = [
            ('GBPUSD', 10.0),
            ('USDJPY', 9.09),
            ('XAGUSD', 50.0),
            ('NAS100', 1.0),
            ('SPX500', 1.0)
        ]
        
        for symbol, expected_value in test_cases:
            with self.subTest(symbol=symbol):
                pip_value = self.calculator.get_pip_value(symbol)
                self.assertEqual(pip_value, expected_value)
    
    def test_get_pip_value_case_insensitive(self):
        """Test case insensitive symbol matching"""
        test_cases = [
            'eurusd',
            'EURUSD', 
            'EurUsd',
            'xauusd',
            'XAUUSD'
        ]
        
        for symbol in test_cases:
            with self.subTest(symbol=symbol):
                pip_value = self.calculator.get_pip_value(symbol)
                self.assertGreater(pip_value, 0)
    
    def test_get_pip_value_aliases(self):
        """Test symbol aliases (GOLD -> XAUUSD, etc.)"""
        test_cases = [
            ('GOLD', 10.0),     # Should map to XAUUSD
            ('DOW', 1.0),       # Should map to US30  
            ('SPX', 1.0)        # Should map to SPX500
        ]
        
        for symbol, expected_value in test_cases:
            with self.subTest(symbol=symbol):
                pip_value = self.calculator.get_pip_value(symbol)
                self.assertEqual(pip_value, expected_value)
    
    def test_get_pip_value_unknown_symbol(self):
        """Test fallback for unknown symbols"""
        unknown_symbols = ['UNKNOWN', 'FAKEPAIR', 'INVALID']
        
        for symbol in unknown_symbols:
            with self.subTest(symbol=symbol):
                pip_value = self.calculator.get_pip_value(symbol)
                self.assertEqual(pip_value, 10.0)  # Default fallback
    
    def test_get_contract_size(self):
        """Test contract size calculation"""
        test_cases = [
            ('EURUSD', 100000),
            ('XAUUSD', 100),
            ('XAGUSD', 5000),
            ('US30', 1),
            ('USOIL', 1000),
            ('BTCUSD', 1)
        ]
        
        for symbol, expected_size in test_cases:
            with self.subTest(symbol=symbol):
                contract_size = self.calculator.get_contract_size(symbol)
                self.assertEqual(contract_size, expected_size)
    
    def test_add_custom_pip_value(self):
        """Test adding custom pip values"""
        # Add new symbol
        success = self.calculator.add_custom_pip_value('NEWPAIR', 25.0, save_to_config=False)
        self.assertTrue(success)
        
        # Verify it was added
        pip_value = self.calculator.get_pip_value('NEWPAIR')
        self.assertEqual(pip_value, 25.0)
        
        # Update existing symbol
        success = self.calculator.add_custom_pip_value('EURUSD', 12.0, save_to_config=False)
        self.assertTrue(success)
        
        # Verify it was updated
        pip_value = self.calculator.get_pip_value('EURUSD')
        self.assertEqual(pip_value, 12.0)
    
    def test_get_all_pip_values(self):
        """Test getting all configured pip values"""
        all_values = self.calculator.get_all_pip_values()
        
        self.assertIsInstance(all_values, dict)
        self.assertIn('EURUSD', all_values)
        self.assertIn('XAUUSD', all_values)
        self.assertIn('US30', all_values)
        self.assertEqual(all_values['EURUSD'], 10.0)
    
    def test_get_statistics(self):
        """Test calculator statistics"""
        stats = self.calculator.get_statistics()
        
        self.assertIn('total_symbols', stats)
        self.assertIn('supported_symbol_types', stats)
        self.assertIn('has_mt5_integration', stats)
        
        self.assertIsInstance(stats['total_symbols'], int)
        self.assertGreater(stats['total_symbols'], 0)
        self.assertFalse(stats['has_mt5_integration'])  # No MT5 in test
    
    def test_mt5_integration_mock(self):
        """Test MT5 integration with mocked bridge"""
        # Create mock MT5 bridge
        mock_mt5_bridge = Mock()
        mock_mt5_bridge.get_symbol_info.return_value = {
            'pip_value': 15.5,
            'contract_size': 150000
        }
        
        # Inject mock bridge
        self.calculator.inject_modules(mt5_bridge=mock_mt5_bridge)
        
        # Test pip value from MT5
        pip_value = self.calculator.get_pip_value('TESTPAIR')
        self.assertEqual(pip_value, 15.5)
        
        # Test contract size from MT5
        contract_size = self.calculator.get_contract_size('TESTPAIR')
        self.assertEqual(contract_size, 150000)
    
    def test_dynamic_pip_value_calculation(self):
        """Test dynamic pip value calculation for forex pairs"""
        # Test direct quotes (quote currency = account currency)
        pip_value = self.calculator._calculate_dynamic_pip_value('EURUSD', 'USD')
        self.assertEqual(pip_value, 10.0)
        
        # Test indirect quotes (base currency = account currency)  
        pip_value = self.calculator._calculate_dynamic_pip_value('USDCAD', 'USD')
        self.assertEqual(pip_value, 7.69)
        
        # Test indices
        pip_value = self.calculator._calculate_dynamic_pip_value('US30', 'USD')
        self.assertEqual(pip_value, 1.0)
        
        # Test metals
        pip_value = self.calculator._calculate_dynamic_pip_value('XAUUSD', 'USD')
        self.assertEqual(pip_value, 10.0)


class TestGlobalFunctions(unittest.TestCase):
    """Test global utility functions"""
    
    def test_get_pip_value_function(self):
        """Test global get_pip_value function"""
        # Test known symbols
        self.assertEqual(get_pip_value('EURUSD'), 10.0)
        self.assertEqual(get_pip_value('XAUUSD'), 10.0)
        self.assertEqual(get_pip_value('US30'), 1.0)
        
        # Test case insensitive
        self.assertEqual(get_pip_value('eurusd'), 10.0)
        self.assertEqual(get_pip_value('GOLD'), 10.0)  # Alias
    
    def test_get_contract_size_function(self):
        """Test global get_contract_size function"""
        self.assertEqual(get_contract_size('EURUSD'), 100000)
        self.assertEqual(get_contract_size('XAUUSD'), 100)
        self.assertEqual(get_contract_size('US30'), 1)
    
    def test_add_custom_pip_value_function(self):
        """Test global add_custom_pip_value function"""
        # Add custom value
        success = add_custom_pip_value('TESTPAIR', 20.0)
        self.assertTrue(success)
        
        # Verify it works
        pip_value = get_pip_value('TESTPAIR')
        self.assertEqual(pip_value, 20.0)
    
    def test_performance_with_multiple_calls(self):
        """Test performance with many pip value lookups"""
        import time
        
        start_time = time.time()
        
        # Perform 1000 lookups
        for i in range(1000):
            symbol = ['EURUSD', 'GBPUSD', 'XAUUSD', 'US30', 'NAS100'][i % 5]
            pip_value = get_pip_value(symbol)
            self.assertGreater(pip_value, 0)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should be fast (less than 1 second for 1000 calls)
        self.assertLess(processing_time, 1.0)


if __name__ == '__main__':
    unittest.main()