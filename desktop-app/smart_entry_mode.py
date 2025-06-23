"""
Smart Entry Mode Engine for SignalOS
Intelligent entry execution system that waits for optimal entry prices within configurable parameters
"""

import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os

class EntryMode(Enum):
    IMMEDIATE = "immediate"
    SMART_WAIT = "smart_wait"
    PRICE_IMPROVEMENT = "price_improvement"
    SPREAD_OPTIMIZED = "spread_optimized"

class EntryStatus(Enum):
    WAITING = "waiting"
    EXECUTED = "executed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    FAILED = "failed"

@dataclass
class EntryCondition:
    max_wait_seconds: int
    price_tolerance_pips: float
    require_spread_improvement: bool = False
    max_spread_pips: Optional[float] = None
    min_volume_threshold: Optional[float] = None
    avoid_news_window: bool = False

@dataclass
class PriceTarget:
    target_price: float
    tolerance_pips: float
    direction: str  # "BUY" or "SELL"
    symbol: str

@dataclass
class EntryAttempt:
    signal_id: str
    symbol: str
    original_entry: float
    target_entry: float
    direction: str
    lot_size: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    mode: EntryMode
    condition: EntryCondition
    start_time: datetime
    status: EntryStatus = EntryStatus.WAITING
    execution_price: Optional[float] = None
    execution_time: Optional[datetime] = None
    attempts_made: int = 0
    best_price_seen: Optional[float] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "original_entry": self.original_entry,
            "target_entry": self.target_entry,
            "direction": self.direction,
            "lot_size": self.lot_size,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "mode": self.mode.value,
            "condition": asdict(self.condition),
            "start_time": self.start_time.isoformat(),
            "status": self.status.value,
            "execution_price": self.execution_price,
            "execution_time": self.execution_time.isoformat() if self.execution_time else None,
            "attempts_made": self.attempts_made,
            "best_price_seen": self.best_price_seen,
            "reason": self.reason
        }

