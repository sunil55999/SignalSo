#!/usr/bin/env python3
"""
SignalOS Copilot Bot - Telegram Bot Interface
"""

import asyncio
import logging
from typing import Dict, Any
from auth.telegram_auth import TelegramAuth

class SignalOSCopilot:
    """SignalOS Telegram Copilot Bot"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.logger = logging.getLogger('SignalOSCopilot')
        self.telegram_auth = TelegramAuth(config_file)
        self.is_running = False
        
    async def start(self):
        """Start the copilot bot"""
        self.is_running = True
        self.logger.info("SignalOS Copilot Bot started")
        
        # Keep running
        while self.is_running:
            await asyncio.sleep(1)
            
    async def stop(self):
        """Stop the copilot bot"""
        self.is_running = False
        self.logger.info("SignalOS Copilot Bot stopped")
        
    def get_status(self) -> Dict[str, Any]:
        """Get bot status"""
        return {
            "running": self.is_running,
            "telegram_configured": self.telegram_auth.is_configured()
        }