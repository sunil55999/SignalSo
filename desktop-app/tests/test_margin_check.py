"""
Tests for Margin Filter functionality in Strategy Runtime
Tests the integration between margin checking and signal filtering
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

# Mock imports for testing environment
class MockMT5Bridge:
    def __init__(self, margin_data=None):
        self.margin_data = margin_data or {
            'free_margin': 5000.0,
            'used_margin': 3000.0,
            'margin_level': 200.0,
            'equity': 8000.0,
            'balance': 8000.0,
            'is_connected': True
        }
    
    async def get_margin_info(self):
        """Get current margin information"""
        return self.margin_data
    
    def is_connected(self):
        return self.margin_data.get('is_connected', True)

class MockStrategyRuntime:
    def __init__(self):
        self.margin_filters = {}
        self.mt5_bridge = None
    
    def inject_modules(self, mt5_bridge=None):
        self.mt5_bridge = mt5_bridge
    
    def add_margin_filter(self, filter_id: str, config: Dict[str, Any]):
        """Add margin filter to strategy"""
        self.margin_filters[filter_id] = config
    
    async def check_margin_filter(self, filter_id: str, signal_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check if signal passes margin filter"""
        if filter_id not in self.margin_filters:
            return {"passes": False, "reason": "Filter not found"}
        
        config = self.margin_filters[filter_id]
        
        if not self.mt5_bridge or not self.mt5_bridge.is_connected():
            return {
                "passes": False,
                "reason": "MT5 not connected",
                "margin_data": None,
                "emergency_mode": False
            }
        
        margin_info = await self.mt5_bridge.get_margin_info()
        
        # Check emergency threshold first
        emergency_threshold = config.get('emergency_threshold', 10)
        if margin_info['margin_level'] < emergency_threshold:
            return {
                "passes": False,
                "reason": f"Emergency threshold breached ({margin_info['margin_level']:.1f}% < {emergency_threshold}%)",
                "margin_data": margin_info,
                "emergency_mode": True
            }
        
        # Determine filter value based on type
        filter_type = config.get('filter_type', 'percentage')
        if filter_type == 'percentage':
            current_value = margin_info['margin_level']
            threshold = config.get('threshold_percentage', 25)
            unit = '%'
        else:
            current_value = margin_info['free_margin']
            threshold = config.get('threshold_absolute', 1000)
            unit = '$'
        
        # Check override conditions
        override_applied = False
        if config.get('allow_override', False) and signal_data:
            signal_type = signal_data.get('signal_type')
            override_types = config.get('override_signal_types', [])
            if signal_type and signal_type in override_types:
                override_applied = True
        
        # Determine if signal passes
        base_pass = current_value >= threshold
        passes = base_pass or override_applied
        
        # Generate reason
        if override_applied:
            reason = f"Override applied for {signal_data.get('signal_type', 'unknown')} signal type"
        elif passes:
            reason = f"Margin sufficient ({current_value:.1f}{unit} ≥ {threshold}{unit})"
        else:
            reason = f"Margin insufficient ({current_value:.1f}{unit} < {threshold}{unit})"
        
        return {
            "passes": passes,
            "reason": reason,
            "margin_data": margin_info,
            "emergency_mode": False,
            "override_applied": override_applied,
            "threshold_value": threshold,
            "current_value": current_value
        }

