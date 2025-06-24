"""
Time Scheduler for SignalOS
Implements time-based trade execution rules with timezone support and configurable trading windows
"""

import json
import logging
import pytz
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TimeFilterResult(Enum):
    ALLOWED = "allowed"
    BLOCKED_TIME_WINDOW = "blocked_time_window"
    BLOCKED_WEEKDAY = "blocked_weekday"
    BLOCKED_SYMBOL_SPECIFIC = "blocked_symbol_specific"
    BLOCKED_PROVIDER_SPECIFIC = "blocked_provider_specific"


@dataclass
class TimeWindow:
    start: time
    end: time
    timezone: str = "UTC"
    
    def contains_time(self, check_time: datetime, tz: str = "UTC") -> bool:
        """Check if given time falls within this window"""
        # Convert check_time to window timezone
        if tz != self.timezone:
            source_tz = pytz.timezone(tz)
            target_tz = pytz.timezone(self.timezone)
            
            if check_time.tzinfo is None:
                check_time = source_tz.localize(check_time)
            
            check_time = check_time.astimezone(target_tz)
        
        current_time = check_time.time()
        
        # Handle overnight windows (e.g., 22:00 to 06:00)
        if self.start <= self.end:
            return self.start <= current_time <= self.end
        else:
            return current_time >= self.start or current_time <= self.end


@dataclass
class ScheduleRule:
    symbol_pattern: str  # e.g., "GOLD", "EUR*", "default"
    provider_pattern: Optional[str] = None
    allowed_weekdays: List[int] = None  # 0=Monday, 6=Sunday
    time_windows: List[TimeWindow] = None
    enabled: bool = True
    priority: int = 0  # Higher priority rules take precedence
    
    def __post_init__(self):
        if self.allowed_weekdays is None:
            self.allowed_weekdays = list(range(7))  # All days allowed by default
        if self.time_windows is None:
            self.time_windows = [TimeWindow(time(0, 0), time(23, 59))]  # 24/7 by default


