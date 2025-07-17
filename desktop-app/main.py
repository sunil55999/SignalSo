#!/usr/bin/env python3
"""
SignalOS Desktop Application - Main Entry Point

This is the main entry point for the SignalOS desktop trading automation application.
It initializes all core modules and starts the application's main loop.
"""

import asyncio
import logging
import signal
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Core modules
from auth import AuthTokenManager, get_auth_token
from api_client import APIClient
from auto_sync import AutoSyncEngine
from mt5_bridge import MT5Bridge
from secure_signal_parser import SecureSignalParser
from strategy_runtime import StrategyRuntime
from copilot_bot import SignalOSCopilot
from retry_engine import RetryEngine

# Create modules directory if it doesn't exist
MODULES_DIR = Path(__file__).parent
LOGS_DIR = MODULES_DIR / "logs"
CONFIG_DIR = MODULES_DIR / "config"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)


class SignalOSDesktopApp:
    """Main application class for SignalOS Desktop"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger('SignalOSDesktop')
        
        # Initialize core modules
        self.auth_manager: Optional[AuthTokenManager] = None
        self.api_client: Optional[APIClient] = None
        self.mt5_bridge: Optional[MT5Bridge] = None
        self.signal_parser: Optional[SecureSignalParser] = None
        self.strategy_runtime: Optional[StrategyRuntime] = None
        self.auto_sync: Optional[AutoSyncEngine] = None
        self.copilot_bot: Optional[SignalOSCopilot] = None
        self.retry_engine: Optional[RetryEngine] = None
        
        # Application state
        self.startup_time = datetime.now()
        self.stats = {
            "startup_time": self.startup_time.isoformat(),
            "modules_initialized": 0,
            "total_modules": 8
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Load application configuration"""
        try:
            config_path = MODULES_DIR / self.config_file
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                return self._create_default_config()
        except Exception as e:
            print(f"Failed to load config: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        default_config = {
            "app": {
                "name": "SignalOS Desktop",
                "version": "1.0.0",
                "debug": False,
                "log_level": "INFO"
            },
            "server": {
                "url": "http://localhost:5000",
                "timeout": 30,
                "retry_attempts": 3
            },
            "mt5": {
                "enabled": True,
                "server": "MetaQuotes-Demo",
                "login": 0,
                "password": "",
                "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
            },
            "telegram": {
                "bot_token": "",
                "allowed_chat_ids": [],
                "enabled": False
            },
            "sync": {
                "enabled": True,
                "interval_seconds": 60,
                "retry_attempts": 3
            },
            "strategy": {
                "enabled": True,
                "auto_execute": False,
                "max_daily_trades": 10
            },
            "risk_management": {
                "max_risk_per_trade": 2.0,
                "daily_loss_limit": 5.0,
                "max_concurrent_trades": 5
            }
        }
        
        try:
            config_path = MODULES_DIR / self.config_file
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"Created default config at: {config_path}")
        except Exception as e:
            print(f"Failed to save default config: {e}")
            
        return default_config
    
    def _setup_logging(self):
        """Setup application logging"""
        log_level = getattr(logging, self.config.get("app", {}).get("log_level", "INFO"))
        
        # Create logs directory
        log_file = LOGS_DIR / "signalos_desktop.log"
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
    async def initialize_modules(self):
        """Initialize all application modules"""
        self.logger.info("Initializing SignalOS Desktop Application...")
        
        try:
            # Initialize authentication
            self.logger.info("Initializing authentication manager...")
            self.auth_manager = AuthTokenManager()
            self.stats["modules_initialized"] += 1
            
            # Initialize API client
            self.logger.info("Initializing API client...")
            server_url = self.config.get("server", {}).get("url")
            self.api_client = APIClient(server_url=server_url)
            self.stats["modules_initialized"] += 1
            
            # Initialize MT5 bridge
            if self.config.get("mt5", {}).get("enabled", True):
                self.logger.info("Initializing MT5 bridge...")
                self.mt5_bridge = MT5Bridge(config_file=self.config_file)
                self.stats["modules_initialized"] += 1
            
            # Initialize signal parser
            self.logger.info("Initializing signal parser...")
            self.signal_parser = SecureSignalParser(config_file=self.config_file)
            self.stats["modules_initialized"] += 1
            
            # Initialize strategy runtime
            if self.config.get("strategy", {}).get("enabled", True):
                self.logger.info("Initializing strategy runtime...")
                self.strategy_runtime = StrategyRuntime(config_file=self.config_file)
                self.stats["modules_initialized"] += 1
            
            # Initialize retry engine
            self.logger.info("Initializing retry engine...")
            self.retry_engine = RetryEngine(config_file=self.config_file)
            self.stats["modules_initialized"] += 1
            
            # Initialize auto sync
            if self.config.get("sync", {}).get("enabled", True):
                self.logger.info("Initializing auto sync engine...")
                self.auto_sync = AutoSyncEngine(config_file=self.config_file)
                # Inject module references
                self.auto_sync.inject_modules(
                    mt5_bridge=self.mt5_bridge,
                    signal_parser=self.signal_parser,
                    retry_engine=self.retry_engine,
                    strategy_runtime=self.strategy_runtime
                )
                self.stats["modules_initialized"] += 1
            
            # Initialize Telegram copilot bot
            if self.config.get("telegram", {}).get("enabled", False):
                bot_token = self.config.get("telegram", {}).get("bot_token")
                if bot_token:
                    self.logger.info("Initializing Telegram copilot bot...")
                    self.copilot_bot = SignalOSCopilot(config_file=self.config_file)
                    self.stats["modules_initialized"] += 1
                else:
                    self.logger.warning("Telegram bot token not configured, skipping bot initialization")
            
            self.logger.info(f"Successfully initialized {self.stats['modules_initialized']}/{self.stats['total_modules']} modules")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize modules: {e}")
            return False
    
    async def start_services(self):
        """Start all background services"""
        self.logger.info("Starting background services...")
        
        tasks = []
        
        # Start auto sync service
        if self.auto_sync:
            self.logger.info("Starting auto sync service...")
            sync_task = asyncio.create_task(self.auto_sync.start_sync_loop())
            tasks.append(sync_task)
        
        # Start Telegram bot
        if self.copilot_bot:
            self.logger.info("Starting Telegram copilot bot...")
            try:
                bot_task = asyncio.create_task(self.copilot_bot.start())
                tasks.append(bot_task)
            except Exception as e:
                self.logger.error(f"Failed to start Telegram bot: {e}")
        
        return tasks
    
    async def shutdown(self):
        """Gracefully shutdown the application"""
        self.logger.info("Shutting down SignalOS Desktop Application...")
        self.is_running = False
        self.shutdown_event.set()
        
        # Stop auto sync
        if self.auto_sync and hasattr(self.auto_sync, 'stop_sync_loop'):
            self.logger.info("Stopping auto sync service...")
            await self.auto_sync.stop_sync_loop()
        
        # Stop Telegram bot
        if self.copilot_bot and hasattr(self.copilot_bot, 'stop'):
            self.logger.info("Stopping Telegram bot...")
            try:
                await self.copilot_bot.stop()
            except Exception as e:
                self.logger.error(f"Error stopping Telegram bot: {e}")
        
        # Close MT5 connection
        if self.mt5_bridge and hasattr(self.mt5_bridge, 'disconnect'):
            self.logger.info("Disconnecting from MT5...")
            try:
                self.mt5_bridge.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting from MT5: {e}")
        
        self.logger.info("Application shutdown complete")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current application status"""
        status = {
            "app": {
                "name": self.config.get("app", {}).get("name", "SignalOS Desktop"),
                "version": self.config.get("app", {}).get("version", "1.0.0"),
                "running": self.is_running,
                "startup_time": self.startup_time.isoformat(),
                "uptime_seconds": (datetime.now() - self.startup_time).total_seconds()
            },
            "modules": {
                "initialized": self.stats["modules_initialized"],
                "total": self.stats["total_modules"],
                "auth_manager": bool(self.auth_manager),
                "api_client": bool(self.api_client),
                "mt5_bridge": bool(self.mt5_bridge),
                "signal_parser": bool(self.signal_parser),
                "strategy_runtime": bool(self.strategy_runtime),
                "auto_sync": bool(self.auto_sync),
                "copilot_bot": bool(self.copilot_bot),
                "retry_engine": bool(self.retry_engine)
            }
        }
        
        # Add MT5 status if available
        if self.mt5_bridge and hasattr(self.mt5_bridge, 'get_status'):
            try:
                status["mt5"] = self.mt5_bridge.get_status()
            except Exception as e:
                status["mt5"] = {"error": str(e)}
        
        # Add sync status if available
        if self.auto_sync and hasattr(self.auto_sync, 'get_sync_status'):
            try:
                status["sync"] = self.auto_sync.get_sync_status()
            except Exception as e:
                status["sync"] = {"error": str(e)}
        
        return status
    
    async def run(self):
        """Main application run loop"""
        self.logger.info("Starting SignalOS Desktop Application...")
        
        try:
            # Initialize modules
            if not await self.initialize_modules():
                self.logger.error("Failed to initialize modules, exiting...")
                return False
            
            # Start services
            service_tasks = await self.start_services()
            
            self.is_running = True
            self.logger.info("SignalOS Desktop Application is now running")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            return False
        finally:
            await self.shutdown()
        
        return True


def setup_signal_handlers(app: SignalOSDesktopApp):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(app.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point"""
    print("=" * 60)
    print("SignalOS Desktop Trading Automation Application")
    print("=" * 60)
    
    # Create application instance
    app = SignalOSDesktopApp()
    
    # Setup signal handlers
    setup_signal_handlers(app)
    
    try:
        # Run the application
        success = await app.run()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nShutdown initiated by user")
        await app.shutdown()
        return 0
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))