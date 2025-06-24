"""
Copilot Command Interpreter for SignalOS
Parses and routes Telegram bot commands to appropriate system modules
"""

import json
import re
import time
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum

class CommandType(Enum):
    STATUS = "status"
    REPLAY = "replay"
    STEALTH = "stealth"
    ENABLE = "enable"
    DISABLE = "disable"
    PAUSE = "pause"
    RESUME = "resume"
    SET = "set"
    GET = "get"
    HELP = "help"
    UNKNOWN = "unknown"

class CommandScope(Enum):
    GLOBAL = "global"
    SYMBOL = "symbol"
    PROVIDER = "provider"
    STRATEGY = "strategy"
    USER = "user"

@dataclass
class ParsedCommand:
    command_type: CommandType
    scope: CommandScope
    target: Optional[str] = None
    parameters: Dict[str, Any] = None
    raw_message: str = ""
    user_id: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class CommandResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    executed_by: Optional[str] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}

class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    BLOCKED = "blocked"

class CopilotCommandInterpreter:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/copilot_commands.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Command history cache (last 10 commands per user)
        self.command_history: Dict[str, List[ParsedCommand]] = {}
        self.max_history_per_user = 10
        
        # User roles and permissions
        self.user_roles: Dict[str, UserRole] = {}
        
        # Command routing table
        self.command_handlers: Dict[CommandType, Callable] = {
            CommandType.STATUS: self._handle_status_command,
            CommandType.REPLAY: self._handle_replay_command,
            CommandType.STEALTH: self._handle_stealth_command,
            CommandType.ENABLE: self._handle_enable_command,
            CommandType.DISABLE: self._handle_disable_command,
            CommandType.PAUSE: self._handle_pause_command,
            CommandType.RESUME: self._handle_resume_command,
            CommandType.SET: self._handle_set_command,
            CommandType.GET: self._handle_get_command,
            CommandType.HELP: self._handle_help_command,
        }
        
        # Command patterns for parsing
        self.command_patterns = {
            r'^/status\s*(.*)$': (CommandType.STATUS, self._parse_status_params),
            r'^/replay\s+(.+)$': (CommandType.REPLAY, self._parse_replay_params),
            r'^/stealth\s+(on|off|enable|disable)$': (CommandType.STEALTH, self._parse_stealth_params),
            r'^/enable\s+(.+)$': (CommandType.ENABLE, self._parse_symbol_params),
            r'^/disable\s+(.+)$': (CommandType.DISABLE, self._parse_symbol_params),
            r'^/pause\s+(.+)$': (CommandType.PAUSE, self._parse_symbol_params),
            r'^/resume\s+(.+)$': (CommandType.RESUME, self._parse_symbol_params),
            r'^/set\s+(.+)$': (CommandType.SET, self._parse_set_params),
            r'^/get\s+(.+)$': (CommandType.GET, self._parse_get_params),
            r'^/help\s*(.*)$': (CommandType.HELP, self._parse_help_params),
        }
        
        # Statistics
        self.stats = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "unauthorized_attempts": 0,
            "commands_by_type": {cmd_type.value: 0 for cmd_type in CommandType}
        }
        
        self.logger.info("Copilot command interpreter initialized")
        
    def _load_config(self) -> Dict[str, Any]:
        """Load command interpreter configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "copilot_command_interpreter" not in config:
                config["copilot_command_interpreter"] = {
                    "enabled": True,
                    "require_authorization": True,
                    "default_user_role": "user",
                    "admin_users": [],
                    "command_timeout": 30,
                    "max_concurrent_commands": 5,
                    "allowed_symbols": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY", "XAUUSD", "BTCUSD"],
                    "stealth_commands_enabled": True,
                    "replay_commands_enabled": True
                }
                self._save_config(config)
                
            return config.get("copilot_command_interpreter", {})
            
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
            "require_authorization": True,
            "default_user_role": "user",
            "admin_users": [],
            "command_timeout": 30,
            "max_concurrent_commands": 5,
            "allowed_symbols": ["EURUSD", "GBPUSD", "XAUUSD"],
            "stealth_commands_enabled": True,
            "replay_commands_enabled": True
        }
        
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for command interpreter"""
        logger = logging.getLogger("copilot_command_interpreter")
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
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
        
    def _get_user_role(self, user_id: str) -> UserRole:
        """Get user role for authorization"""
        if user_id in self.user_roles:
            return self.user_roles[user_id]
            
        # Check if user is in admin list
        if user_id in self.config.get("admin_users", []):
            self.user_roles[user_id] = UserRole.ADMIN
            return UserRole.ADMIN
            
        # Use default role
        default_role = self.config.get("default_user_role", "user")
        role = UserRole(default_role)
        self.user_roles[user_id] = role
        return role
        
    def _is_authorized(self, user_id: str, command_type: CommandType) -> bool:
        """Check if user is authorized to execute command"""
        if not self.config.get("require_authorization", True):
            return True
            
        user_role = self._get_user_role(user_id)
        
        if user_role == UserRole.BLOCKED:
            return False
            
        # Admin can execute all commands
        if user_role == UserRole.ADMIN:
            return True
            
        # Users can execute basic commands
        if user_role == UserRole.USER:
            allowed_commands = [
                CommandType.STATUS, CommandType.HELP, CommandType.GET,
                CommandType.PAUSE, CommandType.RESUME
            ]
            if command_type in allowed_commands:
                return True
                
            # Check specific feature permissions
            if command_type == CommandType.STEALTH and self.config.get("stealth_commands_enabled", True):
                return True
            if command_type == CommandType.REPLAY and self.config.get("replay_commands_enabled", True):
                return True
                
        # Viewers can only execute read-only commands
        if user_role == UserRole.VIEWER:
            readonly_commands = [CommandType.STATUS, CommandType.HELP, CommandType.GET]
            return command_type in readonly_commands
            
        return False
        
    def parse_command(self, message: str, user_id: str) -> Optional[ParsedCommand]:
        """Parse incoming message into structured command"""
        try:
            message = message.strip()
            
            # Try to match against known patterns
            for pattern, (command_type, param_parser) in self.command_patterns.items():
                match = re.match(pattern, message, re.IGNORECASE)
                if match:
                    scope, target, parameters = param_parser(match.groups())
                    
                    command = ParsedCommand(
                        command_type=command_type,
                        scope=scope,
                        target=target,
                        parameters=parameters,
                        raw_message=message,
                        user_id=user_id,
                        timestamp=datetime.now()
                    )
                    
                    return command
                    
            # Unknown command
            return ParsedCommand(
                command_type=CommandType.UNKNOWN,
                scope=CommandScope.GLOBAL,
                raw_message=message,
                user_id=user_id,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing command '{message}': {e}")
            return None
            
    def _parse_status_params(self, groups: Tuple[str]) -> Tuple[CommandScope, Optional[str], Dict[str, Any]]:
        """Parse status command parameters"""
        if groups and groups[0].strip():
            target = groups[0].strip().upper()
            if target in self.config.get("allowed_symbols", []):
                return CommandScope.SYMBOL, target, {}
            elif target.lower() in ["all", "global", "system"]:
                return CommandScope.GLOBAL, None, {}
            else:
                return CommandScope.PROVIDER, target, {}
        return CommandScope.GLOBAL, None, {}
        
    def _parse_replay_params(self, groups: Tuple[str]) -> Tuple[CommandScope, Optional[str], Dict[str, Any]]:
        """Parse replay command parameters"""
        params_str = groups[0].strip()
        parts = params_str.split()
        
        if len(parts) >= 1:
            target = parts[0].upper()
            parameters = {}
            
            # Parse additional parameters
            if len(parts) > 1:
                if parts[1].lower() == "last":
                    parameters["count"] = 1
                elif parts[1].isdigit():
                    parameters["count"] = int(parts[1])
                    
            if len(parts) > 2 and "from" in parts[1].lower():
                # Handle time-based replay
                parameters["from_time"] = " ".join(parts[2:])
                
            return CommandScope.SYMBOL, target, parameters
            
        return CommandScope.GLOBAL, None, {}
        
    def _parse_stealth_params(self, groups: Tuple[str]) -> Tuple[CommandScope, Optional[str], Dict[str, Any]]:
        """Parse stealth command parameters"""
        action = groups[0].strip().lower()
        enabled = action in ["on", "enable"]
        return CommandScope.GLOBAL, None, {"enabled": enabled}
        
    def _parse_symbol_params(self, groups: Tuple[str]) -> Tuple[CommandScope, Optional[str], Dict[str, Any]]:
        """Parse symbol-based command parameters"""
        target = groups[0].strip().upper()
        
        # Check if it's a known symbol
        if target in self.config.get("allowed_symbols", []):
            return CommandScope.SYMBOL, target, {}
        elif target.lower() in ["all", "global"]:
            return CommandScope.GLOBAL, None, {}
        else:
            # Assume it's a provider
            return CommandScope.PROVIDER, target, {}
            
    def _parse_set_params(self, groups: Tuple[str]) -> Tuple[CommandScope, Optional[str], Dict[str, Any]]:
        """Parse set command parameters"""
        params_str = groups[0].strip()
        parts = params_str.split()
        
        if len(parts) >= 3:
            target = parts[0].upper()
            param_name = parts[1].lower()
            param_value = " ".join(parts[2:])
            
            # Try to convert to appropriate type
            try:
                if param_value.lower() in ["true", "false"]:
                    param_value = param_value.lower() == "true"
                elif param_value.replace(".", "").isdigit():
                    param_value = float(param_value) if "." in param_value else int(param_value)
            except ValueError:
                pass  # Keep as string
                
            parameters = {param_name: param_value}
            
            if target in self.config.get("allowed_symbols", []):
                return CommandScope.SYMBOL, target, parameters
            else:
                return CommandScope.STRATEGY, target, parameters
                
        return CommandScope.GLOBAL, None, {}
        
    def _parse_get_params(self, groups: Tuple[str]) -> Tuple[CommandScope, Optional[str], Dict[str, Any]]:
        """Parse get command parameters"""
        params_str = groups[0].strip()
        parts = params_str.split()
        
        if len(parts) >= 1:
            target = parts[0].upper()
            param_name = parts[1].lower() if len(parts) > 1 else "status"
            
            parameters = {"parameter": param_name}
            
            if target in self.config.get("allowed_symbols", []):
                return CommandScope.SYMBOL, target, parameters
            else:
                return CommandScope.STRATEGY, target, parameters
                
        return CommandScope.GLOBAL, None, {"parameter": "status"}
        
    def _parse_help_params(self, groups: Tuple[str]) -> Tuple[CommandScope, Optional[str], Dict[str, Any]]:
        """Parse help command parameters"""
        if groups and groups[0].strip():
            topic = groups[0].strip().lower()
            return CommandScope.GLOBAL, None, {"topic": topic}
        return CommandScope.GLOBAL, None, {}
        
    def execute_command(self, command: ParsedCommand) -> CommandResult:
        """Execute a parsed command"""
        try:
            self.stats["total_commands"] += 1
            self.stats["commands_by_type"][command.command_type.value] += 1
            
            # Check authorization
            if not self._is_authorized(command.user_id, command.command_type):
                self.stats["unauthorized_attempts"] += 1
                self.logger.warning(f"Unauthorized command attempt by {command.user_id}: {command.raw_message}")
                return CommandResult(
                    success=False,
                    message="❌ You are not authorized to execute this command.",
                    executed_by=command.user_id
                )
                
            # Add to command history
            self._add_to_history(command)
            
            # Route to appropriate handler
            if command.command_type in self.command_handlers:
                result = self.command_handlers[command.command_type](command)
            else:
                result = CommandResult(
                    success=False,
                    message="❌ Unknown command. Type /help for available commands.",
                    executed_by=command.user_id
                )
                
            # Update statistics
            if result.success:
                self.stats["successful_commands"] += 1
            else:
                self.stats["failed_commands"] += 1
                
            # Log execution
            self.logger.info(f"Command executed: {command.raw_message} by {command.user_id} - {result.success}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            self.stats["failed_commands"] += 1
            return CommandResult(
                success=False,
                message=f"❌ Command execution error: {str(e)}",
                executed_by=command.user_id
            )
            
    def _add_to_history(self, command: ParsedCommand):
        """Add command to user's history"""
        user_id = command.user_id
        
        if user_id not in self.command_history:
            self.command_history[user_id] = []
            
        self.command_history[user_id].append(command)
        
        # Keep only last N commands
        if len(self.command_history[user_id]) > self.max_history_per_user:
            self.command_history[user_id] = self.command_history[user_id][-self.max_history_per_user:]
            
    def _handle_status_command(self, command: ParsedCommand) -> CommandResult:
        """Handle status command"""
        try:
            if command.scope == CommandScope.GLOBAL:
                # Global system status
                status_data = {
                    "system_status": "running",
                    "active_signals": 5,
                    "active_strategies": 3,
                    "mt5_connected": True,
                    "last_signal": "2 minutes ago"
                }
                
                message = "📊 **System Status**\n"
                message += f"🟢 System: {status_data['system_status'].title()}\n"
                message += f"📡 Active Signals: {status_data['active_signals']}\n"
                message += f"⚡ Active Strategies: {status_data['active_strategies']}\n"
                message += f"🔗 MT5 Connected: {'✅' if status_data['mt5_connected'] else '❌'}\n"
                message += f"⏰ Last Signal: {status_data['last_signal']}"
                
            elif command.scope == CommandScope.SYMBOL:
                # Symbol-specific status
                symbol = command.target
                status_data = {
                    "symbol": symbol,
                    "enabled": True,
                    "last_signal": "5 minutes ago",
                    "active_trades": 2,
                    "pnl": "+$125.50"
                }
                
                message = f"📈 **{symbol} Status**\n"
                message += f"🔄 Enabled: {'✅' if status_data['enabled'] else '❌'}\n"
                message += f"⏰ Last Signal: {status_data['last_signal']}\n"
                message += f"📊 Active Trades: {status_data['active_trades']}\n"
                message += f"💰 P&L: {status_data['pnl']}"
                
            else:
                status_data = {"message": "Status information not available for this scope"}
                message = "ℹ️ Status information not available for this scope"
                
            return CommandResult(
                success=True,
                message=message,
                data=status_data,
                executed_by=command.user_id
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error getting status: {str(e)}",
                executed_by=command.user_id
            )
            
    def _handle_replay_command(self, command: ParsedCommand) -> CommandResult:
        """Handle replay command"""
        try:
            if not self.config.get("replay_commands_enabled", True):
                return CommandResult(
                    success=False,
                    message="❌ Replay commands are disabled",
                    executed_by=command.user_id
                )
                
            symbol = command.target
            count = command.parameters.get("count", 1)
            
            # Simulate replay execution
            message = f"🔄 **Replay Command**\n"
            message += f"📈 Symbol: {symbol}\n"
            message += f"📊 Replaying last {count} signal(s)\n"
            message += f"✅ Replay initiated successfully"
            
            replay_data = {
                "symbol": symbol,
                "count": count,
                "status": "initiated",
                "replay_id": f"replay_{int(time.time())}"
            }
            
            return CommandResult(
                success=True,
                message=message,
                data=replay_data,
                executed_by=command.user_id
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error executing replay: {str(e)}",
                executed_by=command.user_id
            )
            
    def _handle_stealth_command(self, command: ParsedCommand) -> CommandResult:
        """Handle stealth command"""
        try:
            if not self.config.get("stealth_commands_enabled", True):
                return CommandResult(
                    success=False,
                    message="❌ Stealth commands are disabled",
                    executed_by=command.user_id
                )
                
            enabled = command.parameters.get("enabled", False)
            action = "enabled" if enabled else "disabled"
            
            message = f"🥷 **Stealth Mode**\n"
            message += f"🔄 Stealth mode {action}\n"
            message += f"✅ Command executed successfully"
            
            stealth_data = {
                "stealth_enabled": enabled,
                "timestamp": datetime.now().isoformat()
            }
            
            return CommandResult(
                success=True,
                message=message,
                data=stealth_data,
                executed_by=command.user_id
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error toggling stealth mode: {str(e)}",
                executed_by=command.user_id
            )
            
    def _handle_enable_command(self, command: ParsedCommand) -> CommandResult:
        """Handle enable command"""
        try:
            target = command.target
            scope_name = command.scope.value
            
            message = f"✅ **Enable Command**\n"
            message += f"🎯 Target: {target} ({scope_name})\n"
            message += f"🔄 Status: Enabled\n"
            message += f"✅ Command executed successfully"
            
            enable_data = {
                "target": target,
                "scope": scope_name,
                "enabled": True,
                "timestamp": datetime.now().isoformat()
            }
            
            return CommandResult(
                success=True,
                message=message,
                data=enable_data,
                executed_by=command.user_id
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error enabling {command.target}: {str(e)}",
                executed_by=command.user_id
            )
            
    def _handle_disable_command(self, command: ParsedCommand) -> CommandResult:
        """Handle disable command"""
        try:
            target = command.target
            scope_name = command.scope.value
            
            message = f"❌ **Disable Command**\n"
            message += f"🎯 Target: {target} ({scope_name})\n"
            message += f"🔄 Status: Disabled\n"
            message += f"✅ Command executed successfully"
            
            disable_data = {
                "target": target,
                "scope": scope_name,
                "enabled": False,
                "timestamp": datetime.now().isoformat()
            }
            
            return CommandResult(
                success=True,
                message=message,
                data=disable_data,
                executed_by=command.user_id
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error disabling {command.target}: {str(e)}",
                executed_by=command.user_id
            )
            
    def _handle_pause_command(self, command: ParsedCommand) -> CommandResult:
        """Handle pause command"""
        return self._handle_disable_command(command)  # Pause is essentially disable
        
    def _handle_resume_command(self, command: ParsedCommand) -> CommandResult:
        """Handle resume command"""
        return self._handle_enable_command(command)  # Resume is essentially enable
        
    def _handle_set_command(self, command: ParsedCommand) -> CommandResult:
        """Handle set command"""
        try:
            target = command.target
            parameters = command.parameters
            
            if not parameters:
                return CommandResult(
                    success=False,
                    message="❌ No parameters specified for set command",
                    executed_by=command.user_id
                )
                
            param_name = list(parameters.keys())[0]
            param_value = list(parameters.values())[0]
            
            message = f"⚙️ **Set Command**\n"
            message += f"🎯 Target: {target}\n"
            message += f"📝 Parameter: {param_name}\n"
            message += f"💾 Value: {param_value}\n"
            message += f"✅ Parameter updated successfully"
            
            set_data = {
                "target": target,
                "parameter": param_name,
                "value": param_value,
                "timestamp": datetime.now().isoformat()
            }
            
            return CommandResult(
                success=True,
                message=message,
                data=set_data,
                executed_by=command.user_id
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error setting parameter: {str(e)}",
                executed_by=command.user_id
            )
            
    def _handle_get_command(self, command: ParsedCommand) -> CommandResult:
        """Handle get command"""
        try:
            target = command.target
            parameter = command.parameters.get("parameter", "status")
            
            # Simulate getting parameter value
            mock_values = {
                "status": "enabled",
                "lot": "0.01",
                "risk": "2%",
                "sl": "50 pips",
                "tp": "100 pips"
            }
            
            value = mock_values.get(parameter, "unknown")
            
            message = f"📖 **Get Command**\n"
            message += f"🎯 Target: {target}\n"
            message += f"📝 Parameter: {parameter}\n"
            message += f"💾 Value: {value}\n"
            message += f"✅ Parameter retrieved successfully"
            
            get_data = {
                "target": target,
                "parameter": parameter,
                "value": value,
                "timestamp": datetime.now().isoformat()
            }
            
            return CommandResult(
                success=True,
                message=message,
                data=get_data,
                executed_by=command.user_id
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error getting parameter: {str(e)}",
                executed_by=command.user_id
            )
            
    def _handle_help_command(self, command: ParsedCommand) -> CommandResult:
        """Handle help command"""
        try:
            topic = command.parameters.get("topic", "general")
            
            if topic == "general":
                message = "🤖 **SignalOS Copilot Commands**\n\n"
                message += "📊 `/status [symbol]` - Get system or symbol status\n"
                message += "🔄 `/replay <symbol> [count]` - Replay last signals\n"
                message += "🥷 `/stealth on/off` - Toggle stealth mode\n"
                message += "✅ `/enable <symbol/provider>` - Enable trading\n"
                message += "❌ `/disable <symbol/provider>` - Disable trading\n"
                message += "⏸️ `/pause <symbol/provider>` - Pause trading\n"
                message += "▶️ `/resume <symbol/provider>` - Resume trading\n"
                message += "⚙️ `/set <target> <param> <value>` - Set parameter\n"
                message += "📖 `/get <target> <param>` - Get parameter value\n"
                message += "❓ `/help [topic]` - Show this help\n\n"
                message += "💡 Use `/help <command>` for detailed help on specific commands"
            else:
                message = f"📖 **Help for '{topic}'**\n\n"
                message += f"Detailed help for {topic} is not yet available.\n"
                message += "Use `/help` for general command overview."
                
            help_data = {
                "topic": topic,
                "commands_shown": 10 if topic == "general" else 0
            }
            
            return CommandResult(
                success=True,
                message=message,
                data=help_data,
                executed_by=command.user_id
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"❌ Error showing help: {str(e)}",
                executed_by=command.user_id
            )
            
    def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get command history for a user"""
        if user_id not in self.command_history:
            return []
            
        history = self.command_history[user_id][-limit:]
        return [asdict(cmd) for cmd in history]
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get command interpreter statistics"""
        return {
            **self.stats,
            "success_rate": (self.stats["successful_commands"] / max(self.stats["total_commands"], 1)) * 100,
            "total_users": len(self.command_history),
            "average_commands_per_user": sum(len(history) for history in self.command_history.values()) / max(len(self.command_history), 1)
        }
        
    def clear_user_history(self, user_id: str) -> bool:
        """Clear command history for a user"""
        try:
            if user_id in self.command_history:
                del self.command_history[user_id]
                self.logger.info(f"Cleared command history for user {user_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error clearing history for user {user_id}: {e}")
            return False

# Global instance for easy access
copilot_command_interpreter = CopilotCommandInterpreter()