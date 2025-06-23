"""
Smart Retry Engine for MT5 Trade Execution
Handles failed trades with configurable retry logic based on MT5 connection, slippage, spread conditions
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from spread_checker import spread_checker, SpreadCheckResult

class RetryReason(Enum):
    MT5_DISCONNECTED = "mt5_disconnected"
    HIGH_SLIPPAGE = "high_slippage"
    WIDE_SPREAD = "wide_spread"
    INSUFFICIENT_MARGIN = "insufficient_margin"
    MARKET_CLOSED = "market_closed"
    INVALID_PRICE = "invalid_price"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class TradeRequest:
    signal_id: int
    symbol: str
    action: str  # BUY, SELL
    lot_size: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: str = ""
    magic_number: int = 0

@dataclass
class RetryEntry:
    id: str
    trade_request: TradeRequest
    reason: RetryReason
    attempts: int
    max_attempts: int
    next_retry: datetime
    created_at: datetime
    last_error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trade_request": asdict(self.trade_request),
            "reason": self.reason.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "next_retry": self.next_retry.isoformat(),
            "created_at": self.created_at.isoformat(),
            "last_error": self.last_error
        }

class RetryEngine:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/retry_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.retry_buffer: Dict[str, RetryEntry] = {}
        self.config = self._load_config()
        self._setup_logging()
        self._load_retry_buffer()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load retry configuration from config.json"""
        default_config = {
            "retry_delays": {
                "mt5_disconnected": [30, 60, 120, 300],  # seconds
                "high_slippage": [10, 30, 60],
                "wide_spread": [5, 15, 30],
                "insufficient_margin": [60, 300],
                "market_closed": [300, 600, 1800],
                "invalid_price": [5, 15, 30],
                "unknown_error": [30, 60, 120]
            },
            "max_attempts": {
                "mt5_disconnected": 4,
                "high_slippage": 3,
                "wide_spread": 3,
                "insufficient_margin": 2,
                "market_closed": 3,
                "invalid_price": 3,
                "unknown_error": 3
            },
            "conditions": {
                "max_slippage_pips": 2.0,
                "max_spread_pips": 3.0,
                "min_margin_level": 200.0
            }
        }
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults for missing keys
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            # Create default config file
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def _setup_logging(self):
        """Setup logging for retry operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('RetryEngine')
    
    def _load_retry_buffer(self):
        """Load existing retry entries from log file"""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
                for entry_data in data.get("pending_retries", []):
                    entry = RetryEntry(
                        id=entry_data["id"],
                        trade_request=TradeRequest(**entry_data["trade_request"]),
                        reason=RetryReason(entry_data["reason"]),
                        attempts=entry_data["attempts"],
                        max_attempts=entry_data["max_attempts"],
                        next_retry=datetime.fromisoformat(entry_data["next_retry"]),
                        created_at=datetime.fromisoformat(entry_data["created_at"]),
                        last_error=entry_data.get("last_error", "")
                    )
                    self.retry_buffer[entry.id] = entry
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self.retry_buffer = {}
    
    def _save_retry_buffer(self):
        """Save retry buffer to log file"""
        import os
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        data = {
            "pending_retries": [entry.to_dict() for entry in self.retry_buffer.values()],
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.log_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_failed_trade(self, trade_request: TradeRequest, reason: RetryReason, error_message: str = "") -> str:
        """Add a failed trade to the retry buffer"""
        entry_id = f"{trade_request.signal_id}_{int(time.time())}"
        
        # Get retry configuration for this reason
        reason_str = reason.value
        max_attempts = self.config["max_attempts"].get(reason_str, 3)
        retry_delays = self.config["retry_delays"].get(reason_str, [30, 60, 120])
        
        # Calculate next retry time (first delay)
        next_retry = datetime.now() + timedelta(seconds=retry_delays[0])
        
        entry = RetryEntry(
            id=entry_id,
            trade_request=trade_request,
            reason=reason,
            attempts=0,
            max_attempts=max_attempts,
            next_retry=next_retry,
            created_at=datetime.now(),
            last_error=error_message
        )
        
        self.retry_buffer[entry_id] = entry
        self._save_retry_buffer()
        
        self.logger.info(f"Added trade to retry buffer: {entry_id}, reason: {reason.value}")
        return entry_id
    
    def get_pending_retries(self) -> List[RetryEntry]:
        """Get all trades ready for retry"""
        now = datetime.now()
        pending = []
        
        for entry in self.retry_buffer.values():
            if entry.next_retry <= now and entry.attempts < entry.max_attempts:
                pending.append(entry)
        
        return pending
    
    def mark_retry_attempt(self, entry_id: str, success: bool, error_message: str = "") -> bool:
        """Mark a retry attempt as successful or failed"""
        if entry_id not in self.retry_buffer:
            return False
        
        entry = self.retry_buffer[entry_id]
        entry.attempts += 1
        entry.last_error = error_message
        
        if success:
            # Remove from retry buffer on success
            del self.retry_buffer[entry_id]
            self.logger.info(f"Trade retry successful: {entry_id}")
        else:
            # Schedule next retry if attempts remaining
            if entry.attempts < entry.max_attempts:
                reason_str = entry.reason.value
                retry_delays = self.config["retry_delays"].get(reason_str, [30, 60, 120])
                
                # Use the delay for current attempt (with bounds checking)
                delay_index = min(entry.attempts - 1, len(retry_delays) - 1)
                delay = retry_delays[delay_index]
                
                entry.next_retry = datetime.now() + timedelta(seconds=delay)
                self.logger.info(f"Scheduled retry {entry.attempts}/{entry.max_attempts} for {entry_id} in {delay}s")
            else:
                # Max attempts reached, remove from buffer
                del self.retry_buffer[entry_id]
                self.logger.error(f"Trade retry failed permanently: {entry_id} after {entry.attempts} attempts")
        
        self._save_retry_buffer()
        return True
    
    def should_retry_trade(self, mt5_result: Dict[str, Any]) -> Optional[RetryReason]:
        """Analyze MT5 result and determine if trade should be retried"""
        if not mt5_result.get("success", False):
            error_code = mt5_result.get("error_code", 0)
            error_message = mt5_result.get("error_message", "").lower()
            
            # Check for specific MT5 error conditions
            if "no connection" in error_message or error_code in [6, 4]:
                return RetryReason.MT5_DISCONNECTED
            elif "market is closed" in error_message or error_code == 132:
                return RetryReason.MARKET_CLOSED
            elif "not enough money" in error_message or error_code == 134:
                return RetryReason.INSUFFICIENT_MARGIN
            elif "invalid price" in error_message or error_code in [129, 130]:
                return RetryReason.INVALID_PRICE
            elif "slippage" in error_message:
                return RetryReason.HIGH_SLIPPAGE
            else:
                return RetryReason.UNKNOWN_ERROR
        
        return None
    
    def check_market_conditions(self, symbol: str, current_price: float, spread_pips: float = None) -> Optional[RetryReason]:
        """Check if current market conditions allow trading"""
        # Use integrated spread checker for more sophisticated spread checking
        if spread_checker.config.get('enabled', True):
            spread_check_result, spread_info = spread_checker.check_spread_before_trade(symbol)
            
            if spread_check_result in [SpreadCheckResult.BLOCKED_HIGH_SPREAD, 
                                     SpreadCheckResult.BLOCKED_NO_QUOTES, 
                                     SpreadCheckResult.BLOCKED_STALE_QUOTES]:
                return RetryReason.WIDE_SPREAD
        else:
            # Fallback to original logic if spread checker is disabled
            if spread_pips is not None:
                max_spread = self.config["conditions"]["max_spread_pips"]
                if spread_pips > max_spread:
                    return RetryReason.WIDE_SPREAD
        
        return None
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """Get statistics about retry operations"""
        total_pending = len(self.retry_buffer)
        
        stats_by_reason = {}
        for entry in self.retry_buffer.values():
            reason = entry.reason.value
            if reason not in stats_by_reason:
                stats_by_reason[reason] = {"count": 0, "avg_attempts": 0}
            stats_by_reason[reason]["count"] += 1
            stats_by_reason[reason]["avg_attempts"] += entry.attempts
        
        # Calculate averages
        for reason_stats in stats_by_reason.values():
            if reason_stats["count"] > 0:
                reason_stats["avg_attempts"] = reason_stats["avg_attempts"] / reason_stats["count"]
        
        return {
            "total_pending": total_pending,
            "by_reason": stats_by_reason,
            "config": self.config
        }
    
    def cleanup_expired_retries(self, max_age_hours: int = 24):
        """Remove retry entries older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_ids = []
        
        for entry_id, entry in self.retry_buffer.items():
            if entry.created_at < cutoff_time:
                expired_ids.append(entry_id)
        
        for entry_id in expired_ids:
            del self.retry_buffer[entry_id]
            self.logger.info(f"Removed expired retry entry: {entry_id}")
        
        if expired_ids:
            self._save_retry_buffer()
        
        return len(expired_ids)

# Example usage and testing
if __name__ == "__main__":
    # Initialize retry engine
    retry_engine = RetryEngine()
    
    # Example trade request
    trade_request = TradeRequest(
        signal_id=123,
        symbol="EURUSD",
        action="BUY",
        lot_size=0.01,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1050
    )
    
    # Simulate adding a failed trade
    retry_id = retry_engine.add_failed_trade(
        trade_request,
        RetryReason.MT5_DISCONNECTED,
        "MT5 connection lost"
    )
    
    print(f"Added retry entry: {retry_id}")
    
    # Check pending retries
    pending = retry_engine.get_pending_retries()
    print(f"Pending retries: {len(pending)}")
    
    # Get stats
    stats = retry_engine.get_retry_stats()
    print(f"Retry stats: {json.dumps(stats, indent=2)}")