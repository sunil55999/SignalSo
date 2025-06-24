"""
Margin Filter Block for SignalOS Strategy Builder
Checks user's current free margin or margin level before allowing signal execution
"""

import json
import time
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class FilterResult(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    
class MarginThresholdType(Enum):
    PERCENTAGE = "percentage"  # Margin level as percentage
    ABSOLUTE = "absolute"     # Free margin in account currency

@dataclass
class MarginFilterConfig:
    enabled: bool = True
    threshold_value: float = 200.0  # 200% margin level by default
    threshold_type: MarginThresholdType = MarginThresholdType.PERCENTAGE
    emergency_threshold: float = 100.0  # Emergency stop level
    fallback_action: FilterResult = FilterResult.BLOCK  # Block if MT5 data unavailable
    check_free_margin: bool = True
    min_free_margin: float = 1000.0  # Minimum free margin in account currency
    warning_threshold: float = 300.0  # Warning level before blocking
    per_strategy_overrides: Dict[str, float] = None
    
    def __post_init__(self):
        if self.per_strategy_overrides is None:
            self.per_strategy_overrides = {}

class MarginFilter:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/filters/margin_block.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Cache for margin data to avoid excessive MT5 calls
        self.margin_cache = {}
        self.cache_expiry = 30  # seconds
        self.last_cache_update = 0
        
        # Statistics tracking
        self.stats = {
            "total_checks": 0,
            "allowed_signals": 0,
            "blocked_signals": 0,
            "warnings_issued": 0,
            "mt5_failures": 0,
            "cache_hits": 0
        }
        
        self.logger.info("Margin filter initialized")
        
    def _load_config(self) -> MarginFilterConfig:
        """Load margin filter configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
                
            margin_config = config_data.get("margin_filter", {})
            
            # Create config with defaults
            config = MarginFilterConfig(
                enabled=margin_config.get("enabled", True),
                threshold_value=margin_config.get("threshold_value", 200.0),
                threshold_type=MarginThresholdType(margin_config.get("threshold_type", "percentage")),
                emergency_threshold=margin_config.get("emergency_threshold", 100.0),
                fallback_action=FilterResult(margin_config.get("fallback_action", "block")),
                check_free_margin=margin_config.get("check_free_margin", True),
                min_free_margin=margin_config.get("min_free_margin", 1000.0),
                warning_threshold=margin_config.get("warning_threshold", 300.0),
                per_strategy_overrides=margin_config.get("per_strategy_overrides", {})
            )
            
            # Save default config if not present
            if "margin_filter" not in config_data:
                config_data["margin_filter"] = self._config_to_dict(config)
                with open(self.config_path, 'w') as f:
                    json.dump(config_data, f, indent=4)
                    
            return config
            
        except FileNotFoundError:
            # Create default config
            default_config = MarginFilterConfig()
            config_data = {"margin_filter": self._config_to_dict(default_config)}
            
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
                
            return default_config
            
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return MarginFilterConfig()
            
    def _config_to_dict(self, config: MarginFilterConfig) -> Dict[str, Any]:
        """Convert config to dictionary for JSON serialization"""
        return {
            "enabled": config.enabled,
            "threshold_value": config.threshold_value,
            "threshold_type": config.threshold_type.value,
            "emergency_threshold": config.emergency_threshold,
            "fallback_action": config.fallback_action.value,
            "check_free_margin": config.check_free_margin,
            "min_free_margin": config.min_free_margin,
            "warning_threshold": config.warning_threshold,
            "per_strategy_overrides": config.per_strategy_overrides
        }
        
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for margin filter"""
        logger = logging.getLogger("margin_filter")
        logger.setLevel(logging.INFO)
        
        # Create logs directory
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
        
    def _get_mt5_account_info(self) -> Optional[Dict[str, Any]]:
        """Get MT5 account information including margin data"""
        try:
            # Check cache first
            current_time = time.time()
            if (current_time - self.last_cache_update) < self.cache_expiry and self.margin_cache:
                self.stats["cache_hits"] += 1
                return self.margin_cache
                
            # In a real implementation, this would call MT5 API
            # For now, we'll simulate MT5 account info
            try:
                import MetaTrader5 as mt5
                
                if not mt5.initialize():
                    self.logger.error("Failed to initialize MT5")
                    return None
                    
                account_info = mt5.account_info()
                if account_info is None:
                    self.logger.error("Failed to get account info from MT5")
                    return None
                    
                margin_data = {
                    "balance": account_info.balance,
                    "equity": account_info.equity,
                    "margin": account_info.margin,
                    "free_margin": account_info.margin_free,
                    "margin_level": account_info.margin_level,
                    "currency": account_info.currency,
                    "timestamp": current_time
                }
                
                # Update cache
                self.margin_cache = margin_data
                self.last_cache_update = current_time
                
                return margin_data
                
            except ImportError:
                # MT5 not available, simulate data for testing
                self.logger.warning("MT5 library not available, using simulated data")
                
                # Simulate realistic account data
                simulated_data = {
                    "balance": 10000.0,
                    "equity": 9800.0,
                    "margin": 500.0,
                    "free_margin": 9300.0,
                    "margin_level": 1960.0,  # (equity/margin) * 100
                    "currency": "USD",
                    "timestamp": current_time
                }
                
                # Update cache
                self.margin_cache = simulated_data
                self.last_cache_update = current_time
                
                return simulated_data
                
        except Exception as e:
            self.logger.error(f"Error getting MT5 account info: {e}")
            self.stats["mt5_failures"] += 1
            return None
            
    def _check_margin_threshold(self, margin_data: Dict[str, Any], strategy_id: Optional[str] = None) -> Tuple[FilterResult, str]:
        """Check if margin meets threshold requirements"""
        try:
            # Get threshold for this strategy or use default
            threshold = self.config.per_strategy_overrides.get(strategy_id, self.config.threshold_value)
            emergency_threshold = self.config.emergency_threshold
            warning_threshold = self.config.warning_threshold
            
            if self.config.threshold_type == MarginThresholdType.PERCENTAGE:
                # Check margin level percentage
                margin_level = margin_data.get("margin_level", 0)
                
                if margin_level <= emergency_threshold:
                    return FilterResult.BLOCK, f"Emergency margin level: {margin_level:.1f}% <= {emergency_threshold}%"
                elif margin_level <= threshold:
                    return FilterResult.BLOCK, f"Margin level too low: {margin_level:.1f}% <= {threshold}%"
                elif margin_level <= warning_threshold:
                    self.stats["warnings_issued"] += 1
                    self.logger.warning(f"Margin level warning: {margin_level:.1f}% <= {warning_threshold}%")
                    
                return FilterResult.ALLOW, f"Margin level acceptable: {margin_level:.1f}%"
                
            else:  # ABSOLUTE
                # Check free margin in account currency
                free_margin = margin_data.get("free_margin", 0)
                
                if free_margin <= emergency_threshold:
                    return FilterResult.BLOCK, f"Emergency free margin: {free_margin:.2f} <= {emergency_threshold}"
                elif free_margin <= threshold:
                    return FilterResult.BLOCK, f"Free margin too low: {free_margin:.2f} <= {threshold}"
                elif free_margin <= warning_threshold:
                    self.stats["warnings_issued"] += 1
                    self.logger.warning(f"Free margin warning: {free_margin:.2f} <= {warning_threshold}")
                    
                return FilterResult.ALLOW, f"Free margin acceptable: {free_margin:.2f}"
                
        except Exception as e:
            self.logger.error(f"Error checking margin threshold: {e}")
            return FilterResult.BLOCK, f"Error checking margin: {e}"
            
    def check_signal(self, signal_data: Dict[str, Any], strategy_id: Optional[str] = None) -> Tuple[FilterResult, str]:
        """
        Check if signal should be allowed based on margin requirements
        
        Args:
            signal_data: Signal information
            strategy_id: Optional strategy identifier for custom thresholds
            
        Returns:
            Tuple of (FilterResult, reason_string)
        """
        try:
            self.stats["total_checks"] += 1
            
            if not self.config.enabled:
                return FilterResult.ALLOW, "Margin filter disabled"
                
            # Get current margin data
            margin_data = self._get_mt5_account_info()
            
            if margin_data is None:
                # MT5 data unavailable, use fallback action
                reason = "MT5 account data unavailable"
                self.logger.error(reason)
                
                if self.config.fallback_action == FilterResult.BLOCK:
                    self.stats["blocked_signals"] += 1
                    return FilterResult.BLOCK, f"{reason} - blocking for safety"
                else:
                    self.stats["allowed_signals"] += 1
                    return FilterResult.ALLOW, f"{reason} - allowing per fallback config"
                    
            # Check margin thresholds
            result, reason = self._check_margin_threshold(margin_data, strategy_id)
            
            # Update statistics
            if result == FilterResult.ALLOW:
                self.stats["allowed_signals"] += 1
            else:
                self.stats["blocked_signals"] += 1
                
            # Log the decision
            signal_id = signal_data.get("signal_id", "unknown")
            symbol = signal_data.get("symbol", "unknown")
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "signal_id": signal_id,
                "symbol": symbol,
                "strategy_id": strategy_id,
                "result": result.value,
                "reason": reason,
                "margin_data": {
                    "margin_level": margin_data.get("margin_level"),
                    "free_margin": margin_data.get("free_margin"),
                    "balance": margin_data.get("balance"),
                    "equity": margin_data.get("equity")
                }
            }
            
            if result == FilterResult.BLOCK:
                self.logger.warning(f"Signal {signal_id} blocked: {reason}")
            else:
                self.logger.info(f"Signal {signal_id} allowed: {reason}")
                
            # Save detailed log
            self._save_filter_log(log_entry)
            
            return result, reason
            
        except Exception as e:
            self.logger.error(f"Error in margin filter check: {e}")
            self.stats["blocked_signals"] += 1
            return FilterResult.BLOCK, f"Filter error: {e}"
            
    def _save_filter_log(self, log_entry: Dict[str, Any]):
        """Save detailed filter decision to log file"""
        try:
            log_file = self.log_path.replace('.log', '_detailed.json')
            
            # Load existing logs
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    logs = json.load(f)
                    
            # Add new entry
            logs.append(log_entry)
            
            # Keep only recent entries (last 1000)
            if len(logs) > 1000:
                logs = logs[-1000:]
                
            # Save updated logs
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving filter log: {e}")
            
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update margin filter configuration"""
        try:
            # Load current config
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
                
            # Update margin filter section
            config_data["margin_filter"].update(new_config)
            
            # Save updated config
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
                
            # Reload configuration
            self.config = self._load_config()
            
            self.logger.info(f"Configuration updated: {new_config}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating config: {e}")
            return False
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get margin filter statistics"""
        total_checks = self.stats["total_checks"]
        if total_checks > 0:
            allow_rate = (self.stats["allowed_signals"] / total_checks) * 100
            block_rate = (self.stats["blocked_signals"] / total_checks) * 100
        else:
            allow_rate = block_rate = 0
            
        return {
            **self.stats,
            "allow_rate_percent": round(allow_rate, 2),
            "block_rate_percent": round(block_rate, 2),
            "cache_hit_rate": round((self.stats["cache_hits"] / max(total_checks, 1)) * 100, 2),
            "current_config": self._config_to_dict(self.config)
        }
        
    def reset_statistics(self):
        """Reset all statistics counters"""
        self.stats = {
            "total_checks": 0,
            "allowed_signals": 0,
            "blocked_signals": 0,
            "warnings_issued": 0,
            "mt5_failures": 0,
            "cache_hits": 0
        }
        self.logger.info("Statistics reset")
        
    def force_cache_refresh(self):
        """Force refresh of margin data cache"""
        self.margin_cache = {}
        self.last_cache_update = 0
        self.logger.info("Margin data cache cleared")

# Global instance for easy access
margin_filter = MarginFilter()