"""
Multi-Signal Handler Engine for SignalOS
Handles multiple concurrent signals for the same symbol with prioritization, merging, and conflict resolution
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
import hashlib

class SignalPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SignalStatus(Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    EXPIRED = "expired"
    MERGED = "merged"
    CONFLICTED = "conflicted"
    REJECTED = "rejected"

class ConflictResolution(Enum):
    HIGHEST_PRIORITY = "highest_priority"
    HIGHEST_CONFIDENCE = "highest_confidence"
    MOST_RECENT = "most_recent"
    PROVIDER_WEIGHT = "provider_weight"
    SIGNAL_AVERAGE = "signal_average"
    REJECT_ALL = "reject_all"

class SignalDirection(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass
class IncomingSignal:
    signal_id: str
    symbol: str
    direction: SignalDirection
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    volume: Optional[float]
    confidence: float
    provider_id: str
    provider_name: str
    priority: SignalPriority
    timestamp: datetime
    expiry_time: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.expiry_time is None:
            # Default expiry: 30 minutes
            self.expiry_time = self.timestamp + timedelta(minutes=30)

@dataclass
class ProcessedSignal:
    original_signals: List[IncomingSignal]
    final_signal: IncomingSignal
    status: SignalStatus
    processing_reason: str
    conflicts_resolved: List[str]
    merged_signals: List[str]
    processing_time: datetime
    execution_priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_ids": [sig.signal_id for sig in self.original_signals],
            "final_signal_id": self.final_signal.signal_id,
            "symbol": self.final_signal.symbol,
            "direction": self.final_signal.direction.value,
            "status": self.status.value,
            "processing_reason": self.processing_reason,
            "conflicts_resolved": self.conflicts_resolved,
            "merged_signals": self.merged_signals,
            "processing_time": self.processing_time.isoformat(),
            "execution_priority": self.execution_priority
        }

@dataclass
class ProviderProfile:
    provider_id: str
    provider_name: str
    weight: float = 1.0
    success_rate: float = 0.5
    avg_confidence: float = 0.5
    signal_count: int = 0
    last_signal_time: Optional[datetime] = None
    reputation_score: float = 0.5

@dataclass
class ConflictGroup:
    symbol: str
    signals: List[IncomingSignal]
    conflict_type: str
    identified_time: datetime
    resolution_method: ConflictResolution
    resolved: bool = False
    resolution_result: Optional[ProcessedSignal] = None

class MultiSignalHandler:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/multi_signal_handler.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Signal processing
        self.pending_signals: Dict[str, List[IncomingSignal]] = {}  # symbol -> signals
        self.processed_signals: List[ProcessedSignal] = []
        self.conflict_groups: List[ConflictGroup] = []
        
        # Provider management
        self.provider_profiles: Dict[str, ProviderProfile] = {}
        
        # Processing statistics
        self.processing_stats = {
            "total_signals": 0,
            "processed_signals": 0,
            "merged_signals": 0,
            "conflicted_signals": 0,
            "expired_signals": 0,
            "rejected_signals": 0
        }
        
        # Background processing
        self.processing_task = None
        self.is_processing = False
        
        # Load existing data
        self._load_signal_data()
        self._load_provider_profiles()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load multi-signal handler configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "multi_signal_handler" not in config:
                config["multi_signal_handler"] = {
                    "enabled": True,
                    "processing_interval": 2.0,
                    "signal_expiry_minutes": 30,
                    "max_signals_per_symbol": 10,
                    "conflict_resolution_method": "highest_priority",
                    "enable_signal_merging": True,
                    "merge_tolerance_pips": 5.0,
                    "confidence_threshold": 0.3,
                    "provider_weights": {
                        "premium_provider": 2.0,
                        "standard_provider": 1.0,
                        "trial_provider": 0.5
                    },
                    "priority_mappings": {
                        "vip_provider": "critical",
                        "premium_provider": "high",
                        "standard_provider": "medium",
                        "trial_provider": "low"
                    },
                    "symbol_settings": {
                        "EURUSD": {
                            "max_concurrent_signals": 5,
                            "merge_tolerance_pips": 3.0,
                            "priority_boost": 0.1
                        },
                        "XAUUSD": {
                            "max_concurrent_signals": 3,
                            "merge_tolerance_pips": 20.0,
                            "priority_boost": 0.2
                        }
                    }
                }
                self._save_config(config)
                
            return config.get("multi_signal_handler", {})
            
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
            "processing_interval": 2.0,
            "signal_expiry_minutes": 30,
            "max_signals_per_symbol": 10,
            "conflict_resolution_method": "highest_priority",
            "enable_signal_merging": True,
            "merge_tolerance_pips": 5.0,
            "confidence_threshold": 0.3,
            "provider_weights": {},
            "priority_mappings": {},
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
        """Setup dedicated logger for multi-signal handler"""
        logger = logging.getLogger("multi_signal_handler")
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
        
    def _load_signal_data(self):
        """Load existing signal data from storage"""
        signal_file = self.log_path.replace('.log', '_signals.json')
        try:
            if os.path.exists(signal_file):
                with open(signal_file, 'r') as f:
                    signal_data = json.load(f)
                    
                # Load processing statistics
                if 'statistics' in signal_data:
                    self.processing_stats.update(signal_data['statistics'])
                    
                self.logger.info(f"Loaded signal processing data from storage")
                
        except Exception as e:
            self.logger.error(f"Error loading signal data: {e}")
            
    def _save_signal_data(self):
        """Save signal data to storage"""
        signal_file = self.log_path.replace('.log', '_signals.json')
        try:
            signal_data = {
                'statistics': self.processing_stats,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(signal_file, 'w') as f:
                json.dump(signal_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error saving signal data: {e}")
            
    def _load_provider_profiles(self):
        """Load provider profiles from storage"""
        provider_file = self.log_path.replace('.log', '_providers.json')
        try:
            if os.path.exists(provider_file):
                with open(provider_file, 'r') as f:
                    provider_data = json.load(f)
                    
                for provider_id, data in provider_data.get('providers', {}).items():
                    profile = ProviderProfile(
                        provider_id=provider_id,
                        provider_name=data.get('provider_name', provider_id),
                        weight=data.get('weight', 1.0),
                        success_rate=data.get('success_rate', 0.5),
                        avg_confidence=data.get('avg_confidence', 0.5),
                        signal_count=data.get('signal_count', 0),
                        last_signal_time=datetime.fromisoformat(data['last_signal_time']) if data.get('last_signal_time') else None,
                        reputation_score=data.get('reputation_score', 0.5)
                    )
                    self.provider_profiles[provider_id] = profile
                    
                self.logger.info(f"Loaded {len(self.provider_profiles)} provider profiles")
                
        except Exception as e:
            self.logger.error(f"Error loading provider profiles: {e}")
            
    def _save_provider_profiles(self):
        """Save provider profiles to storage"""
        provider_file = self.log_path.replace('.log', '_providers.json')
        try:
            provider_data = {
                'providers': {
                    provider_id: {
                        'provider_name': profile.provider_name,
                        'weight': profile.weight,
                        'success_rate': profile.success_rate,
                        'avg_confidence': profile.avg_confidence,
                        'signal_count': profile.signal_count,
                        'last_signal_time': profile.last_signal_time.isoformat() if profile.last_signal_time else None,
                        'reputation_score': profile.reputation_score
                    }
                    for provider_id, profile in self.provider_profiles.items()
                },
                'last_updated': datetime.now().isoformat()
            }
            
            with open(provider_file, 'w') as f:
                json.dump(provider_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error saving provider profiles: {e}")
            
    def _get_provider_weight(self, provider_id: str) -> float:
        """Get provider weight from configuration or profile"""
        # Check configuration first
        provider_weights = self.config.get("provider_weights", {})
        if provider_id in provider_weights:
            return provider_weights[provider_id]
            
        # Check provider profile
        if provider_id in self.provider_profiles:
            return self.provider_profiles[provider_id].weight
            
        return 1.0  # Default weight
        
    def _get_signal_priority(self, provider_id: str, confidence: float) -> SignalPriority:
        """Determine signal priority based on provider and confidence"""
        # Check configuration mapping
        priority_mappings = self.config.get("priority_mappings", {})
        if provider_id in priority_mappings:
            priority_str = priority_mappings[provider_id]
            try:
                return SignalPriority(priority_str)
            except ValueError:
                pass
                
        # Determine based on confidence and provider reputation
        provider_weight = self._get_provider_weight(provider_id)
        weighted_confidence = confidence * provider_weight
        
        if weighted_confidence >= 0.8:
            return SignalPriority.CRITICAL
        elif weighted_confidence >= 0.6:
            return SignalPriority.HIGH
        elif weighted_confidence >= 0.4:
            return SignalPriority.MEDIUM
        else:
            return SignalPriority.LOW
            
    def _update_provider_profile(self, signal: IncomingSignal):
        """Update provider profile with new signal data"""
        provider_id = signal.provider_id
        
        if provider_id not in self.provider_profiles:
            self.provider_profiles[provider_id] = ProviderProfile(
                provider_id=provider_id,
                provider_name=signal.provider_name
            )
            
        profile = self.provider_profiles[provider_id]
        profile.signal_count += 1
        profile.last_signal_time = signal.timestamp
        
        # Update average confidence
        if profile.signal_count == 1:
            profile.avg_confidence = signal.confidence
        else:
            # Running average
            profile.avg_confidence = (profile.avg_confidence * (profile.signal_count - 1) + signal.confidence) / profile.signal_count
            
        # Update reputation score (simplified calculation)
        provider_weight = self._get_provider_weight(provider_id)
        profile.reputation_score = min(1.0, (profile.avg_confidence * provider_weight + profile.success_rate) / 2)
        
    def _calculate_signal_score(self, signal: IncomingSignal) -> float:
        """Calculate overall signal score for prioritization"""
        base_score = signal.confidence
        
        # Provider weight multiplier
        provider_weight = self._get_provider_weight(signal.provider_id)
        weighted_score = base_score * provider_weight
        
        # Priority bonus
        priority_bonus = {
            SignalPriority.CRITICAL: 0.3,
            SignalPriority.HIGH: 0.2,
            SignalPriority.MEDIUM: 0.1,
            SignalPriority.LOW: 0.0
        }.get(signal.priority, 0.0)
        
        # Time decay (newer signals get slight bonus)
        age_minutes = (datetime.now() - signal.timestamp).total_seconds() / 60
        time_bonus = max(0, (30 - age_minutes) / 30 * 0.1)  # Max 0.1 bonus for fresh signals
        
        # Symbol-specific boost
        symbol_settings = self.config.get("symbol_settings", {}).get(signal.symbol, {})
        priority_boost = symbol_settings.get("priority_boost", 0.0)
        
        final_score = weighted_score + priority_bonus + time_bonus + priority_boost
        return min(1.0, final_score)  # Cap at 1.0
        
    def _check_signal_compatibility(self, signal1: IncomingSignal, signal2: IncomingSignal) -> bool:
        """Check if two signals are compatible for merging"""
        if signal1.symbol != signal2.symbol:
            return False
            
        if signal1.direction != signal2.direction:
            return False
            
        # Check price compatibility
        if signal1.entry_price and signal2.entry_price:
            symbol_settings = self.config.get("symbol_settings", {}).get(signal1.symbol, {})
            tolerance_pips = symbol_settings.get("merge_tolerance_pips", self.config.get("merge_tolerance_pips", 5.0))
            
            # Convert pips to price difference (simplified)
            pip_values = {
                "EURUSD": 0.00001, "GBPUSD": 0.00001, "AUDUSD": 0.00001,
                "USDJPY": 0.001, "EURJPY": 0.001, "GBPJPY": 0.001,
                "XAUUSD": 0.01, "BTCUSD": 1.0
            }
            pip_value = pip_values.get(signal1.symbol, 0.00001)
            tolerance_price = tolerance_pips * pip_value
            
            price_diff = abs(signal1.entry_price - signal2.entry_price)
            if price_diff > tolerance_price:
                return False
                
        return True
        
    def _merge_compatible_signals(self, signals: List[IncomingSignal]) -> IncomingSignal:
        """Merge compatible signals into a single signal"""
        if len(signals) == 1:
            return signals[0]
            
        # Sort by signal score (highest first)
        sorted_signals = sorted(signals, key=self._calculate_signal_score, reverse=True)
        primary_signal = sorted_signals[0]
        
        # Create merged signal based on primary signal
        merged_signal = IncomingSignal(
            signal_id=f"merged_{primary_signal.signal_id}_{int(datetime.now().timestamp())}",
            symbol=primary_signal.symbol,
            direction=primary_signal.direction,
            entry_price=primary_signal.entry_price,
            stop_loss=primary_signal.stop_loss,
            take_profit=primary_signal.take_profit,
            volume=primary_signal.volume,
            confidence=primary_signal.confidence,
            provider_id=f"merged_{len(signals)}providers",
            provider_name=f"Merged from {len(signals)} providers",
            priority=primary_signal.priority,
            timestamp=datetime.now(),
            metadata={
                "merged_from": [sig.signal_id for sig in signals],
                "merge_reason": "compatible_signals",
                "primary_signal": primary_signal.signal_id
            }
        )
        
        # Average out compatible numeric values
        if all(sig.entry_price for sig in signals):
            total_weight = sum(self._calculate_signal_score(sig) for sig in signals)
            weighted_entry = sum(sig.entry_price * self._calculate_signal_score(sig) for sig in signals) / total_weight
            merged_signal.entry_price = weighted_entry
            
        # Use highest confidence
        merged_signal.confidence = max(sig.confidence for sig in signals)
        
        # Use highest priority
        priority_order = [SignalPriority.CRITICAL, SignalPriority.HIGH, SignalPriority.MEDIUM, SignalPriority.LOW]
        for priority in priority_order:
            if any(sig.priority == priority for sig in signals):
                merged_signal.priority = priority
                break
                
        return merged_signal
        
    def _identify_conflicts(self, signals: List[IncomingSignal]) -> List[ConflictGroup]:
        """Identify conflicts among signals for the same symbol"""
        conflicts = []
        
        if len(signals) < 2:
            return conflicts
            
        # Group signals by direction
        buy_signals = [sig for sig in signals if sig.direction == SignalDirection.BUY]
        sell_signals = [sig for sig in signals if sig.direction == SignalDirection.SELL]
        
        # Directional conflict
        if buy_signals and sell_signals:
            conflict = ConflictGroup(
                symbol=signals[0].symbol,
                signals=buy_signals + sell_signals,
                conflict_type="directional_conflict",
                identified_time=datetime.now(),
                resolution_method=ConflictResolution(self.config.get("conflict_resolution_method", "highest_priority"))
            )
            conflicts.append(conflict)
            
        # Entry price conflicts within same direction
        for direction_signals in [buy_signals, sell_signals]:
            if len(direction_signals) > 1:
                # Check for significant entry price differences
                entry_prices = [sig.entry_price for sig in direction_signals if sig.entry_price]
                if len(entry_prices) > 1:
                    price_range = max(entry_prices) - min(entry_prices)
                    symbol_settings = self.config.get("symbol_settings", {}).get(signals[0].symbol, {})
                    tolerance_pips = symbol_settings.get("merge_tolerance_pips", self.config.get("merge_tolerance_pips", 5.0))
                    
                    # Simplified pip calculation
                    pip_value = 0.00001 if "JPY" not in signals[0].symbol else 0.001
                    tolerance_price = tolerance_pips * pip_value
                    
                    if price_range > tolerance_price * 2:  # Significant difference
                        conflict = ConflictGroup(
                            symbol=signals[0].symbol,
                            signals=direction_signals,
                            conflict_type="entry_price_conflict",
                            identified_time=datetime.now(),
                            resolution_method=ConflictResolution(self.config.get("conflict_resolution_method", "highest_priority"))
                        )
                        conflicts.append(conflict)
                        
        return conflicts
        
    def _resolve_conflict(self, conflict: ConflictGroup) -> ProcessedSignal:
        """Resolve a signal conflict using configured method"""
        signals = conflict.signals
        method = conflict.resolution_method
        
        resolved_signal = None
        resolution_reason = ""
        
        if method == ConflictResolution.HIGHEST_PRIORITY:
            # Sort by priority then by score
            priority_order = [SignalPriority.CRITICAL, SignalPriority.HIGH, SignalPriority.MEDIUM, SignalPriority.LOW]
            sorted_signals = sorted(signals, key=lambda sig: (priority_order.index(sig.priority), -self._calculate_signal_score(sig)))
            resolved_signal = sorted_signals[0]
            resolution_reason = f"Highest priority: {resolved_signal.priority.value}"
            
        elif method == ConflictResolution.HIGHEST_CONFIDENCE:
            resolved_signal = max(signals, key=lambda sig: sig.confidence)
            resolution_reason = f"Highest confidence: {resolved_signal.confidence:.2f}"
            
        elif method == ConflictResolution.MOST_RECENT:
            resolved_signal = max(signals, key=lambda sig: sig.timestamp)
            resolution_reason = "Most recent signal"
            
        elif method == ConflictResolution.PROVIDER_WEIGHT:
            resolved_signal = max(signals, key=lambda sig: self._get_provider_weight(sig.provider_id))
            resolution_reason = f"Highest provider weight: {self._get_provider_weight(resolved_signal.provider_id)}"
            
        elif method == ConflictResolution.SIGNAL_AVERAGE:
            # Create averaged signal (for compatible conflicts)
            if conflict.conflict_type != "directional_conflict":
                resolved_signal = self._merge_compatible_signals(signals)
                resolution_reason = "Signal averaging applied"
            else:
                # Fall back to highest priority for directional conflicts
                priority_order = [SignalPriority.CRITICAL, SignalPriority.HIGH, SignalPriority.MEDIUM, SignalPriority.LOW]
                sorted_signals = sorted(signals, key=lambda sig: (priority_order.index(sig.priority), -self._calculate_signal_score(sig)))
                resolved_signal = sorted_signals[0]
                resolution_reason = "Highest priority (directional conflict)"
                
        else:  # REJECT_ALL
            resolution_reason = "All signals rejected due to conflict"
            
        # Create processed signal result
        if resolved_signal:
            processed = ProcessedSignal(
                original_signals=signals,
                final_signal=resolved_signal,
                status=SignalStatus.PROCESSED,
                processing_reason=resolution_reason,
                conflicts_resolved=[conflict.conflict_type],
                merged_signals=[],
                processing_time=datetime.now(),
                execution_priority=self._calculate_signal_score(resolved_signal)
            )
        else:
            # Create a dummy rejected signal
            rejected_signal = signals[0]  # Use first signal as base
            rejected_signal.signal_id = f"rejected_{rejected_signal.signal_id}"
            
            processed = ProcessedSignal(
                original_signals=signals,
                final_signal=rejected_signal,
                status=SignalStatus.REJECTED,
                processing_reason=resolution_reason,
                conflicts_resolved=[conflict.conflict_type],
                merged_signals=[],
                processing_time=datetime.now(),
                execution_priority=0
            )
            
        conflict.resolved = True
        conflict.resolution_result = processed
        
        return processed
        
    def add_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Add a new signal for processing"""
        try:
            if not self.config.get("enabled", True):
                return False
                
            # Create signal object
            signal = IncomingSignal(
                signal_id=signal_data.get("signal_id", f"sig_{int(datetime.now().timestamp())}"),
                symbol=signal_data.get("symbol", ""),
                direction=SignalDirection(signal_data.get("direction", "buy")),
                entry_price=signal_data.get("entry_price"),
                stop_loss=signal_data.get("stop_loss"),
                take_profit=signal_data.get("take_profit"),
                volume=signal_data.get("volume"),
                confidence=signal_data.get("confidence", 0.5),
                provider_id=signal_data.get("provider_id", "unknown"),
                provider_name=signal_data.get("provider_name", "Unknown Provider"),
                priority=self._get_signal_priority(signal_data.get("provider_id", "unknown"), signal_data.get("confidence", 0.5)),
                timestamp=datetime.now(),
                metadata=signal_data.get("metadata", {})
            )
            
            # Check confidence threshold
            if signal.confidence < self.config.get("confidence_threshold", 0.3):
                self.logger.info(f"Signal {signal.signal_id} rejected: confidence below threshold")
                self.processing_stats["rejected_signals"] += 1
                return False
                
            # Add to pending signals
            if signal.symbol not in self.pending_signals:
                self.pending_signals[signal.symbol] = []
                
            # Check maximum signals per symbol
            symbol_settings = self.config.get("symbol_settings", {}).get(signal.symbol, {})
            max_signals = symbol_settings.get("max_concurrent_signals", self.config.get("max_signals_per_symbol", 10))
            
            if len(self.pending_signals[signal.symbol]) >= max_signals:
                # Remove oldest signal
                oldest_signal = min(self.pending_signals[signal.symbol], key=lambda s: s.timestamp)
                self.pending_signals[signal.symbol].remove(oldest_signal)
                self.logger.info(f"Removed oldest signal {oldest_signal.signal_id} due to limit")
                
            self.pending_signals[signal.symbol].append(signal)
            
            # Update provider profile
            self._update_provider_profile(signal)
            
            # Update statistics
            self.processing_stats["total_signals"] += 1
            
            # Start processing if not already running
            if not self.is_processing:
                self.start_processing()
                
            self.logger.info(f"Added signal {signal.signal_id} for {signal.symbol} from {signal.provider_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding signal: {e}")
            return False
            
    async def _process_pending_signals(self):
        """Process all pending signals"""
        while self.is_processing:
            try:
                if not self.pending_signals:
                    await asyncio.sleep(self.config.get("processing_interval", 2.0))
                    continue
                    
                # Process each symbol's signals
                for symbol, signals in list(self.pending_signals.items()):
                    if not signals:
                        continue
                        
                    # Remove expired signals
                    current_time = datetime.now()
                    expired_signals = [sig for sig in signals if sig.expiry_time and current_time > sig.expiry_time]
                    for expired in expired_signals:
                        signals.remove(expired)
                        self.processing_stats["expired_signals"] += 1
                        self.logger.info(f"Signal {expired.signal_id} expired")
                        
                    if not signals:
                        del self.pending_signals[symbol]
                        continue
                        
                    # Check for conflicts
                    conflicts = self._identify_conflicts(signals)
                    self.conflict_groups.extend(conflicts)
                    
                    if conflicts:
                        # Resolve conflicts
                        for conflict in conflicts:
                            if not conflict.resolved:
                                processed = self._resolve_conflict(conflict)
                                self.processed_signals.append(processed)
                                
                                # Remove processed signals from pending
                                for sig in conflict.signals:
                                    if sig in signals:
                                        signals.remove(sig)
                                        
                                self.processing_stats["conflicted_signals"] += len(conflict.signals)
                                self.processing_stats["processed_signals"] += 1
                                
                                self.logger.info(f"Resolved conflict for {symbol}: {processed.processing_reason}")
                                
                    else:
                        # No conflicts, check for merging opportunities
                        if self.config.get("enable_signal_merging", True) and len(signals) > 1:
                            # Group compatible signals
                            compatible_groups = []
                            remaining_signals = signals.copy()
                            
                            while remaining_signals:
                                current_signal = remaining_signals.pop(0)
                                compatible_group = [current_signal]
                                
                                for other_signal in remaining_signals.copy():
                                    if self._check_signal_compatibility(current_signal, other_signal):
                                        compatible_group.append(other_signal)
                                        remaining_signals.remove(other_signal)
                                        
                                compatible_groups.append(compatible_group)
                                
                            # Process each compatible group
                            for group in compatible_groups:
                                if len(group) > 1:
                                    # Merge compatible signals
                                    merged_signal = self._merge_compatible_signals(group)
                                    processed = ProcessedSignal(
                                        original_signals=group,
                                        final_signal=merged_signal,
                                        status=SignalStatus.MERGED,
                                        processing_reason=f"Merged {len(group)} compatible signals",
                                        conflicts_resolved=[],
                                        merged_signals=[sig.signal_id for sig in group],
                                        processing_time=datetime.now(),
                                        execution_priority=self._calculate_signal_score(merged_signal)
                                    )
                                    
                                    self.processed_signals.append(processed)
                                    self.processing_stats["merged_signals"] += len(group)
                                    self.processing_stats["processed_signals"] += 1
                                    
                                    self.logger.info(f"Merged {len(group)} signals for {symbol}")
                                    
                                else:
                                    # Single signal, process as-is
                                    single_signal = group[0]
                                    processed = ProcessedSignal(
                                        original_signals=[single_signal],
                                        final_signal=single_signal,
                                        status=SignalStatus.PROCESSED,
                                        processing_reason="Single signal processed",
                                        conflicts_resolved=[],
                                        merged_signals=[],
                                        processing_time=datetime.now(),
                                        execution_priority=self._calculate_signal_score(single_signal)
                                    )
                                    
                                    self.processed_signals.append(processed)
                                    self.processing_stats["processed_signals"] += 1
                                    
                            # Clear processed signals from pending
                            self.pending_signals[symbol] = []
                            
                        else:
                            # Process signals individually
                            for signal in signals:
                                processed = ProcessedSignal(
                                    original_signals=[signal],
                                    final_signal=signal,
                                    status=SignalStatus.PROCESSED,
                                    processing_reason="Individual signal processed",
                                    conflicts_resolved=[],
                                    merged_signals=[],
                                    processing_time=datetime.now(),
                                    execution_priority=self._calculate_signal_score(signal)
                                )
                                
                                self.processed_signals.append(processed)
                                self.processing_stats["processed_signals"] += 1
                                
                            self.pending_signals[symbol] = []
                            
                # Clean up empty symbol entries
                self.pending_signals = {k: v for k, v in self.pending_signals.items() if v}
                
                # Save data periodically
                self._save_signal_data()
                self._save_provider_profiles()
                
                await asyncio.sleep(self.config.get("processing_interval", 2.0))
                
            except Exception as e:
                self.logger.error(f"Error in signal processing loop: {e}")
                await asyncio.sleep(5)  # Prevent tight error loop
                
    def start_processing(self):
        """Start background signal processing"""
        if not self.config.get('enabled', True):
            self.logger.info("Multi-signal handler is disabled")
            return
            
        if not self.is_processing:
            self.is_processing = True
            try:
                self.processing_task = asyncio.create_task(self._process_pending_signals())
                self.logger.info("Signal processing started")
            except RuntimeError:
                self.is_processing = False
                self.logger.warning("No event loop running, cannot start processing")
                
    def stop_processing(self):
        """Stop background processing"""
        if self.is_processing:
            self.is_processing = False
            if self.processing_task:
                self.processing_task.cancel()
            self.logger.info("Signal processing stopped")
            
    def get_processed_signals(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get processed signals, optionally filtered by symbol"""
        filtered_signals = self.processed_signals
        
        if symbol:
            filtered_signals = [sig for sig in filtered_signals if sig.final_signal.symbol == symbol]
            
        # Sort by processing time (newest first) and limit
        recent_signals = sorted(filtered_signals, key=lambda x: x.processing_time, reverse=True)[:limit]
        
        return [signal.to_dict() for signal in recent_signals]
        
    def get_pending_signals(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get current pending signals by symbol"""
        result = {}
        for symbol, signals in self.pending_signals.items():
            result[symbol] = [
                {
                    "signal_id": sig.signal_id,
                    "direction": sig.direction.value,
                    "confidence": sig.confidence,
                    "provider_id": sig.provider_id,
                    "priority": sig.priority.value,
                    "timestamp": sig.timestamp.isoformat(),
                    "expiry_time": sig.expiry_time.isoformat() if sig.expiry_time else None
                }
                for sig in signals
            ]
        return result
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get signal processing statistics"""
        return {
            **self.processing_stats,
            "pending_signals": sum(len(signals) for signals in self.pending_signals.values()),
            "active_conflicts": len([c for c in self.conflict_groups if not c.resolved]),
            "provider_count": len(self.provider_profiles),
            "processing_active": self.is_processing
        }
        
    def get_provider_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get provider performance statistics"""
        return {
            provider_id: {
                "provider_name": profile.provider_name,
                "weight": profile.weight,
                "success_rate": profile.success_rate,
                "avg_confidence": profile.avg_confidence,
                "signal_count": profile.signal_count,
                "reputation_score": profile.reputation_score,
                "last_signal_time": profile.last_signal_time.isoformat() if profile.last_signal_time else None
            }
            for provider_id, profile in self.provider_profiles.items()
        }

# Global instance for easy access
multi_signal_handler = MultiSignalHandler()