@pytest.mark.asyncio
class TestMarginFilter:
    
    def setup_method(self):
        """Setup test environment"""
        self.strategy_runtime = MockStrategyRuntime()
        self.margin_data_sufficient = {
            'free_margin': 5000.0,
            'used_margin': 2000.0,
            'margin_level': 250.0,
            'equity': 7000.0,
            'balance': 7000.0,
            'is_connected': True
        }
        self.margin_data_insufficient = {
            'free_margin': 800.0,
            'used_margin': 4200.0,
            'margin_level': 20.0,
            'equity': 5000.0,
            'balance': 5000.0,
            'is_connected': True
        }
        self.margin_data_emergency = {
            'free_margin': 100.0,
            'used_margin': 4900.0,
            'margin_level': 5.0,
            'equity': 5000.0,
            'balance': 5000.0,
            'is_connected': True
        }
    
    async def test_margin_filter_passes_with_sufficient_percentage(self):
        """Test margin filter passes when margin level is sufficient"""
        mt5_bridge = MockMT5Bridge(self.margin_data_sufficient)
        self.strategy_runtime.inject_modules(mt5_bridge=mt5_bridge)
        
        config = {
            'filter_type': 'percentage',
            'threshold_percentage': 100,
            'emergency_threshold': 10
        }
        
        self.strategy_runtime.add_margin_filter('test_filter', config)
        result = await self.strategy_runtime.check_margin_filter('test_filter')
        
        assert result['passes'] == True
        assert 'sufficient' in result['reason'].lower()
        assert result['emergency_mode'] == False
        assert result['margin_data']['margin_level'] == 250.0
    
    async def test_margin_filter_blocks_with_insufficient_percentage(self):
        """Test margin filter blocks when margin level is insufficient"""
        mt5_bridge = MockMT5Bridge(self.margin_data_insufficient)
        self.strategy_runtime.inject_modules(mt5_bridge=mt5_bridge)
        
        config = {
            'filter_type': 'percentage',
            'threshold_percentage': 50,
            'emergency_threshold': 10
        }
        
        self.strategy_runtime.add_margin_filter('test_filter', config)
        result = await self.strategy_runtime.check_margin_filter('test_filter')
        
        assert result['passes'] == False
        assert 'insufficient' in result['reason'].lower()
        assert result['emergency_mode'] == False
        assert result['current_value'] == 20.0
        assert result['threshold_value'] == 50
    
    async def test_margin_filter_emergency_mode(self):
        """Test margin filter emergency mode blocks all signals"""
        mt5_bridge = MockMT5Bridge(self.margin_data_emergency)
        self.strategy_runtime.inject_modules(mt5_bridge=mt5_bridge)
        
        config = {
            'filter_type': 'percentage',
            'threshold_percentage': 1,  # Very low threshold
            'emergency_threshold': 10,
            'allow_override': True,
            'override_signal_types': ['HIGH_CONFIDENCE']
        }
        
        self.strategy_runtime.add_margin_filter('test_filter', config)
        
        # Test with override signal type - should still fail in emergency
        signal_data = {'signal_type': 'HIGH_CONFIDENCE', 'symbol': 'EURUSD'}
        result = await self.strategy_runtime.check_margin_filter('test_filter', signal_data)
        
        assert result['passes'] == False
        assert result['emergency_mode'] == True
        assert 'emergency threshold breached' in result['reason'].lower()
    
    async def test_margin_filter_absolute_value_sufficient(self):
        """Test margin filter with absolute value - sufficient margin"""
        mt5_bridge = MockMT5Bridge(self.margin_data_sufficient)
        self.strategy_runtime.inject_modules(mt5_bridge=mt5_bridge)
        
        config = {
            'filter_type': 'absolute',
            'threshold_absolute': 2000,
            'emergency_threshold': 10
        }
        
        self.strategy_runtime.add_margin_filter('test_filter', config)
        result = await self.strategy_runtime.check_margin_filter('test_filter')
        
        assert result['passes'] == True
        assert result['current_value'] == 5000.0
        assert result['threshold_value'] == 2000
    
    async def test_margin_filter_absolute_value_insufficient(self):
        """Test margin filter with absolute value - insufficient margin"""
        mt5_bridge = MockMT5Bridge(self.margin_data_insufficient)
        self.strategy_runtime.inject_modules(mt5_bridge=mt5_bridge)
        
        config = {
            'filter_type': 'absolute',
            'threshold_absolute': 1500,
            'emergency_threshold': 10
        }
        
        self.strategy_runtime.add_margin_filter('test_filter', config)
        result = await self.strategy_runtime.check_margin_filter('test_filter')
        
        assert result['passes'] == False
        assert result['current_value'] == 800.0
        assert result['threshold_value'] == 1500
    
    async def test_margin_filter_override_functionality(self):
        """Test margin filter override for specific signal types"""
        mt5_bridge = MockMT5Bridge(self.margin_data_insufficient)
        self.strategy_runtime.inject_modules(mt5_bridge=mt5_bridge)
        
        config = {
            'filter_type': 'percentage',
            'threshold_percentage': 50,
            'emergency_threshold': 10,
            'allow_override': True,
            'override_signal_types': ['HIGH_CONFIDENCE', 'BREAKOUT']
        }
        
        self.strategy_runtime.add_margin_filter('test_filter', config)
        
        # Test with override signal type
        signal_data = {'signal_type': 'HIGH_CONFIDENCE', 'symbol': 'EURUSD'}
        result = await self.strategy_runtime.check_margin_filter('test_filter', signal_data)
        
        assert result['passes'] == True
        assert result['override_applied'] == True
        assert 'override applied' in result['reason'].lower()
        
        # Test with non-override signal type
        signal_data = {'signal_type': 'SCALP', 'symbol': 'EURUSD'}
        result = await self.strategy_runtime.check_margin_filter('test_filter', signal_data)
        
        assert result['passes'] == False
        assert result['override_applied'] == False
    
    async def test_margin_filter_mt5_disconnected(self):
        """Test margin filter when MT5 is disconnected"""
        disconnected_data = {**self.margin_data_sufficient, 'is_connected': False}
        mt5_bridge = MockMT5Bridge(disconnected_data)
        self.strategy_runtime.inject_modules(mt5_bridge=mt5_bridge)
        
        config = {
            'filter_type': 'percentage',
            'threshold_percentage': 25,
            'emergency_threshold': 10
        }
        
        self.strategy_runtime.add_margin_filter('test_filter', config)
        result = await self.strategy_runtime.check_margin_filter('test_filter')
        
        assert result['passes'] == False
        assert 'not connected' in result['reason'].lower()
        assert result['margin_data'] is None
    
    async def test_margin_filter_invalid_config(self):
        """Test margin filter with invalid configuration"""
        mt5_bridge = MockMT5Bridge(self.margin_data_sufficient)
        self.strategy_runtime.inject_modules(mt5_bridge=mt5_bridge)
        
        # Test non-existent filter
        result = await self.strategy_runtime.check_margin_filter('nonexistent_filter')
        
        assert result['passes'] == False
        assert 'not found' in result['reason'].lower()
    
    async def test_margin_filter_configuration_variations(self):
        """Test various margin filter configurations"""
        mt5_bridge = MockMT5Bridge(self.margin_data_sufficient)
        self.strategy_runtime.inject_modules(mt5_bridge=mt5_bridge)
        
        # Test with different emergency thresholds
        config1 = {
            'filter_type': 'percentage',
            'threshold_percentage': 50,
            'emergency_threshold': 300  # Higher than current margin level
        }
        
        self.strategy_runtime.add_margin_filter('emergency_test', config1)
        result = await self.strategy_runtime.check_margin_filter('emergency_test')
        
        assert result['passes'] == False
        assert result['emergency_mode'] == True
        
        # Test with very permissive settings
        config2 = {
            'filter_type': 'percentage',
            'threshold_percentage': 1,
            'emergency_threshold': 1
        }
        
        self.strategy_runtime.add_margin_filter('permissive_test', config2)
        result = await self.strategy_runtime.check_margin_filter('permissive_test')
        
        assert result['passes'] == True
        assert result['emergency_mode'] == False

if __name__ == "__main__":
    # Run basic functionality test
    async def run_basic_test():
        test_instance = TestMarginFilter()
        test_instance.setup_method()
        
        print("Running basic margin filter tests...")
        
        try:
            await test_instance.test_margin_filter_passes_with_sufficient_percentage()
            print("✓ Sufficient percentage test passed")
            
            await test_instance.test_margin_filter_blocks_with_insufficient_percentage()
            print("✓ Insufficient percentage test passed")
            
            await test_instance.test_margin_filter_emergency_mode()
            print("✓ Emergency mode test passed")
            
            await test_instance.test_margin_filter_override_functionality()
            print("✓ Override functionality test passed")
            
            await test_instance.test_margin_filter_mt5_disconnected()
            print("✓ MT5 disconnected test passed")
            
            print("\nAll margin filter tests passed successfully!")
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            raise
    
    # Run the test
    asyncio.run(run_basic_test())