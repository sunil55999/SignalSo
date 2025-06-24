"""
Tests for Magic Number Hider module
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, mock_open
from datetime import datetime
from desktop_app.magic_number_hider import MagicNumberHider, generate_magic_number


class TestMagicNumberHider:
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Create test config
        test_config = {
            'magic_number_hider': {
                'base_magic_range': [100000, 999999],
                'stealth_mode': True,
                'random_suffix_enabled': True,
                'random_suffix_range': [10, 99],
                'per_user_salt': True,
                'hash_algorithm': 'md5',
                'log_magic_numbers': True
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        self.temp_log.close()
        
        self.magic_hider = MagicNumberHider(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def teardown_method(self):
        """Cleanup test files"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_generate_magic_number_consistency(self):
        """Test that same symbol/user generates same magic number"""
        symbol = "EURUSD"
        user_id = "user123"
        
        magic1 = self.magic_hider.generate_magic_number(symbol, user_id)
        magic2 = self.magic_hider.generate_magic_number(symbol, user_id)
        
        assert magic1 == magic2, "Same symbol/user should generate consistent magic number"
        assert 100000 <= magic1 <= 999999, "Magic number should be within 5-6 digit range"
    
    def test_generate_magic_number_uniqueness(self):
        """Test that different symbols/users generate different magic numbers"""
        magic1 = self.magic_hider.generate_magic_number("EURUSD", "user1")
        magic2 = self.magic_hider.generate_magic_number("GBPUSD", "user1")
        magic3 = self.magic_hider.generate_magic_number("EURUSD", "user2")
        
        assert magic1 != magic2, "Different symbols should generate different magic numbers"
        assert magic1 != magic3, "Different users should generate different magic numbers"
        assert magic2 != magic3, "Different symbol/user combinations should be unique"
    
    def test_magic_number_range(self):
        """Test magic numbers are within configured range"""
        test_cases = [
            ("EURUSD", "user1"),
            ("GBPUSD", "user2"),
            ("XAUUSD", "user3"),
            ("USDJPY", "user4")
        ]
        
        for symbol, user_id in test_cases:
            magic = self.magic_hider.generate_magic_number(symbol, user_id)
            assert 100000 <= magic <= 999999, f"Magic number {magic} for {symbol}/{user_id} out of range"
    
    def test_stealth_mode_randomization(self):
        """Test stealth mode adds random suffix"""
        # Enable stealth mode
        self.magic_hider.config['stealth_mode'] = True
        self.magic_hider.config['random_suffix_enabled'] = True
        
        magic = self.magic_hider.generate_magic_number("EURUSD", "user1")
        
        # Should be longer than base range due to suffix
        assert isinstance(magic, int), "Magic number should be integer"
        assert magic >= 100000, "Magic number should be at least 6 digits with suffix"
    
    def test_stealth_mode_disabled(self):
        """Test stealth mode disabled returns base magic"""
        # Disable stealth mode
        self.magic_hider.config['stealth_mode'] = False
        self.magic_hider.config['random_suffix_enabled'] = False
        
        magic = self.magic_hider.generate_magic_number("EURUSD", "user1")
        
        assert 100000 <= magic <= 999999, "Without stealth mode, should be within base range"
    
    def test_magic_number_caching(self):
        """Test magic numbers are cached properly"""
        symbol = "EURUSD"
        user_id = "user1"
        
        # Clear cache first
        self.magic_hider.magic_history.clear()
        
        # First call should generate and cache
        magic1 = self.magic_hider.generate_magic_number(symbol, user_id)
        
        # Verify it's cached
        cache_key = f"{symbol}_{user_id}"
        assert cache_key in self.magic_hider.magic_history
        assert self.magic_hider.magic_history[cache_key] == magic1
        
        # Second call should return cached value
        magic2 = self.magic_hider.generate_magic_number(symbol, user_id)
        assert magic1 == magic2
    
    def test_get_magic_for_trade_types(self):
        """Test different trade types generate different magic numbers"""
        symbol = "EURUSD"
        user_id = "user1"
        
        magic_standard = self.magic_hider.get_magic_for_trade(symbol, user_id, "standard")
        magic_hedge = self.magic_hider.get_magic_for_trade(symbol, user_id, "hedge")
        magic_grid = self.magic_hider.get_magic_for_trade(symbol, user_id, "grid")
        
        assert magic_standard != magic_hedge, "Different trade types should have different magic numbers"
        assert magic_standard != magic_grid, "Different trade types should have different magic numbers"
        assert magic_hedge != magic_grid, "Different trade types should have different magic numbers"
    
    def test_clear_magic_cache(self):
        """Test cache clearing functionality"""
        # Generate some magic numbers
        self.magic_hider.generate_magic_number("EURUSD", "user1")
        self.magic_hider.generate_magic_number("GBPUSD", "user1")
        
        assert len(self.magic_hider.magic_history) == 2
        
        # Clear specific cache
        self.magic_hider.clear_magic_cache("EURUSD", "user1")
        assert len(self.magic_hider.magic_history) == 1
        
        # Clear all cache
        self.magic_hider.clear_magic_cache()
        assert len(self.magic_hider.magic_history) == 0
    
    def test_hash_algorithms(self):
        """Test different hash algorithms produce different results"""
        symbol = "EURUSD"
        user_id = "user1"
        
        # Test MD5
        self.magic_hider.config['hash_algorithm'] = 'md5'
        magic_md5 = self.magic_hider._calculate_magic_number(symbol, user_id)
        
        # Test SHA256
        self.magic_hider.config['hash_algorithm'] = 'sha256'
        magic_sha256 = self.magic_hider._calculate_magic_number(symbol, user_id)
        
        # Should be different (but not guaranteed, so we test multiple)
        test_symbols = ["EURUSD", "GBPUSD", "XAUUSD"]
        md5_results = []
        sha256_results = []
        
        for test_symbol in test_symbols:
            self.magic_hider.config['hash_algorithm'] = 'md5'
            md5_results.append(self.magic_hider._calculate_magic_number(test_symbol, user_id))
            
            self.magic_hider.config['hash_algorithm'] = 'sha256'
            sha256_results.append(self.magic_hider._calculate_magic_number(test_symbol, user_id))
        
        # At least some should be different
        assert md5_results != sha256_results, "Different hash algorithms should produce different distributions"
    
    def test_get_magic_statistics(self):
        """Test magic number statistics"""
        # Generate some test data
        test_symbols = ["EURUSD", "GBPUSD", "XAUUSD"]
        test_users = ["user1", "user2"]
        
        for symbol in test_symbols:
            for user in test_users:
                self.magic_hider.generate_magic_number(symbol, user)
        
        stats = self.magic_hider.get_magic_statistics()
        
        assert stats['total_generated'] == 6  # 3 symbols * 2 users
        assert stats['unique_symbols'] == 3
        assert stats['unique_users'] == 2
        assert 'range_distribution' in stats
        assert stats['stealth_mode_enabled'] == True
        assert stats['random_suffix_enabled'] == True
    
    def test_per_user_salt_disabled(self):
        """Test magic generation without per-user salt"""
        self.magic_hider.config['per_user_salt'] = False
        
        # Same symbol with different users should generate same magic (if no per-user salt)
        magic1 = self.magic_hider._calculate_magic_number("EURUSD", "user1")
        magic2 = self.magic_hider._calculate_magic_number("EURUSD", "user2")
        
        assert magic1 == magic2, "Without per-user salt, same symbol should generate same magic"
    
    def test_global_convenience_function(self):
        """Test global convenience function"""
        magic = generate_magic_number("EURUSD", "user1")
        
        assert isinstance(magic, int), "Global function should return integer"
        assert 100000 <= magic <= 999999, "Global function should return valid magic number"
    
    def test_module_injection(self):
        """Test module injection functionality"""
        mock_mt5_bridge = object()
        mock_strategy_runtime = object()
        
        self.magic_hider.inject_modules(
            mt5_bridge=mock_mt5_bridge,
            strategy_runtime=mock_strategy_runtime
        )
        
        assert self.magic_hider.mt5_bridge == mock_mt5_bridge
        assert self.magic_hider.strategy_runtime == mock_strategy_runtime
    
    def test_magic_number_edge_cases(self):
        """Test edge cases for magic number generation"""
        # Empty strings
        magic1 = self.magic_hider.generate_magic_number("", "user1")
        assert isinstance(magic1, int)
        
        # Very long strings
        long_symbol = "A" * 100
        magic2 = self.magic_hider.generate_magic_number(long_symbol, "user1")
        assert isinstance(magic2, int)
        
        # Special characters
        magic3 = self.magic_hider.generate_magic_number("EUR/USD", "user@domain.com")
        assert isinstance(magic3, int)
        
        # Unicode characters
        magic4 = self.magic_hider.generate_magic_number("测试", "用户1")
        assert isinstance(magic4, int)


if __name__ == "__main__":
    pytest.main([__file__])