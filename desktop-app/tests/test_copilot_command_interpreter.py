"""
Test Suite for Copilot Command Interpreter
Tests command parsing, routing, and execution functionality
"""

import unittest
import json
import tempfile
import os
import time
from datetime import datetime
from unittest.mock import Mock, patch

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copilot_command_interpreter import (
    CopilotCommandInterpreter, CommandType, CommandScope, ParsedCommand,
    CommandResult, UserRole
)

class TestCopilotCommandInterpreter(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "copilot_command_interpreter": {
                "enabled": True,
                "require_authorization": True,
                "default_user_role": "user",
                "admin_users": ["admin_001"],
                "command_timeout": 30,
                "max_concurrent_commands": 5,
                "allowed_symbols": ["EURUSD", "GBPUSD", "XAUUSD"],
                "stealth_commands_enabled": True,
                "replay_commands_enabled": True
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize command interpreter
        self.interpreter = CopilotCommandInterpreter(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)

class TestBasicFunctionality(TestCopilotCommandInterpreter):
    """Test basic command interpreter functionality"""
    
    def test_initialization(self):
        """Test command interpreter initialization"""
        self.assertTrue(self.interpreter.config['enabled'])
        self.assertEqual(self.interpreter.config['default_user_role'], 'user')
        self.assertIn('admin_001', self.interpreter.config['admin_users'])
        
    def test_user_role_assignment(self):
        """Test user role assignment and authorization"""
        # Test admin user
        admin_role = self.interpreter._get_user_role("admin_001")
        self.assertEqual(admin_role, UserRole.ADMIN)
        
        # Test regular user
        user_role = self.interpreter._get_user_role("user_001")
        self.assertEqual(user_role, UserRole.USER)
        
        # Test authorization
        self.assertTrue(self.interpreter._is_authorized("admin_001", CommandType.STEALTH))
        self.assertTrue(self.interpreter._is_authorized("user_001", CommandType.STATUS))
        self.assertFalse(self.interpreter._is_authorized("user_001", CommandType.SET))

class TestCommandParsing(TestCopilotCommandInterpreter):
    """Test command parsing functionality"""
    
    def test_status_command_parsing(self):
        """Test parsing of status commands"""
        # Global status
        cmd = self.interpreter.parse_command("/status", "user_001")
        self.assertEqual(cmd.command_type, CommandType.STATUS)
        self.assertEqual(cmd.scope, CommandScope.GLOBAL)
        self.assertIsNone(cmd.target)
        
        # Symbol status
        cmd = self.interpreter.parse_command("/status EURUSD", "user_001")
        self.assertEqual(cmd.command_type, CommandType.STATUS)
        self.assertEqual(cmd.scope, CommandScope.SYMBOL)
        self.assertEqual(cmd.target, "EURUSD")
        
        # Provider status
        cmd = self.interpreter.parse_command("/status provider123", "user_001")
        self.assertEqual(cmd.command_type, CommandType.STATUS)
        self.assertEqual(cmd.scope, CommandScope.PROVIDER)
        self.assertEqual(cmd.target, "PROVIDER123")
        
    def test_replay_command_parsing(self):
        """Test parsing of replay commands"""
        # Basic replay
        cmd = self.interpreter.parse_command("/replay XAUUSD", "user_001")
        self.assertEqual(cmd.command_type, CommandType.REPLAY)
        self.assertEqual(cmd.scope, CommandScope.SYMBOL)
        self.assertEqual(cmd.target, "XAUUSD")
        
        # Replay with count
        cmd = self.interpreter.parse_command("/replay GBPUSD 3", "user_001")
        self.assertEqual(cmd.command_type, CommandType.REPLAY)
        self.assertEqual(cmd.target, "GBPUSD")
        self.assertEqual(cmd.parameters.get("count"), 3)
        
        # Replay last signal
        cmd = self.interpreter.parse_command("/replay EURUSD last", "user_001")
        self.assertEqual(cmd.parameters.get("count"), 1)
        
    def test_stealth_command_parsing(self):
        """Test parsing of stealth commands"""
        # Enable stealth
        cmd = self.interpreter.parse_command("/stealth on", "admin_001")
        self.assertEqual(cmd.command_type, CommandType.STEALTH)
        self.assertEqual(cmd.scope, CommandScope.GLOBAL)
        self.assertTrue(cmd.parameters.get("enabled"))
        
        # Disable stealth
        cmd = self.interpreter.parse_command("/stealth off", "admin_001")
        self.assertEqual(cmd.command_type, CommandType.STEALTH)
        self.assertFalse(cmd.parameters.get("enabled"))
        
        # Alternative syntax
        cmd = self.interpreter.parse_command("/stealth enable", "admin_001")
        self.assertTrue(cmd.parameters.get("enabled"))
        
        cmd = self.interpreter.parse_command("/stealth disable", "admin_001")
        self.assertFalse(cmd.parameters.get("enabled"))
        
    def test_enable_disable_command_parsing(self):
        """Test parsing of enable/disable commands"""
        # Enable symbol
        cmd = self.interpreter.parse_command("/enable EURUSD", "user_001")
        self.assertEqual(cmd.command_type, CommandType.ENABLE)
        self.assertEqual(cmd.scope, CommandScope.SYMBOL)
        self.assertEqual(cmd.target, "EURUSD")
        
        # Disable provider
        cmd = self.interpreter.parse_command("/disable provider123", "user_001")
        self.assertEqual(cmd.command_type, CommandType.DISABLE)
        self.assertEqual(cmd.scope, CommandScope.PROVIDER)
        self.assertEqual(cmd.target, "PROVIDER123")
        
        # Enable all
        cmd = self.interpreter.parse_command("/enable all", "admin_001")
        self.assertEqual(cmd.scope, CommandScope.GLOBAL)
        self.assertIsNone(cmd.target)
        
    def test_set_command_parsing(self):
        """Test parsing of set commands"""
        # Set symbol parameter
        cmd = self.interpreter.parse_command("/set EURUSD lot 0.05", "admin_001")
        self.assertEqual(cmd.command_type, CommandType.SET)
        self.assertEqual(cmd.scope, CommandScope.SYMBOL)
        self.assertEqual(cmd.target, "EURUSD")
        self.assertEqual(cmd.parameters.get("lot"), 0.05)
        
        # Set boolean parameter
        cmd = self.interpreter.parse_command("/set strategy123 enabled true", "admin_001")
        self.assertEqual(cmd.scope, CommandScope.STRATEGY)
        self.assertEqual(cmd.target, "STRATEGY123")
        self.assertTrue(cmd.parameters.get("enabled"))
        
        # Set string parameter
        cmd = self.interpreter.parse_command("/set GBPUSD comment test comment", "admin_001")
        self.assertEqual(cmd.parameters.get("comment"), "test comment")
        
    def test_get_command_parsing(self):
        """Test parsing of get commands"""
        # Get specific parameter
        cmd = self.interpreter.parse_command("/get EURUSD lot", "user_001")
        self.assertEqual(cmd.command_type, CommandType.GET)
        self.assertEqual(cmd.scope, CommandScope.SYMBOL)
        self.assertEqual(cmd.target, "EURUSD")
        self.assertEqual(cmd.parameters.get("parameter"), "lot")
        
        # Get default status
        cmd = self.interpreter.parse_command("/get GBPUSD", "user_001")
        self.assertEqual(cmd.parameters.get("parameter"), "status")
        
    def test_help_command_parsing(self):
        """Test parsing of help commands"""
        # General help
        cmd = self.interpreter.parse_command("/help", "user_001")
        self.assertEqual(cmd.command_type, CommandType.HELP)
        self.assertEqual(cmd.scope, CommandScope.GLOBAL)
        
        # Specific topic help
        cmd = self.interpreter.parse_command("/help status", "user_001")
        self.assertEqual(cmd.parameters.get("topic"), "status")
        
    def test_unknown_command_parsing(self):
        """Test parsing of unknown commands"""
        cmd = self.interpreter.parse_command("/unknown command", "user_001")
        self.assertEqual(cmd.command_type, CommandType.UNKNOWN)
        
        cmd = self.interpreter.parse_command("not a command", "user_001")
        self.assertEqual(cmd.command_type, CommandType.UNKNOWN)
        
    def test_invalid_command_parsing(self):
        """Test parsing of invalid/malformed commands"""
        # Empty command
        cmd = self.interpreter.parse_command("", "user_001")
        self.assertEqual(cmd.command_type, CommandType.UNKNOWN)
        
        # Whitespace only
        cmd = self.interpreter.parse_command("   ", "user_001")
        self.assertEqual(cmd.command_type, CommandType.UNKNOWN)

class TestCommandExecution(TestCopilotCommandInterpreter):
    """Test command execution functionality"""
    
    def test_status_command_execution(self):
        """Test execution of status commands"""
        # Global status
        cmd = ParsedCommand(
            command_type=CommandType.STATUS,
            scope=CommandScope.GLOBAL,
            user_id="user_001"
        )
        
        result = self.interpreter.execute_command(cmd)
        self.assertTrue(result.success)
        self.assertIn("System Status", result.message)
        self.assertIn("system_status", result.data)
        
        # Symbol status
        cmd = ParsedCommand(
            command_type=CommandType.STATUS,
            scope=CommandScope.SYMBOL,
            target="EURUSD",
            user_id="user_001"
        )
        
        result = self.interpreter.execute_command(cmd)
        self.assertTrue(result.success)
        self.assertIn("EURUSD Status", result.message)
        self.assertIn("symbol", result.data)
        
    def test_replay_command_execution(self):
        """Test execution of replay commands"""
        cmd = ParsedCommand(
            command_type=CommandType.REPLAY,
            scope=CommandScope.SYMBOL,
            target="XAUUSD",
            parameters={"count": 2},
            user_id="user_001"
        )
        
        result = self.interpreter.execute_command(cmd)
        self.assertTrue(result.success)
        self.assertIn("Replay Command", result.message)
        self.assertIn("XAUUSD", result.message)
        self.assertEqual(result.data["count"], 2)
        
    def test_stealth_command_execution(self):
        """Test execution of stealth commands"""
        # Enable stealth
        cmd = ParsedCommand(
            command_type=CommandType.STEALTH,
            scope=CommandScope.GLOBAL,
            parameters={"enabled": True},
            user_id="admin_001"
        )
        
        result = self.interpreter.execute_command(cmd)
        self.assertTrue(result.success)
        self.assertIn("Stealth Mode", result.message)
        self.assertTrue(result.data["stealth_enabled"])
        
        # Disable stealth
        cmd.parameters["enabled"] = False
        result = self.interpreter.execute_command(cmd)
        self.assertTrue(result.success)
        self.assertFalse(result.data["stealth_enabled"])
        
    def test_enable_disable_command_execution(self):
        """Test execution of enable/disable commands"""
        # Enable command
        cmd = ParsedCommand(
            command_type=CommandType.ENABLE,
            scope=CommandScope.SYMBOL,
            target="EURUSD",
            user_id="user_001"
        )
        
        result = self.interpreter.execute_command(cmd)
        self.assertTrue(result.success)
        self.assertIn("Enable Command", result.message)
        self.assertTrue(result.data["enabled"])
        
        # Disable command
        cmd.command_type = CommandType.DISABLE
        result = self.interpreter.execute_command(cmd)
        self.assertTrue(result.success)
        self.assertIn("Disable Command", result.message)
        self.assertFalse(result.data["enabled"])
        
    def test_set_command_execution(self):
        """Test execution of set commands"""
        cmd = ParsedCommand(
            command_type=CommandType.SET,
            scope=CommandScope.SYMBOL,
            target="EURUSD",
            parameters={"lot": 0.05},
            user_id="admin_001"
        )
        
        result = self.interpreter.execute_command(cmd)
        self.assertTrue(result.success)
        self.assertIn("Set Command", result.message)
        self.assertEqual(result.data["parameter"], "lot")
        self.assertEqual(result.data["value"], 0.05)
        
    def test_get_command_execution(self):
        """Test execution of get commands"""
        cmd = ParsedCommand(
            command_type=CommandType.GET,
            scope=CommandScope.SYMBOL,
            target="EURUSD",
            parameters={"parameter": "lot"},
            user_id="user_001"
        )
        
        result = self.interpreter.execute_command(cmd)
        self.assertTrue(result.success)
        self.assertIn("Get Command", result.message)
        self.assertEqual(result.data["parameter"], "lot")
        self.assertIn("value", result.data)
        
    def test_help_command_execution(self):
        """Test execution of help commands"""
        cmd = ParsedCommand(
            command_type=CommandType.HELP,
            scope=CommandScope.GLOBAL,
            parameters={"topic": "general"},
            user_id="user_001"
        )
        
        result = self.interpreter.execute_command(cmd)
        self.assertTrue(result.success)
        self.assertIn("SignalOS Copilot Commands", result.message)
        self.assertIn("/status", result.message)
        self.assertIn("/help", result.message)

class TestAuthorization(TestCopilotCommandInterpreter):
    """Test authorization and permission functionality"""
    
    def test_admin_permissions(self):
        """Test admin user permissions"""
        # Admin should be able to execute all commands
        admin_commands = [
            CommandType.STATUS, CommandType.REPLAY, CommandType.STEALTH,
            CommandType.ENABLE, CommandType.DISABLE, CommandType.SET, CommandType.GET
        ]
        
        for cmd_type in admin_commands:
            self.assertTrue(
                self.interpreter._is_authorized("admin_001", cmd_type),
                f"Admin should be authorized for {cmd_type.value}"
            )
            
    def test_user_permissions(self):
        """Test regular user permissions"""
        # User should be able to execute basic commands
        allowed_commands = [
            CommandType.STATUS, CommandType.HELP, CommandType.GET,
            CommandType.PAUSE, CommandType.RESUME, CommandType.STEALTH, CommandType.REPLAY
        ]
        
        for cmd_type in allowed_commands:
            self.assertTrue(
                self.interpreter._is_authorized("user_001", cmd_type),
                f"User should be authorized for {cmd_type.value}"
            )
            
        # User should NOT be able to execute admin commands
        restricted_commands = [CommandType.SET]
        
        for cmd_type in restricted_commands:
            self.assertFalse(
                self.interpreter._is_authorized("user_001", cmd_type),
                f"User should NOT be authorized for {cmd_type.value}"
            )
            
    def test_unauthorized_command_execution(self):
        """Test unauthorized command execution"""
        cmd = ParsedCommand(
            command_type=CommandType.SET,
            scope=CommandScope.SYMBOL,
            target="EURUSD",
            parameters={"lot": 0.05},
            user_id="user_001"  # Regular user trying admin command
        )
        
        result = self.interpreter.execute_command(cmd)
        self.assertFalse(result.success)
        self.assertIn("not authorized", result.message)
        
    def test_disabled_features(self):
        """Test disabled feature handling"""
        # Disable stealth commands
        self.interpreter.config["stealth_commands_enabled"] = False
        
        cmd = ParsedCommand(
            command_type=CommandType.STEALTH,
            scope=CommandScope.GLOBAL,
            parameters={"enabled": True},
            user_id="admin_001"
        )
        
        result = self.interpreter.execute_command(cmd)
        self.assertFalse(result.success)
        self.assertIn("disabled", result.message)

class TestHistoryAndStatistics(TestCopilotCommandInterpreter):
    """Test command history and statistics functionality"""
    
    def test_command_history_tracking(self):
        """Test command history tracking"""
        # Execute some commands
        commands = [
            "/status",
            "/status EURUSD",
            "/help"
        ]
        
        for cmd_text in commands:
            cmd = self.interpreter.parse_command(cmd_text, "user_001")
            self.interpreter.execute_command(cmd)
            
        # Check history
        history = self.interpreter.get_user_history("user_001")
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["raw_message"], "/status")
        
    def test_history_limit(self):
        """Test command history limit"""
        # Execute more commands than the limit
        for i in range(15):
            cmd = self.interpreter.parse_command(f"/status test{i}", "user_001")
            self.interpreter.execute_command(cmd)
            
        # Check that history is limited
        history = self.interpreter.get_user_history("user_001")
        self.assertEqual(len(history), self.interpreter.max_history_per_user)
        
    def test_statistics_tracking(self):
        """Test statistics tracking"""
        # Execute some commands
        cmd1 = self.interpreter.parse_command("/status", "user_001")
        self.interpreter.execute_command(cmd1)
        
        cmd2 = self.interpreter.parse_command("/set EURUSD lot 0.05", "user_001")  # Should fail (unauthorized)
        self.interpreter.execute_command(cmd2)
        
        stats = self.interpreter.get_statistics()
        
        self.assertEqual(stats["total_commands"], 2)
        self.assertEqual(stats["successful_commands"], 1)
        self.assertEqual(stats["failed_commands"], 1)
        self.assertEqual(stats["unauthorized_attempts"], 1)
        self.assertGreater(stats["success_rate"], 0)
        
    def test_clear_user_history(self):
        """Test clearing user history"""
        # Add some history
        cmd = self.interpreter.parse_command("/status", "user_001")
        self.interpreter.execute_command(cmd)
        
        # Verify history exists
        history = self.interpreter.get_user_history("user_001")
        self.assertGreater(len(history), 0)
        
        # Clear history
        success = self.interpreter.clear_user_history("user_001")
        self.assertTrue(success)
        
        # Verify history is cleared
        history = self.interpreter.get_user_history("user_001")
        self.assertEqual(len(history), 0)

class TestIntegrationScenarios(TestCopilotCommandInterpreter):
    """Test end-to-end integration scenarios"""
    
    def test_complete_command_flow(self):
        """Test complete command parsing and execution flow"""
        message = "/status EURUSD"
        user_id = "user_001"
        
        # Parse command
        cmd = self.interpreter.parse_command(message, user_id)
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.command_type, CommandType.STATUS)
        
        # Execute command
        result = self.interpreter.execute_command(cmd)
        self.assertTrue(result.success)
        self.assertIn("EURUSD", result.message)
        
        # Check history was updated
        history = self.interpreter.get_user_history(user_id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["raw_message"], message)
        
    def test_multiple_user_interactions(self):
        """Test multiple users using the interpreter"""
        users = ["user_001", "user_002", "admin_001"]
        
        for user in users:
            cmd = self.interpreter.parse_command("/status", user)
            result = self.interpreter.execute_command(cmd)
            self.assertTrue(result.success)
            
        # Check each user has their own history
        for user in users:
            history = self.interpreter.get_user_history(user)
            self.assertEqual(len(history), 1)
            
        # Check statistics
        stats = self.interpreter.get_statistics()
        self.assertEqual(stats["total_commands"], 3)
        self.assertEqual(stats["total_users"], 3)
        
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        # Invalid command parsing
        cmd = self.interpreter.parse_command("", "user_001")
        self.assertEqual(cmd.command_type, CommandType.UNKNOWN)
        
        # Command execution with missing data
        cmd = ParsedCommand(
            command_type=CommandType.SET,
            scope=CommandScope.SYMBOL,
            target="EURUSD",
            parameters={},  # Empty parameters
            user_id="admin_001"
        )
        
        result = self.interpreter.execute_command(cmd)
        self.assertFalse(result.success)
        self.assertIn("No parameters", result.message)

if __name__ == '__main__':
    unittest.main()