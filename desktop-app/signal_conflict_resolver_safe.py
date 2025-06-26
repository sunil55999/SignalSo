"""
Safe Signal Conflict Resolver for SignalOS
Addresses race conditions in signal processing with proper async locks
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from collections import defaultdict

class ConflictType(Enum):
    DUPLICATE_SIGNAL = "duplicate_signal"
    OPPOSITE_DIRECTION = "opposite_direction"
    SYMBOL_OVERLAP = "symbol_overlap"
    TIME_OVERLAP = "time_overlap"

class ResolutionStrategy(Enum):
    FIRST_WINS = "first_wins"
    LAST_WINS = "last_wins"
    HIGHEST_CONFIDENCE = "highest_confidence"
    MERGE_SIGNALS = "merge_signals"

@dataclass
class SignalConflict:
    conflict_id: str
    conflict_type: ConflictType
    signals: List[Dict[str, Any]]
    resolution_strategy: ResolutionStrategy
    resolved: bool = False
    resolution_result: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class SafeSignalConflictResolver:
    """Thread-safe signal conflict resolver with proper locking mechanisms"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        
        # Fix #13: Thread-safe locking mechanisms
        self._lock = asyncio.Lock()
        self._thread_lock = threading.RLock()
        self._processing_queue = asyncio.Queue()
        self._active_conflicts = {}
        self._signal_cache = {}
        self._processing_semaphore = asyncio.Semaphore(5)  # Limit concurrent processing
        
        # Load configuration
        self._load_config()
        
        # Statistics tracking
        self.stats = {
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'resolution_times': [],
            'cache_hits': 0,
            'cache_misses': 0
        }
        
    def _load_config(self):
        """Load configuration safely with defaults"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.config = config.get('conflict_resolver', {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.warning(f"Config load failed: {e}, using defaults")
            self.config = {}
            
        # Set defaults
        self.config.setdefault('duplicate_threshold_seconds', 30)
        self.config.setdefault('symbol_overlap_threshold', 0.8)
        self.config.setdefault('default_resolution_strategy', 'highest_confidence')
        self.config.setdefault('max_cache_size', 1000)
        self.config.setdefault('cache_ttl_seconds', 300)
        
    async def process_signal_safely(self, signal: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Process signal with conflict detection and resolution
        
        Args:
            signal: Signal data to process
            
        Returns:
            Tuple of (is_valid, resolved_signal)
        """
        async with self._lock:  # Fix #13: Async lock for race condition prevention
            try:
                # Generate signal fingerprint for caching
                signal_id = self._generate_signal_id(signal)
                
                # Check cache first
                cached_result = self._check_cache(signal_id)
                if cached_result is not None:
                    self.stats['cache_hits'] += 1
                    return cached_result
                
                self.stats['cache_misses'] += 1
                
                # Detect conflicts
                conflicts = await self._detect_conflicts(signal)
                
                if not conflicts:
                    # No conflicts, signal is valid
                    result = (True, signal)
                    self._cache_result(signal_id, result)
                    return result
                
                # Process conflicts
                self.stats['conflicts_detected'] += len(conflicts)
                resolved_signal = await self._resolve_conflicts(signal, conflicts)
                
                if resolved_signal:
                    self.stats['conflicts_resolved'] += 1
                    result = (True, resolved_signal)
                else:
                    result = (False, None)
                
                self._cache_result(signal_id, result)
                return result
                
            except Exception as e:
                self.logger.error(f"Signal processing error: {e}")
                return (False, None)
                
    def _generate_signal_id(self, signal: Dict[str, Any]) -> str:
        """Generate unique signal identifier for caching"""
        key_parts = [
            signal.get('symbol', ''),
            signal.get('action', ''),
            signal.get('entry', ''),
            str(signal.get('timestamp', time.time()))
        ]
        return f"signal_{hash('_'.join(key_parts))}"
        
    def _check_cache(self, signal_id: str) -> Optional[Tuple[bool, Optional[Dict[str, Any]]]]:
        """Check if signal result is cached and still valid"""
        if signal_id in self._signal_cache:
            cached_data = self._signal_cache[signal_id]
            
            # Check if cache entry is still valid
            if time.time() - cached_data['timestamp'] < self.config['cache_ttl_seconds']:
                return cached_data['result']
            else:
                # Remove expired cache entry
                del self._signal_cache[signal_id]
                
        return None
        
    def _cache_result(self, signal_id: str, result: Tuple[bool, Optional[Dict[str, Any]]]):
        """Cache signal processing result"""
        # Implement LRU-style cache management
        if len(self._signal_cache) >= self.config['max_cache_size']:
            # Remove oldest entries
            oldest_keys = sorted(
                self._signal_cache.keys(),
                key=lambda k: self._signal_cache[k]['timestamp']
            )[:len(self._signal_cache) // 4]  # Remove 25% of cache
            
            for key in oldest_keys:
                del self._signal_cache[key]
                
        self._signal_cache[signal_id] = {
            'result': result,
            'timestamp': time.time()
        }
        
    async def _detect_conflicts(self, signal: Dict[str, Any]) -> List[SignalConflict]:
        """Detect various types of signal conflicts"""
        conflicts = []
        current_time = datetime.now()
        
        # Check for duplicate signals
        duplicate_conflict = self._check_duplicate_signals(signal, current_time)
        if duplicate_conflict:
            conflicts.append(duplicate_conflict)
            
        # Check for opposite direction conflicts
        opposite_conflict = self._check_opposite_direction(signal, current_time)
        if opposite_conflict:
            conflicts.append(opposite_conflict)
            
        # Check for symbol overlap conflicts
        symbol_conflict = self._check_symbol_overlap(signal, current_time)
        if symbol_conflict:
            conflicts.append(symbol_conflict)
            
        return conflicts
        
    def _check_duplicate_signals(self, signal: Dict[str, Any], current_time: datetime) -> Optional[SignalConflict]:
        """Check for duplicate signals within threshold time"""
        symbol = signal.get('symbol')
        action = signal.get('action')
        entry = signal.get('entry')
        
        # Look for similar signals in active conflicts
        threshold = timedelta(seconds=self.config['duplicate_threshold_seconds'])
        
        for conflict_id, conflict in self._active_conflicts.items():
            if conflict.conflict_type == ConflictType.DUPLICATE_SIGNAL:
                for existing_signal in conflict.signals:
                    if (existing_signal.get('symbol') == symbol and
                        existing_signal.get('action') == action and
                        abs(float(existing_signal.get('entry', 0)) - float(entry or 0)) < 0.0001):
                        
                        time_diff = current_time - conflict.timestamp
                        if time_diff < threshold:
                            return SignalConflict(
                                conflict_id=f"dup_{int(time.time())}_{hash(symbol)}",
                                conflict_type=ConflictType.DUPLICATE_SIGNAL,
                                signals=[existing_signal, signal],
                                resolution_strategy=ResolutionStrategy.FIRST_WINS,
                                timestamp=current_time
                            )
        return None
        
    def _check_opposite_direction(self, signal: Dict[str, Any], current_time: datetime) -> Optional[SignalConflict]:
        """Check for opposite direction signals on same symbol"""
        symbol = signal.get('symbol')
        action = signal.get('action', '').upper()
        
        opposite_action = 'SELL' if action == 'BUY' else 'BUY'
        
        # Check recent signals for opposite direction
        for conflict_id, conflict in self._active_conflicts.items():
            for existing_signal in conflict.signals:
                if (existing_signal.get('symbol') == symbol and
                    existing_signal.get('action', '').upper() == opposite_action):
                    
                    return SignalConflict(
                        conflict_id=f"opp_{int(time.time())}_{hash(symbol)}",
                        conflict_type=ConflictType.OPPOSITE_DIRECTION,
                        signals=[existing_signal, signal],
                        resolution_strategy=ResolutionStrategy.HIGHEST_CONFIDENCE,
                        timestamp=current_time
                    )
        return None
        
    def _check_symbol_overlap(self, signal: Dict[str, Any], current_time: datetime) -> Optional[SignalConflict]:
        """Check for overlapping symbols (like EURUSD vs EURGBP)"""
        symbol = signal.get('symbol', '')
        
        if len(symbol) >= 6:
            base_currency = symbol[:3]
            quote_currency = symbol[3:6]
            
            # Look for signals with overlapping currencies
            for conflict_id, conflict in self._active_conflicts.items():
                for existing_signal in conflict.signals:
                    existing_symbol = existing_signal.get('symbol', '')
                    if len(existing_symbol) >= 6:
                        existing_base = existing_symbol[:3]
                        existing_quote = existing_symbol[3:6]
                        
                        # Check for currency overlap
                        overlap_score = 0
                        if base_currency == existing_base or base_currency == existing_quote:
                            overlap_score += 0.5
                        if quote_currency == existing_base or quote_currency == existing_quote:
                            overlap_score += 0.5
                            
                        if overlap_score >= self.config['symbol_overlap_threshold']:
                            return SignalConflict(
                                conflict_id=f"sym_{int(time.time())}_{hash(symbol)}",
                                conflict_type=ConflictType.SYMBOL_OVERLAP,
                                signals=[existing_signal, signal],
                                resolution_strategy=ResolutionStrategy.MERGE_SIGNALS,
                                timestamp=current_time
                            )
        return None
        
    async def _resolve_conflicts(self, signal: Dict[str, Any], conflicts: List[SignalConflict]) -> Optional[Dict[str, Any]]:
        """Resolve signal conflicts using configured strategies"""
        async with self._processing_semaphore:  # Limit concurrent processing
            start_time = time.time()
            
            try:
                for conflict in conflicts:
                    # Store conflict for tracking
                    self._active_conflicts[conflict.conflict_id] = conflict
                    
                    # Apply resolution strategy
                    if conflict.resolution_strategy == ResolutionStrategy.FIRST_WINS:
                        resolved_signal = conflict.signals[0]  # Keep first signal
                    elif conflict.resolution_strategy == ResolutionStrategy.LAST_WINS:
                        resolved_signal = signal  # Keep new signal
                    elif conflict.resolution_strategy == ResolutionStrategy.HIGHEST_CONFIDENCE:
                        resolved_signal = self._resolve_by_confidence(conflict.signals)
                    elif conflict.resolution_strategy == ResolutionStrategy.MERGE_SIGNALS:
                        resolved_signal = self._merge_signals(conflict.signals)
                    else:
                        resolved_signal = signal  # Default to new signal
                    
                    # Mark conflict as resolved
                    conflict.resolved = True
                    conflict.resolution_result = resolved_signal
                    
                    # Clean up old conflicts
                    await self._cleanup_old_conflicts()
                    
                    # Record resolution time
                    resolution_time = time.time() - start_time
                    self.stats['resolution_times'].append(resolution_time)
                    
                    return resolved_signal
                    
            except Exception as e:
                self.logger.error(f"Conflict resolution error: {e}")
                return None
                
        return signal  # Return original signal if no conflicts resolved
        
    def _resolve_by_confidence(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select signal with highest confidence score"""
        best_signal = signals[0]
        best_confidence = float(best_signal.get('confidence', 0))
        
        for signal in signals[1:]:
            confidence = float(signal.get('confidence', 0))
            if confidence > best_confidence:
                best_confidence = confidence
                best_signal = signal
                
        return best_signal
        
    def _merge_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple signals into one optimized signal"""
        if not signals:
            return {}
            
        # Start with first signal as base
        merged = signals[0].copy()
        
        # Average numerical values
        numerical_fields = ['entry', 'stopLoss', 'takeProfit1', 'takeProfit2', 'takeProfit3']
        
        for field in numerical_fields:
            values = []
            for signal in signals:
                if field in signal and signal[field] is not None:
                    try:
                        values.append(float(signal[field]))
                    except (ValueError, TypeError):
                        continue
                        
            if values:
                merged[field] = sum(values) / len(values)
                
        # Use highest confidence
        confidences = [float(s.get('confidence', 0)) for s in signals]
        merged['confidence'] = max(confidences) if confidences else 0
        
        # Combine comments
        comments = [s.get('comment', '') for s in signals if s.get('comment')]
        if comments:
            merged['comment'] = ' | '.join(comments)
            
        return merged
        
    async def _cleanup_old_conflicts(self):
        """Remove old resolved conflicts to prevent memory leaks"""
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        expired_conflicts = [
            conflict_id for conflict_id, conflict in self._active_conflicts.items()
            if conflict.timestamp < cutoff_time and conflict.resolved
        ]
        
        for conflict_id in expired_conflicts:
            del self._active_conflicts[conflict_id]
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get resolver statistics"""
        avg_resolution_time = 0
        if self.stats['resolution_times']:
            avg_resolution_time = sum(self.stats['resolution_times']) / len(self.stats['resolution_times'])
            
        return {
            'conflicts_detected': self.stats['conflicts_detected'],
            'conflicts_resolved': self.stats['conflicts_resolved'],
            'active_conflicts': len(self._active_conflicts),
            'cache_size': len(self._signal_cache),
            'cache_hit_rate': self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses']) * 100 if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0,
            'avg_resolution_time_ms': avg_resolution_time * 1000,
            'config': self.config
        }

# Global resolver instance
safe_resolver = SafeSignalConflictResolver()

async def process_signal_with_conflict_resolution(signal: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Global function for safe signal processing"""
    return await safe_resolver.process_signal_safely(signal)

def get_resolver_statistics() -> Dict[str, Any]:
    """Global function to get resolver statistics"""
    return safe_resolver.get_statistics()