"""
Test Suite for Entrypoint Range Handler
Tests multi-entry parsing, selection modes, and edge cases
"""

import unittest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from entrypoint_range_handler import (
    EntrypointRangeHandler, EntrySelectionMode, EntryRangeData, resolve_entry
)


class TestEntrypointRangeHandler(unittest.TestCase):
    """Unit tests for Entrypoint Range Handler"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        config_data = {
            'entrypoint_range': {
                'default_mode': 'best',
                'max_entries': 5,
                'precision_digits': 5,
                'fallback_to_first': True,
                'min_confidence_threshold': 0.7,
                'price_tolerance_pips': 2.0,
                'enable_logging': True
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        self.temp_log.close()
        
        self.handler = EntrypointRangeHandler(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_parse_range_entries_dash_format(self):
        """Test parsing entry ranges with dash format"""
        signal_text = "BUY EURUSD\nEntry: 1.1010 – 1.1050\nSL: 1.0980"
        
        entry_data = self.handler.parse_entry_text(signal_text)
        
        self.assertIsNotNone(entry_data)
        self.assertEqual(len(entry_data.entries), 3)  # Range should generate 3 entries
        self.assertAlmostEqual(entry_data.entries[0], 1.1010, places=5)
        self.assertAlmostEqual(entry_data.entries[1], 1.1030, places=5)  # Mid-point
        self.assertAlmostEqual(entry_data.entries[2], 1.1050, places=5)
        self.assertGreaterEqual(entry_data.confidence, 0.8)
    
    def test_parse_list_entries_comma_format(self):
        """Test parsing comma-separated entry lists"""
        signal_text = "SELL GBPUSD\nEntries: 1.2980, 1.3025, 1.3070\nSL: 1.3120"
        
        entry_data = self.handler.parse_entry_text(signal_text)
        
        self.assertIsNotNone(entry_data)
        self.assertEqual(len(entry_data.entries), 3)
        self.assertAlmostEqual(entry_data.entries[0], 1.2980, places=5)
        self.assertAlmostEqual(entry_data.entries[1], 1.3025, places=5)
        self.assertAlmostEqual(entry_data.entries[2], 1.3070, places=5)
        self.assertGreaterEqual(entry_data.confidence, 0.9)
    
    def test_parse_zone_entries(self):
        """Test parsing entry zone format"""
        signal_text = "BUY USDJPY\nEntry zone: 110.20 - 110.50\nStop: 109.80"
        
        entry_data = self.handler.parse_entry_text(signal_text)
        
        self.assertIsNotNone(entry_data)
        self.assertEqual(len(entry_data.entries), 3)
        self.assertAlmostEqual(entry_data.entries[0], 110.20, places=5)
        self.assertAlmostEqual(entry_data.entries[2], 110.50, places=5)
    
    def test_parse_to_keyword_format(self):
        """Test parsing entries with 'to' keyword"""
        signal_text = "SELL EURUSD\nEntry: 1.0950 to 1.0980\nSL: 1.1020"
        
        entry_data = self.handler.parse_entry_text(signal_text)
        
        self.assertIsNotNone(entry_data)
        self.assertEqual(len(entry_data.entries), 3)
        self.assertAlmostEqual(entry_data.entries[0], 1.0950, places=5)
        self.assertAlmostEqual(entry_data.entries[2], 1.0980, places=5)
    
    def test_parse_slash_separated_entries(self):
        """Test parsing slash-separated entry lists"""
        signal_text = "BUY GBPUSD\nEntries: 1.2500/1.2525/1.2550\nSL: 1.2450"
        
        entry_data = self.handler.parse_entry_text(signal_text)
        
        self.assertIsNotNone(entry_data)
        self.assertEqual(len(entry_data.entries), 3)
        self.assertAlmostEqual(entry_data.entries[0], 1.2500, places=5)
        self.assertAlmostEqual(entry_data.entries[1], 1.2525, places=5)
        self.assertAlmostEqual(entry_data.entries[2], 1.2550, places=5)
    
    def test_resolve_entry_average_mode(self):
        """Test entry resolution with average mode"""
        entries = [1.1000, 1.1020, 1.1040]
        current_price = 1.1030
        
        result = self.handler.resolve_entry(entries, "average", current_price)
        
        expected_average = sum(entries) / len(entries)
        self.assertAlmostEqual(result, expected_average, places=5)
    
    def test_resolve_entry_best_mode(self):
        """Test entry resolution with best mode (closest to current price)"""
        entries = [1.1000, 1.1020, 1.1040, 1.1060]
        current_price = 1.1025
        
        result = self.handler.resolve_entry(entries, "best", current_price)
        
        # 1.1020 should be closest to 1.1025
        self.assertAlmostEqual(result, 1.1020, places=5)
    
    def test_resolve_entry_second_mode(self):
        """Test entry resolution with second mode"""
        entries = [1.1000, 1.1020, 1.1040]
        current_price = 1.1030
        
        result = self.handler.resolve_entry(entries, "second", current_price)
        
        # Second entry in sorted list should be 1.1020
        self.assertAlmostEqual(result, 1.1020, places=5)
    
    def test_resolve_entry_second_mode_insufficient_entries(self):
        """Test second mode fallback when only one entry available"""
        entries = [1.1020]
        current_price = 1.1030
        
        result = self.handler.resolve_entry(entries, "second", current_price)
        
        # Should fallback to first (and only) entry
        self.assertAlmostEqual(result, 1.1020, places=5)
    
    def test_resolve_entry_empty_list_fallback(self):
        """Test fallback behavior with empty entry list"""
        entries = []
        current_price = 1.1030
        
        result = self.handler.resolve_entry(entries, "best", current_price)
        
        # Should fallback to current price
        self.assertAlmostEqual(result, current_price, places=5)
    
    def test_mode_detection_from_signal_text(self):
        """Test automatic mode detection from signal text"""
        test_cases = [
            ("Entry: 1.1000-1.1020 average", EntrySelectionMode.AVERAGE),
            ("Best entry: 1.1000 to 1.1020", EntrySelectionMode.BEST),
            ("Second entry: 1.1000-1.1020", EntrySelectionMode.SECOND),
            ("Entry: 1.1000-1.1020", EntrySelectionMode.BEST)  # Default
        ]
        
        for signal_text, expected_mode in test_cases:
            with self.subTest(signal_text=signal_text):
                entry_data = self.handler.parse_entry_text(signal_text)
                self.assertIsNotNone(entry_data)
                self.assertEqual(entry_data.mode, expected_mode)
    
    def test_precision_handling(self):
        """Test that precision is handled correctly"""
        entries = [1.123456789, 1.987654321]
        current_price = 1.5
        
        result = self.handler.resolve_entry(entries, "average", current_price)
        
        # Result should be rounded to configured precision (5 digits)
        expected = round((1.123456789 + 1.987654321) / 2, 5)
        self.assertAlmostEqual(result, expected, places=5)
    
    def test_max_entries_limit(self):
        """Test that entry list is limited to max_entries configuration"""
        # Create signal with more than max_entries (5)
        signal_text = "Entries: 1.1000, 1.1010, 1.1020, 1.1030, 1.1040, 1.1050, 1.1060"
        
        entry_data = self.handler.parse_entry_text(signal_text)
        
        self.assertIsNotNone(entry_data)
        self.assertLessEqual(len(entry_data.entries), self.handler.config['max_entries'])
    
    def test_confidence_threshold_filtering(self):
        """Test that low confidence parses are rejected"""
        # Mock a low confidence pattern
        with patch.object(self.handler, '_initialize_entry_patterns') as mock_patterns:
            mock_patterns.return_value = [{
                'pattern': r'entry:\s*(\d+\.\d+)',
                'type': 'single',
                'confidence': 0.5  # Below threshold
            }]
            
            # Reinitialize with low confidence pattern
            self.handler.entry_patterns = mock_patterns.return_value
            
            result = self.handler.process_signal_entries("Entry: 1.1000", 1.1050)
            
            # Should fail due to low confidence
            self.assertFalse(result['success'])
            self.assertIn('confidence', result['fallback_reason'])
    
    def test_process_signal_entries_complete_workflow(self):
        """Test complete signal processing workflow"""
        signal_text = "BUY EURUSD\nEntry: 1.1010-1.1050 best\nSL: 1.0980\nTP: 1.1100"
        current_price = 1.1030
        
        result = self.handler.process_signal_entries(signal_text, current_price)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['mode_used'], 'best')
        self.assertEqual(len(result['entries_found']), 3)
        self.assertGreater(result['confidence'], 0.7)
        self.assertIsNone(result['fallback_reason'])
        
        # Best entry should be closest to current price (1.1030)
        # From range 1.1010-1.1050, middle entry (1.1030) should be closest
        self.assertAlmostEqual(result['entry_price'], 1.1030, places=5)
    
    def test_mode_override_functionality(self):
        """Test that mode override works correctly"""
        signal_text = "Entry: 1.1000, 1.1020, 1.1040"  # No mode specified in text
        current_price = 1.1030
        
        # Test with mode override
        result = self.handler.process_signal_entries(
            signal_text, current_price, mode_override="average"
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['mode_used'], 'average')
        
        # Should be average of three entries
        expected_avg = (1.1000 + 1.1020 + 1.1040) / 3
        self.assertAlmostEqual(result['entry_price'], expected_avg, places=5)
    
    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly"""
        initial_stats = self.handler.get_parsing_statistics()
        
        # Process some signals
        test_signals = [
            "Entry: 1.1000-1.1020",
            "Entries: 1.2000, 1.2020",
            "Invalid signal with no entries"
        ]
        
        for signal in test_signals:
            self.handler.process_signal_entries(signal, 1.1500)
        
        final_stats = self.handler.get_parsing_statistics()
        
        # Should have processed more signals
        self.assertGreater(
            final_stats['total_signals_parsed'],
            initial_stats['total_signals_parsed']
        )
    
    def test_fallback_logging(self):
        """Test that fallback events are logged correctly"""
        # Process a signal that should cause fallback
        result = self.handler.process_signal_entries("No entries here", 1.1000)
        
        self.assertFalse(result['success'])
        
        # Check that log file was written to
        with open(self.temp_log.name, 'r') as f:
            log_content = f.read()
            self.assertIn('ENTRYPOINT_FALLBACK', log_content)
    
    def test_configuration_update(self):
        """Test configuration update functionality"""
        new_config = {
            'default_mode': 'average',
            'max_entries': 10,
            'precision_digits': 3
        }
        
        success = self.handler.update_configuration(new_config)
        
        self.assertTrue(success)
        self.assertEqual(self.handler.config['default_mode'], 'average')
        self.assertEqual(self.handler.config['max_entries'], 10)
        self.assertEqual(self.handler.config['precision_digits'], 3)
    
    def test_legacy_resolve_entry_function(self):
        """Test legacy compatibility function"""
        entries = [1.1000, 1.1020, 1.1040]
        current_price = 1.1025
        
        result = resolve_entry(entries, "best", current_price)
        
        # Should return closest to current price
        self.assertAlmostEqual(result, 1.1020, places=5)


