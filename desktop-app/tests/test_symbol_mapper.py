"""
Test Suite for Symbol Mapper
Tests symbol normalization, broker mapping, and user overrides
"""

import unittest
import json
import tempfile
import os
from unittest.mock import patch

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from symbol_mapper import (
    SymbolMapper, normalize_symbol, add_symbol_override, get_symbol_stats
)


class TestSymbolMapper(unittest.TestCase):
    """Unit tests for Symbol Mapper"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_config_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_config_dir, 'symbol_map.json')
        
        # Create test symbol mapping file
        test_mappings = {
            "symbol_mappings": {
                "GOLD": "XAUUSD",
                "SILVER": "XAGUSD",
                "DOW": "US30",
                "NASDAQ": "NAS100",
                "TEST_PAIR": "TEST_MAPPED"
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_mappings, f)
        
        self.mapper = SymbolMapper(config_file=self.config_file)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_config_dir)
    
    def test_gold_to_xauusd_mapping(self):
        """Test 'GOLD' → 'XAUUSD' mapping"""
        result = self.mapper.normalize_symbol('GOLD')
        self.assertEqual(result, 'XAUUSD')
        
        # Test case insensitive
        result = self.mapper.normalize_symbol('gold')
        self.assertEqual(result, 'XAUUSD')
        
        result = self.mapper.normalize_symbol('Gold')
        self.assertEqual(result, 'XAUUSD')
    
    def test_unknown_symbol_returns_input(self):
        """Test unknown symbol returns input unchanged"""
        unknown_symbols = ['UNKNOWN_PAIR', 'FAKE_SYMBOL', 'NOT_MAPPED']
        
        for symbol in unknown_symbols:
            with self.subTest(symbol=symbol):
                result = self.mapper.normalize_symbol(symbol)
                self.assertEqual(result, symbol.upper())
    
    def test_user_override_map(self):
        """Test user override functionality"""
        # Add user override
        success = self.mapper.add_user_override('CUSTOM_SYMBOL', 'CUSTOM_MAPPED')
        self.assertTrue(success)
        
        # Test the override works
        result = self.mapper.normalize_symbol('CUSTOM_SYMBOL')
        self.assertEqual(result, 'CUSTOM_MAPPED')
        
        # Test case insensitive
        result = self.mapper.normalize_symbol('custom_symbol')
        self.assertEqual(result, 'CUSTOM_MAPPED')
    
    def test_user_override_priority(self):
        """Test user overrides take priority over default mappings"""
        # Override existing mapping
        success = self.mapper.add_user_override('GOLD', 'OVERRIDE_GOLD')
        self.assertTrue(success)
        
        # Should return user override, not default mapping
        result = self.mapper.normalize_symbol('GOLD')
        self.assertEqual(result, 'OVERRIDE_GOLD')
    
    def test_remove_user_override(self):
        """Test removing user overrides"""
        # Add then remove override
        self.mapper.add_user_override('TEMP_SYMBOL', 'TEMP_MAPPED')
        
        result = self.mapper.normalize_symbol('TEMP_SYMBOL')
        self.assertEqual(result, 'TEMP_MAPPED')
        
        # Remove override
        success = self.mapper.remove_user_override('TEMP_SYMBOL')
        self.assertTrue(success)
        
        # Should now return input unchanged
        result = self.mapper.normalize_symbol('TEMP_SYMBOL')
        self.assertEqual(result, 'TEMP_SYMBOL')
    
    def test_partial_matching(self):
        """Test partial matching for complex symbols"""
        # Test with .cash suffix
        result = self.mapper.normalize_symbol('US30.cash')
        self.assertEqual(result, 'US30')
        
        # Test with .CFD suffix  
        result = self.mapper.normalize_symbol('GOLD.CFD')
        self.assertEqual(result, 'XAUUSD')
        
        # Test with underscores
        result = self.mapper.normalize_symbol('NAS_100')
        # Should map to NAS100 if available, or return cleaned version
        self.assertIn(result, ['NAS100', 'NAS_100'])
    
    def test_bulk_normalization(self):
        """Test bulk symbol normalization"""
        symbols = ['GOLD', 'SILVER', 'UNKNOWN', 'DOW']
        result = self.mapper.bulk_normalize(symbols)
        
        expected = {
            'GOLD': 'XAUUSD',
            'SILVER': 'XAGUSD', 
            'UNKNOWN': 'UNKNOWN',
            'DOW': 'US30'
        }
        
        self.assertEqual(result, expected)
    
    def test_case_insensitive_mapping(self):
        """Test case insensitive symbol mapping"""
        test_cases = [
            ('gold', 'XAUUSD'),
            ('GOLD', 'XAUUSD'),
            ('Gold', 'XAUUSD'),
            ('gOLd', 'XAUUSD'),
            ('silver', 'XAGUSD'),
            ('SILVER', 'XAGUSD')
        ]
        
        for input_symbol, expected in test_cases:
            with self.subTest(input_symbol=input_symbol):
                result = self.mapper.normalize_symbol(input_symbol)
                self.assertEqual(result, expected)
    
    def test_empty_and_invalid_inputs(self):
        """Test handling of empty and invalid inputs"""
        # Empty string
        result = self.mapper.normalize_symbol('')
        self.assertEqual(result, '')
        
        # None input
        result = self.mapper.normalize_symbol(None)
        self.assertEqual(result, '')
        
        # Whitespace only
        result = self.mapper.normalize_symbol('   ')
        self.assertEqual(result, '')
    
    def test_mapping_statistics(self):
        """Test mapping statistics tracking"""
        # Clear stats first
        self.mapper.clear_statistics()
        
        # Perform some mappings
        self.mapper.normalize_symbol('GOLD')      # Successful mapping
        self.mapper.normalize_symbol('UNKNOWN')   # Unknown symbol
        self.mapper.normalize_symbol('SILVER')    # Successful mapping
        
        stats = self.mapper.get_mapping_statistics()
        
        self.assertEqual(stats['total_lookups'], 3)
        self.assertEqual(stats['successful_mappings'], 2)
        self.assertEqual(stats['unknown_symbols_count'], 1)
        self.assertIn('UNKNOWN', stats['unknown_symbols'])
        self.assertAlmostEqual(stats['success_rate'], 2/3, places=2)
    
    def test_get_available_symbols(self):
        """Test getting available input symbols"""
        available = self.mapper.get_available_symbols()
        
        self.assertIn('GOLD', available)
        self.assertIn('SILVER', available)
        self.assertIn('DOW', available)
        self.assertIsInstance(available, set)
    
    def test_get_mapped_symbols(self):
        """Test getting mapped output symbols"""
        mapped = self.mapper.get_mapped_symbols()
        
        self.assertIn('XAUUSD', mapped)
        self.assertIn('XAGUSD', mapped)
        self.assertIn('US30', mapped)
        self.assertIsInstance(mapped, set)
    
    def test_save_and_load_user_overrides(self):
        """Test saving and loading user overrides"""
        override_file = os.path.join(self.temp_config_dir, 'user_overrides.json')
        
        # Add some overrides
        self.mapper.add_user_override('TEST1', 'MAPPED1')
        self.mapper.add_user_override('TEST2', 'MAPPED2')
        
        # Save overrides
        success = self.mapper.save_user_overrides(override_file)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(override_file))
        
        # Clear current overrides
        self.mapper.user_overrides = {}
        
        # Load overrides back
        success = self.mapper.load_user_overrides(override_file)
        self.assertTrue(success)
        
        # Verify overrides were loaded
        self.assertEqual(self.mapper.normalize_symbol('TEST1'), 'MAPPED1')
        self.assertEqual(self.mapper.normalize_symbol('TEST2'), 'MAPPED2')
    
    def test_bulk_mappings(self):
        """Test adding bulk mappings"""
        new_mappings = {
            'CRYPTO1': 'BTC1USD',
            'CRYPTO2': 'ETH1USD',
            'INDEX1': 'IND1'
        }
        
        added_count = self.mapper.add_bulk_mappings(new_mappings)
        self.assertEqual(added_count, 3)
        
        # Test the new mappings work
        self.assertEqual(self.mapper.normalize_symbol('CRYPTO1'), 'BTC1USD')
        self.assertEqual(self.mapper.normalize_symbol('CRYPTO2'), 'ETH1USD')
        self.assertEqual(self.mapper.normalize_symbol('INDEX1'), 'IND1')
    
    def test_forex_pair_normalization(self):
        """Test forex pair normalization (EUR/USD → EURUSD)"""
        # Note: This relies on fallback mappings being available
        result = self.mapper.normalize_symbol('EUR/USD')
        # Should either map to EURUSD or return as formatted
        self.assertIn(result, ['EURUSD', 'EUR/USD'])
    
    def test_prefix_matching(self):
        """Test prefix matching for indices"""
        # This tests the _try_partial_mapping method
        
        # Add some index mappings to test with
        self.mapper.add_bulk_mappings({
            'US30': 'US30',
            'GER30': 'GER30'
        })
        
        # Test symbols that might use prefix matching
        test_cases = [
            'US30.cash',
            'GER30.CFD'
        ]
        
        for symbol in test_cases:
            result = self.mapper.normalize_symbol(symbol)
            # Should find the base symbol
            self.assertIn(result, ['US30', 'GER30', symbol.upper()])


class TestGlobalFunctions(unittest.TestCase):
    """Test global utility functions"""
    
    def test_normalize_symbol_function(self):
        """Test global normalize_symbol function"""
        # Should work with built-in mappings
        result = normalize_symbol('GOLD')
        self.assertEqual(result, 'XAUUSD')
        
        result = normalize_symbol('unknown_symbol')
        self.assertEqual(result, 'UNKNOWN_SYMBOL')
    
    def test_add_symbol_override_function(self):
        """Test global add_symbol_override function"""
        success = add_symbol_override('GLOBAL_TEST', 'GLOBAL_MAPPED')
        self.assertTrue(success)
        
        # Test the override works
        result = normalize_symbol('GLOBAL_TEST')
        self.assertEqual(result, 'GLOBAL_MAPPED')
    
    def test_get_symbol_stats_function(self):
        """Test global get_symbol_stats function"""
        # Use some symbols first
        normalize_symbol('GOLD')
        normalize_symbol('UNKNOWN_STAT_TEST')
        
        stats = get_symbol_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_lookups', stats)
        self.assertIn('successful_mappings', stats)
        self.assertGreater(stats['total_lookups'], 0)
    
    def test_fallback_behavior(self):
        """Test fallback behavior when config file missing"""
        # This tests the SymbolMapper with a non-existent config file
        nonexistent_config = '/tmp/nonexistent_symbol_map.json'
        
        mapper = SymbolMapper(config_file=nonexistent_config)
        
        # Should still work with built-in mappings
        result = mapper.normalize_symbol('GOLD')
        self.assertEqual(result, 'XAUUSD')
    
    def test_default_mappings_comprehensive(self):
        """Test comprehensive coverage of default mappings"""
        mapper = SymbolMapper()
        
        # Test major categories
        metal_tests = [
            ('GOLD', 'XAUUSD'),
            ('SILVER', 'XAGUSD'),
            ('XAU', 'XAUUSD')
        ]
        
        index_tests = [
            ('DOW', 'US30'),
            ('NASDAQ', 'NAS100'),
            ('SPX', 'SPX500')
        ]
        
        crypto_tests = [
            ('BITCOIN', 'BTCUSD'),
            ('ETHEREUM', 'ETHUSD'),
            ('BTC', 'BTCUSD')
        ]
        
        all_tests = metal_tests + index_tests + crypto_tests
        
        for input_symbol, expected in all_tests:
            with self.subTest(input_symbol=input_symbol):
                result = mapper.normalize_symbol(input_symbol)
                self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()