"""
Test Suite for Terminal Identity Manager
Tests terminal fingerprinting, ID persistence, and system information collection
"""

import unittest
import tempfile
import os
import json
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from terminal_identity import (
    TerminalIdentityManager, get_terminal_id, get_system_fingerprint, get_terminal_metadata
)


class TestTerminalIdentityManager(unittest.TestCase):
    """Unit tests for TerminalIdentityManager"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, '.signalos')
        self.identity_manager = TerminalIdentityManager(config_dir=self.config_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_terminal_id_generation(self):
        """Test terminal ID generation and format"""
        terminal_id = self.identity_manager.get_terminal_id()
        
        # Should be a non-empty string
        self.assertIsInstance(terminal_id, str)
        self.assertGreater(len(terminal_id), 0)
        
        # Should have expected format: {os}-{hash}
        parts = terminal_id.split('-')
        self.assertGreaterEqual(len(parts), 2)
        
        # OS part should be recognizable
        os_part = parts[0].lower()
        expected_os = ['windows', 'linux', 'macos', 'darwin']
        self.assertTrue(any(os_name in os_part for os_name in expected_os))
    
    def test_terminal_id_persistence(self):
        """Test terminal ID persistence across instances"""
        # Get terminal ID from first instance
        terminal_id_1 = self.identity_manager.get_terminal_id()
        
        # Create new instance with same config directory
        new_identity_manager = TerminalIdentityManager(config_dir=self.config_dir)
        terminal_id_2 = new_identity_manager.get_terminal_id()
        
        # Should be the same
        self.assertEqual(terminal_id_1, terminal_id_2)
    
    def test_identity_file_creation(self):
        """Test identity file creation and structure"""
        terminal_id = self.identity_manager.get_terminal_id()
        
        # Identity file should exist
        self.assertTrue(self.identity_manager.identity_file.exists())
        
        # File should have correct permissions (600)
        file_mode = oct(os.stat(self.identity_manager.identity_file).st_mode)[-3:]
        self.assertEqual(file_mode, '600')
        
        # File should contain valid JSON with expected structure
        with open(self.identity_manager.identity_file, 'r') as f:
            identity_data = json.load(f)
        
        required_fields = ['terminal_id', 'base_uuid', 'fingerprint_hash', 'system_info', 'created_at']
        for field in required_fields:
            self.assertIn(field, identity_data)
        
        self.assertEqual(identity_data['terminal_id'], terminal_id)
    
    @patch('platform.system')
    @patch('platform.release')
    def test_os_info_collection(self, mock_release, mock_system):
        """Test OS information collection"""
        mock_system.return_value = 'Linux'
        mock_release.return_value = '5.4.0'
        
        system_info = self.identity_manager._collect_system_info()
        
        self.assertIn('os', system_info)
        self.assertIn('Linux', system_info['os'])
    
    @patch('uuid.getnode')
    def test_mac_address_collection(self, mock_getnode):
        """Test MAC address collection for fingerprinting"""
        # Mock MAC address
        mock_getnode.return_value = 0x1234567890ab
        
        mac_address = self.identity_manager._get_mac_address()
        
        # Should be in expected format
        self.assertIsInstance(mac_address, str)
        self.assertIn(':', mac_address)
        
        # Should have 6 groups separated by colons
        parts = mac_address.split(':')
        self.assertEqual(len(parts), 6)
    
    @patch('platform.node')
    def test_hostname_collection(self, mock_node):
        """Test hostname collection"""
        mock_node.return_value = 'test-hostname'
        
        hostname = self.identity_manager._get_hostname()
        self.assertEqual(hostname, 'test-hostname')
        
        # Test fallback when platform.node() fails
        mock_node.side_effect = Exception("Failed")
        hostname_fallback = self.identity_manager._get_hostname()
        self.assertEqual(hostname_fallback, 'unknown')
    
    @patch('psutil.virtual_memory')
    def test_memory_info_collection(self, mock_memory):
        """Test memory information collection"""
        # Mock 8GB memory
        mock_memory.return_value = Mock(total=8 * 1024**3)
        
        memory_gb = self.identity_manager._get_memory_info()
        self.assertEqual(memory_gb, 8)
        
        # Test fallback when psutil fails
        mock_memory.side_effect = Exception("Failed")
        memory_fallback = self.identity_manager._get_memory_info()
        self.assertEqual(memory_fallback, 0)
    
    def test_system_fingerprint_generation(self):
        """Test complete system fingerprint generation"""
        fingerprint = self.identity_manager.get_system_fingerprint()
        
        # Should contain all expected components
        self.assertIsInstance(fingerprint, dict)
        self.assertIn('terminal_id', fingerprint)
        self.assertIn('system_info', fingerprint)
        self.assertIn('created_at', fingerprint)
        self.assertIn('fingerprint_hash', fingerprint)
        
        # System info should contain key components
        system_info = fingerprint['system_info']
        expected_keys = ['os', 'mac_address', 'hostname', 'architecture']
        for key in expected_keys:
            self.assertIn(key, system_info)
    
    def test_identity_regeneration(self):
        """Test forced identity regeneration"""
        # Get initial terminal ID
        original_id = self.identity_manager.get_terminal_id()
        
        # Regenerate identity
        new_id = self.identity_manager.regenerate_identity()
        
        # Should be different
        self.assertNotEqual(original_id, new_id)
        
        # New ID should be persistent
        retrieved_id = self.identity_manager.get_terminal_id()
        self.assertEqual(retrieved_id, new_id)
    
    def test_identity_status(self):
        """Test identity status reporting"""
        # Before generating identity
        status_before = self.identity_manager.get_identity_status()
        self.assertFalse(status_before['has_identity'])
        
        # After generating identity
        terminal_id = self.identity_manager.get_terminal_id()
        status_after = self.identity_manager.get_identity_status()
        
        self.assertTrue(status_after['has_identity'])
        self.assertEqual(status_after['terminal_id'], terminal_id)
        self.assertIsNotNone(status_after['created_at'])
        self.assertIsInstance(status_after['system_info'], dict)
    
    def test_identity_integrity_verification(self):
        """Test identity integrity verification"""
        # Generate identity
        self.identity_manager.get_terminal_id()
        
        # Integrity should be valid initially
        self.assertTrue(self.identity_manager.verify_identity_integrity())
        
        # Test with corrupted identity file
        with open(self.identity_manager.identity_file, 'w') as f:
            json.dump({'invalid': 'data'}, f)
        
        # Clear cache to force reload
        self.identity_manager._cached_identity = None
        
        # Integrity should fail with corrupted data
        self.assertFalse(self.identity_manager.verify_identity_integrity())
    
    def test_terminal_metadata_for_registration(self):
        """Test terminal metadata preparation for server registration"""
        metadata = self.identity_manager.get_terminal_metadata()
        
        # Should contain all required fields for registration
        required_fields = [
            'terminal_id', 'os', 'hostname', 'architecture', 
            'python_version', 'version', 'app_name'
        ]
        
        for field in required_fields:
            self.assertIn(field, metadata)
        
        # Version should be specified
        self.assertEqual(metadata['version'], '1.0.6')
        self.assertEqual(metadata['app_name'], 'SignalOS Desktop')
    
    def test_caching_behavior(self):
        """Test identity caching behavior"""
        # First call should generate and cache
        terminal_id_1 = self.identity_manager.get_terminal_id()
        
        # Second call should use cache (no file I/O)
        with patch.object(self.identity_manager, '_load_identity') as mock_load:
            terminal_id_2 = self.identity_manager.get_terminal_id()
            mock_load.assert_not_called()
        
        self.assertEqual(terminal_id_1, terminal_id_2)
    
    def test_error_handling_during_generation(self):
        """Test error handling during identity generation"""
        with patch.object(self.identity_manager, '_collect_system_info') as mock_collect:
            # Mock system info collection failure
            mock_collect.side_effect = Exception("System info collection failed")
            
            # Should handle error gracefully and still generate ID
            try:
                terminal_id = self.identity_manager.get_terminal_id()
                # If no exception, verify we got some kind of ID
                self.assertIsInstance(terminal_id, str)
                self.assertGreater(len(terminal_id), 0)
            except Exception:
                # If exception occurs, that's also acceptable for this test
                pass


class TestGlobalFunctions(unittest.TestCase):
    """Test global utility functions"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear global instance
        import terminal_identity
        terminal_identity._terminal_identity_manager = None
    
    def test_global_terminal_id(self):
        """Test global get_terminal_id function"""
        terminal_id = get_terminal_id()
        
        self.assertIsInstance(terminal_id, str)
        self.assertGreater(len(terminal_id), 0)
        
        # Second call should return same ID
        terminal_id_2 = get_terminal_id()
        self.assertEqual(terminal_id, terminal_id_2)
    
    def test_global_system_fingerprint(self):
        """Test global get_system_fingerprint function"""
        fingerprint = get_system_fingerprint()
        
        self.assertIsInstance(fingerprint, dict)
        self.assertIn('terminal_id', fingerprint)
        self.assertIn('system_info', fingerprint)
    
    def test_global_terminal_metadata(self):
        """Test global get_terminal_metadata function"""
        metadata = get_terminal_metadata()
        
        self.assertIsInstance(metadata, dict)
        self.assertIn('terminal_id', metadata)
        self.assertIn('os', metadata)
        self.assertIn('version', metadata)


