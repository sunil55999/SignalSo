"""
Copilot Alert Manager for SignalOS
Handles all Telegram notifications for signal errors, confirmations, and system alerts
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import queue
import threading

class AlertType(Enum):
    PARSING_FAILED = "parsing_failed"
    RETRY_TRIGGERED = "retry_triggered"
    TRADE_EXECUTED = "trade_executed"
    RISK_RULE_BLOCKED = "risk_rule_blocked"
    MT5_CONNECTION_LOST = "mt5_connection_lost"
    MARGIN_WARNING = "margin_warning"
    DRAWDOWN_ALERT = "drawdown_alert"
    STRATEGY_ERROR = "strategy_error"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"

class AlertPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertCategory(Enum):
    TRADING = "trading"
    SYSTEM = "system"
    ERROR = "error"
    SUCCESS = "success"
    WARNING = "warning"

@dataclass
class Alert:
    alert_type: AlertType
    priority: AlertPriority
    category: AlertCategory
    title: str
    message: str
    timestamp: datetime
    provider: Optional[str] = None
    symbol: Optional[str] = None
    signal_id: Optional[str] = None
    user_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    sent: bool = False
    retry_count: int = 0
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}

@dataclass
class UserAlertSettings:
    user_id: str
    enabled_categories: Set[AlertCategory]
    enabled_types: Set[AlertType]
    priority_threshold: AlertPriority
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None    # HH:MM format
    rate_limit_per_hour: int = 50
    
    def __post_init__(self):
        if isinstance(self.enabled_categories, list):
            self.enabled_categories = set(self.enabled_categories)
        if isinstance(self.enabled_types, list):
            self.enabled_types = set(self.enabled_types)

class CopilotAlertManager:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/copilot_alerts.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.fallback_log_path = "logs/alerts_fallback.log"
        
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Alert queue for async processing
        self.alert_queue = queue.Queue()
        self.processing = False
        self.process_thread = None
        
        # User settings
        self.user_settings: Dict[str, UserAlertSettings] = {}
        
        # Rate limiting
        self.rate_limits: Dict[str, List[datetime]] = {}
        
        # Alert templates
        self.alert_templates = self._load_alert_templates()
        
        # Copilot bot integration
        self.copilot_bot = None
        self._initialize_copilot_bot()
        
        # Statistics
        self.stats = {
            "total_alerts": 0,
            "sent_alerts": 0,
            "failed_alerts": 0,
            "blocked_by_settings": 0,
            "rate_limited": 0,
            "alerts_by_type": {alert_type.value: 0 for alert_type in AlertType},
            "alerts_by_priority": {priority.value: 0 for priority in AlertPriority}
        }
        
        self.logger.info("Copilot alert manager initialized")
        
    def _load_config(self) -> Dict[str, Any]:
        """Load alert manager configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "copilot_alert_manager" not in config:
                config["copilot_alert_manager"] = {
                    "enabled": True,
                    "max_retries": 3,
                    "retry_delay": 5,
                    "batch_size": 10,
                    "processing_interval": 2.0,
                    "default_rate_limit": 30,
                    "enable_quiet_hours": True,
                    "fallback_to_logs": True,
                    "alert_timeout": 30,
                    "user_settings": {}
                }
                self._save_config(config)
                
            return config.get("copilot_alert_manager", {})
            
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            return self._get_default_config()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "enabled": True,
            "max_retries": 3,
            "retry_delay": 5,
            "batch_size": 10,
            "processing_interval": 2.0,
            "default_rate_limit": 30,
            "enable_quiet_hours": True,
            "fallback_to_logs": True,
            "alert_timeout": 30,
            "user_settings": {}
        }
        
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for alert manager"""
        logger = logging.getLogger("copilot_alert_manager")
        logger.setLevel(logging.INFO)
        
        # Create logs directory
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.fallback_log_path), exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
        return logger
        
    def _initialize_copilot_bot(self):
        """Initialize connection to copilot bot"""
        try:
            # Try to import and use existing copilot bot
            import sys
            sys.path.append(os.path.dirname(__file__))
            
            try:
                from copilot_bot import SignalOSCopilot
                self.copilot_bot = SignalOSCopilot(self.config_path)
                self.logger.info("Connected to copilot bot")
            except ImportError:
                self.logger.warning("Copilot bot not available, using fallback logging")
            except Exception as e:
                self.logger.error(f"Error initializing copilot bot: {e}")
                
        except Exception as e:
            self.logger.error(f"Error connecting to copilot bot: {e}")
            
    def _load_alert_templates(self) -> Dict[AlertType, str]:
        """Load alert message templates"""
        return {
            AlertType.PARSING_FAILED: "❌ **Signal Parsing Failed**\n🕒 {timestamp}\n📡 Provider: {provider}\n🔗 Signal ID: {signal_id}\n❗ Error: {error}",
            AlertType.RETRY_TRIGGERED: "⚠️ **Retry Triggered**\n🕒 {timestamp}\n📈 Symbol: {symbol}\n🔄 Attempt: {retry_count}\n📝 Reason: {reason}",
            AlertType.TRADE_EXECUTED: "✅ **Trade Executed**\n🕒 {timestamp}\n📈 Symbol: {symbol}\n📊 Direction: {direction}\n💰 Volume: {volume}\n🎯 Entry: {entry_price}",
            AlertType.RISK_RULE_BLOCKED: "🛑 **Risk Rule Blocked**\n🕒 {timestamp}\n📈 Symbol: {symbol}\n⚠️ Rule: {rule_name}\n📝 Reason: {reason}",
            AlertType.MT5_CONNECTION_LOST: "🔴 **MT5 Connection Lost**\n🕒 {timestamp}\n❗ Status: Disconnected\n🔄 Auto-reconnect: {auto_reconnect}",
            AlertType.MARGIN_WARNING: "⚠️ **Margin Warning**\n🕒 {timestamp}\n📊 Current Level: {margin_level}%\n⚠️ Threshold: {threshold}%\n💰 Free Margin: ${free_margin}",
            AlertType.DRAWDOWN_ALERT: "📉 **Drawdown Alert**\n🕒 {timestamp}\n📊 Current DD: {drawdown}%\n⚠️ Limit: {limit}%\n💰 Account Equity: ${equity}",
            AlertType.STRATEGY_ERROR: "❌ **Strategy Error**\n🕒 {timestamp}\n⚙️ Strategy: {strategy_name}\n❗ Error: {error}\n📝 Action: {action}",
            AlertType.SYSTEM_STARTUP: "🟢 **System Started**\n🕒 {timestamp}\n✅ SignalOS is now running\n🤖 Copilot bot active",
            AlertType.SYSTEM_SHUTDOWN: "🔴 **System Shutdown**\n🕒 {timestamp}\n⏹️ SignalOS shutting down\n📊 Session stats available"
        }
        
    def _load_user_settings(self):
        """Load user alert settings from config"""
        user_configs = self.config.get("user_settings", {})
        
        for user_id, settings in user_configs.items():
            try:
                # Convert string enum values back to enum objects
                enabled_categories = set()
                for cat in settings.get("enabled_categories", []):
                    if isinstance(cat, str):
                        enabled_categories.add(AlertCategory(cat))
                    else:
                        enabled_categories.add(cat)
                        
                enabled_types = set()
                for alert_type in settings.get("enabled_types", []):
                    if isinstance(alert_type, str):
                        enabled_types.add(AlertType(alert_type))
                    else:
                        enabled_types.add(alert_type)
                        
                priority_threshold = AlertPriority(settings.get("priority_threshold", "medium"))
                
                user_setting = UserAlertSettings(
                    user_id=user_id,
                    enabled_categories=enabled_categories,
                    enabled_types=enabled_types,
                    priority_threshold=priority_threshold,
                    quiet_hours_start=settings.get("quiet_hours_start"),
                    quiet_hours_end=settings.get("quiet_hours_end"),
                    rate_limit_per_hour=settings.get("rate_limit_per_hour", 30)
                )
                
                self.user_settings[user_id] = user_setting
                
            except Exception as e:
                self.logger.error(f"Error loading settings for user {user_id}: {e}")
                
    def _save_user_settings(self):
        """Save user settings to config"""
        try:
            # Load current config
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            # Update user settings
            user_configs = {}
            for user_id, settings in self.user_settings.items():
                user_configs[user_id] = {
                    "enabled_categories": [cat.value for cat in settings.enabled_categories],
                    "enabled_types": [alert_type.value for alert_type in settings.enabled_types],
                    "priority_threshold": settings.priority_threshold.value,
                    "quiet_hours_start": settings.quiet_hours_start,
                    "quiet_hours_end": settings.quiet_hours_end,
                    "rate_limit_per_hour": settings.rate_limit_per_hour
                }
                
            config["copilot_alert_manager"]["user_settings"] = user_configs
            
            # Save config
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error saving user settings: {e}")
            
    def _is_rate_limited(self, user_id: str) -> bool:
        """Check if user is rate limited"""
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = []
            
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old entries
        self.rate_limits[user_id] = [
            timestamp for timestamp in self.rate_limits[user_id]
            if timestamp > hour_ago
        ]
        
        # Check rate limit
        user_settings = self.user_settings.get(user_id)
        rate_limit = user_settings.rate_limit_per_hour if user_settings else self.config.get("default_rate_limit", 30)
        
        if len(self.rate_limits[user_id]) >= rate_limit:
            return True
            
        # Add current timestamp
        self.rate_limits[user_id].append(now)
        return False
        
    def _is_in_quiet_hours(self, user_id: str) -> bool:
        """Check if current time is in user's quiet hours"""
        if not self.config.get("enable_quiet_hours", True):
            return False
            
        user_settings = self.user_settings.get(user_id)
        if not user_settings or not user_settings.quiet_hours_start or not user_settings.quiet_hours_end:
            return False
            
        try:
            now = datetime.now().time()
            start = datetime.strptime(user_settings.quiet_hours_start, "%H:%M").time()
            end = datetime.strptime(user_settings.quiet_hours_end, "%H:%M").time()
            
            if start <= end:
                return start <= now <= end
            else:  # Overnight quiet hours
                return now >= start or now <= end
                
        except ValueError:
            return False
            
    def _should_send_alert(self, alert: Alert, user_id: str) -> bool:
        """Determine if alert should be sent to user"""
        user_settings = self.user_settings.get(user_id)
        
        if not user_settings:
            # Default settings - allow most alerts
            return alert.priority in [AlertPriority.HIGH, AlertPriority.CRITICAL]
            
        # Check if alert type is enabled
        if alert.alert_type not in user_settings.enabled_types:
            return False
            
        # Check if alert category is enabled
        if alert.category not in user_settings.enabled_categories:
            return False
            
        # Check priority threshold
        priority_levels = {
            AlertPriority.LOW: 1,
            AlertPriority.MEDIUM: 2,
            AlertPriority.HIGH: 3,
            AlertPriority.CRITICAL: 4
        }
        
        if priority_levels[alert.priority] < priority_levels[user_settings.priority_threshold]:
            return False
            
        # Check rate limiting
        if self._is_rate_limited(user_id):
            self.stats["rate_limited"] += 1
            return False
            
        # Check quiet hours (except for critical alerts)
        if alert.priority != AlertPriority.CRITICAL and self._is_in_quiet_hours(user_id):
            return False
            
        return True
        
    def _format_alert_message(self, alert: Alert) -> str:
        """Format alert message using template"""
        template = self.alert_templates.get(alert.alert_type, "{title}\n{message}")
        
        # Prepare formatting data
        format_data = {
            "timestamp": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "title": alert.title,
            "message": alert.message,
            "provider": alert.provider or "Unknown",
            "symbol": alert.symbol or "N/A",
            "signal_id": alert.signal_id or "N/A",
            "priority": alert.priority.value.upper(),
            "category": alert.category.value.upper()
        }
        
        # Add alert-specific data
        if alert.data:
            format_data.update(alert.data)
            
        try:
            return template.format(**format_data)
        except KeyError as e:
            self.logger.warning(f"Missing template variable {e} for alert {alert.alert_type.value}")
            # Fallback to basic format
            return f"{alert.title}\n{alert.message}\nTime: {format_data['timestamp']}"
            
    async def _send_telegram_alert(self, alert: Alert, user_id: str) -> bool:
        """Send alert via Telegram"""
        try:
            if not self.copilot_bot:
                return False
                
            formatted_message = self._format_alert_message(alert)
            
            # Try to send via copilot bot
            if hasattr(self.copilot_bot, 'send_alert'):
                success = await self.copilot_bot.send_alert(formatted_message, user_id)
                return success
            elif hasattr(self.copilot_bot, 'application') and self.copilot_bot.application:
                # Direct telegram send
                await self.copilot_bot.application.bot.send_message(
                    chat_id=user_id,
                    text=formatted_message,
                    parse_mode='Markdown'
                )
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Telegram alert to {user_id}: {e}")
            return False
            
    def _log_fallback_alert(self, alert: Alert, user_id: str, reason: str):
        """Log alert to fallback file when Telegram fails"""
        try:
            log_entry = {
                "timestamp": alert.timestamp.isoformat(),
                "user_id": user_id,
                "alert_type": alert.alert_type.value,
                "priority": alert.priority.value,
                "title": alert.title,
                "message": alert.message,
                "reason": reason,
                "data": alert.data
            }
            
            with open(self.fallback_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            self.logger.error(f"Error writing fallback log: {e}")
            
    async def _process_alert(self, alert: Alert):
        """Process a single alert"""
        try:
            self.stats["total_alerts"] += 1
            self.stats["alerts_by_type"][alert.alert_type.value] += 1
            self.stats["alerts_by_priority"][alert.priority.value] += 1
            
            # Get target users (for now, use all configured users or default)
            target_users = list(self.user_settings.keys()) if self.user_settings else ["default"]
            
            sent_to_any = False
            
            for user_id in target_users:
                if not self._should_send_alert(alert, user_id):
                    self.stats["blocked_by_settings"] += 1
                    continue
                    
                # Try to send via Telegram
                success = await self._send_telegram_alert(alert, user_id)
                
                if success:
                    sent_to_any = True
                    self.logger.info(f"Alert sent to {user_id}: {alert.alert_type.value}")
                else:
                    # Fallback to log
                    if self.config.get("fallback_to_logs", True):
                        self._log_fallback_alert(alert, user_id, "Telegram send failed")
                        self.logger.warning(f"Alert fallback logged for {user_id}: {alert.alert_type.value}")
                        
            if sent_to_any:
                self.stats["sent_alerts"] += 1
                alert.sent = True
            else:
                self.stats["failed_alerts"] += 1
                
        except Exception as e:
            self.logger.error(f"Error processing alert: {e}")
            self.stats["failed_alerts"] += 1
            
    def _process_alerts_background(self):
        """Background thread to process alerts"""
        while self.processing:
            try:
                # Get alerts from queue
                alerts_to_process = []
                batch_size = self.config.get("batch_size", 10)
                
                for _ in range(batch_size):
                    try:
                        alert = self.alert_queue.get_nowait()
                        alerts_to_process.append(alert)
                    except queue.Empty:
                        break
                        
                if alerts_to_process:
                    # Process alerts asynchronously
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    for alert in alerts_to_process:
                        loop.run_until_complete(self._process_alert(alert))
                        
                    loop.close()
                    
                time.sleep(self.config.get("processing_interval", 2.0))
                
            except Exception as e:
                self.logger.error(f"Error in alert processing loop: {e}")
                time.sleep(5)  # Prevent tight error loops
                
    def start_processing(self):
        """Start background alert processing"""
        if not self.config.get("enabled", True):
            self.logger.info("Alert manager is disabled")
            return
            
        if self.processing:
            return
            
        self.processing = True
        self._load_user_settings()
        
        self.process_thread = threading.Thread(target=self._process_alerts_background, daemon=True)
        self.process_thread.start()
        
        self.logger.info("Alert processing started")
        
    def stop_processing(self):
        """Stop background alert processing"""
        if self.processing:
            self.processing = False
            if self.process_thread:
                self.process_thread.join(timeout=5)
            self.logger.info("Alert processing stopped")
            
    def send_alert(self, alert_type: AlertType, title: str, message: str, 
                   priority: AlertPriority = AlertPriority.MEDIUM,
                   category: AlertCategory = AlertCategory.SYSTEM,
                   provider: Optional[str] = None,
                   symbol: Optional[str] = None,
                   signal_id: Optional[str] = None,
                   user_id: Optional[str] = None,
                   data: Optional[Dict[str, Any]] = None):
        """Send an alert (add to processing queue)"""
        try:
            alert = Alert(
                alert_type=alert_type,
                priority=priority,
                category=category,
                title=title,
                message=message,
                timestamp=datetime.now(),
                provider=provider,
                symbol=symbol,
                signal_id=signal_id,
                user_id=user_id,
                data=data or {}
            )
            
            self.alert_queue.put(alert)
            
        except Exception as e:
            self.logger.error(f"Error queuing alert: {e}")
            
    def send_parsing_failed_alert(self, provider: str, signal_id: str, error: str):
        """Send parsing failed alert"""
        self.send_alert(
            alert_type=AlertType.PARSING_FAILED,
            title="Signal Parsing Failed",
            message=f"Failed to parse signal from {provider}",
            priority=AlertPriority.HIGH,
            category=AlertCategory.ERROR,
            provider=provider,
            signal_id=signal_id,
            data={"error": error}
        )
        
    def send_retry_triggered_alert(self, symbol: str, retry_count: int, reason: str):
        """Send retry triggered alert"""
        self.send_alert(
            alert_type=AlertType.RETRY_TRIGGERED,
            title="Retry Triggered",
            message=f"Retry attempt {retry_count} for {symbol}",
            priority=AlertPriority.MEDIUM,
            category=AlertCategory.WARNING,
            symbol=symbol,
            data={"retry_count": retry_count, "reason": reason}
        )
        
    def send_trade_executed_alert(self, symbol: str, direction: str, volume: float, entry_price: float):
        """Send trade executed alert"""
        self.send_alert(
            alert_type=AlertType.TRADE_EXECUTED,
            title="Trade Executed",
            message=f"{direction} {volume} lots of {symbol} at {entry_price}",
            priority=AlertPriority.LOW,
            category=AlertCategory.SUCCESS,
            symbol=symbol,
            data={
                "direction": direction,
                "volume": volume,
                "entry_price": entry_price
            }
        )
        
    def send_risk_rule_blocked_alert(self, symbol: str, rule_name: str, reason: str):
        """Send risk rule blocked alert"""
        self.send_alert(
            alert_type=AlertType.RISK_RULE_BLOCKED,
            title="Risk Rule Blocked",
            message=f"Trade blocked by {rule_name}",
            priority=AlertPriority.HIGH,
            category=AlertCategory.WARNING,
            symbol=symbol,
            data={"rule_name": rule_name, "reason": reason}
        )
        
    def add_user_settings(self, user_id: str, settings: UserAlertSettings):
        """Add or update user alert settings"""
        self.user_settings[user_id] = settings
        self._save_user_settings()
        self.logger.info(f"Updated alert settings for user {user_id}")
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert manager statistics"""
        total_alerts = self.stats["total_alerts"]
        success_rate = (self.stats["sent_alerts"] / max(total_alerts, 1)) * 100
        
        return {
            **self.stats,
            "success_rate": round(success_rate, 2),
            "queue_size": self.alert_queue.qsize(),
            "processing_active": self.processing,
            "configured_users": len(self.user_settings)
        }

# Global instance for easy access
copilot_alert_manager = CopilotAlertManager()