class TestEntrypointRangeHandlerIntegration(unittest.TestCase):
    """Integration tests for entrypoint range handler"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.handler = EntrypointRangeHandler()
    
    def test_real_world_signal_formats(self):
        """Test with real-world signal formats"""
        test_signals = [
            # Standard format
            "🔥 EURUSD SELL 📉\n\nEntry: 1.0850 - 1.0870\nSL: 1.0920\nTP1: 1.0800\nTP2: 1.0750",
            
            # Multiple entries
            "GBPUSD BUY\nEntries: 1.2650, 1.2670, 1.2690\nStop Loss: 1.2620\nTake Profit: 1.2750",
            
            # Zone format
            "USDJPY LONG\nEntry Zone: 110.20 to 110.50\nSL: 109.80\nTarget: 111.00",
            
            # Best entry format
            "EURUSD SHORT\nBest entry between 1.0980 and 1.1000\nSL: 1.1030\nTP: 1.0920",
            
            # Average entry format
            "GBPUSD BUY\nEntry range: 1.2500/1.2520/1.2540 (average)\nSL: 1.2450\nTP: 1.2600"
        ]
        
        current_price = 1.1000
        
        for i, signal in enumerate(test_signals):
            with self.subTest(signal_index=i):
                result = self.handler.process_signal_entries(signal, current_price)
                
                # All should parse successfully
                self.assertTrue(result['success'], 
                              f"Signal {i} failed: {result.get('fallback_reason')}")
                self.assertGreater(result['confidence'], 0.7)
                self.assertIsInstance(result['entry_price'], float)
                self.assertGreater(len(result['entries_found']), 0)
    
    def test_edge_case_scenarios(self):
        """Test edge cases and error scenarios"""
        edge_cases = [
            ("", 1.1000, False),  # Empty signal
            ("No entry information", 1.1000, False),  # No entries
            ("Entry: invalid_price", 1.1000, False),  # Invalid price format
            ("Entry: 1.1000", 1.1000, True),  # Single entry (should work)
            ("Entry: -1.1000", 1.1000, False),  # Negative price (should be invalid)
            ("Entry: 0.0000", 1.1000, False),  # Zero price
        ]
        
        for signal, current_price, should_succeed in edge_cases:
            with self.subTest(signal=signal[:20]):
                result = self.handler.process_signal_entries(signal, current_price)
                self.assertEqual(result['success'], should_succeed)
    
    def test_performance_with_large_dataset(self):
        """Test performance with many signals"""
        import time
        
        # Generate test signals
        test_signals = []
        for i in range(100):
            price1 = 1.1000 + (i * 0.0001)
            price2 = price1 + 0.0020
            signal = f"Entry: {price1:.4f} - {price2:.4f}"
            test_signals.append(signal)
        
        start_time = time.time()
        
        successful_parses = 0
        for signal in test_signals:
            result = self.handler.process_signal_entries(signal, 1.1000)
            if result['success']:
                successful_parses += 1
        
        end_time = time.time()
        
        # Should process quickly and successfully
        processing_time = end_time - start_time
        self.assertLess(processing_time, 5.0, "Processing took too long")
        self.assertGreater(successful_parses, 90, "Too many parsing failures")
    
    def test_test_entry_parsing_method(self):
        """Test the built-in test method"""
        test_signals = [
            "Entry: 1.1000-1.1020",
            "Entries: 1.2000, 1.2020, 1.2040",
            "Entry zone: 110.20 to 110.50"
        ]
        
        test_results = self.handler.test_entry_parsing(test_signals)
        
        self.assertIn('test_summary', test_results)
        self.assertIn('individual_results', test_results)
        self.assertEqual(test_results['test_summary']['total_tests'], 3)
        self.assertGreater(test_results['test_summary']['success_rate'], 80)


if __name__ == '__main__':
    unittest.main()