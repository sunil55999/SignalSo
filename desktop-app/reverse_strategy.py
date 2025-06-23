"""
Reverse Strategy Engine for SignalOS
Implements contrarian trading logic by inverting trading signals based on configurable conditions
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os

class ReversalCondition(Enum):
    ALWAYS = "always"
    MARKET_HOURS = "market_hours"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    NEWS_EVENTS = "news_events"
    TREND_REVERSAL = "trend_reversal"
    PROVIDER_SPECIFIC = "provider_specific"
    SYMBOL_SPECIFIC = "symbol_specific"
    TIME_WINDOW = "time_window"

class ReversalMode(Enum):
    FULL_REVERSE = "full_reverse"  # BUY -> SELL, SELL -> BUY
    DIRECTION_ONLY = "direction_only"  # Only reverse direction, keep SL/TP
    IGNORE_SIGNAL = "ignore_signal"  # Block signal entirely
    MODIFY_PARAMS = "modify_params"  # Reverse with modified parameters

class SignalDirection(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass
class ReversalRule:
    rule_id: str
    name: str
    condition: ReversalCondition
    mode: ReversalMode
    enabled: bool = True
    priority: int = 1  # Higher priority rules apply first
    symbols: List[str] = None  # Specific symbols, None = all
    providers: List[str] = None  # Specific providers, None = all
    time_windows: List[Dict[str, Any]] = None  # Time-based conditions
    market_conditions: Dict[str, Any] = None  # Market state conditions
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = []
        if self.providers is None:
            self.providers = []
        if self.time_windows is None:
            self.time_windows = []
        if self.market_conditions is None:
            self.market_conditions = {}

@dataclass
class OriginalSignal:
    signal_id: str
    symbol: str
    direction: SignalDirection
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    volume: Optional[float]
    provider_id: str
    provider_name: str
    timestamp: datetime
    confidence: float = 0.0
    additional_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_params is None:
            self.additional_params = {}

@dataclass
class ReversedSignal:
    original_signal: OriginalSignal
    reversed_direction: SignalDirection
    reversed_entry: Optional[float]
    reversed_sl: Optional[float]
    reversed_tp: Optional[float]
    reversed_volume: Optional[float]
    reversal_rule: ReversalRule
    reversal_reason: str
    timestamp: datetime
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_signal_id": self.original_signal.signal_id,
            "original_direction": self.original_signal.direction.value,
            "reversed_direction": self.reversed_direction.value,
            "original_entry": self.original_signal.entry_price,
            "reversed_entry": self.reversed_entry,
            "reversal_rule_id": self.reversal_rule.rule_id,
            "reversal_reason": self.reversal_reason,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message
        }

class ReverseStrategy:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/reverse_strategy.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Reversal rules
        self.reversal_rules: List[ReversalRule] = []
        self.reversal_history: List[ReversedSignal] = []
        
        # Market data cache for conditions
        self.market_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = 60  # seconds
        
        # Statistics
        self.reversal_stats = {
            "total_reversals": 0,
            "successful_reversals": 0,
            "failed_reversals": 0,
            "ignored_signals": 0
        }
        
        # Module dependencies
        self.news_filter = None
        self.market_data_provider = None
        
        # Load configuration
        self._load_reversal_rules()
        self._load_reversal_history()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load reverse strategy configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "reverse_strategy" not in config:
                config["reverse_strategy"] = {
                    "enabled": True,
                    "default_reversal_mode": "full_reverse",
                    "enable_partial_reversals": True,
                    "reversal_confidence_threshold": 0.7,
                    "market_volatility_threshold": 2.0,
                    "reversal_rules": [
                        {
                            "rule_id": "high_volatility_reverse",
                            "name": "High Volatility Reversal",
                            "condition": "high_volatility",
                            "mode": "full_reverse",
                            "enabled": True,
                            "priority": 1,
                            "market_conditions": {
                                "volatility_threshold": 2.5,
                                "min_confidence": 0.8
                            }
                        },
                        {
                            "rule_id": "news_event_reverse",
                            "name": "News Event Contrarian",
                            "condition": "news_events",
                            "mode": "direction_only",
                            "enabled": False,
                            "priority": 2,
                            "market_conditions": {
                                "news_impact_level": "high"
                            }
                        },
                        {
                            "rule_id": "provider_specific_reverse",
                            "name": "Specific Provider Reversal",
                            "condition": "provider_specific",
                            "mode": "full_reverse",
                            "enabled": False,
                            "priority": 3,
                            "providers": ["contrarian_provider"]
                        }
                    ],
                    "symbol_settings": {
                        "EURUSD": {
                            "enable_reversal": True,
                            "reversal_strength": 1.0
                        },
                        "XAUUSD": {
                            "enable_reversal": True,
                            "reversal_strength": 1.5
                        }
                    }
                }
                self._save_config(config)
                
            return config.get("reverse_strategy", {})
            
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
            "default_reversal_mode": "full_reverse",
            "enable_partial_reversals": True,
            "reversal_confidence_threshold": 0.7,
            "market_volatility_threshold": 2.0,
            "reversal_rules": [],
            "symbol_settings": {}
        }
        
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for reverse strategy"""
        logger = logging.getLogger("reverse_strategy")
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
        
    def _load_reversal_rules(self):
        """Load reversal rules from configuration"""
        rules_config = self.config.get("reversal_rules", [])
        
        for rule_config in rules_config:
            try:
                rule = ReversalRule(
                    rule_id=rule_config.get("rule_id", ""),
                    name=rule_config.get("name", ""),
                    condition=ReversalCondition(rule_config.get("condition", "always")),
                    mode=ReversalMode(rule_config.get("mode", "full_reverse")),
                    enabled=rule_config.get("enabled", True),
                    priority=rule_config.get("priority", 1),
                    symbols=rule_config.get("symbols", []),
                    providers=rule_config.get("providers", []),
                    time_windows=rule_config.get("time_windows", []),
                    market_conditions=rule_config.get("market_conditions", {})
                )
                self.reversal_rules.append(rule)
            except Exception as e:
                self.logger.error(f"Error loading reversal rule: {e}")
                
        # Sort by priority
        self.reversal_rules.sort(key=lambda x: x.priority)
        self.logger.info(f"Loaded {len(self.reversal_rules)} reversal rules")
        
    def _load_reversal_history(self):
        """Load reversal history from storage"""
        history_file = self.log_path.replace('.log', '_history.json')
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                    
                for reversal_data in history_data.get('reversal_history', []):
                    # Reconstruct reversal record (simplified for storage)
                    # In practice, you'd want a more complete reconstruction
                    pass
                    
                # Load statistics
                if 'statistics' in history_data:
                    self.reversal_stats.update(history_data['statistics'])
                    
                self.logger.info(f"Loaded reversal history: {len(self.reversal_history)} records")
                
        except Exception as e:
            self.logger.error(f"Error loading reversal history: {e}")
            
    def _save_reversal_history(self):
        """Save reversal history to storage"""
        history_file = self.log_path.replace('.log', '_history.json')
        try:
            # Keep only recent history (last 7 days)
            cutoff_time = datetime.now() - timedelta(days=7)
            recent_history = [r for r in self.reversal_history if r.timestamp > cutoff_time]
            
            history_data = {
                'reversal_history': [reversal.to_dict() for reversal in recent_history],
                'statistics': self.reversal_stats,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=4)
                
            # Update in-memory history
            self.reversal_history = recent_history
            
        except Exception as e:
            self.logger.error(f"Error saving reversal history: {e}")
            
    def set_dependencies(self, news_filter=None, market_data_provider=None):
        """Set module dependencies"""
        self.news_filter = news_filter
        self.market_data_provider = market_data_provider
        
    def _reverse_direction(self, direction: SignalDirection) -> SignalDirection:
        """Reverse signal direction"""
        if direction == SignalDirection.BUY:
            return SignalDirection.SELL
        elif direction == SignalDirection.SELL:
            return SignalDirection.BUY
        else:
            return direction  # HOLD remains HOLD
            
    def _calculate_reversed_levels(self, original: OriginalSignal, rule: ReversalRule) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Calculate reversed entry, SL, and TP levels"""
        if rule.mode == ReversalMode.DIRECTION_ONLY:
            # Keep original levels, just reverse direction
            return original.entry_price, original.stop_loss, original.take_profit
            
        elif rule.mode == ReversalMode.FULL_REVERSE:
            # Fully reverse the signal parameters
            entry = original.entry_price
            
            if original.direction == SignalDirection.BUY:
                # Original BUY becomes SELL
                # Original SL becomes TP, original TP becomes SL
                new_sl = original.take_profit  # What was TP is now SL
                new_tp = original.stop_loss    # What was SL is now TP
            else:
                # Original SELL becomes BUY
                # Original SL becomes TP, original TP becomes SL
                new_sl = original.take_profit  # What was TP is now SL
                new_tp = original.stop_loss    # What was SL is now TP
                
            return entry, new_sl, new_tp
            
        elif rule.mode == ReversalMode.MODIFY_PARAMS:
            # Custom parameter modification based on rule conditions
            entry = original.entry_price
            
            # Apply symbol-specific modifications if available
            symbol_settings = self.config.get("symbol_settings", {}).get(original.symbol, {})
            reversal_strength = symbol_settings.get("reversal_strength", 1.0)
            
            # Calculate modified levels
            if original.stop_loss and original.take_profit:
                sl_distance = abs(original.entry_price - original.stop_loss) if original.entry_price else 0
                tp_distance = abs(original.take_profit - original.entry_price) if original.entry_price else 0
                
                # Apply reversal strength
                modified_sl_distance = sl_distance * reversal_strength
                modified_tp_distance = tp_distance * reversal_strength
                
                if original.direction == SignalDirection.BUY:
                    # Reversed to SELL
                    new_sl = original.entry_price + modified_sl_distance if original.entry_price else None
                    new_tp = original.entry_price - modified_tp_distance if original.entry_price else None
                else:
                    # Reversed to BUY
                    new_sl = original.entry_price - modified_sl_distance if original.entry_price else None
                    new_tp = original.entry_price + modified_tp_distance if original.entry_price else None
                    
                return entry, new_sl, new_tp
                
        return original.entry_price, original.stop_loss, original.take_profit
        
    def _check_reversal_conditions(self, signal: OriginalSignal, rule: ReversalRule) -> Tuple[bool, str]:
        """Check if reversal conditions are met"""
        try:
            # Check symbol filter
            if rule.symbols and signal.symbol not in rule.symbols:
                return False, "Symbol not in rule filter"
                
            # Check provider filter
            if rule.providers and signal.provider_id not in rule.providers:
                return False, "Provider not in rule filter"
                
            # Check specific conditions
            if rule.condition == ReversalCondition.ALWAYS:
                return True, "Always reverse condition"
                
            elif rule.condition == ReversalCondition.MARKET_HOURS:
                # Check if within specific market hours
                current_hour = datetime.now().hour
                market_hours = rule.market_conditions.get("market_hours", [9, 17])
                if market_hours[0] <= current_hour <= market_hours[1]:
                    return True, "Within market hours"
                return False, "Outside market hours"
                
            elif rule.condition == ReversalCondition.HIGH_VOLATILITY:
                # Check volatility conditions
                volatility_threshold = rule.market_conditions.get("volatility_threshold", 2.0)
                # In real implementation, you'd get actual volatility data
                # For now, simulate based on symbol
                if signal.symbol == "XAUUSD":  # Gold is typically more volatile
                    return True, f"High volatility detected for {signal.symbol}"
                return False, "Volatility below threshold"
                
            elif rule.condition == ReversalCondition.LOW_VOLATILITY:
                # Check for low volatility conditions
                volatility_threshold = rule.market_conditions.get("volatility_threshold", 1.0)
                # Simulate low volatility check
                if signal.symbol in ["EURUSD", "GBPUSD"]:  # Major pairs during calm periods
                    return True, f"Low volatility detected for {signal.symbol}"
                return False, "Volatility above threshold"
                
            elif rule.condition == ReversalCondition.NEWS_EVENTS:
                # Check for news events using news filter
                if self.news_filter:
                    # Check if there are active news events
                    filter_result = self.news_filter.check_symbol_filter(signal.symbol)
                    if filter_result.status.value == "blocked_news":
                        return True, "Active news events detected"
                return False, "No relevant news events"
                
            elif rule.condition == ReversalCondition.PROVIDER_SPECIFIC:
                # Always true if provider matches (already checked above)
                return True, f"Provider-specific reversal for {signal.provider_id}"
                
            elif rule.condition == ReversalCondition.SYMBOL_SPECIFIC:
                # Check symbol-specific settings
                symbol_settings = self.config.get("symbol_settings", {}).get(signal.symbol, {})
                if symbol_settings.get("enable_reversal", False):
                    return True, f"Symbol-specific reversal enabled for {signal.symbol}"
                return False, "Symbol reversal not enabled"
                
            elif rule.condition == ReversalCondition.TIME_WINDOW:
                # Check time window conditions
                current_time = datetime.now().time()
                for window in rule.time_windows:
                    start_time = datetime.strptime(window.get("start", "00:00"), "%H:%M").time()
                    end_time = datetime.strptime(window.get("end", "23:59"), "%H:%M").time()
                    if start_time <= current_time <= end_time:
                        return True, f"Within time window {window.get('name', 'unnamed')}"
                return False, "Outside all time windows"
                
            elif rule.condition == ReversalCondition.TREND_REVERSAL:
                # Check for trend reversal patterns
                # This would require technical analysis integration
                # For now, simulate based on signal confidence
                if signal.confidence < 0.6:  # Low confidence might indicate trend uncertainty
                    return True, "Low confidence signal indicates potential trend reversal"
                return False, "High confidence signal, no trend reversal detected"
                
            return False, "Unknown condition"
            
        except Exception as e:
            self.logger.error(f"Error checking reversal conditions: {e}")
            return False, f"Error: {str(e)}"
            
    def _find_applicable_rule(self, signal: OriginalSignal) -> Optional[Tuple[ReversalRule, str]]:
        """Find the first applicable reversal rule for a signal"""
        for rule in self.reversal_rules:
            if not rule.enabled:
                continue
                
            should_reverse, reason = self._check_reversal_conditions(signal, rule)
            if should_reverse:
                return rule, reason
                
        return None
        
    def process_signal(self, signal_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a signal through the reverse strategy engine"""
        try:
            if not self.config.get("enabled", True):
                return signal_data  # Pass through unchanged
                
            # Convert signal data to OriginalSignal object
            original_signal = OriginalSignal(
                signal_id=signal_data.get("signal_id", ""),
                symbol=signal_data.get("symbol", ""),
                direction=SignalDirection(signal_data.get("direction", "buy")),
                entry_price=signal_data.get("entry_price"),
                stop_loss=signal_data.get("stop_loss"),
                take_profit=signal_data.get("take_profit"),
                volume=signal_data.get("volume"),
                provider_id=signal_data.get("provider_id", ""),
                provider_name=signal_data.get("provider_name", ""),
                timestamp=datetime.now(),
                confidence=signal_data.get("confidence", 0.0),
                additional_params=signal_data.get("additional_params", {})
            )
            
            # Check if any reversal rule applies
            rule_result = self._find_applicable_rule(original_signal)
            
            if not rule_result:
                # No reversal rule applies, return original signal
                return signal_data
                
            rule, reason = rule_result
            
            # Handle different reversal modes
            if rule.mode == ReversalMode.IGNORE_SIGNAL:
                self.logger.info(f"Signal {original_signal.signal_id} ignored due to reversal rule: {rule.name}")
                self.reversal_stats["ignored_signals"] += 1
                return None  # Signal is blocked
                
            # Perform reversal
            reversed_direction = self._reverse_direction(original_signal.direction)
            reversed_entry, reversed_sl, reversed_tp = self._calculate_reversed_levels(original_signal, rule)
            
            # Create reversed signal object
            reversed_signal = ReversedSignal(
                original_signal=original_signal,
                reversed_direction=reversed_direction,
                reversed_entry=reversed_entry,
                reversed_sl=reversed_sl,
                reversed_tp=reversed_tp,
                reversed_volume=original_signal.volume,
                reversal_rule=rule,
                reversal_reason=reason,
                timestamp=datetime.now()
            )
            
            # Update statistics
            self.reversal_stats["total_reversals"] += 1
            self.reversal_stats["successful_reversals"] += 1
            
            # Log reversal
            self.logger.info(f"Signal reversed: {original_signal.direction.value} -> {reversed_direction.value} "
                           f"for {original_signal.symbol} (Rule: {rule.name}, Reason: {reason})")
            
            # Store in history
            self.reversal_history.append(reversed_signal)
            
            # Create modified signal data
            modified_signal = signal_data.copy()
            modified_signal.update({
                "direction": reversed_direction.value,
                "entry_price": reversed_entry,
                "stop_loss": reversed_sl,
                "take_profit": reversed_tp,
                "volume": reversed_signal.reversed_volume,
                "reversal_applied": True,
                "reversal_rule": rule.name,
                "reversal_reason": reason,
                "original_direction": original_signal.direction.value
            })
            
            # Save history periodically
            if len(self.reversal_history) % 10 == 0:  # Save every 10 reversals
                self._save_reversal_history()
                
            return modified_signal
            
        except Exception as e:
            self.logger.error(f"Error processing signal for reversal: {e}")
            self.reversal_stats["failed_reversals"] += 1
            return signal_data  # Return original on error
            
    def add_reversal_rule(self, rule: ReversalRule) -> bool:
        """Add a new reversal rule"""
        try:
            self.reversal_rules.append(rule)
            self.reversal_rules.sort(key=lambda x: x.priority)
            
            self.logger.info(f"Added reversal rule: {rule.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding reversal rule: {e}")
            return False
            
    def remove_reversal_rule(self, rule_id: str) -> bool:
        """Remove a reversal rule by ID"""
        try:
            self.reversal_rules = [r for r in self.reversal_rules if r.rule_id != rule_id]
            self.logger.info(f"Removed reversal rule: {rule_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing reversal rule: {e}")
            return False
            
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a reversal rule"""
        for rule in self.reversal_rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                self.logger.info(f"Enabled reversal rule: {rule_id}")
                return True
        return False
        
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a reversal rule"""
        for rule in self.reversal_rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                self.logger.info(f"Disabled reversal rule: {rule_id}")
                return True
        return False
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get reversal strategy statistics"""
        total_processed = (self.reversal_stats["total_reversals"] + 
                          self.reversal_stats["ignored_signals"])
        
        success_rate = 0.0
        if self.reversal_stats["total_reversals"] > 0:
            success_rate = (self.reversal_stats["successful_reversals"] / 
                           self.reversal_stats["total_reversals"] * 100)
            
        return {
            "total_signals_processed": total_processed,
            "total_reversals": self.reversal_stats["total_reversals"],
            "successful_reversals": self.reversal_stats["successful_reversals"],
            "failed_reversals": self.reversal_stats["failed_reversals"],
            "ignored_signals": self.reversal_stats["ignored_signals"],
            "success_rate": success_rate,
            "active_rules": len([r for r in self.reversal_rules if r.enabled]),
            "total_rules": len(self.reversal_rules)
        }
        
    def get_recent_reversals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent reversal events"""
        recent = sorted(self.reversal_history, key=lambda x: x.timestamp, reverse=True)[:limit]
        return [reversal.to_dict() for reversal in recent]
        
    def get_active_rules(self) -> List[Dict[str, Any]]:
        """Get list of active reversal rules"""
        return [
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "condition": rule.condition.value,
                "mode": rule.mode.value,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "symbols": rule.symbols,
                "providers": rule.providers
            }
            for rule in self.reversal_rules
        ]

# Global instance for easy access
reverse_strategy = ReverseStrategy()