class TimeScheduler:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/time_scheduler_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self.schedule_rules: List[ScheduleRule] = []
        
        self._setup_logging()
        self._load_schedule_rules()
        
        # Injected modules
        self.strategy_runtime = None
        self.parser = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    return config_data.get('time_scheduler', self._create_default_config())
            else:
                return self._create_default_config()
        except Exception as e:
            logging.warning(f"Failed to load time scheduler config: {e}")
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default time scheduler configuration"""
        default_config = {
            'enabled': True,
            'default_timezone': 'UTC',
            'log_filtering_actions': True,
            'rules': {
                'GOLD': {
                    'start': '08:30',
                    'end': '15:00',
                    'timezone': 'UTC',
                    'weekdays': [0, 1, 2, 3, 4]  # Monday to Friday
                },
                'EURUSD': {
                    'start': '07:00',
                    'end': '17:00',
                    'timezone': 'UTC',
                    'weekdays': [0, 1, 2, 3, 4]
                },
                'GBPUSD': {
                    'start': '07:00',
                    'end': '17:00',
                    'timezone': 'UTC',
                    'weekdays': [0, 1, 2, 3, 4]
                },
                'default': {
                    'start': '00:00',
                    'end': '23:59',
                    'timezone': 'UTC',
                    'weekdays': [0, 1, 2, 3, 4, 5, 6]  # All days
                }
            }
        }
        
        try:
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['time_scheduler'] = default_config
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            logging.error(f"Failed to save default time scheduler config: {e}")
        
        return default_config

    def _setup_logging(self):
        """Setup logging for time scheduler operations"""
        self.logger = logging.getLogger('TimeScheduler')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _load_schedule_rules(self):
        """Load schedule rules from configuration"""
        self.schedule_rules = []
        
        rules_config = self.config.get('rules', {})
        
        for symbol_pattern, rule_data in rules_config.items():
            try:
                # Parse time window
                start_time = datetime.strptime(rule_data['start'], '%H:%M').time()
                end_time = datetime.strptime(rule_data['end'], '%H:%M').time()
                timezone = rule_data.get('timezone', 'UTC')
                
                time_window = TimeWindow(start_time, end_time, timezone)
                
                # Create schedule rule
                rule = ScheduleRule(
                    symbol_pattern=symbol_pattern,
                    allowed_weekdays=rule_data.get('weekdays', list(range(7))),
                    time_windows=[time_window],
                    enabled=rule_data.get('enabled', True),
                    priority=rule_data.get('priority', 0)
                )
                
                self.schedule_rules.append(rule)
                
            except Exception as e:
                self.logger.error(f"Failed to load rule for {symbol_pattern}: {e}")
        
        # Sort rules by priority (highest first)
        self.schedule_rules.sort(key=lambda r: r.priority, reverse=True)
        
        self.logger.info(f"Loaded {len(self.schedule_rules)} time schedule rules")

    def inject_modules(self, strategy_runtime=None, parser=None):
        """Inject module references"""
        self.strategy_runtime = strategy_runtime
        self.parser = parser
        self.logger.info("Time scheduler modules injected")

    def _match_symbol_pattern(self, symbol: str, pattern: str) -> bool:
        """Check if symbol matches pattern (supports wildcards)"""
        symbol = symbol.upper()
        pattern = pattern.upper()
        
        if pattern == "DEFAULT":
            return True
        elif pattern.endswith("*"):
            return symbol.startswith(pattern[:-1])
        elif pattern.startswith("*"):
            return symbol.endswith(pattern[1:])
        else:
            return symbol == pattern

    def _match_provider_pattern(self, provider: str, pattern: Optional[str]) -> bool:
        """Check if provider matches pattern"""
        if pattern is None:
            return True
        
        provider = provider.upper() if provider else ""
        pattern = pattern.upper()
        
        if pattern == "DEFAULT":
            return True
        elif pattern.endswith("*"):
            return provider.startswith(pattern[:-1])
        elif pattern.startswith("*"):
            return provider.endswith(pattern[1:])
        else:
            return provider == pattern

    def _find_matching_rule(self, symbol: str, provider: Optional[str] = None) -> Optional[ScheduleRule]:
        """Find the highest priority matching rule for symbol/provider"""
        for rule in self.schedule_rules:
            if not rule.enabled:
                continue
                
            if (self._match_symbol_pattern(symbol, rule.symbol_pattern) and 
                self._match_provider_pattern(provider, rule.provider_pattern)):
                return rule
        
        return None

    def should_execute_trade(self, signal_time: datetime, pair: str, provider: Optional[str] = None) -> Tuple[bool, TimeFilterResult, str]:
        """
        Determine if trade should be executed based on time rules
        
        Args:
            signal_time: Time when signal was received
            pair: Trading pair/symbol
            provider: Signal provider name (optional)
            
        Returns:
            Tuple of (should_execute, filter_result, reason)
        """
        if not self.config.get('enabled', True):
            return True, TimeFilterResult.ALLOWED, "Time filtering disabled"
        
        # Find matching rule
        matching_rule = self._find_matching_rule(pair, provider)
        
        if not matching_rule:
            # No specific rule found, check for default rule
            default_rule = self._find_matching_rule("default")
            if default_rule:
                matching_rule = default_rule
            else:
                # No rules found, allow by default
                return True, TimeFilterResult.ALLOWED, "No time rules configured"
        
        # Check weekday restriction
        current_weekday = signal_time.weekday()
        if current_weekday not in matching_rule.allowed_weekdays:
            reason = f"Trade blocked: {pair} not allowed on {signal_time.strftime('%A')} (weekday {current_weekday})"
            self._log_filter_action(pair, provider, signal_time, False, reason)
            return False, TimeFilterResult.BLOCKED_WEEKDAY, reason
        
        # Check time windows
        time_allowed = False
        for window in matching_rule.time_windows:
            if window.contains_time(signal_time, self.config.get('default_timezone', 'UTC')):
                time_allowed = True
                break
        
        if not time_allowed:
            reason = f"Trade blocked: {pair} outside allowed time windows for {matching_rule.symbol_pattern}"
            self._log_filter_action(pair, provider, signal_time, False, reason)
            return False, TimeFilterResult.BLOCKED_TIME_WINDOW, reason
        
        # Trade is allowed
        reason = f"Trade allowed: {pair} within time window for rule {matching_rule.symbol_pattern}"
        self._log_filter_action(pair, provider, signal_time, True, reason)
        return True, TimeFilterResult.ALLOWED, reason

    def _log_filter_action(self, symbol: str, provider: Optional[str], signal_time: datetime, allowed: bool, reason: str):
        """Log time filtering action"""
        if not self.config.get('log_filtering_actions', True):
            return
            
        try:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'provider': provider,
                'signal_time': signal_time.isoformat(),
                'allowed': allowed,
                'reason': reason,
                'weekday': signal_time.strftime('%A'),
                'time': signal_time.strftime('%H:%M:%S')
            }
            
            # Read existing log data
            log_data = {'filter_actions': []}
            if Path(self.log_file).exists():
                try:
                    with open(self.log_file, 'r') as f:
                        log_data = json.load(f)
                except json.JSONDecodeError:
                    pass
            
            # Add new entry
            log_data['filter_actions'].append(log_entry)
            
            # Keep only last 1000 entries
            if len(log_data['filter_actions']) > 1000:
                log_data['filter_actions'] = log_data['filter_actions'][-1000:]
            
            # Save updated log
            with open(self.log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to log filter action: {e}")

    def add_time_rule(self, symbol_pattern: str, start_time: str, end_time: str, 
                      weekdays: List[int] = None, timezone: str = "UTC", 
                      provider_pattern: Optional[str] = None, priority: int = 0) -> bool:
        """Add new time rule dynamically"""
        try:
            start = datetime.strptime(start_time, '%H:%M').time()
            end = datetime.strptime(end_time, '%H:%M').time()
            
            time_window = TimeWindow(start, end, timezone)
            
            rule = ScheduleRule(
                symbol_pattern=symbol_pattern,
                provider_pattern=provider_pattern,
                allowed_weekdays=weekdays or list(range(7)),
                time_windows=[time_window],
                enabled=True,
                priority=priority
            )
            
            self.schedule_rules.append(rule)
            self.schedule_rules.sort(key=lambda r: r.priority, reverse=True)
            
            self.logger.info(f"Added time rule for {symbol_pattern}: {start_time}-{end_time} {timezone}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add time rule: {e}")
            return False

    def remove_time_rule(self, symbol_pattern: str, provider_pattern: Optional[str] = None) -> bool:
        """Remove time rule for symbol/provider"""
        initial_count = len(self.schedule_rules)
        
        self.schedule_rules = [
            rule for rule in self.schedule_rules
            if not (rule.symbol_pattern == symbol_pattern and rule.provider_pattern == provider_pattern)
        ]
        
        removed_count = initial_count - len(self.schedule_rules)
        
        if removed_count > 0:
            self.logger.info(f"Removed {removed_count} time rule(s) for {symbol_pattern}")
            return True
        else:
            self.logger.warning(f"No time rules found for {symbol_pattern}")
            return False

    def get_time_statistics(self) -> Dict[str, Any]:
        """Get statistics about time filtering"""
        if not Path(self.log_file).exists():
            return {
                'total_checks': 0,
                'allowed_trades': 0,
                'blocked_trades': 0,
                'block_reasons': {}
            }
        
        try:
            with open(self.log_file, 'r') as f:
                log_data = json.load(f)
            
            filter_actions = log_data.get('filter_actions', [])
            
            total_checks = len(filter_actions)
            allowed_trades = sum(1 for action in filter_actions if action['allowed'])
            blocked_trades = total_checks - allowed_trades
            
            # Count block reasons
            block_reasons = {}
            for action in filter_actions:
                if not action['allowed']:
                    reason = action['reason']
                    block_type = "time_window" if "time window" in reason else "weekday" if "weekday" in reason else "other"
                    block_reasons[block_type] = block_reasons.get(block_type, 0) + 1
            
            return {
                'total_checks': total_checks,
                'allowed_trades': allowed_trades,
                'blocked_trades': blocked_trades,
                'block_reasons': block_reasons,
                'active_rules': len([r for r in self.schedule_rules if r.enabled]),
                'total_rules': len(self.schedule_rules)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get time statistics: {e}")
            return {'error': str(e)}

    def list_active_rules(self) -> List[Dict[str, Any]]:
        """Get list of active time rules"""
        active_rules = []
        
        for rule in self.schedule_rules:
            if not rule.enabled:
                continue
                
            rule_info = {
                'symbol_pattern': rule.symbol_pattern,
                'provider_pattern': rule.provider_pattern,
                'weekdays': rule.allowed_weekdays,
                'time_windows': [],
                'priority': rule.priority
            }
            
            for window in rule.time_windows:
                rule_info['time_windows'].append({
                    'start': window.start.strftime('%H:%M'),
                    'end': window.end.strftime('%H:%M'),
                    'timezone': window.timezone
                })
            
            active_rules.append(rule_info)
        
        return active_rules


# Global instance for easy access
time_scheduler = TimeScheduler()


def should_execute_trade(signal_time: datetime, pair: str, provider: str = None) -> bool:
    """Convenience function for time filtering"""
    allowed, _, _ = time_scheduler.should_execute_trade(signal_time, pair, provider)
    return allowed