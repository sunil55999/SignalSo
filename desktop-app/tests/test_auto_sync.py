"""
Test suite for Auto Sync Engine
Tests synchronization logic, error handling, and module integration
"""

import unittest
import json
import tempfile
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from auto_sync import AutoSyncEngine, SyncStatus

class TestAutoSyncEngine(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        self.sync_log_file = os.path.join(self.temp_dir, "test_sync_log.json")
        
        # Create test configuration
        test_config = {
            "sync": {
                "interval_seconds": 30,
                "retry_attempts": 3,
                "timeout_seconds": 5
            },
            "server": {
                "url": "http://localhost:5000"
            },
            "user": {
                "id": 123
            },
            "desktop_app": {
                "terminal_id": "test_terminal",
                "version": "1.0.0"
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
        
        self.sync_engine = AutoSyncEngine(self.config_file, self.sync_log_file)
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_config_loading(self):
        """Test configuration loading"""
        self.assertEqual(self.sync_engine.sync_interval, 30)
        self.assertEqual(self.sync_engine.server_url, "http://localhost:5000")
        self.assertEqual(self.sync_engine.user_id, 123)
    
    def test_default_config_creation(self):
        """Test default configuration creation when file doesn't exist"""
        non_existent_config = os.path.join(self.temp_dir, "nonexistent.json")
        new_sync_engine = AutoSyncEngine(non_existent_config)
        
        # Should create default config
        self.assertTrue(os.path.exists(non_existent_config))
        self.assertEqual(new_sync_engine.sync_interval, 60)  # Default interval
    
    def test_module_injection(self):
        """Test injecting module references"""
        mock_mt5 = Mock()
        mock_parser = Mock()
        mock_retry = Mock()
        mock_strategy = Mock()
        
        self.sync_engine.inject_modules(
            mt5_bridge=mock_mt5,
            signal_parser=mock_parser,
            retry_engine=mock_retry,
            strategy_runtime=mock_strategy
        )
        
        self.assertEqual(self.sync_engine.mt5_bridge, mock_mt5)
        self.assertEqual(self.sync_engine.signal_parser, mock_parser)
        self.assertEqual(self.sync_engine.retry_engine, mock_retry)
        self.assertEqual(self.sync_engine.strategy_runtime, mock_strategy)
    
    def test_terminal_status_collection(self):
        """Test collecting terminal status"""
        # Inject mock modules
        mock_mt5 = Mock()
        mock_mt5.get_connection_status.return_value = {
            "connected": True,
            "account_info": {"balance": 10000},
            "last_ping": datetime.now().isoformat()
        }
        
        mock_parser = Mock()
        mock_parser.get_statistics.return_value = {
            "total_parsed": 50,
            "success_rate": 95.0
        }
        
        self.sync_engine.inject_modules(mt5_bridge=mock_mt5, signal_parser=mock_parser)
        
        status = self.sync_engine._collect_terminal_status()
        
        self.assertEqual(status["terminal_id"], "test_terminal")
        self.assertEqual(status["version"], "1.0.0")
        self.assertIn("modules", status)
        self.assertTrue(status["modules"]["mt5"]["connected"])
        self.assertEqual(status["modules"]["parser"]["signals_parsed"], 50)
    
    def test_parser_status_collection(self):
        """Test collecting parser status"""
        parser_status = self.sync_engine._collect_parser_status()
        
        self.assertIn("last_update", parser_status)
        self.assertIn("parser_version", parser_status)
        self.assertIn("supported_formats", parser_status)
        self.assertIn("confidence_threshold", parser_status)
    
    @patch('requests.post')
    async def test_successful_sync(self, mock_post):
        """Test successful sync operation"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "strategy": {
                "id": "new_strategy",
                "name": "Updated Strategy",
                "rules": []
            },
            "timestamp": datetime.now().isoformat()
        }
        mock_post.return_value = mock_response
        
        success = await self.sync_engine.sync_with_server()
        
        self.assertTrue(success)
        self.assertTrue(self.sync_engine.sync_status.server_reachable)
        self.assertEqual(self.sync_engine.sync_status.sync_count, 1)
        self.assertIsNone(self.sync_engine.sync_status.last_error)
    
    @patch('requests.post')
    async def test_failed_sync(self, mock_post):
        """Test failed sync operation"""
        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        success = await self.sync_engine.sync_with_server()
        
        self.assertFalse(success)
        self.assertFalse(self.sync_engine.sync_status.server_reachable)
        self.assertEqual(self.sync_engine.sync_status.failed_syncs, 1)
        self.assertIsNotNone(self.sync_engine.sync_status.last_error)
    
    @patch('requests.post')
    async def test_connection_error_handling(self, mock_post):
        """Test handling of connection errors"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        success = await self.sync_engine.sync_with_server()
        
        self.assertFalse(success)
        self.assertIn("Connection error", self.sync_engine.sync_status.last_error)
    
    @patch('requests.post')
    async def test_timeout_error_handling(self, mock_post):
        """Test handling of timeout errors"""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        success = await self.sync_engine.sync_with_server()
        
        self.assertFalse(success)
        self.assertIn("Request timeout", self.sync_engine.sync_status.last_error)
    
    async def test_strategy_update_handling(self):
        """Test handling strategy updates from server"""
        # Mock strategy runtime
        mock_strategy_runtime = Mock()
        mock_strategy_runtime.current_strategy = None
        self.sync_engine.inject_modules(strategy_runtime=mock_strategy_runtime)
        
        strategy_data = {
            "id": "updated_strategy",
            "name": "Updated Strategy",
            "rules": [],
            "global_settings": {}
        }
        
        await self.sync_engine._handle_strategy_update(strategy_data)
        
        # Should call load_strategy on the strategy runtime
        mock_strategy_runtime.load_strategy.assert_called_once_with(strategy_data)
    
    @patch('requests.post')
    async def test_error_alert_sending(self, mock_post):
        """Test sending error alerts to server"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response
        
        await self.sync_engine.send_error_alert("test_error", "Test error message", {"extra": "data"})
        
        # Verify API call was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        self.assertIn("/firebridge/error-alert", call_args[1]["url"])
        
        # Check payload
        payload = call_args[1]["json"]
        self.assertEqual(payload["userId"], 123)
        self.assertEqual(payload["error"], "test_error")
        self.assertIn("Test error message", payload["details"]["message"])
    
    def test_sync_status_tracking(self):
        """Test sync status tracking"""
        initial_status = self.sync_engine.get_sync_status()
        
        self.assertIn("is_running", initial_status)
        self.assertIn("sync_count", initial_status)
        self.assertIn("server_reachable", initial_status)
        self.assertEqual(initial_status["sync_interval"], 30)
        self.assertEqual(initial_status["server_url"], "http://localhost:5000")
    
    def test_sync_interval_update(self):
        """Test updating sync interval"""
        self.sync_engine.update_sync_interval(120)
        self.assertEqual(self.sync_engine.sync_interval, 120)
        
        # Test minimum interval enforcement
        self.sync_engine.update_sync_interval(5)
        self.assertEqual(self.sync_engine.sync_interval, 10)  # Should be clamped to minimum
    
    def test_sync_log_creation(self):
        """Test sync event logging"""
        request_data = {"test": "request"}
        response_data = {"test": "response"}
        
        self.sync_engine._log_sync_event("success", request_data, response_data)
        
        # Check that log file was created
        self.assertTrue(os.path.exists(self.sync_log_file))
        
        # Check log content
        with open(self.sync_log_file, 'r') as f:
            logs = json.load(f)
        
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["event_type"], "success")
        self.assertEqual(logs[0]["user_id"], 123)
    
    def test_sync_log_retrieval(self):
        """Test retrieving sync logs"""
        # Create some test log entries
        for i in range(5):
            self.sync_engine._log_sync_event(f"event_{i}", {"data": i}, {"result": i})
        
        # Retrieve logs
        logs = self.sync_engine.get_sync_logs(3)
        
        self.assertEqual(len(logs), 3)  # Should return last 3 logs
        self.assertEqual(logs[-1]["event_type"], "event_4")  # Most recent should be last
    
    def test_force_sync(self):
        """Test force sync functionality"""
        with patch.object(self.sync_engine, 'sync_with_server') as mock_sync:
            mock_sync.return_value = True
            
            # Test force sync (this would be called with asyncio.run in real usage)
            # We'll just test that it calls the sync method
            asyncio.create_task(self.sync_engine.force_sync())
            
            # In a real async test, we'd await the result

class TestAutoSyncIntegration(unittest.TestCase):
    """Integration tests for auto sync engine"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.json")
        self.sync_log_file = os.path.join(self.temp_dir, "sync_log.json")
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('requests.post')
    async def test_full_sync_cycle_with_strategy_update(self, mock_post):
        """Test complete sync cycle with strategy update"""
        sync_engine = AutoSyncEngine(self.config_file, self.sync_log_file)
        
        # Mock successful sync with strategy update
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "strategy": {
                "id": "new_strategy_123",
                "name": "Integration Test Strategy",
                "description": "Test strategy for integration",
                "rules": [
                    {
                        "id": "rule_1",
                        "name": "Test Rule",
                        "condition": {
                            "type": "confidence_threshold",
                            "parameters": {"min_confidence": 75.0},
                            "description": "Confidence filter"
                        },
                        "action": {
                            "type": "execute_normal",
                            "parameters": {},
                            "description": "Execute normally"
                        },
                        "enabled": True,
                        "priority": 100
                    }
                ],
                "global_settings": {"max_concurrent_trades": 3},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
        mock_post.return_value = mock_response
        
        # Mock strategy runtime
        mock_strategy_runtime = Mock()
        mock_strategy_runtime.current_strategy = None
        sync_engine.inject_modules(strategy_runtime=mock_strategy_runtime)
        
        # Perform sync
        success = await sync_engine.sync_with_server()
        
        self.assertTrue(success)
        self.assertEqual(sync_engine.sync_status.strategy_version, "new_strategy_123")
        mock_strategy_runtime.load_strategy.assert_called_once()

if __name__ == '__main__':
    unittest.main(verbosity=2)