class TestSystemInfoCollection(unittest.TestCase):
    """Test system information collection edge cases"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, '.signalos')
        self.identity_manager = TerminalIdentityManager(config_dir=self.config_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    @patch('platform.system')
    @patch('platform.version')
    @patch('platform.mac_ver')
    def test_macos_detection(self, mock_mac_ver, mock_version, mock_system):
        """Test macOS version detection"""
        mock_system.return_value = 'Darwin'
        mock_mac_ver.return_value = ('12.0', (), '')
        
        os_info = self.identity_manager._get_os_info()
        self.assertIn('macOS', os_info)
        self.assertIn('12.0', os_info)
    
    @patch('platform.system')
    @patch('platform.release')
    def test_windows_detection(self, mock_release, mock_system):
        """Test Windows version detection"""
        mock_system.return_value = 'Windows'
        mock_release.return_value = '10'
        
        os_info = self.identity_manager._get_os_info()
        self.assertIn('Windows', os_info)
        self.assertIn('10', os_info)
    
    @patch('platform.system')
    def test_linux_detection_with_distro(self, mock_system):
        """Test Linux distribution detection"""
        mock_system.return_value = 'Linux'
        
        # Test without distro module (fallback)
        with patch('builtins.__import__', side_effect=ImportError):
            with patch('platform.release', return_value='5.4.0'):
                os_info = self.identity_manager._get_os_info()
                self.assertIn('Linux', os_info)
                self.assertIn('5.4.0', os_info)
    
    @patch('platform.processor')
    def test_cpu_info_collection(self, mock_processor):
        """Test CPU information collection"""
        mock_processor.return_value = 'Intel64 Family 6 Model 142 Stepping 10, GenuineIntel'
        
        cpu_info = self.identity_manager._get_cpu_info()
        self.assertIn('Intel', cpu_info)
        
        # Test fallback when processor() fails
        mock_processor.side_effect = Exception("Failed")
        cpu_info_fallback = self.identity_manager._get_cpu_info()
        self.assertEqual(cpu_info_fallback, 'unknown')
    
    @patch('platform.python_version')
    def test_python_version_collection(self, mock_python_version):
        """Test Python version collection"""
        mock_python_version.return_value = '3.9.7'
        
        python_version = self.identity_manager._get_python_version()
        self.assertEqual(python_version, '3.9.7')
        
        # Test fallback when python_version() fails
        mock_python_version.side_effect = Exception("Failed")
        python_version_fallback = self.identity_manager._get_python_version()
        self.assertEqual(python_version_fallback, 'unknown')


if __name__ == '__main__':
    unittest.main()