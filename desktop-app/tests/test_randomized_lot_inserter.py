"""
Tests for Randomized Lot Inserter functionality
Tests the lot size randomization for prop firm stealth operations
"""

import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

# Import the module to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from randomized_lot_inserter import RandomizedLotInserter, LotRandomizationConfig, LotRandomizationResult

class TestRandomizedLotInserter:
    
    def setup_method(self):
        """Setup test environment with temporary files"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        self.history_file = os.path.join(self.temp_dir, "test_history.json")
        
        # Create test inserter
        self.inserter = RandomizedLotInserter(
            config_file=self.config_file,
            history_file=self.history_file
        )
        
        # Mock modules
        self.mock_mt5_bridge = Mock()
        self.mock_copilot_bot = Mock()
        self.inserter.inject_modules(
            mt5_bridge=self.mock_mt5_bridge,
            copilot_bot=self.mock_copilot_bot
        )
    
    def teardown_method(self):
        """Cleanup temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_default_configuration_creation(self):
        """Test default configuration is created properly"""
        config = self.inserter.config
        
        assert config.enabled == True
        assert config.variance_range == 0.003
        assert config.min_lot_size == 0.01
        assert config.max_lot_size == 10.0
        assert config.rounding_enabled == True
        assert config.rounding_precision == 3
        assert config.avoid_repeats == True
    
    def test_basic_lot_randomization_within_bounds(self):
        """Test basic lot randomization stays within configured bounds"""
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': 0.10,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat(),
            'signal_id': 'test_001'
        }
        
        result = self.inserter.randomize_lot_size(signal_data)
        
        assert result.original_lot == 0.10
        assert result.randomized_lot != result.original_lot  # Should be different
        assert abs(result.variance_applied) <= self.inserter.config.variance_range
        assert result.symbol == 'EURUSD'
        assert result.signal_id == 'test_001'
        
        # Check bounds
        expected_min = 0.10 - self.inserter.config.variance_range
        expected_max = 0.10 + self.inserter.config.variance_range
        assert expected_min <= result.randomized_lot <= expected_max
    
    def test_deterministic_randomization_with_same_seed(self):
        """Test that same signal data produces same randomization"""
        signal_data = {
            'symbol': 'GBPUSD',
            'lot_size': 0.05,
            'entry': 1.2750,
            'action': 'SELL',
            'timestamp': '2025-06-23T10:00:00',
            'signal_id': 'consistent_test'
        }
        
        result1 = self.inserter.randomize_lot_size(signal_data)
        
        # Create new inserter instance to ensure reproducibility
        inserter2 = RandomizedLotInserter(
            config_file=self.config_file,
            history_file=os.path.join(self.temp_dir, "test_history2.json")
        )
        result2 = inserter2.randomize_lot_size(signal_data)
        
        assert result1.randomized_lot == result2.randomized_lot
        assert result1.variance_applied == result2.variance_applied
        assert result1.seed_used == result2.seed_used
    
    def test_different_signals_produce_different_results(self):
        """Test that different signals produce different randomization"""
        signal1 = {
            'symbol': 'EURUSD',
            'lot_size': 0.10,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': '2025-06-23T10:00:00'
        }
        
        signal2 = {
            'symbol': 'GBPUSD',
            'lot_size': 0.10,
            'entry': 1.2750,
            'action': 'SELL',
            'timestamp': '2025-06-23T10:05:00'
        }
        
        result1 = self.inserter.randomize_lot_size(signal1)
        result2 = self.inserter.randomize_lot_size(signal2)
        
        # Should produce different results due to different seed components
        assert result1.randomized_lot != result2.randomized_lot
        assert result1.seed_used != result2.seed_used
    
    def test_variance_range_configuration(self):
        """Test custom variance range is respected"""
        # Update config to larger variance range
        self.inserter.update_config({'variance_range': 0.01})
        
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': 0.10,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat()
        }
        
        result = self.inserter.randomize_lot_size(signal_data)
        
        # Variance should be within new range
        assert abs(result.variance_applied) <= 0.01
        
        # Check bounds with new range
        expected_min = 0.10 - 0.01
        expected_max = 0.10 + 0.01
        assert expected_min <= result.randomized_lot <= expected_max
    
    def test_rounding_functionality(self):
        """Test lot size rounding when enabled"""
        # Ensure rounding is enabled with 3 decimal precision
        self.inserter.update_config({
            'rounding_enabled': True,
            'rounding_precision': 3
        })
        
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': 0.10,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat()
        }
        
        result = self.inserter.randomize_lot_size(signal_data)
        
        # Check that result is rounded to 3 decimal places
        rounded_check = round(result.randomized_lot, 3)
        assert result.randomized_lot == rounded_check
    
    def test_rounding_disabled(self):
        """Test behavior when rounding is disabled"""
        self.inserter.update_config({'rounding_enabled': False})
        
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': 0.10,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat()
        }
        
        result = self.inserter.randomize_lot_size(signal_data)
        
        # Result might have more precision when rounding is disabled
        # We just check it's still within bounds
        assert abs(result.variance_applied) <= self.inserter.config.variance_range
    
    def test_lot_size_bounds_validation(self):
        """Test lot size validation against min/max bounds"""
        # Test with very small lot that might go below minimum
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': 0.011,  # Close to minimum
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat()
        }
        
        result = self.inserter.randomize_lot_size(signal_data)
        
        # Result should not go below minimum
        assert result.randomized_lot >= self.inserter.config.min_lot_size
        
        # Test with large lot size
        signal_data['lot_size'] = 9.99  # Close to maximum
        result = self.inserter.randomize_lot_size(signal_data)
        
        # Result should not exceed maximum
        assert result.randomized_lot <= self.inserter.config.max_lot_size
    
    def test_repeat_avoidance(self):
        """Test that repeat lot sizes are avoided when enabled"""
        self.inserter.update_config({
            'avoid_repeats': True,
            'variance_range': 0.001  # Small range to make repeats more likely
        })
        
        base_signal = {
            'symbol': 'EURUSD',
            'lot_size': 0.10,
            'entry': 1.0850,
            'action': 'BUY'
        }
        
        results = []
        # Generate multiple randomizations for same symbol
        for i in range(5):
            signal_data = base_signal.copy()
            signal_data['timestamp'] = f"2025-06-23T10:0{i}:00"
            signal_data['signal_id'] = f"test_{i:03d}"
            
            result = self.inserter.randomize_lot_size(signal_data)
            results.append(result.randomized_lot)
        
        # Check that not all results are identical (some variance should occur)
        unique_results = set(results)
        assert len(unique_results) > 1, "All randomized lots are identical - repeat avoidance may not be working"
    
    def test_randomization_disabled(self):
        """Test behavior when randomization is disabled"""
        self.inserter.update_config({'enabled': False})
        
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': 0.10,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat()
        }
        
        result = self.inserter.randomize_lot_size(signal_data)
        
        # Should return original lot unchanged
        assert result.original_lot == result.randomized_lot
        assert result.variance_applied == 0.0
        assert result.seed_used == "disabled"
        assert "disabled" in result.reason.lower()
    
    def test_history_tracking(self):
        """Test that randomization history is properly tracked"""
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': 0.10,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat()
        }
        
        initial_count = len(self.inserter.randomization_history)
        
        result = self.inserter.randomize_lot_size(signal_data)
        
        # History should have one more entry
        assert len(self.inserter.randomization_history) == initial_count + 1
        
        # Latest entry should match our result
        latest = self.inserter.randomization_history[-1]
        assert latest.original_lot == result.original_lot
        assert latest.randomized_lot == result.randomized_lot
        assert latest.symbol == result.symbol
    
    def test_statistics_calculation(self):
        """Test statistics calculation functionality"""
        # Generate several randomizations
        for i in range(3):
            signal_data = {
                'symbol': f'SYMBOL{i}',
                'lot_size': 0.10,
                'entry': 1.0850,
                'action': 'BUY',
                'timestamp': f"2025-06-23T10:0{i}:00"
            }
            self.inserter.randomize_lot_size(signal_data)
        
        stats = self.inserter.get_randomization_statistics()
        
        assert stats['total_randomizations'] == 3
        assert stats['symbols_processed'] == 3
        assert stats['enabled'] == True
        assert 'average_variance' in stats
        assert 'last_randomization' in stats
    
    def test_recent_randomizations_retrieval(self):
        """Test retrieval of recent randomization results"""
        # Generate several randomizations
        for i in range(5):
            signal_data = {
                'symbol': 'EURUSD',
                'lot_size': 0.10,
                'entry': 1.0850,
                'action': 'BUY',
                'timestamp': f"2025-06-23T10:0{i}:00",
                'signal_id': f"test_{i}"
            }
            self.inserter.randomize_lot_size(signal_data)
        
        recent = self.inserter.get_recent_randomizations(limit=3)
        
        assert len(recent) == 3
        assert all('symbol' in r for r in recent)
        assert all('original_lot' in r for r in recent)
        assert all('randomized_lot' in r for r in recent)
        
        # Should be in chronological order (latest first)
        assert recent[0]['signal_id'] == 'test_4'
        assert recent[2]['signal_id'] == 'test_2'
    
    def test_configuration_persistence(self):
        """Test that configuration changes are persisted"""
        new_config = {
            'variance_range': 0.005,
            'rounding_precision': 2,
            'notify_copilot': True
        }
        
        self.inserter.update_config(new_config)
        
        # Verify changes in memory
        assert self.inserter.config.variance_range == 0.005
        assert self.inserter.config.rounding_precision == 2
        assert self.inserter.config.notify_copilot == True
        
        # Create new inserter to test persistence
        inserter2 = RandomizedLotInserter(
            config_file=self.config_file,
            history_file=os.path.join(self.temp_dir, "test_history2.json")
        )
        
        assert inserter2.config.variance_range == 0.005
        assert inserter2.config.rounding_precision == 2
        assert inserter2.config.notify_copilot == True
    
    def test_history_persistence(self):
        """Test that randomization history is persisted"""
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': 0.10,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat(),
            'signal_id': 'persistence_test'
        }
        
        result = self.inserter.randomize_lot_size(signal_data)
        
        # Create new inserter to test persistence
        inserter2 = RandomizedLotInserter(
            config_file=self.config_file,
            history_file=self.history_file
        )
        
        assert len(inserter2.randomization_history) == 1
        loaded_result = inserter2.randomization_history[0]
        assert loaded_result.original_lot == result.original_lot
        assert loaded_result.randomized_lot == result.randomized_lot
        assert loaded_result.signal_id == 'persistence_test'
    
    def test_clear_history_functionality(self):
        """Test clearing randomization history"""
        # Generate some history
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': 0.10,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat()
        }
        
        self.inserter.randomize_lot_size(signal_data)
        assert len(self.inserter.randomization_history) > 0
        
        # Clear history
        self.inserter.clear_history()
        
        assert len(self.inserter.randomization_history) == 0
        assert len(self.inserter.recent_lots) == 0
    
    def test_edge_case_zero_lot_size(self):
        """Test handling of zero lot size"""
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': 0.0,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat()
        }
        
        result = self.inserter.randomize_lot_size(signal_data)
        
        # Should enforce minimum lot size
        assert result.randomized_lot >= self.inserter.config.min_lot_size
    
    def test_edge_case_negative_lot_size(self):
        """Test handling of negative lot size"""
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': -0.05,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat()
        }
        
        result = self.inserter.randomize_lot_size(signal_data)
        
        # Should enforce minimum lot size
        assert result.randomized_lot >= self.inserter.config.min_lot_size
    
    def test_copilot_notification_when_enabled(self):
        """Test Copilot notification functionality"""
        self.inserter.update_config({'notify_copilot': True})
        
        signal_data = {
            'symbol': 'EURUSD',
            'lot_size': 0.10,
            'entry': 1.0850,
            'action': 'BUY',
            'timestamp': datetime.now().isoformat()
        }
        
        # Mock the notification method
        with patch.object(self.inserter, '_send_copilot_notification') as mock_notify:
            result = self.inserter.randomize_lot_size(signal_data)
            mock_notify.assert_called_once()
    
    def test_multiple_symbols_tracking(self):
        """Test tracking of multiple symbols separately"""
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
        
        for symbol in symbols:
            signal_data = {
                'symbol': symbol,
                'lot_size': 0.10,
                'entry': 1.0850,
                'action': 'BUY',
                'timestamp': datetime.now().isoformat()
            }
            self.inserter.randomize_lot_size(signal_data)
        
        # Should track all symbols
        assert len(self.inserter.recent_lots) == 3
        for symbol in symbols:
            assert symbol in self.inserter.recent_lots
            assert len(self.inserter.recent_lots[symbol]) == 1

