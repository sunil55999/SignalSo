"""
Spread Checker Module for SignalOS
Real-time trade blocker that checks market spread against configured thresholds before order placement
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os

class SpreadCheckResult(Enum):
    ALLOWED = "allowed"
    BLOCKED_HIGH_SPREAD = "blocked_high_spread"
    BLOCKED_NO_QUOTES = "blocked_no_quotes"
    BLOCKED_STALE_QUOTES = "blocked_stale_quotes"
    WARNING_FALLBACK = "warning_fallback"

@dataclass
class SpreadInfo:
    symbol: str
    bid: float
    ask: float
    spread_pips: float
    spread_points: float
    timestamp: datetime
    is_stale: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "bid": self.bid,
            "ask": self.ask,
            "spread_pips": self.spread_pips,
            "spread_points": self.spread_points,
            "timestamp": self.timestamp.isoformat(),
            "is_stale": self.is_stale
        }

@dataclass
class SpreadCheckLog:
    timestamp: datetime
    symbol: str
    result: SpreadCheckResult
    current_spread: Optional[float]
    max_allowed_spread: Optional[float]
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "result": self.result.value,
            "current_spread": self.current_spread,
            "max_allowed_spread": self.max_allowed_spread,
            "details": self.details
        }

class SpreadChecker:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/trade_filters.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        self.mt5_bridge = None  # Will be injected
        self.quote_cache = {}  # Cache recent quotes to reduce MT5 calls
        self.cache_duration = 5  # seconds
        
    def set_mt5_bridge(self, mt5_bridge):
        """Inject MT5 bridge dependency"""
        self.mt5_bridge = mt5_bridge
        
    def _load_config(self) -> Dict[str, Any]:
        """Load spread checker configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            # Initialize spread_checker config if not exists
            if "spread_checker" not in config:
                config["spread_checker"] = {
                    "enabled": True,
                    "default_max_spread_pips": 3.0,
                    "symbol_specific_limits": {
                        "EURUSD": 2.0,
                        "GBPUSD": 2.5,
                        "USDJPY": 2.0,
                        "AUDUSD": 2.5,
                        "USDCAD": 2.5,
                        "USDCHF": 2.5,
                        "NZDUSD": 3.0,
                        "EURJPY": 3.0,
                        "GBPJPY": 3.5,
                        "EURGBP": 2.5,
                        "XAUUSD": 5.0,
                        "XAGUSD": 8.0,
                        "BTCUSD": 50.0,
                        "ETHUSD": 10.0
                    },
                    "high_spread_overrides": {
                        "BTCUSD": True,
                        "ETHUSD": True,
                        "XAUUSD": True,
                        "XAGUSD": True
                    },
                    "stale_quote_threshold_seconds": 10,
                    "enable_fallback_warning": True,
                    "block_on_no_quotes": True,
                    "log_all_checks": False,
                    "log_blocked_only": True
                }
                self._save_config(config)
                
            return config.get("spread_checker", {})
            
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
            "default_max_spread_pips": 3.0,
            "symbol_specific_limits": {},
            "high_spread_overrides": {},
            "stale_quote_threshold_seconds": 10,
            "enable_fallback_warning": True,
            "block_on_no_quotes": True,
            "log_all_checks": False,
            "log_blocked_only": True
        }
        
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for spread checking"""
        logger = logging.getLogger("spread_checker")
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
        
    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol (1 pip in points)"""
        # Standard pip values for common symbols
        pip_values = {
            # Major pairs (5-digit brokers)
            "EURUSD": 0.00001, "GBPUSD": 0.00001, "AUDUSD": 0.00001,
            "NZDUSD": 0.00001, "USDCAD": 0.00001, "USDCHF": 0.00001,
            
            # JPY pairs (3-digit brokers)
            "USDJPY": 0.001, "EURJPY": 0.001, "GBPJPY": 0.001,
            "AUDJPY": 0.001, "CADJPY": 0.001, "CHFJPY": 0.001,
            
            # Cross pairs
            "EURGBP": 0.00001, "EURAUD": 0.00001, "EURCHF": 0.00001,
            "GBPAUD": 0.00001, "GBPCAD": 0.00001, "GBPCHF": 0.00001,
            
            # Metals
            "XAUUSD": 0.01, "XAGUSD": 0.001,
            
            # Crypto (if available)
            "BTCUSD": 1.0, "ETHUSD": 0.1
        }
        
        return pip_values.get(symbol, 0.00001)  # Default to 5-digit
        
    def _get_current_spread(self, symbol: str) -> Optional[SpreadInfo]:
        """Get current spread for symbol from MT5"""
        try:
            # Check cache first
            cache_key = symbol
            if cache_key in self.quote_cache:
                cached_quote, cache_time = self.quote_cache[cache_key]
                if time.time() - cache_time < self.cache_duration:
                    return cached_quote
                    
            if not self.mt5_bridge:
                self.logger.warning("MT5 bridge not available, cannot check spread")
                return None
                
            # Get symbol tick from MT5
            tick_data = self.mt5_bridge.get_symbol_tick(symbol)
            if not tick_data:
                self.logger.warning(f"No tick data available for {symbol}")
                return None
                
            bid = tick_data.get('bid', 0)
            ask = tick_data.get('ask', 0)
            tick_time = tick_data.get('time', datetime.now())
            
            if bid <= 0 or ask <= 0:
                self.logger.warning(f"Invalid bid/ask prices for {symbol}: bid={bid}, ask={ask}")
                return None
                
            # Calculate spread
            spread_points = ask - bid
            pip_value = self._get_pip_value(symbol)
            spread_pips = spread_points / pip_value
            
            # Check if quote is stale
            current_time = datetime.now()
            if isinstance(tick_time, (int, float)):
                tick_time = datetime.fromtimestamp(tick_time)
            elif isinstance(tick_time, str):
                tick_time = datetime.fromisoformat(tick_time)
                
            time_diff = (current_time - tick_time).total_seconds()
            is_stale = time_diff > self.config.get("stale_quote_threshold_seconds", 10)
            
            spread_info = SpreadInfo(
                symbol=symbol,
                bid=bid,
                ask=ask,
                spread_pips=round(spread_pips, 2),
                spread_points=round(spread_points, 6),
                timestamp=tick_time,
                is_stale=is_stale
            )
            
            # Cache the result
            self.quote_cache[cache_key] = (spread_info, time.time())
            
            return spread_info
            
        except Exception as e:
            self.logger.error(f"Error getting spread for {symbol}: {e}")
            return None
            
    def _get_max_spread_for_symbol(self, symbol: str) -> float:
        """Get maximum allowed spread for symbol"""
        symbol_limits = self.config.get("symbol_specific_limits", {})
        return symbol_limits.get(symbol, self.config.get("default_max_spread_pips", 3.0))
        
    def _has_high_spread_override(self, symbol: str) -> bool:
        """Check if symbol has high spread override enabled"""
        overrides = self.config.get("high_spread_overrides", {})
        return overrides.get(symbol, False)
        
    def check_spread_before_trade(self, symbol: str, signal_data: Optional[Dict[str, Any]] = None) -> Tuple[SpreadCheckResult, Optional[SpreadInfo]]:
        """
        Check if spread allows trade execution
        
        Args:
            symbol: Trading symbol
            signal_data: Optional signal information for logging
            
        Returns:
            Tuple of (result, spread_info)
        """
        if not self.config.get("enabled", True):
            return SpreadCheckResult.ALLOWED, None
            
        try:
            spread_info = self._get_current_spread(symbol)
            max_spread = self._get_max_spread_for_symbol(symbol)
            has_override = self._has_high_spread_override(symbol)
            
            # No quotes available
            if spread_info is None:
                result = SpreadCheckResult.BLOCKED_NO_QUOTES if self.config.get("block_on_no_quotes", True) else SpreadCheckResult.WARNING_FALLBACK
                self._log_spread_check(symbol, result, None, max_spread, {
                    "reason": "No quotes available",
                    "signal_data": signal_data,
                    "has_override": has_override
                })
                return result, None
                
            # Stale quotes
            if spread_info.is_stale:
                result = SpreadCheckResult.BLOCKED_STALE_QUOTES
                self._log_spread_check(symbol, result, spread_info.spread_pips, max_spread, {
                    "reason": "Stale quotes",
                    "quote_age_seconds": (datetime.now() - spread_info.timestamp).total_seconds(),
                    "signal_data": signal_data,
                    "spread_info": spread_info.to_dict()
                })
                return result, spread_info
                
            # High spread check
            if spread_info.spread_pips > max_spread:
                if has_override:
                    # Override enabled, allow with warning
                    result = SpreadCheckResult.WARNING_FALLBACK
                    self._log_spread_check(symbol, result, spread_info.spread_pips, max_spread, {
                        "reason": "High spread but override enabled",
                        "signal_data": signal_data,
                        "spread_info": spread_info.to_dict()
                    })
                    return result, spread_info
                else:
                    # Block trade
                    result = SpreadCheckResult.BLOCKED_HIGH_SPREAD
                    self._log_spread_check(symbol, result, spread_info.spread_pips, max_spread, {
                        "reason": "Spread exceeds maximum allowed",
                        "signal_data": signal_data,
                        "spread_info": spread_info.to_dict()
                    })
                    return result, spread_info
                    
            # Spread is acceptable
            result = SpreadCheckResult.ALLOWED
            if self.config.get("log_all_checks", False):
                self._log_spread_check(symbol, result, spread_info.spread_pips, max_spread, {
                    "signal_data": signal_data,
                    "spread_info": spread_info.to_dict()
                })
                
            return result, spread_info
            
        except Exception as e:
            self.logger.error(f"Error in spread check for {symbol}: {e}")
            result = SpreadCheckResult.WARNING_FALLBACK if self.config.get("enable_fallback_warning", True) else SpreadCheckResult.BLOCKED_NO_QUOTES
            return result, None
            
    def _log_spread_check(self, symbol: str, result: SpreadCheckResult, current_spread: Optional[float], 
                         max_spread: Optional[float], details: Dict[str, Any]):
        """Log spread check result"""
        try:
            # Skip logging if configured to log blocked only and result is allowed
            if self.config.get("log_blocked_only", True) and result == SpreadCheckResult.ALLOWED:
                return
                
            log_entry = SpreadCheckLog(
                timestamp=datetime.now(),
                symbol=symbol,
                result=result,
                current_spread=current_spread,
                max_allowed_spread=max_spread,
                details=details
            )
            
            # Log to file
            log_message = f"Spread check for {symbol}: {result.value}"
            if current_spread is not None:
                log_message += f" (current: {current_spread} pips, max: {max_spread} pips)"
                
            if result == SpreadCheckResult.ALLOWED:
                self.logger.info(log_message)
            elif result in [SpreadCheckResult.WARNING_FALLBACK]:
                self.logger.warning(log_message)
            else:
                self.logger.warning(log_message)
                
            # Also log detailed JSON for analysis
            self.logger.info(f"Spread check details: {json.dumps(log_entry.to_dict())}")
            
        except Exception as e:
            self.logger.error(f"Error logging spread check: {e}")
            
    def is_trade_allowed(self, symbol: str, signal_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Simple boolean check if trade is allowed based on spread
        
        Args:
            symbol: Trading symbol
            signal_data: Optional signal information
            
        Returns:
            True if trade is allowed, False if blocked
        """
        result, _ = self.check_spread_before_trade(symbol, signal_data)
        return result in [SpreadCheckResult.ALLOWED, SpreadCheckResult.WARNING_FALLBACK]
        
    def get_spread_info(self, symbol: str) -> Optional[SpreadInfo]:
        """Get current spread information for symbol"""
        return self._get_current_spread(symbol)
        
    def update_symbol_limit(self, symbol: str, max_spread_pips: float):
        """Update maximum spread limit for specific symbol"""
        try:
            # Load full config
            with open(self.config_path, 'r') as f:
                full_config = json.load(f)
                
            if "spread_checker" not in full_config:
                full_config["spread_checker"] = self._get_default_config()
                
            if "symbol_specific_limits" not in full_config["spread_checker"]:
                full_config["spread_checker"]["symbol_specific_limits"] = {}
                
            full_config["spread_checker"]["symbol_specific_limits"][symbol] = max_spread_pips
            
            # Save updated config
            self._save_config(full_config)
            
            # Update local config
            self.config = full_config["spread_checker"]
            
            self.logger.info(f"Updated spread limit for {symbol}: {max_spread_pips} pips")
            
        except Exception as e:
            self.logger.error(f"Error updating symbol limit: {e}")
            
    def enable_high_spread_override(self, symbol: str, enabled: bool = True):
        """Enable/disable high spread override for symbol"""
        try:
            # Load full config
            with open(self.config_path, 'r') as f:
                full_config = json.load(f)
                
            if "spread_checker" not in full_config:
                full_config["spread_checker"] = self._get_default_config()
                
            if "high_spread_overrides" not in full_config["spread_checker"]:
                full_config["spread_checker"]["high_spread_overrides"] = {}
                
            full_config["spread_checker"]["high_spread_overrides"][symbol] = enabled
            
            # Save updated config
            self._save_config(full_config)
            
            # Update local config
            self.config = full_config["spread_checker"]
            
            self.logger.info(f"High spread override for {symbol}: {'enabled' if enabled else 'disabled'}")
            
        except Exception as e:
            self.logger.error(f"Error updating high spread override: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Get spread checker statistics"""
        try:
            stats = {
                "enabled": self.config.get("enabled", True),
                "default_max_spread": self.config.get("default_max_spread_pips", 3.0),
                "symbol_count": len(self.config.get("symbol_specific_limits", {})),
                "override_count": len([k for k, v in self.config.get("high_spread_overrides", {}).items() if v]),
                "cache_size": len(self.quote_cache),
                "config": self.config
            }
            return stats
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}

# Global instance for easy access
spread_checker = SpreadChecker()