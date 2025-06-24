"""
Test Suite for Copilot Alert Manager
Tests alert generation, user settings, rate limiting, and Telegram integration
"""

import unittest
import json
import tempfile
import os
import time
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copilot_alert_manager import (
    CopilotAlertManager, Alert, AlertType, AlertPriority, AlertCategory,
    UserAlertSettings
)

class TestCopilotAlertManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "copilot_alert_manager": {
                "enabled": True,
                "max_retries": 3,
                "retry_delay": 1,  # Fast for testing
                "batch_size": 5,
                "processing_interval": 0.5,
                "default_rate_limit": 10,
                "enable_quiet_hours": True,
                "fallback_to_logs": True,
                "alert_timeout": 10,
                "user_settings": {
                    "test_user": {
                        "enabled_categories": ["trading", "error", "success"],
                        "enabled_types": ["trade_executed", "parsing_failed", "risk_rule_blocked"],
                        "priority_threshold": "medium",
                        "quiet_hours_start": "22:00",
                        "quiet_hours_end": "08:00",
                        "rate_limit_per_hour": 5
                    }
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize alert manager
        self.alert_manager = CopilotAlertManager(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
    def tearDown(self):
        """Clean up test environment"""
        self.alert_manager.stop_processing()
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
        # Clean up fallback log if created
        fallback_log = self.alert_manager.fallback_log_path
        if os.path.exists(fallback_log):
            os.unlink(fallback_log)

class TestBasicFunctionality(TestCopilotAlertManager):
    """Test basic alert manager functionality"""
    
    def test_initialization(self):
        """Test alert manager initialization"""
        self.assertTrue(self.alert_manager.config['enabled'])
        self.assertEqual(self.alert_manager.config['max_retries'], 3)
        self.assertEqual(self.alert_manager.config['default_rate_limit'], 10)
        
    def test_config_loading(self):
        """Test configuration loading"""
        config = self.alert_manager.config
        
        self.assertTrue(config['enabled'])
        self.assertEqual(config['batch_size'], 5)
        self.assertEqual(config['processing_interval'], 0.5)
        self.assertTrue(config['fallback_to_logs'])
        
    def test_user_settings_loading(self):
        """Test user settings loading from config"""
        self.alert_manager._load_user_settings()
        
        self.assertIn("test_user", self.alert_manager.user_settings)
        user_settings = self.alert_manager.user_settings["test_user"]
        
        self.assertEqual(user_settings.user_id, "test_user")
        self.assertIn(AlertCategory.TRADING, user_settings.enabled_categories)
        self.assertIn(AlertType.TRADE_EXECUTED, user_settings.enabled_types)
        self.assertEqual(user_settings.priority_threshold, AlertPriority.MEDIUM)
        self.assertEqual(user_settings.rate_limit_per_hour, 5)

class TestAlertCreation(TestCopilotAlertManager):
    """Test alert creation and formatting"""
    
    def test_alert_creation(self):
        """Test creating basic alerts"""
        alert = Alert(
            alert_type=AlertType.TRADE_EXECUTED,
            priority=AlertPriority.LOW,
            category=AlertCategory.SUCCESS,
            title="Trade Executed",
            message="EURUSD trade executed successfully",
            timestamp=datetime.now(),
            symbol="EURUSD",
            data={"volume": 0.1, "price": 1.1234}
        )
        
        self.assertEqual(alert.alert_type, AlertType.TRADE_EXECUTED)
        self.assertEqual(alert.priority, AlertPriority.LOW)
        self.assertEqual(alert.category, AlertCategory.SUCCESS)
        self.assertEqual(alert.symbol, "EURUSD")
        self.assertFalse(alert.sent)
        self.assertEqual(alert.retry_count, 0)
        
    def test_alert_message_formatting(self):
        """Test alert message formatting with templates"""
        alert = Alert(
            alert_type=AlertType.TRADE_EXECUTED,
            priority=AlertPriority.LOW,
            category=AlertCategory.SUCCESS,
            title="Trade Executed",
            message="Trade completed",
            timestamp=datetime(2023, 6, 23, 14, 30, 0),
            symbol="EURUSD",
            data={
                "direction": "BUY",
                "volume": 0.1,
                "entry_price": 1.1234
            }
        )
        
        formatted = self.alert_manager._format_alert_message(alert)
        
        self.assertIn("Trade Executed", formatted)
        self.assertIn("EURUSD", formatted)
        self.assertIn("BUY", formatted)
        self.assertIn("0.1", formatted)
        self.assertIn("1.1234", formatted)
        self.assertIn("2023-06-23 14:30:00", formatted)
        
    def test_parsing_failed_alert(self):
        """Test parsing failed alert creation"""
        self.alert_manager.send_parsing_failed_alert(
            provider="TestProvider",
            signal_id="SIG_001",
            error="Invalid format"
        )
        
        # Check alert was queued
        self.assertGreater(self.alert_manager.alert_queue.qsize(), 0)
        
    def test_trade_executed_alert(self):
        """Test trade executed alert creation"""
        self.alert_manager.send_trade_executed_alert(
            symbol="GBPUSD",
            direction="SELL",
            volume=0.05,
            entry_price=1.2567
        )
        
        # Check alert was queued
        self.assertGreater(self.alert_manager.alert_queue.qsize(), 0)
        
    def test_risk_rule_blocked_alert(self):
        """Test risk rule blocked alert creation"""
        self.alert_manager.send_risk_rule_blocked_alert(
            symbol="XAUUSD",
            rule_name="Margin Check",
            reason="Insufficient margin"
        )
        
        # Check alert was queued
        self.assertGreater(self.alert_manager.alert_queue.qsize(), 0)

class TestUserSettings(TestCopilotAlertManager):
    """Test user settings and filtering functionality"""
    
    def test_user_settings_creation(self):
        """Test creating user alert settings"""
        settings = UserAlertSettings(
            user_id="test_user_2",
            enabled_categories={AlertCategory.TRADING, AlertCategory.ERROR},
            enabled_types={AlertType.TRADE_EXECUTED, AlertType.PARSING_FAILED},
            priority_threshold=AlertPriority.HIGH,
            rate_limit_per_hour=20
        )
        
        self.assertEqual(settings.user_id, "test_user_2")
        self.assertIn(AlertCategory.TRADING, settings.enabled_categories)
        self.assertIn(AlertType.TRADE_EXECUTED, settings.enabled_types)
        self.assertEqual(settings.priority_threshold, AlertPriority.HIGH)
        self.assertEqual(settings.rate_limit_per_hour, 20)
        
    def test_should_send_alert_filtering(self):
        """Test alert filtering based on user settings"""
        self.alert_manager._load_user_settings()
        
        # Create alerts with different priorities and types
        low_priority_alert = Alert(
            alert_type=AlertType.TRADE_EXECUTED,
            priority=AlertPriority.LOW,
            category=AlertCategory.SUCCESS,
            title="Low Priority Trade",
            message="Trade executed",
            timestamp=datetime.now()
        )
        
        high_priority_alert = Alert(
            alert_type=AlertType.PARSING_FAILED,
            priority=AlertPriority.HIGH,
            category=AlertCategory.ERROR,
            title="High Priority Error",
            message="Parsing failed",
            timestamp=datetime.now()
        )
        
        disabled_type_alert = Alert(
            alert_type=AlertType.MT5_CONNECTION_LOST,  # Not in enabled_types
            priority=AlertPriority.CRITICAL,
            category=AlertCategory.ERROR,
            title="MT5 Error",
            message="Connection lost",
            timestamp=datetime.now()
        )
        
        # Test filtering
        self.assertFalse(self.alert_manager._should_send_alert(low_priority_alert, "test_user"))  # Below threshold
        self.assertTrue(self.alert_manager._should_send_alert(high_priority_alert, "test_user"))   # Matches criteria
        self.assertFalse(self.alert_manager._should_send_alert(disabled_type_alert, "test_user"))  # Type not enabled
        
    def test_quiet_hours_filtering(self):
        """Test quiet hours filtering"""
        self.alert_manager._load_user_settings()
        
        # Mock current time to be in quiet hours (e.g., 23:00)
        with patch('copilot_alert_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = datetime.strptime("23:00", "%H:%M").time()
            
            alert = Alert(
                alert_type=AlertType.TRADE_EXECUTED,
                priority=AlertPriority.MEDIUM,  # Not critical
                category=AlertCategory.SUCCESS,
                title="Trade",
                message="Trade executed",
                timestamp=datetime.now()
            )
            
            # Should be blocked during quiet hours
            self.assertFalse(self.alert_manager._should_send_alert(alert, "test_user"))
            
            # Critical alerts should still go through
            alert.priority = AlertPriority.CRITICAL
            self.assertTrue(self.alert_manager._should_send_alert(alert, "test_user"))
            
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        user_id = "rate_test_user"
        
        # Set up user with low rate limit
        settings = UserAlertSettings(
            user_id=user_id,
            enabled_categories={AlertCategory.TRADING},
            enabled_types={AlertType.TRADE_EXECUTED},
            priority_threshold=AlertPriority.LOW,
            rate_limit_per_hour=2  # Very low limit
        )
        self.alert_manager.user_settings[user_id] = settings
        
        # First two calls should pass
        self.assertFalse(self.alert_manager._is_rate_limited(user_id))
        self.assertFalse(self.alert_manager._is_rate_limited(user_id))
        
        # Third call should be rate limited
        self.assertTrue(self.alert_manager._is_rate_limited(user_id))

class TestAlertProcessing(TestCopilotAlertManager):
    """Test alert processing and Telegram integration"""
    
    def test_alert_queue_management(self):
        """Test alert queue operations"""
        initial_size = self.alert_manager.alert_queue.qsize()
        
        # Add alert to queue
        self.alert_manager.send_alert(
            alert_type=AlertType.TRADE_EXECUTED,
            title="Test Alert",
            message="Test message",
            priority=AlertPriority.MEDIUM,
            category=AlertCategory.SUCCESS
        )
        
        # Check queue size increased
        self.assertEqual(self.alert_manager.alert_queue.qsize(), initial_size + 1)
        
    @patch('copilot_alert_manager.CopilotAlertManager._send_telegram_alert')
    def test_alert_processing_success(self, mock_send):
        """Test successful alert processing"""
        async def run_test():
            # Mock successful Telegram send
            mock_send.return_value = True
            
            alert = Alert(
                alert_type=AlertType.TRADE_EXECUTED,
                priority=AlertPriority.MEDIUM,
                category=AlertCategory.SUCCESS,
                title="Test Trade",
                message="Trade executed",
                timestamp=datetime.now(),
                symbol="EURUSD"
            )
            
            # Process alert
            await self.alert_manager._process_alert(alert)
            
            # Check statistics
            self.assertEqual(self.alert_manager.stats["total_alerts"], 1)
            
        asyncio.run(run_test())
        
    @patch('copilot_alert_manager.CopilotAlertManager._send_telegram_alert')
    def test_alert_processing_failure_with_fallback(self, mock_send):
        """Test alert processing failure with fallback logging"""
        async def run_test():
            # Mock failed Telegram send
            mock_send.return_value = False
            
            alert = Alert(
                alert_type=AlertType.PARSING_FAILED,
                priority=AlertPriority.HIGH,
                category=AlertCategory.ERROR,
                title="Parse Error",
                message="Failed to parse signal",
                timestamp=datetime.now(),
                provider="TestProvider"
            )
            
            # Process alert
            await self.alert_manager._process_alert(alert)
            
            # Check that fallback log was created
            self.assertTrue(os.path.exists(self.alert_manager.fallback_log_path))
            
        asyncio.run(run_test())
        
    def test_telegram_integration_mock(self):
        """Test Telegram integration with mocked bot"""
        async def run_test():
            # Mock copilot bot
            mock_bot = Mock()
            mock_bot.send_alert = AsyncMock(return_value=True)
            self.alert_manager.copilot_bot = mock_bot
            
            alert = Alert(
                alert_type=AlertType.TRADE_EXECUTED,
                priority=AlertPriority.MEDIUM,
                category=AlertCategory.SUCCESS,
                title="Mock Test",
                message="Mock trade executed",
                timestamp=datetime.now()
            )
            
            # Test sending
            success = await self.alert_manager._send_telegram_alert(alert, "test_user")
            
            self.assertTrue(success)
            mock_bot.send_alert.assert_called_once()
            
        asyncio.run(run_test())

class TestStatistics(TestCopilotAlertManager):
    """Test statistics tracking"""
    
    def test_statistics_initialization(self):
        """Test initial statistics state"""
        stats = self.alert_manager.get_statistics()
        
        self.assertEqual(stats["total_alerts"], 0)
        self.assertEqual(stats["sent_alerts"], 0)
        self.assertEqual(stats["failed_alerts"], 0)
        self.assertEqual(stats["success_rate"], 0.0)
        self.assertGreaterEqual(stats["queue_size"], 0)
        
    def test_statistics_tracking(self):
        """Test statistics updates during processing"""
        # Simulate some alerts
        self.alert_manager.stats["total_alerts"] = 10
        self.alert_manager.stats["sent_alerts"] = 8
        self.alert_manager.stats["failed_alerts"] = 2
        
        stats = self.alert_manager.get_statistics()
        
        self.assertEqual(stats["total_alerts"], 10)
        self.assertEqual(stats["sent_alerts"], 8)
        self.assertEqual(stats["failed_alerts"], 2)
        self.assertEqual(stats["success_rate"], 80.0)

class TestProcessingControl(TestCopilotAlertManager):
    """Test processing start/stop functionality"""
    
    def test_start_stop_processing(self):
        """Test starting and stopping alert processing"""
        # Start processing
        self.alert_manager.start_processing()
        self.assertTrue(self.alert_manager.processing)
        
        # Stop processing
        self.alert_manager.stop_processing()
        self.assertFalse(self.alert_manager.processing)
        
    def test_disabled_manager(self):
        """Test behavior when alert manager is disabled"""
        # Disable in config
        self.alert_manager.config["enabled"] = False
        
        # Try to start processing
        self.alert_manager.start_processing()
        
        # Should remain stopped
        self.assertFalse(self.alert_manager.processing)

class TestErrorHandling(TestCopilotAlertManager):
    """Test error handling and edge cases"""
    
    def test_invalid_config_handling(self):
        """Test handling of invalid configuration"""
        # Create alert manager with invalid config
        invalid_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        invalid_config.write("invalid json content")
        invalid_config.close()
        
        try:
            manager = CopilotAlertManager(config_path=invalid_config.name)
            # Should use default config
            self.assertIsNotNone(manager.config)
            self.assertTrue(manager.config.get("enabled", False))
        finally:
            os.unlink(invalid_config.name)
            
    def test_missing_template_variables(self):
        """Test handling of missing template variables"""
        alert = Alert(
            alert_type=AlertType.TRADE_EXECUTED,
            priority=AlertPriority.MEDIUM,
            category=AlertCategory.SUCCESS,
            title="Test",
            message="Test message",
            timestamp=datetime.now(),
            data={}  # Missing expected variables
        )
        
        # Should not crash and return fallback format
        formatted = self.alert_manager._format_alert_message(alert)
        self.assertIsNotNone(formatted)
        self.assertIn("Test", formatted)

if __name__ == '__main__':
    unittest.main()