# Integration test
def test_integration_with_strategy_runtime():
    """Test integration scenario with strategy runtime"""
    inserter = RandomizedLotInserter()
    
    # Mock strategy runtime flow
    original_signal = {
        'symbol': 'EURUSD',
        'lot_size': 0.10,
        'entry': 1.0850,
        'stop_loss': 1.0800,
        'take_profit': 1.0900,
        'action': 'BUY',
        'timestamp': datetime.now().isoformat(),
        'signal_id': 'integration_test'
    }
    
    # Apply lot randomization
    randomization_result = inserter.randomize_lot_size(original_signal)
    
    # Update signal with randomized lot
    modified_signal = original_signal.copy()
    modified_signal['lot_size'] = randomization_result.randomized_lot
    
    # Verify integration
    assert modified_signal['lot_size'] != original_signal['lot_size']
    assert abs(modified_signal['lot_size'] - original_signal['lot_size']) <= inserter.config.variance_range
    assert modified_signal['symbol'] == original_signal['symbol']
    assert modified_signal['entry'] == original_signal['entry']
    
    print(f"Integration test passed:")
    print(f"  Original lot: {original_signal['lot_size']}")
    print(f"  Randomized lot: {modified_signal['lot_size']}")
    print(f"  Variance: {randomization_result.variance_applied:+.6f}")

# Main execution for testing
def run_basic_tests():
    """Run basic functionality tests"""
    test_instance = TestRandomizedLotInserter()
    test_instance.setup_method()
    
    try:
        test_instance.test_basic_lot_randomization_within_bounds()
        print("✓ Basic lot randomization test passed")
        
        test_instance.test_deterministic_randomization_with_same_seed()
        print("✓ Deterministic randomization test passed")
        
        test_instance.test_variance_range_configuration()
        print("✓ Variance range configuration test passed")
        
        test_instance.test_rounding_functionality()
        print("✓ Rounding functionality test passed")
        
        test_instance.test_randomization_disabled()
        print("✓ Randomization disabled test passed")
        
        test_instance.test_lot_size_bounds_validation()
        print("✓ Lot size bounds validation test passed")
        
        test_integration_with_strategy_runtime()
        print("✓ Integration test passed")
        
        print("\nAll randomized lot inserter tests passed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        test_instance.teardown_method()

if __name__ == "__main__":
    run_basic_tests()