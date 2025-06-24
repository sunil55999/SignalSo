"""
Test Suite for Signal Parser
Tests multilingual parsing, NLP capabilities, and confidence scoring
"""

import unittest
import json
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser import (
    SignalParser, ParsedSignal, ParserConfig, OrderType, SignalDirection,
    parse_signal, extract_signal_data
)


class TestSignalParser(unittest.TestCase):
    """Unit tests for Signal Parser"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'signal_parser': {
                'confidence_threshold': 0.7,
                'enable_nlp': True,
                'enable_regex_fallback': True,
                'enable_multilingual': True,
                'log_failed_parses': True,
                'dry_run_mode': False,
                'max_tp_levels': 3
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        self.parser = SignalParser(config_file=self.temp_config.name)
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
    
    def test_basic_signal_parsing(self):
        """Test basic signal parsing functionality"""
        signal_text = "Buy GOLD at 2355 SL 2349 TP 2362"
        
        result = self.parser.parse_signal(signal_text)
        
        self.assertEqual(result.symbol, "XAUUSD")
        self.assertEqual(result.direction, "BUY")
        self.assertEqual(result.entry, 2355.0)
        self.assertEqual(result.sl, 2349.0)
        self.assertIn(2362.0, result.tp)
        self.assertGreater(result.confidence, 0.7)
    
    def test_forex_pair_parsing(self):
        """Test forex pair signal parsing"""
        signal_text = "SELL EURUSD Entry: 1.0990 Stop: 1.0940 Target: 1.1060"
        
        result = self.parser.parse_signal(signal_text)
        
        self.assertEqual(result.symbol, "EURUSD")
        self.assertEqual(result.direction, "SELL")
        self.assertEqual(result.entry, 1.0990)
        self.assertEqual(result.sl, 1.0940)
        self.assertIn(1.1060, result.tp)
        self.assertGreater(result.confidence, 0.7)
    
    def test_limit_order_parsing(self):
        """Test limit order parsing"""
        signal_text = "BUY LIMIT GBPUSD @ 1.2850 SL 1.2800 TP1 1.2900 TP2 1.2950"
        
        result = self.parser.parse_signal(signal_text)
        
        self.assertEqual(result.symbol, "GBPUSD")
        self.assertEqual(result.direction, "BUY")
        self.assertEqual(result.order_type, "BUY_LIMIT")
        self.assertEqual(result.entry, 1.2850)
        self.assertEqual(result.sl, 1.2800)
        self.assertIn(1.2900, result.tp)
        self.assertIn(1.2950, result.tp)
    
    def test_multiple_tp_levels(self):
        """Test parsing multiple take profit levels"""
        signal_text = "BUY EURUSD 1.1000 SL 1.0950 TP1 1.1050 TP2 1.1100 TP3 1.1150"
        
        result = self.parser.parse_signal(signal_text)
        
        self.assertEqual(result.symbol, "EURUSD")
        self.assertEqual(len(result.tp), 3)
        self.assertIn(1.1050, result.tp)
        self.assertIn(1.1100, result.tp)
        self.assertIn(1.1150, result.tp)
    
    def test_range_entry_parsing(self):
        """Test entry range parsing"""
        signal_text = "LONG BTC 45000-45500 Stop 44000 Target 47000"
        
        result = self.parser.parse_signal(signal_text)
        
        self.assertEqual(result.symbol, "BTCUSD")
        self.assertEqual(result.direction, "BUY")  # LONG -> BUY
        self.assertEqual(result.entry, 45250.0)  # Average of range
        self.assertEqual(result.sl, 44000.0)
        self.assertIn(47000.0, result.tp)
    
    def test_arabic_signal_parsing(self):
        """Test Arabic language signal parsing"""
        signal_text = "بيع EURUSD دخول: 1.0990 وقف: 1.0940 هدف: 1.1060"
        
        result = self.parser.parse_signal(signal_text)
        
        self.assertEqual(result.symbol, "EURUSD")
        self.assertEqual(result.entry, 1.0990)
        self.assertEqual(result.sl, 1.0940)
        self.assertIn(1.1060, result.tp)
        self.assertGreater(result.confidence, 0.6)  # Multilingual may have slightly lower confidence
    
    def test_symbol_aliases(self):
        """Test symbol alias recognition"""
        test_cases = [
            ("Buy GOLD 2350", "XAUUSD"),
            ("Sell SILVER 25.50", "XAGUSD"),
            ("BTC LONG 45000", "BTCUSD"),
            ("ETH Short 3000", "ETHUSD"),
            ("US30 Buy 35000", "US30"),
            ("NAS100 Sell 15000", "NAS100")
        ]
        
        for signal_text, expected_symbol in test_cases:
            with self.subTest(signal_text=signal_text):
                result = self.parser.parse_signal(signal_text)
                self.assertEqual(result.symbol, expected_symbol)
    
    def test_confidence_scoring(self):
        """Test confidence scoring system"""
        test_cases = [
            # High confidence - complete signal
            ("BUY EURUSD 1.1000 SL 1.0950 TP 1.1050", 0.8),
            # Medium confidence - missing SL
            ("BUY EURUSD 1.1000 TP 1.1050", 0.6),
            # Lower confidence - minimal information
            ("BUY EURUSD", 0.4),
            # Very low confidence - unclear signal
            ("Something about trading", 0.2)
        ]
        
        for signal_text, min_confidence in test_cases:
            with self.subTest(signal_text=signal_text):
                result = self.parser.parse_signal(signal_text)
                if min_confidence > 0.5:
                    self.assertGreaterEqual(result.confidence, min_confidence)
                else:
                    # For low confidence signals, just check they're below threshold
                    self.assertLess(result.confidence, 0.7)
    
    def test_price_extraction_patterns(self):
        """Test various price extraction patterns"""
        test_cases = [
            # Standard format
            ("Entry: 1.1000 SL: 1.0950 TP: 1.1050", 1.1000, 1.0950, [1.1050]),
            # Abbreviated format
            ("@ 1.1000 SL 1.0950 TP 1.1050", 1.1000, 1.0950, [1.1050]),
            # Range format
            ("Entry 1.1000-1.1020 Stop 1.0950", 1.1010, 1.0950, []),
            # Multiple TPs
            ("Entry 1.1000 SL 1.0950 TP1 1.1030 TP2 1.1060", 1.1000, 1.0950, [1.1030, 1.1060])
        ]
        
        for signal_text, expected_entry, expected_sl, expected_tp in test_cases:
            with self.subTest(signal_text=signal_text):
                result = self.parser.parse_signal(signal_text)
                self.assertEqual(result.entry, expected_entry)
                self.assertEqual(result.sl, expected_sl)
                for tp in expected_tp:
                    self.assertIn(tp, result.tp)
    
    def test_multilingual_keywords(self):
        """Test multilingual keyword recognition"""
        multilingual_signals = [
            # Arabic
            "شراء EURUSD دخول 1.1000 وقف 1.0950",
            # Hindi (using Latin script for testing)
            "खरीदें EURUSD प्रवेश 1.1000",
            # Russian
            "КУПИТЬ EURUSD ВХОД 1.1000 СТОП 1.0950",
            # Chinese
            "买入 EURUSD 入场 1.1000 止损 1.0950"
        ]
        
        for signal in multilingual_signals:
            with self.subTest(signal=signal[:20]):
                result = self.parser.parse_signal(signal)
                # Should recognize as buy signal and extract EURUSD
                self.assertEqual(result.symbol, "EURUSD")
                self.assertGreater(result.confidence, 0.5)
    
    def test_order_type_detection(self):
        """Test different order type detection"""
        test_cases = [
            ("BUY LIMIT EURUSD 1.1000", "BUY_LIMIT"),
            ("SELL LIMIT GBPUSD 1.3000", "SELL_LIMIT"),
            ("BUY STOP USDJPY 110.00", "BUY_STOP"),
            ("SELL STOP AUDUSD 0.7500", "SELL_STOP"),
            ("BUY EURUSD 1.1000", "BUY"),  # Market order
            ("SELL GBPUSD 1.3000", "SELL")  # Market order
        ]
        
        for signal_text, expected_order_type in test_cases:
            with self.subTest(signal_text=signal_text):
                result = self.parser.parse_signal(signal_text)
                self.assertEqual(result.order_type, expected_order_type)
    
    def test_text_cleaning(self):
        """Test text cleaning and normalization"""
        dirty_signal = "🔥 BUY   GOLD  📈 @  2355   SL:2349 TP→2362 💰"
        clean_expected = "BUY GOLD @ 2355 SL:2349 TP→2362"
        
        cleaned = self.parser._clean_text(dirty_signal)
        
        # Should remove emojis and normalize whitespace
        self.assertNotIn('🔥', cleaned)
        self.assertNotIn('📈', cleaned)
        self.assertNotIn('💰', cleaned)
        self.assertNotRegex(cleaned, r'\s{2,}')  # No multiple spaces
    
    def test_failed_parse_handling(self):
        """Test handling of unparseable signals"""
        unclear_signals = [
            "",  # Empty signal
            "Random text with no trading information",
            "Maybe something about market but unclear",
            "BUY undefined symbol at unknown price"
        ]
        
        for signal in unclear_signals:
            with self.subTest(signal=signal[:20]):
                result = self.parser.parse_signal(signal)
                self.assertLess(result.confidence, 0.7)
                # Should not crash and should have some error information
                self.assertIsInstance(result, ParsedSignal)
    
    def test_dry_run_mode(self):
        """Test dry run mode functionality"""
        signal_text = "BUY EURUSD 1.1000 SL 1.0950 TP 1.1050"
        
        # Test with dry run enabled
        result = self.parser.parse_signal(signal_text, dry_run=True)
        self.assertIsInstance(result, ParsedSignal)
        
        # Test with dry run disabled
        result = self.parser.parse_signal(signal_text, dry_run=False)
        self.assertIsInstance(result, ParsedSignal)
    
    def test_custom_pattern_addition(self):
        """Test adding custom parsing patterns"""
        # Add custom symbol pattern
        success = self.parser.add_custom_pattern(
            'symbol', r'\bCUSTOM_PAIR\b', 'CUSTOMUSD', 0.9
        )
        self.assertTrue(success)
        
        # Test parsing with custom pattern
        result = self.parser.parse_signal("BUY CUSTOM_PAIR 1.0000")
        self.assertEqual(result.symbol, "CUSTOMUSD")
    
    def test_configuration_update(self):
        """Test configuration update functionality"""
        new_config = {
            'confidence_threshold': 0.8,
            'max_tp_levels': 5,
            'enable_multilingual': False
        }
        
        success = self.parser.update_configuration(new_config)
        
        self.assertTrue(success)
        self.assertEqual(self.parser.config.confidence_threshold, 0.8)
        self.assertEqual(self.parser.config.max_tp_levels, 5)
        self.assertFalse(self.parser.config.enable_multilingual)
    
    def test_statistics_tracking(self):
        """Test parsing statistics tracking"""
        initial_stats = self.parser.get_statistics()
        
        # Parse several signals
        test_signals = [
            "BUY EURUSD 1.1000 SL 1.0950 TP 1.1050",
            "SELL GBPUSD 1.3000 SL 1.3050 TP 1.2950",
            "Invalid signal text"
        ]
        
        for signal in test_signals:
            self.parser.parse_signal(signal)
        
        final_stats = self.parser.get_statistics()
        
        # Should have processed more signals
        self.assertGreater(
            final_stats['parse_stats']['total_parsed'],
            initial_stats['parse_stats']['total_parsed']
        )
        
        # Should have success rate information
        self.assertIn('success_rate', final_stats)
        self.assertIsInstance(final_stats['success_rate'], float)
    
    def test_legacy_compatibility_functions(self):
        """Test legacy compatibility functions"""
        signal_text = "BUY EURUSD 1.1000 SL 1.0950 TP 1.1050"
        
        # Test parse_signal function
        result_dict = parse_signal(signal_text, confidence_threshold=0.7)
        
        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict['symbol'], 'EURUSD')
        self.assertEqual(result_dict['direction'], 'BUY')
        self.assertEqual(result_dict['entry'], 1.1000)
        self.assertIn('success', result_dict)
        
        # Test extract_signal_data function
        result_obj = extract_signal_data(signal_text)
        
        self.assertIsInstance(result_obj, ParsedSignal)
        self.assertEqual(result_obj.symbol, 'EURUSD')
        self.assertEqual(result_obj.direction, 'BUY')
    
    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        edge_cases = [
            None,  # None input
            "",    # Empty string
            "   ",  # Whitespace only
            "BUY" * 1000,  # Very long text
            "BUY EURUSD 1.1000 SL abc TP xyz",  # Invalid numbers
            "૱ᅟᅳ𝗺𝗮𝗿𝗸𝗲𝘁",  # Unicode edge case
        ]
        
        for test_case in edge_cases:
            with self.subTest(test_case=str(test_case)[:20]):
                try:
                    if test_case is None:
                        # Handle None case separately
                        continue
                    result = self.parser.parse_signal(test_case)
                    # Should not crash
                    self.assertIsInstance(result, ParsedSignal)
                except Exception as e:
                    self.fail(f"Parser crashed on edge case: {test_case} - {e}")


class TestParserIntegration(unittest.TestCase):
    """Integration tests for parser with other modules"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.parser = SignalParser()
    
    def test_real_world_signals(self):
        """Test with real-world signal formats"""
        real_signals = [
            # Forex signals
            "🔥EURUSD🔥\n✅BUY\n📊Entry: 1.1045-1.1055\n❌SL: 1.1000\n🎯TP1: 1.1080\n🎯TP2: 1.1100\n🎯TP3: 1.1120",
            
            # Gold signal
            "GOLD SELL SIGNAL\nEntry: 2355.50\nStop Loss: 2362.00\nTake Profit: 2349.00\nR:R 1:2",
            
            # Crypto signal
            "BTC/USD LONG 🚀\nBuy Zone: $45,000 - $45,500\nStop: $44,000\nTargets: $47,000 | $48,500 | $50,000",
            
            # Index signal
            "US30 (Dow Jones)\nDirection: SELL\nEntry Price: 35,250\nStop Loss: 35,350\nTake Profit: 35,050",
            
            # Arabic signal
            "🔥 إشارة بيع ذهب 🔥\nالدخول: 2355\nوقف الخسارة: 2362\nجني الأرباح: 2349",
        ]
        
        for signal in real_signals:
            with self.subTest(signal=signal[:30]):
                result = self.parser.parse_signal(signal)
                
                # Should extract meaningful data
                self.assertIsNotNone(result.symbol)
                self.assertIsNotNone(result.direction)
                
                # Should have reasonable confidence
                if result.confidence >= 0.7:
                    self.assertIsNotNone(result.entry)
    
    def test_performance_benchmarking(self):
        """Test parser performance with large number of signals"""
        import time
        
        # Generate test signals
        signals = [
            f"BUY EURUSD {1.1000 + i*0.0001} SL {1.0950 + i*0.0001} TP {1.1050 + i*0.0001}"
            for i in range(100)
        ]
        
        start_time = time.time()
        
        results = []
        for signal in signals:
            result = self.parser.parse_signal(signal)
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process quickly (less than 2 seconds for 100 signals)
        self.assertLess(processing_time, 2.0)
        
        # Should have high success rate
        successful = sum(1 for r in results if r.confidence >= 0.7)
        success_rate = successful / len(results)
        self.assertGreater(success_rate, 0.95)
    
    def test_parser_registry_compatibility(self):
        """Test compatibility with parser registry pattern"""
        # Test that parser can be used in modular architecture
        parsers = {
            'default': SignalParser(),
            'strict': SignalParser(),
            'relaxed': SignalParser()
        }
        
        # Configure different parsers
        parsers['strict'].config.confidence_threshold = 0.9
        parsers['relaxed'].config.confidence_threshold = 0.5
        
        signal = "BUY EURUSD 1.1000"
        
        for name, parser in parsers.items():
            with self.subTest(parser=name):
                result = parser.parse_signal(signal)
                self.assertIsInstance(result, ParsedSignal)


if __name__ == '__main__':
    # Run specific test scenarios from task requirements
    print("Running specific test scenarios from task requirements...")
    
    parser = SignalParser()
    
    test_scenarios = [
        "Buy GOLD at 2355 SL 2349 TP 2362",
        "بيع EURUSD دخول: 1.0990 وقف: 1.0940 هدف: 1.1060",
        "SELL GBPUSD Entry 1.2850 Stop 1.2900 Target 1.2800",
        "Unclear message with no trading information"
    ]
    
    print("\nTest Results:")
    print("=" * 80)
    
    for i, signal in enumerate(test_scenarios, 1):
        result = parser.parse_signal(signal)
        print(f"Test {i}: {signal[:50]}...")
        print(f"Symbol: {result.symbol}")
        print(f"Direction: {result.direction}")
        print(f"Entry: {result.entry}")
        print(f"SL: {result.sl}")
        print(f"TP: {result.tp}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Parse Method: {result.parse_method}")
        if result.errors:
            print(f"Errors: {result.errors}")
        print("-" * 40)
    
    # Run unit tests
    unittest.main(verbosity=2)