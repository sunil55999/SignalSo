"""
Test suite for the Telegram Copilot Bot
Tests command handling, authorization, and API integration
"""

import unittest
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
import asyncio

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from copilot_bot import SignalOSCopilot

class TestCopilotBot(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        
        # Create test configuration
        test_config = {
            "telegram": {
                "bot_token": "test_token_123",
                "allowed_chat_ids": [12345, 67890]
            },
            "server": {
                "url": "http://localhost:5000"
            },
            "conditions": {
                "max_slippage_pips": 2.0,
                "max_spread_pips": 3.0
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_config_loading(self):
        """Test configuration loading"""
        bot = SignalOSCopilot(self.config_file)
        self.assertEqual(bot.bot_token, "test_token_123")
        self.assertEqual(bot.allowed_chat_ids, [12345, 67890])
        self.assertEqual(bot.server_url, "http://localhost:5000")
    
    def test_authorization(self):
        """Test chat authorization"""
        bot = SignalOSCopilot(self.config_file)
        
        # Authorized chat
        self.assertTrue(bot._is_authorized(12345))
        self.assertTrue(bot._is_authorized(67890))
        
        # Unauthorized chat
        self.assertFalse(bot._is_authorized(99999))
    
    @patch('requests.get')
    async def test_api_request_get(self, mock_get):
        """Test GET API requests"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        result = await bot._api_request("/test-endpoint")
        self.assertEqual(result, {"status": "ok"})
        mock_get.assert_called_once_with("http://localhost:5000/api/test-endpoint", timeout=10)
    
    @patch('requests.post')
    async def test_api_request_post(self, mock_post):
        """Test POST API requests"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response
        
        test_data = {"signal_id": 123}
        result = await bot._api_request("/test-endpoint", "POST", test_data)
        self.assertEqual(result, {"success": True})
        mock_post.assert_called_once_with(
            "http://localhost:5000/api/test-endpoint", 
            json=test_data, 
            timeout=10
        )
    
    async def test_status_command(self):
        """Test /status command"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock API responses
        bot._api_request = AsyncMock(side_effect=[
            {"isConnected": True},  # MT5 status
            {"activeTrades": 3, "todaysPnL": "150.00", "signalsProcessed": 10, "successRate": "85.5"}  # Dashboard stats
        ])
        
        # Mock update and context
        update = Mock()
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        
        await bot.status_command(update, context)
        
        # Verify reply was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]
        
        self.assertIn("Connected", message_text)
        self.assertIn("Active Trades: 3", message_text)
        self.assertIn("$150.00", message_text)
    
    async def test_trades_command(self):
        """Test /trades command"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock API response with trades
        mock_trades = [
            {
                "symbol": "EURUSD",
                "action": "BUY",
                "entryPrice": "1.1000",
                "currentPrice": "1.1025",
                "lotSize": "0.01",
                "profit": "25.00",
                "mt5Ticket": "12345"
            }
        ]
        bot._api_request = AsyncMock(return_value=mock_trades)
        
        # Mock update and context
        update = Mock()
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        
        await bot.trades_command(update, context)
        
        # Verify reply contains trade information
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]
        
        self.assertIn("EURUSD BUY", message_text)
        self.assertIn("$25.00", message_text)
        self.assertIn("Ticket: 12345", message_text)
    
    async def test_replay_command(self):
        """Test /replay command"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock successful replay
        bot._api_request = AsyncMock(return_value={"success": True})
        
        # Mock update and context
        update = Mock()
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        context.args = ["123"]
        
        await bot.replay_command(update, context)
        
        # Verify API call and reply
        bot._api_request.assert_called_once_with("/signals/123/replay", "POST")
        update.message.reply_text.assert_called_once()
        
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("Signal 123 queued for replay", message_text)
    
    async def test_replay_command_invalid_id(self):
        """Test /replay command with invalid signal ID"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock update and context
        update = Mock()
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        context.args = ["invalid"]
        
        await bot.replay_command(update, context)
        
        # Verify error message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("Invalid signal ID", message_text)
    
    async def test_stealth_command(self):
        """Test /stealth command toggle"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock update and context
        update = Mock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        
        # Initial state should be False
        self.assertFalse(bot.stealth_mode)
        
        # Toggle stealth mode on
        await bot.stealth_command(update, context)
        self.assertTrue(bot.stealth_mode)
        
        # Verify reply
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("enabled", message_text)
        
        # Toggle stealth mode off
        update.message.reply_text.reset_mock()
        await bot.stealth_command(update, context)
        self.assertFalse(bot.stealth_mode)
        
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("disabled", message_text)
    
    async def test_pause_resume_commands(self):
        """Test /pause and /resume commands"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock update and context
        update = Mock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        
        # Initial state should be False (not paused)
        self.assertFalse(bot.trading_paused)
        
        # Pause trading
        await bot.pause_command(update, context)
        self.assertTrue(bot.trading_paused)
        
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("paused", message_text)
        
        # Resume trading
        update.message.reply_text.reset_mock()
        await bot.resume_command(update, context)
        self.assertFalse(bot.trading_paused)
        
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("resumed", message_text)
    
    async def test_handle_signal_message(self):
        """Test handling of signal-like messages"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock update and context
        update = Mock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.text = "BUY EURUSD\nEntry: 1.1000\nSL: 1.0950\nTP: 1.1050"
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        
        await bot.handle_message(update, context)
        
        # Should detect signal and acknowledge
        self.assertEqual(update.message.reply_text.call_count, 2)
        
        first_call = update.message.reply_text.call_args_list[0][0][0]
        second_call = update.message.reply_text.call_args_list[1][0][0]
        
        self.assertIn("Signal detected", first_call)
        self.assertIn("parsed and queued", second_call)
    
    async def test_unauthorized_access(self):
        """Test unauthorized chat access"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock update from unauthorized chat
        update = Mock()
        update.effective_chat.id = 99999  # Not in allowed list
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        
        await bot.status_command(update, context)
        
        # Should not reply to unauthorized user
        update.message.reply_text.assert_not_called()
    
    async def test_send_alert(self):
        """Test sending alerts to authorized chats"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock the bot's send_message method
        bot.application = Mock()
        bot.application.bot = Mock()
        bot.application.bot.send_message = AsyncMock()
        
        await bot.send_alert("Test alert message")
        
        # Should send to all allowed chat IDs
        self.assertEqual(bot.application.bot.send_message.call_count, 2)
        
        # Check first call
        first_call = bot.application.bot.send_message.call_args_list[0]
        self.assertEqual(first_call.kwargs['chat_id'], 12345)
        self.assertIn("Test alert message", first_call.kwargs['text'])
    
    async def test_send_trade_notification(self):
        """Test sending trade execution notifications"""
        bot = SignalOSCopilot(self.config_file)
        
        # Mock the bot's send_message method
        bot.application = Mock()
        bot.application.bot = Mock()
        bot.application.bot.send_message = AsyncMock()
        
        trade_info = {
            "symbol": "EURUSD",
            "action": "BUY",
            "entry_price": "1.1000",
            "mt5_ticket": "12345"
        }
        
        await bot.send_trade_notification(trade_info)
        
        # Should send to all allowed chat IDs
        self.assertEqual(bot.application.bot.send_message.call_count, 2)
        
        # Check message content
        first_call = bot.application.bot.send_message.call_args_list[0]
        message_text = first_call.kwargs['text']
        self.assertIn("Trade Executed", message_text)
        self.assertIn("EURUSD", message_text)
        self.assertIn("BUY", message_text)

class TestCopilotBotIntegration(unittest.TestCase):
    """Integration tests for bot with mocked Telegram API"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.json")
        
        test_config = {
            "telegram": {
                "bot_token": "test_token",
                "allowed_chat_ids": [12345]
            },
            "server": {
                "url": "http://localhost:5000"
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('telegram.ext.Application.builder')
    def test_bot_initialization(self, mock_builder):
        """Test bot initialization and handler setup"""
        mock_app = Mock()
        mock_builder.return_value.token.return_value.build.return_value = mock_app
        
        bot = SignalOSCopilot(self.config_file)
        
        # Verify application was created with correct token
        mock_builder.assert_called_once()
        mock_builder.return_value.token.assert_called_once_with("test_token")
        
        # Verify handlers were added
        self.assertTrue(mock_app.add_handler.called)
        self.assertGreater(mock_app.add_handler.call_count, 5)  # Multiple handlers added

if __name__ == '__main__':
    unittest.main(verbosity=2)