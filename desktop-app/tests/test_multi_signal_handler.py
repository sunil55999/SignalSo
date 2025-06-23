"""
Test Suite for Multi-Signal Handler Engine
Tests signal prioritization, merging, conflict resolution, and provider management
"""

import unittest
import asyncio
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multi_signal_handler import (
    MultiSignalHandler, IncomingSignal, SignalDirection, SignalPriority,
    SignalStatus, ConflictResolution, ProviderProfile, ConflictGroup
)

class TestMultiSignalHandler(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "multi_signal_handler": {
                "enabled": True,
                "processing_interval": 0.1,  # Fast for testing
                "signal_expiry_minutes": 5,
                "max_signals_per_symbol": 5,
                "conflict_resolution_method": "highest_priority",
                "enable_signal_merging": True,
                "merge_tolerance_pips": 5.0,
                "confidence_threshold": 0.3,
                "provider_weights": {
                    "premium_provider": 2.0,
                    "standard_provider": 1.0,
                    "trial_provider": 0.5
                },
                "priority_mappings": {
                    "vip_provider": "critical",
                    "premium_provider": "high",
                    "standard_provider": "medium",
                    "trial_provider": "low"
                },
                "symbol_settings": {
                    "EURUSD": {
                        "max_concurrent_signals": 3,
                        "merge_tolerance_pips": 3.0,
                        "priority_boost": 0.1
                    }
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize multi-signal handler
        self.handler = MultiSignalHandler(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
    def tearDown(self):
        """Clean up test environment"""
        self.handler.stop_processing()
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
        # Clean up data files if created
        for suffix in ['_signals.json', '_providers.json']:
            data_file = self.temp_log.name.replace('.log', suffix)
            if os.path.exists(data_file):
                os.unlink(data_file)

class TestBasicFunctionality(TestMultiSignalHandler):
    """Test basic multi-signal handler functionality"""
    
    def test_initialization(self):
        """Test multi-signal handler initialization"""
        self.assertTrue(self.handler.config['enabled'])
        self.assertEqual(self.handler.config['max_signals_per_symbol'], 5)
        self.assertEqual(self.handler.config['conflict_resolution_method'], 'highest_priority')
        
    def test_provider_weight_calculation(self):
        """Test provider weight calculation"""
        # Test configured weight
        weight = self.handler._get_provider_weight('premium_provider')
        self.assertEqual(weight, 2.0)
        
        # Test default weight
        weight = self.handler._get_provider_weight('unknown_provider')
        self.assertEqual(weight, 1.0)
        
    def test_signal_priority_determination(self):
        """Test signal priority determination"""
        # Test configured priority mapping
        priority = self.handler._get_signal_priority('vip_provider', 0.8)
        self.assertEqual(priority, SignalPriority.CRITICAL)
        
        # Test confidence-based priority
        priority = self.handler._get_signal_priority('unknown_provider', 0.9)
        self.assertEqual(priority, SignalPriority.CRITICAL)
        
        priority = self.handler._get_signal_priority('unknown_provider', 0.3)
        self.assertEqual(priority, SignalPriority.LOW)
        
    def test_signal_score_calculation(self):
        """Test signal score calculation"""
        signal = IncomingSignal(
            signal_id="test_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            confidence=0.8,
            provider_id="premium_provider",
            provider_name="Premium Provider",
            priority=SignalPriority.HIGH,
            timestamp=datetime.now()
        )
        
        score = self.handler._calculate_signal_score(signal)
        
        # Should be higher than base confidence due to provider weight and priority
        self.assertGreater(score, 0.8)

class TestSignalManagement(TestMultiSignalHandler):
    """Test signal addition and management"""
    
    def test_add_signal_success(self):
        """Test successful signal addition"""
        signal_data = {
            "signal_id": "test_001",
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1050,
            "volume": 0.1,
            "confidence": 0.8,
            "provider_id": "test_provider",
            "provider_name": "Test Provider"
        }
        
        success = self.handler.add_signal(signal_data)
        
        self.assertTrue(success)
        self.assertIn("EURUSD", self.handler.pending_signals)
        self.assertEqual(len(self.handler.pending_signals["EURUSD"]), 1)
        self.assertEqual(self.handler.processing_stats["total_signals"], 1)
        
    def test_add_signal_low_confidence(self):
        """Test signal rejection due to low confidence"""
        signal_data = {
            "signal_id": "test_002",
            "symbol": "EURUSD",
            "direction": "buy",
            "confidence": 0.2,  # Below threshold
            "provider_id": "test_provider",
            "provider_name": "Test Provider"
        }
        
        success = self.handler.add_signal(signal_data)
        
        self.assertFalse(success)
        self.assertEqual(self.handler.processing_stats["rejected_signals"], 1)
        
    def test_add_signal_limit_enforcement(self):
        """Test signal limit enforcement per symbol"""
        # Add signals up to the limit (3 for EURUSD)
        for i in range(4):  # Try to add 4 signals
            signal_data = {
                "signal_id": f"test_{i:03d}",
                "symbol": "EURUSD",
                "direction": "buy",
                "confidence": 0.8,
                "provider_id": f"provider_{i}",
                "provider_name": f"Provider {i}"
            }
            self.handler.add_signal(signal_data)
            
        # Should only have 3 signals (the limit)
        self.assertEqual(len(self.handler.pending_signals["EURUSD"]), 3)
        
        # The first signal should have been removed
        signal_ids = [sig.signal_id for sig in self.handler.pending_signals["EURUSD"]]
        self.assertNotIn("test_000", signal_ids)
        
    def test_provider_profile_update(self):
        """Test provider profile updates"""
        signal_data = {
            "signal_id": "test_003",
            "symbol": "EURUSD",
            "direction": "buy",
            "confidence": 0.9,
            "provider_id": "new_provider",
            "provider_name": "New Provider"
        }
        
        self.handler.add_signal(signal_data)
        
        # Check provider profile was created
        self.assertIn("new_provider", self.handler.provider_profiles)
        
        profile = self.handler.provider_profiles["new_provider"]
        self.assertEqual(profile.signal_count, 1)
        self.assertEqual(profile.avg_confidence, 0.9)

class TestSignalCompatibility(TestMultiSignalHandler):
    """Test signal compatibility checking and merging"""
    
    def test_signal_compatibility_same_direction(self):
        """Test compatibility check for signals in same direction"""
        signal1 = IncomingSignal(
            signal_id="test_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            confidence=0.8,
            provider_id="provider_1",
            provider_name="Provider 1",
            priority=SignalPriority.HIGH,
            timestamp=datetime.now()
        )
        
        signal2 = IncomingSignal(
            signal_id="test_002",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1002,  # Close price
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            confidence=0.7,
            provider_id="provider_2",
            provider_name="Provider 2",
            priority=SignalPriority.MEDIUM,
            timestamp=datetime.now()
        )
        
        compatible = self.handler._check_signal_compatibility(signal1, signal2)
        self.assertTrue(compatible)
        
    def test_signal_compatibility_different_direction(self):
        """Test compatibility check for signals in different directions"""
        signal1 = IncomingSignal(
            signal_id="test_003",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            confidence=0.8,
            provider_id="provider_1",
            provider_name="Provider 1",
            priority=SignalPriority.HIGH,
            timestamp=datetime.now()
        )
        
        signal2 = IncomingSignal(
            signal_id="test_004",
            symbol="EURUSD",
            direction=SignalDirection.SELL,  # Different direction
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0950,
            volume=0.1,
            confidence=0.7,
            provider_id="provider_2",
            provider_name="Provider 2",
            priority=SignalPriority.MEDIUM,
            timestamp=datetime.now()
        )
        
        compatible = self.handler._check_signal_compatibility(signal1, signal2)
        self.assertFalse(compatible)
        
    def test_signal_compatibility_price_difference(self):
        """Test compatibility check for signals with large price differences"""
        signal1 = IncomingSignal(
            signal_id="test_005",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            confidence=0.8,
            provider_id="provider_1",
            provider_name="Provider 1",
            priority=SignalPriority.HIGH,
            timestamp=datetime.now()
        )
        
        signal2 = IncomingSignal(
            signal_id="test_006",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1020,  # Large price difference (20 pips)
            stop_loss=1.0970,
            take_profit=1.1070,
            volume=0.1,
            confidence=0.7,
            provider_id="provider_2",
            provider_name="Provider 2",
            priority=SignalPriority.MEDIUM,
            timestamp=datetime.now()
        )
        
        compatible = self.handler._check_signal_compatibility(signal1, signal2)
        self.assertFalse(compatible)  # Should not be compatible due to large price difference
        
    def test_merge_compatible_signals(self):
        """Test merging of compatible signals"""
        signal1 = IncomingSignal(
            signal_id="test_007",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            confidence=0.8,
            provider_id="provider_1",
            provider_name="Provider 1",
            priority=SignalPriority.HIGH,
            timestamp=datetime.now()
        )
        
        signal2 = IncomingSignal(
            signal_id="test_008",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1002,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            confidence=0.7,
            provider_id="provider_2",
            provider_name="Provider 2",
            priority=SignalPriority.MEDIUM,
            timestamp=datetime.now()
        )
        
        merged = self.handler._merge_compatible_signals([signal1, signal2])
        
        self.assertEqual(merged.symbol, "EURUSD")
        self.assertEqual(merged.direction, SignalDirection.BUY)
        self.assertEqual(merged.priority, SignalPriority.HIGH)  # Highest priority
        self.assertEqual(merged.confidence, 0.8)  # Highest confidence
        self.assertIn("merged", merged.signal_id)
        self.assertIn("merged_from", merged.metadata)

class TestConflictDetection(TestMultiSignalHandler):
    """Test conflict detection and resolution"""
    
    def test_identify_directional_conflict(self):
        """Test identification of directional conflicts"""
        buy_signal = IncomingSignal(
            signal_id="test_buy",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            confidence=0.8,
            provider_id="provider_1",
            provider_name="Provider 1",
            priority=SignalPriority.HIGH,
            timestamp=datetime.now()
        )
        
        sell_signal = IncomingSignal(
            signal_id="test_sell",
            symbol="EURUSD",
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0950,
            volume=0.1,
            confidence=0.7,
            provider_id="provider_2",
            provider_name="Provider 2",
            priority=SignalPriority.MEDIUM,
            timestamp=datetime.now()
        )
        
        conflicts = self.handler._identify_conflicts([buy_signal, sell_signal])
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].conflict_type, "directional_conflict")
        self.assertEqual(len(conflicts[0].signals), 2)
        
    def test_resolve_conflict_highest_priority(self):
        """Test conflict resolution using highest priority method"""
        high_priority_signal = IncomingSignal(
            signal_id="test_high",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            confidence=0.7,
            provider_id="vip_provider",
            provider_name="VIP Provider",
            priority=SignalPriority.CRITICAL,
            timestamp=datetime.now()
        )
        
        low_priority_signal = IncomingSignal(
            signal_id="test_low",
            symbol="EURUSD",
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0950,
            volume=0.1,
            confidence=0.9,  # Higher confidence but lower priority
            provider_id="trial_provider",
            provider_name="Trial Provider",
            priority=SignalPriority.LOW,
            timestamp=datetime.now()
        )
        
        conflict = ConflictGroup(
            symbol="EURUSD",
            signals=[high_priority_signal, low_priority_signal],
            conflict_type="directional_conflict",
            identified_time=datetime.now(),
            resolution_method=ConflictResolution.HIGHEST_PRIORITY
        )
        
        result = self.handler._resolve_conflict(conflict)
        
        self.assertEqual(result.final_signal.signal_id, "test_high")
        self.assertEqual(result.status, SignalStatus.PROCESSED)
        self.assertIn("Highest priority", result.processing_reason)
        
    def test_resolve_conflict_highest_confidence(self):
        """Test conflict resolution using highest confidence method"""
        high_confidence_signal = IncomingSignal(
            signal_id="test_high_conf",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            confidence=0.95,
            provider_id="provider_1",
            provider_name="Provider 1",
            priority=SignalPriority.MEDIUM,
            timestamp=datetime.now()
        )
        
        low_confidence_signal = IncomingSignal(
            signal_id="test_low_conf",
            symbol="EURUSD",
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0950,
            volume=0.1,
            confidence=0.5,
            provider_id="provider_2",
            provider_name="Provider 2",
            priority=SignalPriority.HIGH,  # Higher priority but lower confidence
            timestamp=datetime.now()
        )
        
        conflict = ConflictGroup(
            symbol="EURUSD",
            signals=[high_confidence_signal, low_confidence_signal],
            conflict_type="directional_conflict",
            identified_time=datetime.now(),
            resolution_method=ConflictResolution.HIGHEST_CONFIDENCE
        )
        
        result = self.handler._resolve_conflict(conflict)
        
        self.assertEqual(result.final_signal.signal_id, "test_high_conf")
        self.assertIn("Highest confidence", result.processing_reason)

class TestSignalProcessing(TestMultiSignalHandler):
    """Test complete signal processing workflow"""
    
    def test_add_and_process_single_signal(self):
        """Test adding and processing a single signal"""
        async def run_test():
            signal_data = {
                "signal_id": "test_single",
                "symbol": "EURUSD",
                "direction": "buy",
                "entry_price": 1.1000,
                "confidence": 0.8,
                "provider_id": "test_provider"
            }
            
            # Add signal
            success = self.handler.add_signal(signal_data)
            self.assertTrue(success)
            
            # Start processing
            self.handler.start_processing()
            
            # Wait for processing
            await asyncio.sleep(0.2)
            
            # Check results
            processed_signals = self.handler.get_processed_signals()
            self.assertEqual(len(processed_signals), 1)
            
            processed = processed_signals[0]
            self.assertEqual(processed['symbol'], 'EURUSD')
            self.assertEqual(processed['status'], 'processed')
            
            # Stop processing
            self.handler.stop_processing()
            
        asyncio.run(run_test())
        
    def test_process_mergeable_signals(self):
        """Test processing of mergeable signals"""
        async def run_test():
            # Add compatible signals
            for i in range(2):
                signal_data = {
                    "signal_id": f"test_merge_{i}",
                    "symbol": "EURUSD",
                    "direction": "buy",
                    "entry_price": 1.1000 + i * 0.00001,  # Very close prices
                    "confidence": 0.8,
                    "provider_id": f"provider_{i}"
                }
                self.handler.add_signal(signal_data)
                
            # Start processing
            self.handler.start_processing()
            
            # Wait for processing
            await asyncio.sleep(0.2)
            
            # Check results
            processed_signals = self.handler.get_processed_signals()
            self.assertEqual(len(processed_signals), 1)
            
            processed = processed_signals[0]
            self.assertEqual(processed['status'], 'merged')
            self.assertEqual(len(processed['merged_signals']), 2)
            
            # Stop processing
            self.handler.stop_processing()
            
        asyncio.run(run_test())

class TestStatistics(TestMultiSignalHandler):
    """Test statistics and reporting functionality"""
    
    def test_get_statistics(self):
        """Test getting processing statistics"""
        # Add some signals
        for i in range(3):
            signal_data = {
                "signal_id": f"test_stats_{i}",
                "symbol": "EURUSD",
                "direction": "buy",
                "confidence": 0.8,
                "provider_id": f"provider_{i}"
            }
            self.handler.add_signal(signal_data)
            
        stats = self.handler.get_statistics()
        
        self.assertEqual(stats['total_signals'], 3)
        self.assertEqual(stats['pending_signals'], 3)
        self.assertEqual(stats['provider_count'], 3)
        
    def test_get_provider_statistics(self):
        """Test getting provider statistics"""
        # Add signals from different providers
        signal_data_1 = {
            "signal_id": "test_prov_1",
            "symbol": "EURUSD",
            "direction": "buy",
            "confidence": 0.9,
            "provider_id": "premium_provider",
            "provider_name": "Premium Provider"
        }
        
        signal_data_2 = {
            "signal_id": "test_prov_2",
            "symbol": "GBPUSD",
            "direction": "sell",
            "confidence": 0.6,
            "provider_id": "standard_provider",
            "provider_name": "Standard Provider"
        }
        
        self.handler.add_signal(signal_data_1)
        self.handler.add_signal(signal_data_2)
        
        provider_stats = self.handler.get_provider_statistics()
        
        self.assertIn('premium_provider', provider_stats)
        self.assertIn('standard_provider', provider_stats)
        
        premium_stats = provider_stats['premium_provider']
        self.assertEqual(premium_stats['signal_count'], 1)
        self.assertEqual(premium_stats['avg_confidence'], 0.9)
        self.assertEqual(premium_stats['weight'], 2.0)  # From config
        
    def test_get_pending_signals(self):
        """Test getting pending signals"""
        # Add signals for different symbols
        signal_data_1 = {
            "signal_id": "test_pending_1",
            "symbol": "EURUSD",
            "direction": "buy",
            "confidence": 0.8,
            "provider_id": "provider_1"
        }
        
        signal_data_2 = {
            "signal_id": "test_pending_2",
            "symbol": "GBPUSD",
            "direction": "sell",
            "confidence": 0.7,
            "provider_id": "provider_2"
        }
        
        self.handler.add_signal(signal_data_1)
        self.handler.add_signal(signal_data_2)
        
        pending = self.handler.get_pending_signals()
        
        self.assertIn('EURUSD', pending)
        self.assertIn('GBPUSD', pending)
        self.assertEqual(len(pending['EURUSD']), 1)
        self.assertEqual(len(pending['GBPUSD']), 1)
        
        eurusd_signal = pending['EURUSD'][0]
        self.assertEqual(eurusd_signal['signal_id'], 'test_pending_1')
        self.assertEqual(eurusd_signal['direction'], 'buy')

if __name__ == '__main__':
    unittest.main()