class SmartEntryMode:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/smart_entry.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Active entry attempts
        self.active_entries: Dict[str, EntryAttempt] = {}
        self.completed_entries: List[EntryAttempt] = []
        
        # Module dependencies
        self.mt5_bridge = None
        self.spread_checker = None
        self.strategy_runtime = None
        
        # Price monitoring
        self.price_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = 1  # seconds
        
        # Background monitoring task
        self.monitoring_task = None
        self.is_monitoring = False
        
    def _load_config(self) -> Dict[str, Any]:
        """Load smart entry configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "smart_entry" not in config:
                config["smart_entry"] = {
                    "enabled": True,
                    "default_mode": "smart_wait",
                    "default_wait_seconds": 300,
                    "default_price_tolerance_pips": 2.0,
                    "max_concurrent_entries": 50,
                    "price_update_interval": 0.5,
                    "cleanup_completed_hours": 24,
                    "require_spread_improvement": True,
                    "fallback_to_immediate": True,
                    "symbol_specific_settings": {
                        "EURUSD": {
                            "price_tolerance_pips": 1.5,
                            "max_wait_seconds": 180
                        },
                        "GBPUSD": {
                            "price_tolerance_pips": 2.0,
                            "max_wait_seconds": 240
                        },
                        "XAUUSD": {
                            "price_tolerance_pips": 5.0,
                            "max_wait_seconds": 600
                        }
                    }
                }
                self._save_config(config)
                
            return config.get("smart_entry", {})
            
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
            "default_mode": "smart_wait",
            "default_wait_seconds": 300,
            "default_price_tolerance_pips": 2.0,
            "max_concurrent_entries": 50,
            "price_update_interval": 0.5,
            "cleanup_completed_hours": 24,
            "require_spread_improvement": True,
            "fallback_to_immediate": True,
            "symbol_specific_settings": {}
        }
        
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for smart entry"""
        logger = logging.getLogger("smart_entry")
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
        
    def set_dependencies(self, mt5_bridge=None, spread_checker=None, strategy_runtime=None):
        """Set module dependencies"""
        self.mt5_bridge = mt5_bridge
        self.spread_checker = spread_checker
        self.strategy_runtime = strategy_runtime
        
    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol"""
        pip_values = {
            "EURUSD": 0.00001, "GBPUSD": 0.00001, "AUDUSD": 0.00001,
            "NZDUSD": 0.00001, "USDCAD": 0.00001, "USDCHF": 0.00001,
            "USDJPY": 0.001, "EURJPY": 0.001, "GBPJPY": 0.001,
            "EURGBP": 0.00001, "EURAUD": 0.00001, "EURCHF": 0.00001,
            "XAUUSD": 0.01, "XAGUSD": 0.001,
            "BTCUSD": 1.0, "ETHUSD": 0.1
        }
        return pip_values.get(symbol, 0.00001)
        
    def _get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current market price for symbol"""
        try:
            # Check cache first
            if symbol in self.price_cache:
                cached_data, cache_time = self.price_cache[symbol]
                if time.time() - cache_time < self.cache_duration:
                    return cached_data
                    
            if not self.mt5_bridge:
                self.logger.warning("MT5 bridge not available")
                return None
                
            # Get tick data from MT5
            tick_data = self.mt5_bridge.get_symbol_tick(symbol)
            if not tick_data:
                return None
                
            price_data = {
                'symbol': symbol,
                'bid': tick_data.get('bid', 0),
                'ask': tick_data.get('ask', 0),
                'last': tick_data.get('last', 0),
                'volume': tick_data.get('volume', 0),
                'time': tick_data.get('time', datetime.now()),
                'spread': tick_data.get('ask', 0) - tick_data.get('bid', 0)
            }
            
            # Cache the result
            self.price_cache[symbol] = (price_data, time.time())
            return price_data
            
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return None
            
    def _get_symbol_settings(self, symbol: str) -> Dict[str, Any]:
        """Get symbol-specific settings"""
        symbol_settings = self.config.get("symbol_specific_settings", {})
        default_settings = {
            "price_tolerance_pips": self.config.get("default_price_tolerance_pips", 2.0),
            "max_wait_seconds": self.config.get("default_wait_seconds", 300)
        }
        return symbol_settings.get(symbol, default_settings)
        
    def _is_price_favorable(self, current_price: float, target_price: float, direction: str, tolerance_pips: float, symbol: str) -> bool:
        """Check if current price is favorable for entry"""
        pip_value = self._get_pip_value(symbol)
        tolerance = tolerance_pips * pip_value
        
        if direction.upper() == "BUY":
            # For BUY, we want price at or below target (including tolerance)
            return current_price <= (target_price + tolerance)
        else:  # SELL
            # For SELL, we want price at or above target (including tolerance)  
            return current_price >= (target_price - tolerance)
            
    def _should_execute_immediately(self, entry_attempt: EntryAttempt, current_price_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Determine if trade should be executed immediately"""
        if not current_price_data:
            return True, "No price data available, executing immediately"
            
        # Check spread if spread checker is available
        if self.spread_checker and entry_attempt.condition.require_spread_improvement:
            spread_result, spread_info = self.spread_checker.check_spread_before_trade(entry_attempt.symbol)
            if spread_result.value in ["blocked_high_spread", "blocked_no_quotes", "blocked_stale_quotes"]:
                return False, f"Spread check failed: {spread_result.value}"
                
        # Check if we've been waiting too long
        wait_time = (datetime.now() - entry_attempt.start_time).total_seconds()
        if wait_time >= entry_attempt.condition.max_wait_seconds:
            return True, "Maximum wait time reached"
            
        # Check if current price is favorable
        current_price = current_price_data.get('ask' if entry_attempt.direction.upper() == 'BUY' else 'bid', 0)
        if self._is_price_favorable(current_price, entry_attempt.target_entry, entry_attempt.direction, 
                                  entry_attempt.condition.price_tolerance_pips, entry_attempt.symbol):
            return True, "Favorable price reached"
            
        # Update best price seen
        if entry_attempt.best_price_seen is None:
            entry_attempt.best_price_seen = current_price
        else:
            if entry_attempt.direction.upper() == "BUY" and current_price < entry_attempt.best_price_seen:
                entry_attempt.best_price_seen = current_price
            elif entry_attempt.direction.upper() == "SELL" and current_price > entry_attempt.best_price_seen:
                entry_attempt.best_price_seen = current_price
                
        return False, "Waiting for better conditions"
        
    async def _execute_trade(self, entry_attempt: EntryAttempt, reason: str) -> bool:
        """Execute the actual trade"""
        try:
            if not self.mt5_bridge:
                self.logger.error("MT5 bridge not available for trade execution")
                return False
                
            # Get current price for execution
            price_data = self._get_current_price(entry_attempt.symbol)
            if not price_data:
                self.logger.error(f"Cannot get price data for {entry_attempt.symbol}")
                return False
                
            execution_price = price_data.get('ask' if entry_attempt.direction.upper() == 'BUY' else 'bid', 0)
            
            # Prepare trade request
            trade_request = {
                'symbol': entry_attempt.symbol,
                'action': entry_attempt.direction.upper(),
                'volume': entry_attempt.lot_size,
                'price': execution_price,
                'sl': entry_attempt.stop_loss,
                'tp': entry_attempt.take_profit,
                'type': 'market',
                'comment': f"SmartEntry: {reason}",
                'deviation': 10  # Allow some slippage
            }
            
            # Execute trade through MT5 bridge
            result = await self.mt5_bridge.execute_trade(trade_request)
            
            if result.get('success', False):
                entry_attempt.status = EntryStatus.EXECUTED
                entry_attempt.execution_price = execution_price
                entry_attempt.execution_time = datetime.now()
                entry_attempt.reason = reason
                
                self.logger.info(f"Smart entry executed: {entry_attempt.signal_id} at {execution_price} ({reason})")
                return True
            else:
                self.logger.error(f"Trade execution failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing trade for {entry_attempt.signal_id}: {e}")
            return False
            
    async def _monitor_entry_attempts(self):
        """Background task to monitor active entry attempts"""
        while self.is_monitoring:
            try:
                if not self.active_entries:
                    await asyncio.sleep(self.config.get("price_update_interval", 0.5))
                    continue
                    
                # Check each active entry
                completed_entries = []
                
                for signal_id, entry_attempt in self.active_entries.items():
                    try:
                        # Get current market data
                        price_data = self._get_current_price(entry_attempt.symbol)
                        
                        # Check if we should execute
                        should_execute, reason = self._should_execute_immediately(entry_attempt, price_data)
                        
                        if should_execute:
                            entry_attempt.attempts_made += 1
                            success = await self._execute_trade(entry_attempt, reason)
                            
                            if success:
                                completed_entries.append(signal_id)
                            elif entry_attempt.attempts_made >= 3:
                                # Max attempts reached, mark as failed
                                entry_attempt.status = EntryStatus.FAILED
                                entry_attempt.reason = "Max execution attempts reached"
                                completed_entries.append(signal_id)
                                
                        # Check for timeout
                        elif (datetime.now() - entry_attempt.start_time).total_seconds() >= entry_attempt.condition.max_wait_seconds:
                            if self.config.get("fallback_to_immediate", True):
                                # Final attempt with immediate execution
                                entry_attempt.attempts_made += 1
                                success = await self._execute_trade(entry_attempt, "Timeout - fallback execution")
                                
                                if success:
                                    completed_entries.append(signal_id)
                                else:
                                    entry_attempt.status = EntryStatus.TIMEOUT
                                    entry_attempt.reason = "Timeout and fallback execution failed"
                                    completed_entries.append(signal_id)
                            else:
                                entry_attempt.status = EntryStatus.TIMEOUT
                                entry_attempt.reason = "Maximum wait time exceeded"
                                completed_entries.append(signal_id)
                                
                    except Exception as e:
                        self.logger.error(f"Error monitoring entry {signal_id}: {e}")
                        
                # Move completed entries
                for signal_id in completed_entries:
                    if signal_id in self.active_entries:
                        entry = self.active_entries.pop(signal_id)
                        self.completed_entries.append(entry)
                        
                        # Log completion
                        self.logger.info(f"Entry attempt completed: {signal_id} - Status: {entry.status.value}")
                        
                await asyncio.sleep(self.config.get("price_update_interval", 0.5))
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(1)  # Prevent tight error loop
                
    def start_monitoring(self):
        """Start background monitoring of entry attempts"""
        if not self.is_monitoring:
            self.is_monitoring = True
            try:
                self.monitoring_task = asyncio.create_task(self._monitor_entry_attempts())
                self.logger.info("Smart entry monitoring started")
            except RuntimeError:
                # No event loop running
                self.is_monitoring = False
                raise
            
    def stop_monitoring(self):
        """Stop background monitoring"""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
            self.logger.info("Smart entry monitoring stopped")
            
    def request_smart_entry(self, signal_id: str, symbol: str, direction: str, original_entry: float,
                          lot_size: float, stop_loss: Optional[float] = None, take_profit: Optional[float] = None,
                          mode: EntryMode = EntryMode.SMART_WAIT, custom_condition: Optional[EntryCondition] = None) -> bool:
        """Request smart entry execution for a signal"""
        try:
            if not self.config.get("enabled", True):
                self.logger.info("Smart entry disabled, using immediate execution")
                return False
                
            # Check if we're already monitoring this signal
            if signal_id in self.active_entries:
                self.logger.warning(f"Signal {signal_id} already has active entry attempt")
                return False
                
            # Check concurrent entry limit
            if len(self.active_entries) >= self.config.get("max_concurrent_entries", 50):
                self.logger.warning("Maximum concurrent entries reached")
                return False
                
            # Get symbol-specific settings
            symbol_settings = self._get_symbol_settings(symbol)
            
            # Create entry condition
            if custom_condition:
                condition = custom_condition
            else:
                condition = EntryCondition(
                    max_wait_seconds=symbol_settings["max_wait_seconds"],
                    price_tolerance_pips=symbol_settings["price_tolerance_pips"],
                    require_spread_improvement=self.config.get("require_spread_improvement", True)
                )
                
            # Calculate target entry price (slightly better than original)
            pip_value = self._get_pip_value(symbol)
            improvement_pips = condition.price_tolerance_pips / 2  # Try to get entry halfway to tolerance
            
            if direction.upper() == "BUY":
                target_entry = original_entry - (improvement_pips * pip_value)
            else:  # SELL
                target_entry = original_entry + (improvement_pips * pip_value)
                
            # Create entry attempt
            entry_attempt = EntryAttempt(
                signal_id=signal_id,
                symbol=symbol,
                original_entry=original_entry,
                target_entry=target_entry,
                direction=direction,
                lot_size=lot_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                mode=mode,
                condition=condition,
                start_time=datetime.now()
            )
            
            # Add to active entries
            self.active_entries[signal_id] = entry_attempt
            
            # Start monitoring if not already running
            if not self.is_monitoring:
                try:
                    self.start_monitoring()
                except RuntimeError:
                    # No event loop running, skip monitoring for now
                    self.logger.debug("No event loop running, skipping monitoring start")
                
            self.logger.info(f"Smart entry requested for {signal_id}: {symbol} {direction} target={target_entry}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error requesting smart entry for {signal_id}: {e}")
            return False
            
    def cancel_entry_attempt(self, signal_id: str, reason: str = "Manual cancellation") -> bool:
        """Cancel an active entry attempt"""
        try:
            if signal_id not in self.active_entries:
                self.logger.warning(f"No active entry found for signal {signal_id}")
                return False
                
            entry = self.active_entries.pop(signal_id)
            entry.status = EntryStatus.CANCELLED
            entry.reason = reason
            
            self.completed_entries.append(entry)
            
            self.logger.info(f"Entry attempt cancelled for {signal_id}: {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling entry attempt {signal_id}: {e}")
            return False
            
    def get_entry_status(self, signal_id: str) -> Optional[EntryAttempt]:
        """Get status of an entry attempt"""
        if signal_id in self.active_entries:
            return self.active_entries[signal_id]
            
        # Check completed entries
        for entry in self.completed_entries:
            if entry.signal_id == signal_id:
                return entry
                
        return None
        
    def get_active_entries(self) -> Dict[str, EntryAttempt]:
        """Get all active entry attempts"""
        return self.active_entries.copy()
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get smart entry statistics"""
        total_completed = len(self.completed_entries)
        if total_completed == 0:
            return {
                "total_attempts": 0,
                "success_rate": 0.0,
                "average_wait_time": 0.0,
                "active_count": len(self.active_entries)
            }
            
        successful = len([e for e in self.completed_entries if e.status == EntryStatus.EXECUTED])
        timeouts = len([e for e in self.completed_entries if e.status == EntryStatus.TIMEOUT])
        cancelled = len([e for e in self.completed_entries if e.status == EntryStatus.CANCELLED])
        failed = len([e for e in self.completed_entries if e.status == EntryStatus.FAILED])
        
        # Calculate average wait time for successful entries
        successful_entries = [e for e in self.completed_entries if e.status == EntryStatus.EXECUTED and e.execution_time]
        avg_wait_time = 0.0
        if successful_entries:
            total_wait = sum((e.execution_time - e.start_time).total_seconds() for e in successful_entries)
            avg_wait_time = total_wait / len(successful_entries)
            
        return {
            "total_attempts": total_completed,
            "successful": successful,
            "timeouts": timeouts,
            "cancelled": cancelled,
            "failed": failed,
            "success_rate": (successful / total_completed) * 100 if total_completed > 0 else 0.0,
            "average_wait_time": avg_wait_time,
            "active_count": len(self.active_entries)
        }
        
    def cleanup_old_entries(self, max_age_hours: int = None):
        """Clean up old completed entries"""
        if max_age_hours is None:
            max_age_hours = self.config.get("cleanup_completed_hours", 24)
            
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        original_count = len(self.completed_entries)
        self.completed_entries = [
            entry for entry in self.completed_entries 
            if entry.start_time > cutoff_time
        ]
        
        removed_count = original_count - len(self.completed_entries)
        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} old entry attempts")
            
        return removed_count

# Global instance for easy access
smart_entry = SmartEntryMode()