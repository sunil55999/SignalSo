"""
Signal Conflict Resolver for SignalOS
Detects and resolves conflicts when new signals contradict existing trades or other signals
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
import json
import hashlib


class ConflictType(Enum):
    OPPOSITE_DIRECTION = "opposite_direction"  # BUY vs SELL on same pair
    PROVIDER_CONFLICT = "provider_conflict"    # Different providers, same pair
    TIME_OVERLAP = "time_overlap"             # Signals too close in time
    DUPLICATE_SIGNAL = "duplicate_signal"     # Exact same signal repeated


class ConflictAction(Enum):
    CLOSE_EXISTING = "close_existing"         # Close conflicting trade
    REJECT_NEW = "reject_new"                 # Reject new signal
    WARN_ONLY = "warn_only"                   # Log warning but proceed
    ALLOW_BOTH = "allow_both"                 # Allow both (hedge mode)
    WAIT_AND_RETRY = "wait_and_retry"         # Wait for conflict to resolve


class TradeDirection(Enum):
    BUY = "buy"
    SELL = "sell"
    PENDING_BUY = "pending_buy"
    PENDING_SELL = "pending_sell"


@dataclass
class SignalInfo:
    signal_id: str
    provider_id: str
    symbol: str
    direction: TradeDirection
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    lot_size: float
    timestamp: datetime
    raw_content: str
    confidence: float = 0.0
    tags: List[str] = field(default_factory=list)
    session_id: Optional[str] = None


@dataclass
class ExistingTrade:
    ticket: int
    symbol: str
    direction: TradeDirection
    entry_price: float
    current_price: float
    lot_size: float
    profit: float
    open_time: datetime
    provider_id: Optional[str] = None
    signal_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ConflictDetails:
    conflict_type: ConflictType
    new_signal: SignalInfo
    conflicting_trades: List[ExistingTrade]
    conflicting_signals: List[SignalInfo] = field(default_factory=list)
    resolution_action: Optional[ConflictAction] = None
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConflictResolution:
    action: ConflictAction
    reason: str
    trades_to_close: List[int] = field(default_factory=list)
    signals_to_reject: List[str] = field(default_factory=list)
    notification_message: str = ""
    wait_duration: Optional[timedelta] = None


class SignalConflictResolver:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/conflict_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self.active_signals: Dict[str, SignalInfo] = {}
        self.conflict_history: List[ConflictDetails] = []
        self.pending_resolutions: Dict[str, ConflictResolution] = {}
        
        # Module dependencies (injected)
        self.mt5_bridge = None
        self.parser = None
        self.copilot_bot = None
        self.strategy_runtime = None
        
        self._setup_logging()
        self._load_conflict_history()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get("conflict_resolver", self._create_default_config())
        except FileNotFoundError:
            return self._create_default_config()
        except Exception as e:
            logging.error(f"Error loading conflict resolver config: {e}")
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        return {
            "enabled": True,
            "default_action": "warn_only",
            "hedge_mode": False,
            "provider_priorities": {},
            "symbol_settings": {},
            "time_overlap_threshold_minutes": 5,
            "confidence_threshold": 0.7,
            "max_conflicts_per_hour": 10,
            "auto_close_opposite": False,
            "notification_enabled": True,
            "exception_tags": ["hedge", "scalp", "manual"],
            "conflict_cooldown_minutes": 15
        }

    def _setup_logging(self):
        """Setup logging for conflict resolution"""
        import os
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/conflict_resolver.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _load_conflict_history(self):
        """Load existing conflict history from log file"""
        try:
            with open(self.log_file, 'r') as f:
                history_data = json.load(f)
                for item in history_data:
                    # Convert dict back to ConflictDetails (simplified)
                    conflict = ConflictDetails(
                        conflict_type=ConflictType(item.get("conflict_type")),
                        new_signal=SignalInfo(**item.get("new_signal", {})),
                        conflicting_trades=[],  # Simplified for persistence
                        reason=item.get("reason", ""),
                        timestamp=datetime.fromisoformat(item.get("timestamp"))
                    )
                    self.conflict_history.append(conflict)
        except FileNotFoundError:
            self.conflict_history = []
        except Exception as e:
            self.logger.error(f"Error loading conflict history: {e}")
            self.conflict_history = []

    def _save_conflict_history(self):
        """Save conflict history to log file"""
        try:
            history_data = []
            for conflict in self.conflict_history[-100:]:  # Keep last 100 conflicts
                history_data.append({
                    "conflict_type": conflict.conflict_type.value,
                    "new_signal": {
                        "signal_id": conflict.new_signal.signal_id,
                        "provider_id": conflict.new_signal.provider_id,
                        "symbol": conflict.new_signal.symbol,
                        "direction": conflict.new_signal.direction.value,
                        "timestamp": conflict.new_signal.timestamp.isoformat()
                    },
                    "reason": conflict.reason,
                    "timestamp": conflict.timestamp.isoformat(),
                    "resolution_action": conflict.resolution_action.value if conflict.resolution_action else None
                })
            
            with open(self.log_file, 'w') as f:
                json.dump(history_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving conflict history: {e}")

    def inject_modules(self, mt5_bridge=None, parser=None, copilot_bot=None, strategy_runtime=None):
        """Inject module references for conflict resolution operations"""
        self.mt5_bridge = mt5_bridge
        self.parser = parser
        self.copilot_bot = copilot_bot
        self.strategy_runtime = strategy_runtime
        self.logger.info("Conflict resolver modules injected")

    def register_signal(self, signal: SignalInfo) -> bool:
        """Register a new signal for conflict detection"""
        if not self.config.get("enabled", True):
            return True  # Conflict resolution disabled
        
        # Check for exception tags
        if any(tag in signal.tags for tag in self.config.get("exception_tags", [])):
            self.logger.info(f"Signal {signal.signal_id} has exception tag, skipping conflict check")
            return True
        
        self.active_signals[signal.signal_id] = signal
        self.logger.info(f"Registered signal {signal.signal_id} for conflict detection")
        return True

    async def check_signal_conflicts(self, new_signal: SignalInfo) -> Optional[ConflictDetails]:
        """Check if new signal conflicts with existing trades or signals"""
        if not self.config.get("enabled", True):
            return None
        
        conflicts = ConflictDetails(
            conflict_type=ConflictType.OPPOSITE_DIRECTION,  # Default, will be updated
            new_signal=new_signal,
            conflicting_trades=[],
            conflicting_signals=[]
        )
        
        # Get existing trades for the symbol
        existing_trades = await self._get_existing_trades(new_signal.symbol)
        
        # Check for direction conflicts
        direction_conflicts = self._check_direction_conflicts(new_signal, existing_trades)
        if direction_conflicts:
            conflicts.conflicting_trades.extend(direction_conflicts)
            conflicts.conflict_type = ConflictType.OPPOSITE_DIRECTION
            conflicts.reason = f"Opposite direction trade detected: {new_signal.direction.value} vs existing trades"
        
        # Check for provider conflicts
        provider_conflicts = self._check_provider_conflicts(new_signal, existing_trades)
        if provider_conflicts:
            conflicts.conflicting_trades.extend(provider_conflicts)
            if conflicts.conflict_type == ConflictType.OPPOSITE_DIRECTION:
                conflicts.conflict_type = ConflictType.PROVIDER_CONFLICT
            conflicts.reason += f" | Provider conflict with {len(provider_conflicts)} trades"
        
        # Check for time overlap conflicts
        time_conflicts = self._check_time_overlap_conflicts(new_signal)
        if time_conflicts:
            conflicts.conflicting_signals.extend(time_conflicts)
            conflicts.conflict_type = ConflictType.TIME_OVERLAP
            conflicts.reason += f" | Time overlap with {len(time_conflicts)} recent signals"
        
        # Check for duplicate signals
        duplicate_conflicts = self._check_duplicate_signals(new_signal)
        if duplicate_conflicts:
            conflicts.conflicting_signals.extend(duplicate_conflicts)
            conflicts.conflict_type = ConflictType.DUPLICATE_SIGNAL
            conflicts.reason = f"Duplicate signal detected: {duplicate_conflicts[0].signal_id}"
        
        if conflicts.conflicting_trades or conflicts.conflicting_signals:
            self.conflict_history.append(conflicts)
            self._save_conflict_history()
            return conflicts
        
        return None

    def _check_direction_conflicts(self, new_signal: SignalInfo, existing_trades: List[ExistingTrade]) -> List[ExistingTrade]:
        """Check for opposite direction conflicts"""
        if self.config.get("hedge_mode", False):
            return []  # Hedge mode allows opposite directions
        
        conflicts = []
        new_direction = new_signal.direction
        
        for trade in existing_trades:
            if self._is_opposite_direction(new_direction, trade.direction):
                conflicts.append(trade)
        
        return conflicts

    def _check_provider_conflicts(self, new_signal: SignalInfo, existing_trades: List[ExistingTrade]) -> List[ExistingTrade]:
        """Check for provider-specific conflicts"""
        conflicts = []
        provider_settings = self.config.get("provider_settings", {})
        
        for trade in existing_trades:
            if trade.provider_id and trade.provider_id != new_signal.provider_id:
                # Check if providers are configured to conflict
                if self._providers_conflict(new_signal.provider_id, trade.provider_id):
                    conflicts.append(trade)
        
        return conflicts

    def _check_time_overlap_conflicts(self, new_signal: SignalInfo) -> List[SignalInfo]:
        """Check for signals that are too close in time"""
        conflicts = []
        threshold = timedelta(minutes=self.config.get("time_overlap_threshold_minutes", 5))
        
        for signal_id, signal in self.active_signals.items():
            if (signal.symbol == new_signal.symbol and 
                signal.provider_id == new_signal.provider_id and
                abs((new_signal.timestamp - signal.timestamp).total_seconds()) < threshold.total_seconds()):
                conflicts.append(signal)
        
        return conflicts

    def _check_duplicate_signals(self, new_signal: SignalInfo) -> List[SignalInfo]:
        """Check for exact duplicate signals"""
        conflicts = []
        new_hash = self._calculate_signal_hash(new_signal)
        
        for signal_id, signal in self.active_signals.items():
            if self._calculate_signal_hash(signal) == new_hash:
                conflicts.append(signal)
        
        return conflicts

    def _is_opposite_direction(self, dir1: TradeDirection, dir2: TradeDirection) -> bool:
        """Check if two directions are opposite"""
        opposite_pairs = [
            (TradeDirection.BUY, TradeDirection.SELL),
            (TradeDirection.SELL, TradeDirection.BUY),
            (TradeDirection.PENDING_BUY, TradeDirection.PENDING_SELL),
            (TradeDirection.PENDING_SELL, TradeDirection.PENDING_BUY)
        ]
        return (dir1, dir2) in opposite_pairs or (dir2, dir1) in opposite_pairs

    def _providers_conflict(self, provider1: str, provider2: str) -> bool:
        """Check if two providers are configured to conflict"""
        provider_settings = self.config.get("provider_settings", {})
        conflicts = provider_settings.get("conflicts", [])
        
        for conflict_pair in conflicts:
            if (provider1 in conflict_pair and provider2 in conflict_pair):
                return True
        return False

    def _calculate_signal_hash(self, signal: SignalInfo) -> str:
        """Calculate hash for signal deduplication"""
        content = f"{signal.symbol}_{signal.direction.value}_{signal.entry_price}_{signal.provider_id}"
        return hashlib.md5(content.encode()).hexdigest()

    async def resolve_conflict(self, conflict: ConflictDetails) -> ConflictResolution:
        """Resolve detected conflict based on configuration"""
        action = self._determine_resolution_action(conflict)
        resolution = ConflictResolution(action=action, reason="")
        
        if action == ConflictAction.CLOSE_EXISTING:
            resolution.trades_to_close = [trade.ticket for trade in conflict.conflicting_trades]
            resolution.reason = f"Closing {len(resolution.trades_to_close)} conflicting trades"
            resolution.notification_message = f"🔄 Conflict resolved: Closed {len(resolution.trades_to_close)} opposite trades for {conflict.new_signal.symbol}"
            
            # Execute trade closures
            for ticket in resolution.trades_to_close:
                success = await self._close_trade(ticket, "Conflict resolution")
                if not success:
                    self.logger.error(f"Failed to close trade {ticket} for conflict resolution")
        
        elif action == ConflictAction.REJECT_NEW:
            resolution.signals_to_reject = [conflict.new_signal.signal_id]
            resolution.reason = f"Rejecting new signal due to conflict"
            resolution.notification_message = f"⚠️ Signal rejected: {conflict.new_signal.symbol} conflicts with existing trade"
        
        elif action == ConflictAction.WARN_ONLY:
            resolution.reason = f"Warning logged, proceeding with signal"
            resolution.notification_message = f"⚠️ Conflict warning: {conflict.new_signal.symbol} may conflict with existing positions"
        
        elif action == ConflictAction.ALLOW_BOTH:
            resolution.reason = f"Hedge mode: allowing both positions"
            resolution.notification_message = f"🔀 Hedge position: {conflict.new_signal.symbol} opened opposite to existing trade"
        
        elif action == ConflictAction.WAIT_AND_RETRY:
            resolution.wait_duration = timedelta(minutes=self.config.get("conflict_cooldown_minutes", 15))
            resolution.reason = f"Waiting {resolution.wait_duration.total_seconds()/60} minutes for conflict to resolve"
            resolution.notification_message = f"⏱️ Signal delayed: {conflict.new_signal.symbol} waiting for conflict resolution"
        
        # Update conflict with resolution
        conflict.resolution_action = action
        
        # Send notification if enabled
        if self.config.get("notification_enabled", True) and resolution.notification_message:
            await self._send_conflict_notification(resolution.notification_message, conflict)
        
        # Log resolution
        self.logger.info(f"Conflict resolved: {action.value} - {resolution.reason}")
        
        return resolution

    def _determine_resolution_action(self, conflict: ConflictDetails) -> ConflictAction:
        """Determine the appropriate resolution action"""
        # Check for hedge mode
        if self.config.get("hedge_mode", False):
            return ConflictAction.ALLOW_BOTH
        
        # Check symbol-specific settings
        symbol_settings = self.config.get("symbol_settings", {}).get(conflict.new_signal.symbol, {})
        if "conflict_action" in symbol_settings:
            return ConflictAction(symbol_settings["conflict_action"])
        
        # Check provider priorities
        if conflict.conflicting_trades:
            new_priority = self._get_provider_priority(conflict.new_signal.provider_id)
            for trade in conflict.conflicting_trades:
                existing_priority = self._get_provider_priority(trade.provider_id or "unknown")
                if new_priority > existing_priority:
                    return ConflictAction.CLOSE_EXISTING
                elif existing_priority > new_priority:
                    return ConflictAction.REJECT_NEW
        
        # Check confidence levels
        if conflict.new_signal.confidence >= self.config.get("confidence_threshold", 0.7):
            if self.config.get("auto_close_opposite", False):
                return ConflictAction.CLOSE_EXISTING
        
        # Default action
        default_action = self.config.get("default_action", "warn_only")
        return ConflictAction(default_action)

    def _get_provider_priority(self, provider_id: str) -> int:
        """Get priority for provider (higher = more important)"""
        priorities = self.config.get("provider_priorities", {})
        return priorities.get(provider_id, 0)

    async def _get_existing_trades(self, symbol: str) -> List[ExistingTrade]:
        """Get existing trades for symbol from MT5"""
        if not self.mt5_bridge:
            return []
        
        try:
            # This would call the actual MT5 bridge method
            trades_data = getattr(self.mt5_bridge, 'get_open_trades', lambda x: [])(symbol)
            
            trades = []
            for trade_data in trades_data:
                trade = ExistingTrade(
                    ticket=trade_data.get('ticket'),
                    symbol=trade_data.get('symbol'),
                    direction=TradeDirection(trade_data.get('type', 'buy')),
                    entry_price=trade_data.get('entry_price', 0.0),
                    current_price=trade_data.get('current_price', 0.0),
                    lot_size=trade_data.get('lot_size', 0.0),
                    profit=trade_data.get('profit', 0.0),
                    open_time=datetime.fromisoformat(trade_data.get('open_time', datetime.now().isoformat())),
                    provider_id=trade_data.get('provider_id'),
                    signal_id=trade_data.get('signal_id')
                )
                trades.append(trade)
            
            return trades
        except Exception as e:
            self.logger.error(f"Error getting existing trades: {e}")
            return []

    async def _close_trade(self, ticket: int, reason: str) -> bool:
        """Close trade via MT5 bridge"""
        if not self.mt5_bridge:
            self.logger.warning(f"MT5 bridge not available, cannot close trade {ticket}")
            return False
        
        try:
            # This would call the actual MT5 bridge method
            close_method = getattr(self.mt5_bridge, 'close_position', None)
            if close_method:
                result = await close_method(ticket, reason)
                self.logger.info(f"Trade {ticket} closed: {result}")
                return result.get('success', False) if isinstance(result, dict) else bool(result)
            else:
                self.logger.warning(f"MT5 bridge missing close_position method")
                return False
        except Exception as e:
            self.logger.error(f"Error closing trade {ticket}: {e}")
            return False

    async def _send_conflict_notification(self, message: str, conflict: ConflictDetails):
        """Send conflict notification via Copilot Bot"""
        if not self.copilot_bot:
            return
        
        try:
            notification_method = getattr(self.copilot_bot, 'send_alert', None)
            if notification_method:
                detailed_message = f"{message}\n\nDetails:\n"
                detailed_message += f"Symbol: {conflict.new_signal.symbol}\n"
                detailed_message += f"New Signal: {conflict.new_signal.direction.value}\n"
                detailed_message += f"Conflicting Trades: {len(conflict.conflicting_trades)}\n"
                detailed_message += f"Conflict Type: {conflict.conflict_type.value}\n"
                detailed_message += f"Resolution: {conflict.resolution_action.value if conflict.resolution_action else 'pending'}"
                
                await notification_method(detailed_message)
        except Exception as e:
            self.logger.error(f"Error sending conflict notification: {e}")

    async def process_signal_with_conflict_check(self, signal: SignalInfo) -> Tuple[bool, Optional[ConflictResolution]]:
        """Process signal with full conflict checking and resolution"""
        self.register_signal(signal)
        
        # Check for conflicts
        conflict = await self.check_signal_conflicts(signal)
        
        if conflict:
            # Resolve conflict
            resolution = await self.resolve_conflict(conflict)
            
            # Determine if signal should proceed
            proceed = resolution.action in [ConflictAction.WARN_ONLY, ConflictAction.ALLOW_BOTH]
            if resolution.action == ConflictAction.CLOSE_EXISTING:
                proceed = True  # Proceed after closing conflicting trades
            elif resolution.action == ConflictAction.WAIT_AND_RETRY:
                # Schedule retry (simplified)
                proceed = False
            
            return proceed, resolution
        
        return True, None  # No conflict, proceed normally

    def get_conflict_statistics(self) -> Dict[str, Any]:
        """Get statistics about conflict resolution"""
        total_conflicts = len(self.conflict_history)
        
        # Count by type
        type_counts = {}
        action_counts = {}
        recent_conflicts = 0
        recent_threshold = datetime.now() - timedelta(hours=24)
        
        for conflict in self.conflict_history:
            type_counts[conflict.conflict_type.value] = type_counts.get(conflict.conflict_type.value, 0) + 1
            if conflict.resolution_action:
                action_counts[conflict.resolution_action.value] = action_counts.get(conflict.resolution_action.value, 0) + 1
            if conflict.timestamp >= recent_threshold:
                recent_conflicts += 1
        
        return {
            "total_conflicts": total_conflicts,
            "recent_24h": recent_conflicts,
            "by_type": type_counts,
            "by_resolution": action_counts,
            "config": {
                "enabled": self.config.get("enabled", True),
                "hedge_mode": self.config.get("hedge_mode", False),
                "default_action": self.config.get("default_action", "warn_only")
            }
        }

    def get_active_signals(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active signals"""
        return {
            signal_id: {
                "symbol": signal.symbol,
                "direction": signal.direction.value,
                "provider": signal.provider_id,
                "timestamp": signal.timestamp.isoformat(),
                "confidence": signal.confidence
            }
            for signal_id, signal in self.active_signals.items()
        }

    def clear_old_signals(self, max_age_hours: int = 24):
        """Clear old signals from active tracking"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        signals_to_remove = [
            signal_id for signal_id, signal in self.active_signals.items()
            if signal.timestamp < cutoff_time
        ]
        
        for signal_id in signals_to_remove:
            del self.active_signals[signal_id]
        
        if signals_to_remove:
            self.logger.info(f"Cleared {len(signals_to_remove)} old signals from tracking")

    def update_config(self, new_config: Dict[str, Any]):
        """Update conflict resolver configuration"""
        self.config.update(new_config)
        try:
            # Save updated config
            with open(self.config_file, 'r') as f:
                full_config = json.load(f)
            full_config["conflict_resolver"] = self.config
            with open(self.config_file, 'w') as f:
                json.dump(full_config, f, indent=2)
            self.logger.info("Conflict resolver configuration updated")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")


async def main():
    """Example usage of Signal Conflict Resolver"""
    resolver = SignalConflictResolver()
    
    # Example signal
    signal = SignalInfo(
        signal_id="signal_001",
        provider_id="provider_a",
        symbol="EURUSD",
        direction=TradeDirection.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        lot_size=0.1,
        timestamp=datetime.now(),
        raw_content="BUY EURUSD @ 1.1000",
        confidence=0.8
    )
    
    # Process signal with conflict checking
    proceed, resolution = await resolver.process_signal_with_conflict_check(signal)
    
    print(f"Signal processing: {'Proceed' if proceed else 'Blocked'}")
    if resolution:
        print(f"Resolution: {resolution.action.value} - {resolution.reason}")
    
    # Show statistics
    stats = resolver.get_conflict_statistics()
    print(f"Conflict statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(main())