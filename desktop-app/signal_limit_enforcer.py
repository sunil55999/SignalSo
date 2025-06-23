"""
Signal Limit Enforcer Engine for SignalOS
Prevents overtrading by limiting the number of signals per trading pair, provider, and time period
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os
from collections import defaultdict, deque

class LimitType(Enum):
    SYMBOL_HOURLY = "symbol_hourly"
    SYMBOL_DAILY = "symbol_daily"
    PROVIDER_HOURLY = "provider_hourly"
    PROVIDER_DAILY = "provider_daily"
    GLOBAL_HOURLY = "global_hourly"
    GLOBAL_DAILY = "global_daily"

class EnforcementResult(Enum):
    ALLOWED = "allowed"
    BLOCKED_SYMBOL_HOURLY = "blocked_symbol_hourly"
    BLOCKED_SYMBOL_DAILY = "blocked_symbol_daily"
    BLOCKED_PROVIDER_HOURLY = "blocked_provider_hourly"
    BLOCKED_PROVIDER_DAILY = "blocked_provider_daily"
    BLOCKED_GLOBAL_HOURLY = "blocked_global_hourly"
    BLOCKED_GLOBAL_DAILY = "blocked_global_daily"
    BLOCKED_COOLDOWN = "blocked_cooldown"
    OVERRIDE_ACTIVE = "override_active"

@dataclass
class SignalRecord:
    signal_id: str
    symbol: str
    provider_id: str
    provider_name: str
    timestamp: datetime
    signal_type: str = "trade"  # trade, notification, alert
    override_used: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "timestamp": self.timestamp.isoformat(),
            "signal_type": self.signal_type,
            "override_used": self.override_used
        }

@dataclass
class LimitConfig:
    symbol_hourly_limit: int = 3
    symbol_daily_limit: int = 10
    provider_hourly_limit: int = 5
    provider_daily_limit: int = 20
    global_hourly_limit: int = 15
    global_daily_limit: int = 50
    cooldown_minutes: int = 15
    emergency_override_limit: int = 5  # Per day
    symbol_specific_limits: Dict[str, Dict[str, int]] = None
    provider_specific_limits: Dict[str, Dict[str, int]] = None
    
    def __post_init__(self):
        if self.symbol_specific_limits is None:
            self.symbol_specific_limits = {
                "XAUUSD": {
                    "hourly": 2,
                    "daily": 6
                },
                "BTCUSD": {
                    "hourly": 1,
                    "daily": 3
                }
            }
        if self.provider_specific_limits is None:
            self.provider_specific_limits = {
                "high_frequency_provider": {
                    "hourly": 2,
                    "daily": 8
                },
                "premium_provider": {
                    "hourly": 10,
                    "daily": 40
                }
            }

@dataclass
class EnforcementStatus:
    result: EnforcementResult
    reason: str
    current_count: int
    limit: int
    next_reset_time: Optional[datetime] = None
    cooldown_expires: Optional[datetime] = None
    override_expires: Optional[datetime] = None

class SignalLimitEnforcer:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/signal_limit_enforcer.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Signal tracking
        self.signal_history: List[SignalRecord] = []
        self.last_signal_time: Dict[str, datetime] = {}  # symbol -> last signal time
        
        # Sliding window counters
        self.hourly_counters = {
            'symbol': defaultdict(deque),      # symbol -> deque of timestamps
            'provider': defaultdict(deque),    # provider -> deque of timestamps
            'global': deque()                  # global deque of timestamps
        }
        
        self.daily_counters = {
            'symbol': defaultdict(deque),
            'provider': defaultdict(deque),
            'global': deque()
        }
        
        # Override state
        self.emergency_override_active = False
        self.override_expires: Optional[datetime] = None
        self.daily_override_count = 0
        self.last_override_reset = datetime.now().date()
        
        # Load existing data
        self._load_signal_history()
        self._rebuild_counters()
        
    def _load_config(self) -> LimitConfig:
        """Load signal limit enforcer configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "signal_limit_enforcer" not in config:
                config["signal_limit_enforcer"] = {
                    "enabled": True,
                    "symbol_hourly_limit": 3,
                    "symbol_daily_limit": 10,
                    "provider_hourly_limit": 5,
                    "provider_daily_limit": 20,
                    "global_hourly_limit": 15,
                    "global_daily_limit": 50,
                    "cooldown_minutes": 15,
                    "emergency_override_limit": 5,
                    "cleanup_days": 7,
                    "symbol_specific_limits": {
                        "XAUUSD": {"hourly": 2, "daily": 6},
                        "BTCUSD": {"hourly": 1, "daily": 3},
                        "ETHUSD": {"hourly": 1, "daily": 3}
                    },
                    "provider_specific_limits": {
                        "high_frequency_provider": {"hourly": 2, "daily": 8},
                        "premium_provider": {"hourly": 10, "daily": 40}
                    }
                }
                self._save_config(config)
                
            enforcer_config = config.get("signal_limit_enforcer", {})
            
            return LimitConfig(
                symbol_hourly_limit=enforcer_config.get("symbol_hourly_limit", 3),
                symbol_daily_limit=enforcer_config.get("symbol_daily_limit", 10),
                provider_hourly_limit=enforcer_config.get("provider_hourly_limit", 5),
                provider_daily_limit=enforcer_config.get("provider_daily_limit", 20),
                global_hourly_limit=enforcer_config.get("global_hourly_limit", 15),
                global_daily_limit=enforcer_config.get("global_daily_limit", 50),
                cooldown_minutes=enforcer_config.get("cooldown_minutes", 15),
                emergency_override_limit=enforcer_config.get("emergency_override_limit", 5),
                symbol_specific_limits=enforcer_config.get("symbol_specific_limits"),
                provider_specific_limits=enforcer_config.get("provider_specific_limits")
            )
            
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return LimitConfig()
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            return LimitConfig()
            
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for signal limit enforcer"""
        logger = logging.getLogger("signal_limit_enforcer")
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
        
    def _load_signal_history(self):
        """Load existing signal history from storage"""
        history_file = self.log_path.replace('.log', '_history.json')
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                    
                for record_data in history_data.get('signal_history', []):
                    record = SignalRecord(
                        signal_id=record_data['signal_id'],
                        symbol=record_data['symbol'],
                        provider_id=record_data['provider_id'],
                        provider_name=record_data['provider_name'],
                        timestamp=datetime.fromisoformat(record_data['timestamp']),
                        signal_type=record_data.get('signal_type', 'trade'),
                        override_used=record_data.get('override_used', False)
                    )
                    self.signal_history.append(record)
                    
                # Load override state
                override_data = history_data.get('override_state', {})
                self.daily_override_count = override_data.get('daily_count', 0)
                last_reset_str = override_data.get('last_reset')
                if last_reset_str:
                    self.last_override_reset = datetime.fromisoformat(last_reset_str).date()
                    
                self.logger.info(f"Loaded {len(self.signal_history)} signal records from storage")
                
        except Exception as e:
            self.logger.error(f"Error loading signal history: {e}")
            
    def _save_signal_history(self):
        """Save signal history to storage"""
        history_file = self.log_path.replace('.log', '_history.json')
        try:
            # Keep only recent history (configurable days)
            with open(self.config_path, 'r') as f:
                full_config = json.load(f)
            cleanup_days = full_config.get("signal_limit_enforcer", {}).get("cleanup_days", 7)
            
            cutoff_time = datetime.now() - timedelta(days=cleanup_days)
            recent_history = [record for record in self.signal_history if record.timestamp > cutoff_time]
            
            history_data = {
                'signal_history': [record.to_dict() for record in recent_history],
                'override_state': {
                    'daily_count': self.daily_override_count,
                    'last_reset': self.last_override_reset.isoformat()
                },
                'last_updated': datetime.now().isoformat()
            }
            
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=4)
                
            # Update in-memory history
            self.signal_history = recent_history
            
        except Exception as e:
            self.logger.error(f"Error saving signal history: {e}")
            
    def _rebuild_counters(self):
        """Rebuild sliding window counters from signal history"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        # Clear existing counters
        for counter_type in ['symbol', 'provider']:
            self.hourly_counters[counter_type].clear()
            self.daily_counters[counter_type].clear()
        self.hourly_counters['global'].clear()
        self.daily_counters['global'].clear()
        
        # Rebuild from history
        for record in self.signal_history:
            if record.timestamp > one_hour_ago:
                self.hourly_counters['symbol'][record.symbol].append(record.timestamp)
                self.hourly_counters['provider'][record.provider_id].append(record.timestamp)
                self.hourly_counters['global'].append(record.timestamp)
                
            if record.timestamp > one_day_ago:
                self.daily_counters['symbol'][record.symbol].append(record.timestamp)
                self.daily_counters['provider'][record.provider_id].append(record.timestamp)
                self.daily_counters['global'].append(record.timestamp)
                
            # Update last signal time
            if record.symbol not in self.last_signal_time or record.timestamp > self.last_signal_time[record.symbol]:
                self.last_signal_time[record.symbol] = record.timestamp
                
    def _clean_old_timestamps(self, timestamp_deque: deque, cutoff_time: datetime):
        """Remove timestamps older than cutoff time from deque"""
        while timestamp_deque and timestamp_deque[0] < cutoff_time:
            timestamp_deque.popleft()
            
    def _update_counters(self, symbol: str, provider_id: str, timestamp: datetime):
        """Update sliding window counters with new signal"""
        # Add to hourly counters
        self.hourly_counters['symbol'][symbol].append(timestamp)
        self.hourly_counters['provider'][provider_id].append(timestamp)
        self.hourly_counters['global'].append(timestamp)
        
        # Add to daily counters
        self.daily_counters['symbol'][symbol].append(timestamp)
        self.daily_counters['provider'][provider_id].append(timestamp)
        self.daily_counters['global'].append(timestamp)
        
        # Clean old timestamps
        one_hour_ago = timestamp - timedelta(hours=1)
        one_day_ago = timestamp - timedelta(days=1)
        
        self._clean_old_timestamps(self.hourly_counters['symbol'][symbol], one_hour_ago)
        self._clean_old_timestamps(self.hourly_counters['provider'][provider_id], one_hour_ago)
        self._clean_old_timestamps(self.hourly_counters['global'], one_hour_ago)
        
        self._clean_old_timestamps(self.daily_counters['symbol'][symbol], one_day_ago)
        self._clean_old_timestamps(self.daily_counters['provider'][provider_id], one_day_ago)
        self._clean_old_timestamps(self.daily_counters['global'], one_day_ago)
        
    def _get_effective_limits(self, symbol: str, provider_id: str) -> Dict[str, int]:
        """Get effective limits for symbol and provider"""
        limits = {
            'symbol_hourly': self.config.symbol_hourly_limit,
            'symbol_daily': self.config.symbol_daily_limit,
            'provider_hourly': self.config.provider_hourly_limit,
            'provider_daily': self.config.provider_daily_limit,
            'global_hourly': self.config.global_hourly_limit,
            'global_daily': self.config.global_daily_limit
        }
        
        # Apply symbol-specific limits
        if symbol in self.config.symbol_specific_limits:
            symbol_limits = self.config.symbol_specific_limits[symbol]
            limits['symbol_hourly'] = symbol_limits.get('hourly', limits['symbol_hourly'])
            limits['symbol_daily'] = symbol_limits.get('daily', limits['symbol_daily'])
            
        # Apply provider-specific limits
        if provider_id in self.config.provider_specific_limits:
            provider_limits = self.config.provider_specific_limits[provider_id]
            limits['provider_hourly'] = provider_limits.get('hourly', limits['provider_hourly'])
            limits['provider_daily'] = provider_limits.get('daily', limits['provider_daily'])
            
        return limits
        
    def _check_cooldown(self, symbol: str, current_time: datetime) -> Tuple[bool, Optional[datetime]]:
        """Check if symbol is in cooldown period"""
        if symbol not in self.last_signal_time:
            return False, None
            
        last_time = self.last_signal_time[symbol]
        cooldown_expires = last_time + timedelta(minutes=self.config.cooldown_minutes)
        
        if current_time < cooldown_expires:
            return True, cooldown_expires
            
        return False, None
        
    def check_signal_allowed(self, symbol: str, provider_id: str, provider_name: str = None,
                           current_time: Optional[datetime] = None) -> EnforcementStatus:
        """Check if a signal is allowed based on current limits"""
        if current_time is None:
            current_time = datetime.now()
            
        # Check if enforcement is disabled
        with open(self.config_path, 'r') as f:
            full_config = json.load(f)
        if not full_config.get("signal_limit_enforcer", {}).get("enabled", True):
            return EnforcementStatus(
                result=EnforcementResult.ALLOWED,
                reason="Signal limit enforcement disabled",
                current_count=0,
                limit=0
            )
            
        # Check emergency override
        if self.emergency_override_active and self.override_expires and current_time < self.override_expires:
            return EnforcementStatus(
                result=EnforcementResult.OVERRIDE_ACTIVE,
                reason="Emergency override active",
                current_count=0,
                limit=0,
                override_expires=self.override_expires
            )
            
        # Reset daily override count if needed
        current_date = current_time.date()
        if current_date > self.last_override_reset:
            self.daily_override_count = 0
            self.last_override_reset = current_date
            
        # Get effective limits
        limits = self._get_effective_limits(symbol, provider_id)
        
        # Clean old timestamps before checking
        one_hour_ago = current_time - timedelta(hours=1)
        one_day_ago = current_time - timedelta(days=1)
        
        self._clean_old_timestamps(self.hourly_counters['symbol'][symbol], one_hour_ago)
        self._clean_old_timestamps(self.hourly_counters['provider'][provider_id], one_hour_ago)
        self._clean_old_timestamps(self.hourly_counters['global'], one_hour_ago)
        
        self._clean_old_timestamps(self.daily_counters['symbol'][symbol], one_day_ago)
        self._clean_old_timestamps(self.daily_counters['provider'][provider_id], one_day_ago)
        self._clean_old_timestamps(self.daily_counters['global'], one_day_ago)
        
        # Check symbol hourly limit
        symbol_hourly_count = len(self.hourly_counters['symbol'][symbol])
        if symbol_hourly_count >= limits['symbol_hourly']:
            next_reset = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            return EnforcementStatus(
                result=EnforcementResult.BLOCKED_SYMBOL_HOURLY,
                reason=f"Symbol {symbol} hourly limit exceeded",
                current_count=symbol_hourly_count,
                limit=limits['symbol_hourly'],
                next_reset_time=next_reset
            )
            
        # Check symbol daily limit
        symbol_daily_count = len(self.daily_counters['symbol'][symbol])
        if symbol_daily_count >= limits['symbol_daily']:
            next_reset = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return EnforcementStatus(
                result=EnforcementResult.BLOCKED_SYMBOL_DAILY,
                reason=f"Symbol {symbol} daily limit exceeded",
                current_count=symbol_daily_count,
                limit=limits['symbol_daily'],
                next_reset_time=next_reset
            )
            
        # Check provider hourly limit
        provider_hourly_count = len(self.hourly_counters['provider'][provider_id])
        if provider_hourly_count >= limits['provider_hourly']:
            next_reset = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            return EnforcementStatus(
                result=EnforcementResult.BLOCKED_PROVIDER_HOURLY,
                reason=f"Provider {provider_id} hourly limit exceeded",
                current_count=provider_hourly_count,
                limit=limits['provider_hourly'],
                next_reset_time=next_reset
            )
            
        # Check provider daily limit
        provider_daily_count = len(self.daily_counters['provider'][provider_id])
        if provider_daily_count >= limits['provider_daily']:
            next_reset = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return EnforcementStatus(
                result=EnforcementResult.BLOCKED_PROVIDER_DAILY,
                reason=f"Provider {provider_id} daily limit exceeded",
                current_count=provider_daily_count,
                limit=limits['provider_daily'],
                next_reset_time=next_reset
            )
            
        # Check global hourly limit
        global_hourly_count = len(self.hourly_counters['global'])
        if global_hourly_count >= limits['global_hourly']:
            next_reset = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            return EnforcementStatus(
                result=EnforcementResult.BLOCKED_GLOBAL_HOURLY,
                reason="Global hourly limit exceeded",
                current_count=global_hourly_count,
                limit=limits['global_hourly'],
                next_reset_time=next_reset
            )
            
        # Check global daily limit
        global_daily_count = len(self.daily_counters['global'])
        if global_daily_count >= limits['global_daily']:
            next_reset = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return EnforcementStatus(
                result=EnforcementResult.BLOCKED_GLOBAL_DAILY,
                reason="Global daily limit exceeded",
                current_count=global_daily_count,
                limit=limits['global_daily'],
                next_reset_time=next_reset
            )
            
        # Check cooldown last (after limit checks)
        in_cooldown, cooldown_expires = self._check_cooldown(symbol, current_time)
        if in_cooldown:
            return EnforcementStatus(
                result=EnforcementResult.BLOCKED_COOLDOWN,
                reason=f"Symbol {symbol} in cooldown period",
                current_count=0,
                limit=0,
                cooldown_expires=cooldown_expires
            )
            
        # All checks passed
        return EnforcementStatus(
            result=EnforcementResult.ALLOWED,
            reason="Signal allowed - within all limits",
            current_count=0,
            limit=0
        )
        
    def record_signal(self, signal_id: str, symbol: str, provider_id: str, provider_name: str = None,
                     signal_type: str = "trade", override_used: bool = False,
                     timestamp: Optional[datetime] = None) -> bool:
        """Record a processed signal"""
        try:
            if timestamp is None:
                timestamp = datetime.now()
                
            # Create signal record
            record = SignalRecord(
                signal_id=signal_id,
                symbol=symbol,
                provider_id=provider_id,
                provider_name=provider_name or provider_id,
                timestamp=timestamp,
                signal_type=signal_type,
                override_used=override_used
            )
            
            # Add to history
            self.signal_history.append(record)
            
            # Update counters
            self._update_counters(symbol, provider_id, timestamp)
            
            # Update last signal time
            self.last_signal_time[symbol] = timestamp
            
            # Save to storage
            self._save_signal_history()
            
            self.logger.info(f"Recorded signal: {signal_id} for {symbol} from {provider_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording signal {signal_id}: {e}")
            return False
            
    def enable_emergency_override(self, duration_minutes: int = 60) -> bool:
        """Enable emergency override to bypass limits"""
        try:
            # Check if daily override limit exceeded
            if self.daily_override_count >= self.config.emergency_override_limit:
                self.logger.warning("Daily emergency override limit exceeded")
                return False
                
            self.emergency_override_active = True
            self.override_expires = datetime.now() + timedelta(minutes=duration_minutes)
            self.daily_override_count += 1
            
            self.logger.info(f"Emergency override enabled for {duration_minutes} minutes (daily count: {self.daily_override_count})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enabling emergency override: {e}")
            return False
            
    def disable_emergency_override(self) -> bool:
        """Disable emergency override"""
        try:
            self.emergency_override_active = False
            self.override_expires = None
            
            self.logger.info("Emergency override disabled")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disabling emergency override: {e}")
            return False
            
    def get_current_statistics(self) -> Dict[str, Any]:
        """Get current signal limit statistics"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        # Clean counters
        for symbol in list(self.hourly_counters['symbol'].keys()):
            self._clean_old_timestamps(self.hourly_counters['symbol'][symbol], one_hour_ago)
            self._clean_old_timestamps(self.daily_counters['symbol'][symbol], one_day_ago)
            
        for provider in list(self.hourly_counters['provider'].keys()):
            self._clean_old_timestamps(self.hourly_counters['provider'][provider], one_hour_ago)
            self._clean_old_timestamps(self.daily_counters['provider'][provider], one_day_ago)
            
        self._clean_old_timestamps(self.hourly_counters['global'], one_hour_ago)
        self._clean_old_timestamps(self.daily_counters['global'], one_day_ago)
        
        # Calculate statistics
        symbol_stats = {}
        for symbol, hourly_deque in self.hourly_counters['symbol'].items():
            if hourly_deque or symbol in self.daily_counters['symbol']:
                daily_deque = self.daily_counters['symbol'][symbol]
                limits = self._get_effective_limits(symbol, "default")
                symbol_stats[symbol] = {
                    "hourly_count": len(hourly_deque),
                    "daily_count": len(daily_deque),
                    "hourly_limit": limits['symbol_hourly'],
                    "daily_limit": limits['symbol_daily'],
                    "last_signal": self.last_signal_time.get(symbol, datetime.min).isoformat()
                }
                
        provider_stats = {}
        for provider, hourly_deque in self.hourly_counters['provider'].items():
            if hourly_deque or provider in self.daily_counters['provider']:
                daily_deque = self.daily_counters['provider'][provider]
                limits = self._get_effective_limits("default", provider)
                provider_stats[provider] = {
                    "hourly_count": len(hourly_deque),
                    "daily_count": len(daily_deque),
                    "hourly_limit": limits['provider_hourly'],
                    "daily_limit": limits['provider_daily']
                }
                
        return {
            "global_hourly_count": len(self.hourly_counters['global']),
            "global_daily_count": len(self.daily_counters['global']),
            "global_hourly_limit": self.config.global_hourly_limit,
            "global_daily_limit": self.config.global_daily_limit,
            "symbol_statistics": symbol_stats,
            "provider_statistics": provider_stats,
            "emergency_override_active": self.emergency_override_active,
            "override_expires": self.override_expires.isoformat() if self.override_expires else None,
            "daily_override_count": self.daily_override_count,
            "daily_override_limit": self.config.emergency_override_limit,
            "total_signals_recorded": len(self.signal_history)
        }
        
    def get_symbol_status(self, symbol: str) -> Dict[str, Any]:
        """Get detailed status for a specific symbol"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        # Clean counters for this symbol
        self._clean_old_timestamps(self.hourly_counters['symbol'][symbol], one_hour_ago)
        self._clean_old_timestamps(self.daily_counters['symbol'][symbol], one_day_ago)
        
        limits = self._get_effective_limits(symbol, "default")
        
        # Check cooldown
        in_cooldown, cooldown_expires = self._check_cooldown(symbol, now)
        
        return {
            "symbol": symbol,
            "hourly_count": len(self.hourly_counters['symbol'][symbol]),
            "daily_count": len(self.daily_counters['symbol'][symbol]),
            "hourly_limit": limits['symbol_hourly'],
            "daily_limit": limits['symbol_daily'],
            "in_cooldown": in_cooldown,
            "cooldown_expires": cooldown_expires.isoformat() if cooldown_expires else None,
            "last_signal": self.last_signal_time.get(symbol, datetime.min).isoformat()
        }
        
    def get_recent_signals(self, limit: int = 50, symbol: str = None, provider_id: str = None) -> List[Dict[str, Any]]:
        """Get recent signal records with optional filtering"""
        filtered_signals = self.signal_history
        
        if symbol:
            filtered_signals = [s for s in filtered_signals if s.symbol == symbol]
            
        if provider_id:
            filtered_signals = [s for s in filtered_signals if s.provider_id == provider_id]
            
        # Sort by timestamp (newest first) and limit
        recent_signals = sorted(filtered_signals, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        return [signal.to_dict() for signal in recent_signals]

# Global instance for easy access
signal_limit_enforcer = SignalLimitEnforcer()