#!/usr/bin/env python3
"""
Signal Confidence System for SignalOS Desktop Application

Tracks signal outcomes and provides confidence scoring based on historical performance.
Implements learning algorithms to improve signal quality assessment over time.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import statistics
import math

class SignalOutcome(Enum):
    """Possible signal outcomes"""
    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    TP3_HIT = "tp3_hit"
    STOP_LOSS = "stop_loss"
    BREAKEVEN = "breakeven"
    PARTIAL_CLOSE = "partial_close"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class ConfidenceLevel(Enum):
    """Confidence levels for signal classification"""
    VERY_HIGH = "very_high"  # 90-100%
    HIGH = "high"           # 75-89%
    MEDIUM = "medium"       # 60-74%
    LOW = "low"            # 40-59%
    VERY_LOW = "very_low"  # 0-39%

@dataclass
class SignalPerformance:
    """Signal performance tracking"""
    signal_id: str
    provider: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profits: List[float]
    
    # Outcome data
    outcome: Optional[SignalOutcome] = None
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl_pips: Optional[float] = None
    pnl_percent: Optional[float] = None
    
    # Signal quality metrics
    initial_confidence: float = 0.0
    parsing_method: str = "unknown"
    language_detected: Optional[str] = None
    
    # Timing data
    signal_time: datetime = None
    execution_time: Optional[datetime] = None
    duration_minutes: Optional[float] = None
    
    def __post_init__(self):
        if self.signal_time is None:
            self.signal_time = datetime.now()

@dataclass
class ProviderStats:
    """Provider performance statistics"""
    provider: str
    total_signals: int
    successful_signals: int
    failed_signals: int
    win_rate: float
    avg_pnl_pips: float
    avg_duration_hours: float
    confidence_accuracy: float
    
    # Signal quality metrics
    avg_initial_confidence: float
    confidence_vs_outcome_correlation: float
    
    # Time-based performance
    performance_by_hour: Dict[int, float]
    performance_by_day: Dict[str, float]
    
    # Symbol-specific performance
    symbol_performance: Dict[str, float]

class SignalConfidenceSystem:
    """Signal confidence tracking and learning system"""
    
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/confidence_system.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Initialize database
        self.db = self._init_database()
        
        # Provider statistics cache
        self.provider_stats_cache = {}
        self.cache_expiry = timedelta(hours=1)
        self.last_cache_update = datetime.min
        
        # Confidence model parameters
        self.confidence_weights = {
            'provider_win_rate': 0.25,
            'symbol_performance': 0.20,
            'parsing_confidence': 0.15,
            'time_of_day': 0.10,
            'market_conditions': 0.10,
            'signal_completeness': 0.10,
            'historical_accuracy': 0.10
        }
        
        # Learning parameters
        self.learning_rate = 0.1
        self.min_samples_for_learning = 10
        
        self.logger.info("Signal confidence system initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('confidence_system', {
                    'min_confidence_threshold': 0.5,
                    'high_confidence_threshold': 0.8,
                    'enable_learning': True,
                    'learning_window_days': 30,
                    'min_provider_signals': 5
                })
        except Exception as e:
            logging.warning(f"Failed to load config: {e}")
            return {'min_confidence_threshold': 0.5, 'enable_learning': True}
    
    def _setup_logging(self):
        """Setup logging"""
        self.logger = logging.getLogger('ConfidenceSystem')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _init_database(self) -> sqlite3.Connection:
        """Initialize confidence system database"""
        try:
            db_path = Path("logs/confidence_system.db")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            db = sqlite3.connect(str(db_path))
            
            # Create tables
            db.execute('''
                CREATE TABLE IF NOT EXISTS signal_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT UNIQUE,
                    provider TEXT,
                    symbol TEXT,
                    direction TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profits TEXT,
                    outcome TEXT,
                    exit_price REAL,
                    exit_time TEXT,
                    pnl_pips REAL,
                    pnl_percent REAL,
                    initial_confidence REAL,
                    parsing_method TEXT,
                    language_detected TEXT,
                    signal_time TEXT,
                    execution_time TEXT,
                    duration_minutes REAL
                )
            ''')
            
            db.execute('''
                CREATE TABLE IF NOT EXISTS provider_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT UNIQUE,
                    total_signals INTEGER,
                    successful_signals INTEGER,
                    failed_signals INTEGER,
                    win_rate REAL,
                    avg_pnl_pips REAL,
                    avg_duration_hours REAL,
                    confidence_accuracy REAL,
                    last_updated TEXT
                )
            ''')
            
            db.execute('''
                CREATE TABLE IF NOT EXISTS confidence_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT,
                    original_confidence REAL,
                    adjusted_confidence REAL,
                    adjustment_reason TEXT,
                    timestamp TEXT
                )
            ''')
            
            db.commit()
            return db
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def record_signal(self, signal_data: Dict[str, Any]) -> str:
        """
        Record a new signal for confidence tracking
        
        Args:
            signal_data: Parsed signal data
            
        Returns:
            Signal ID for tracking
        """
        try:
            # Generate signal ID
            signal_id = self._generate_signal_id(signal_data)
            
            # Create performance record
            performance = SignalPerformance(
                signal_id=signal_id,
                provider=signal_data.get('provider', 'unknown'),
                symbol=signal_data.get('symbol', ''),
                direction=signal_data.get('direction', ''),
                entry_price=signal_data.get('entry_price', 0.0),
                stop_loss=signal_data.get('stop_loss', 0.0),
                take_profits=signal_data.get('take_profits', []),
                initial_confidence=signal_data.get('confidence', 0.0),
                parsing_method=signal_data.get('parsing_method', 'unknown'),
                language_detected=signal_data.get('language', None),
                signal_time=datetime.now()
            )
            
            # Store in database
            self.db.execute('''
                INSERT OR REPLACE INTO signal_performance 
                (signal_id, provider, symbol, direction, entry_price, stop_loss, 
                 take_profits, initial_confidence, parsing_method, language_detected, signal_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_id, performance.provider, performance.symbol, performance.direction,
                performance.entry_price, performance.stop_loss, json.dumps(performance.take_profits),
                performance.initial_confidence, performance.parsing_method, 
                performance.language_detected, performance.signal_time.isoformat()
            ))
            
            self.db.commit()
            
            self.logger.info(f"Recorded signal: {signal_id} from {performance.provider}")
            return signal_id
            
        except Exception as e:
            self.logger.error(f"Failed to record signal: {e}")
            return ""
    
    def record_outcome(self, signal_id: str, outcome: SignalOutcome, 
                      exit_price: Optional[float] = None, pnl_pips: Optional[float] = None):
        """
        Record signal outcome for learning
        
        Args:
            signal_id: Signal identifier
            outcome: Signal outcome
            exit_price: Exit price if applicable
            pnl_pips: PnL in pips if applicable
        """
        try:
            # Calculate additional metrics
            exit_time = datetime.now()
            
            # Get original signal data
            cursor = self.db.execute(
                'SELECT signal_time, entry_price, stop_loss FROM signal_performance WHERE signal_id = ?',
                (signal_id,)
            )
            row = cursor.fetchone()
            
            if row:
                signal_time = datetime.fromisoformat(row[0])
                entry_price = row[1]
                stop_loss = row[2]
                
                # Calculate duration
                duration_minutes = (exit_time - signal_time).total_seconds() / 60
                
                # Calculate PnL percentage if not provided
                pnl_percent = None
                if exit_price and entry_price:
                    pnl_percent = ((exit_price - entry_price) / entry_price) * 100
                
                # Update database
                self.db.execute('''
                    UPDATE signal_performance 
                    SET outcome = ?, exit_price = ?, exit_time = ?, pnl_pips = ?, 
                        pnl_percent = ?, duration_minutes = ?
                    WHERE signal_id = ?
                ''', (
                    outcome.value, exit_price, exit_time.isoformat(), 
                    pnl_pips, pnl_percent, duration_minutes, signal_id
                ))
                
                self.db.commit()
                
                # Update provider statistics
                self._update_provider_stats(signal_id)
                
                # Learn from outcome if enabled
                if self.config.get('enable_learning', True):
                    self._learn_from_outcome(signal_id, outcome)
                
                self.logger.info(f"Recorded outcome for {signal_id}: {outcome.value}")
                
        except Exception as e:
            self.logger.error(f"Failed to record outcome: {e}")
    
    def calculate_confidence_score(self, signal_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score for a signal
        
        Args:
            signal_data: Signal data for scoring
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        try:
            provider = signal_data.get('provider', 'unknown')
            symbol = signal_data.get('symbol', '')
            parsing_confidence = signal_data.get('confidence', 0.0)
            
            # Get provider statistics
            provider_stats = self._get_provider_stats(provider)
            
            # Calculate component scores
            scores = {}
            
            # Provider win rate component
            if provider_stats:
                scores['provider_win_rate'] = provider_stats.win_rate
            else:
                scores['provider_win_rate'] = 0.5  # Neutral for unknown providers
            
            # Symbol performance component
            scores['symbol_performance'] = self._get_symbol_performance(symbol, provider)
            
            # Parsing confidence component
            scores['parsing_confidence'] = parsing_confidence
            
            # Time of day component
            scores['time_of_day'] = self._get_time_of_day_score()
            
            # Market conditions component (placeholder)
            scores['market_conditions'] = 0.5
            
            # Signal completeness component
            scores['signal_completeness'] = self._calculate_completeness_score(signal_data)
            
            # Historical accuracy component
            scores['historical_accuracy'] = self._get_historical_accuracy(provider)
            
            # Calculate weighted average
            total_score = 0.0
            for component, weight in self.confidence_weights.items():
                score = scores.get(component, 0.5)
                total_score += score * weight
            
            # Apply learning adjustments
            if self.config.get('enable_learning', True):
                total_score = self._apply_learning_adjustments(total_score, signal_data)
            
            # Ensure score is within bounds
            final_score = max(0.0, min(1.0, total_score))
            
            self.logger.debug(f"Calculated confidence score: {final_score:.3f} for {provider}")
            return final_score
            
        except Exception as e:
            self.logger.error(f"Failed to calculate confidence score: {e}")
            return 0.5  # Neutral score on error
    
    def _generate_signal_id(self, signal_data: Dict[str, Any]) -> str:
        """Generate unique signal ID"""
        provider = signal_data.get('provider', 'unknown')
        symbol = signal_data.get('symbol', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"{provider}_{symbol}_{timestamp}"
    
    def _get_provider_stats(self, provider: str) -> Optional[ProviderStats]:
        """Get provider statistics with caching"""
        now = datetime.now()
        
        # Check cache validity
        if (now - self.last_cache_update) > self.cache_expiry:
            self.provider_stats_cache.clear()
            self.last_cache_update = now
        
        # Return cached stats if available
        if provider in self.provider_stats_cache:
            return self.provider_stats_cache[provider]
        
        # Query database
        try:
            cursor = self.db.execute('''
                SELECT 
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN outcome IN ('tp1_hit', 'tp2_hit', 'tp3_hit') THEN 1 ELSE 0 END) as successful_signals,
                    SUM(CASE WHEN outcome = 'stop_loss' THEN 1 ELSE 0 END) as failed_signals,
                    AVG(pnl_pips) as avg_pnl_pips,
                    AVG(duration_minutes) as avg_duration_minutes,
                    AVG(initial_confidence) as avg_initial_confidence
                FROM signal_performance 
                WHERE provider = ? AND outcome IS NOT NULL
                AND signal_time >= datetime('now', '-30 days')
            ''', (provider,))
            
            row = cursor.fetchone()
            
            if row and row[0] >= self.config.get('min_provider_signals', 5):
                total_signals = row[0]
                successful_signals = row[1] or 0
                failed_signals = row[2] or 0
                
                stats = ProviderStats(
                    provider=provider,
                    total_signals=total_signals,
                    successful_signals=successful_signals,
                    failed_signals=failed_signals,
                    win_rate=successful_signals / total_signals if total_signals > 0 else 0.0,
                    avg_pnl_pips=row[3] or 0.0,
                    avg_duration_hours=(row[4] or 0.0) / 60.0,
                    confidence_accuracy=self._calculate_confidence_accuracy(provider),
                    avg_initial_confidence=row[5] or 0.0,
                    confidence_vs_outcome_correlation=0.0,  # Placeholder
                    performance_by_hour={},
                    performance_by_day={},
                    symbol_performance={}
                )
                
                # Cache the stats
                self.provider_stats_cache[provider] = stats
                return stats
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get provider stats: {e}")
            return None
    
    def _get_symbol_performance(self, symbol: str, provider: str) -> float:
        """Get symbol-specific performance score"""
        try:
            cursor = self.db.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome IN ('tp1_hit', 'tp2_hit', 'tp3_hit') THEN 1 ELSE 0 END) as successful
                FROM signal_performance 
                WHERE symbol = ? AND provider = ? AND outcome IS NOT NULL
                AND signal_time >= datetime('now', '-30 days')
            ''', (symbol, provider))
            
            row = cursor.fetchone()
            
            if row and row[0] >= 3:  # Minimum 3 signals for symbol analysis
                return row[1] / row[0]
            
            return 0.5  # Neutral for unknown symbols
            
        except Exception as e:
            self.logger.error(f"Failed to get symbol performance: {e}")
            return 0.5
    
    def _get_time_of_day_score(self) -> float:
        """Get time of day performance score"""
        # Simple implementation - can be enhanced with market session analysis
        current_hour = datetime.now().hour
        
        # Assume better performance during trading hours
        if 8 <= current_hour <= 17:  # Trading hours
            return 0.7
        elif 18 <= current_hour <= 22:  # Evening
            return 0.6
        else:  # Night/early morning
            return 0.4
    
    def _calculate_completeness_score(self, signal_data: Dict[str, Any]) -> float:
        """Calculate signal completeness score"""
        required_fields = ['symbol', 'direction', 'entry_price', 'stop_loss']
        optional_fields = ['take_profits', 'order_type']
        
        score = 0.0
        max_score = len(required_fields) + len(optional_fields)
        
        # Check required fields
        for field in required_fields:
            if field in signal_data and signal_data[field] is not None:
                score += 1.0
        
        # Check optional fields
        for field in optional_fields:
            if field in signal_data and signal_data[field] is not None:
                score += 0.5
        
        return score / max_score
    
    def _get_historical_accuracy(self, provider: str) -> float:
        """Get historical confidence accuracy"""
        try:
            cursor = self.db.execute('''
                SELECT initial_confidence, outcome
                FROM signal_performance 
                WHERE provider = ? AND outcome IS NOT NULL
                AND signal_time >= datetime('now', '-30 days')
            ''', (provider,))
            
            rows = cursor.fetchall()
            
            if len(rows) < 5:
                return 0.5
            
            # Calculate correlation between confidence and success
            confidences = []
            successes = []
            
            for row in rows:
                confidences.append(row[0])
                successes.append(1 if row[1] in ['tp1_hit', 'tp2_hit', 'tp3_hit'] else 0)
            
            if len(confidences) >= 5:
                correlation = self._calculate_correlation(confidences, successes)
                return max(0.0, min(1.0, (correlation + 1) / 2))  # Normalize to 0-1
            
            return 0.5
            
        except Exception as e:
            self.logger.error(f"Failed to get historical accuracy: {e}")
            return 0.5
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate correlation coefficient"""
        try:
            if len(x) != len(y) or len(x) < 2:
                return 0.0
            
            mean_x = statistics.mean(x)
            mean_y = statistics.mean(y)
            
            numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
            denominator = math.sqrt(
                sum((x[i] - mean_x) ** 2 for i in range(len(x))) *
                sum((y[i] - mean_y) ** 2 for i in range(len(y)))
            )
            
            return numerator / denominator if denominator != 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_confidence_accuracy(self, provider: str) -> float:
        """Calculate confidence prediction accuracy"""
        try:
            cursor = self.db.execute('''
                SELECT initial_confidence, outcome
                FROM signal_performance 
                WHERE provider = ? AND outcome IS NOT NULL
                AND signal_time >= datetime('now', '-30 days')
            ''', (provider,))
            
            rows = cursor.fetchall()
            
            if len(rows) < 5:
                return 0.5
            
            correct_predictions = 0
            total_predictions = len(rows)
            
            for row in rows:
                confidence = row[0]
                success = row[1] in ['tp1_hit', 'tp2_hit', 'tp3_hit']
                
                # Consider prediction correct if high confidence leads to success
                # or low confidence leads to failure
                if (confidence >= 0.7 and success) or (confidence < 0.5 and not success):
                    correct_predictions += 1
            
            return correct_predictions / total_predictions
            
        except Exception as e:
            self.logger.error(f"Failed to calculate confidence accuracy: {e}")
            return 0.5
    
    def _apply_learning_adjustments(self, base_score: float, signal_data: Dict[str, Any]) -> float:
        """Apply learning-based adjustments to confidence score"""
        try:
            # This is a placeholder for machine learning adjustments
            # In a full implementation, this would use trained models
            
            provider = signal_data.get('provider', 'unknown')
            symbol = signal_data.get('symbol', '')
            
            # Simple adjustment based on recent performance
            provider_stats = self._get_provider_stats(provider)
            if provider_stats:
                recent_performance = provider_stats.win_rate
                
                # Adjust score based on recent performance vs base score
                if recent_performance > 0.7:
                    adjustment = 0.1  # Boost for good performers
                elif recent_performance < 0.3:
                    adjustment = -0.1  # Penalize poor performers
                else:
                    adjustment = 0.0
                
                return base_score + adjustment
            
            return base_score
            
        except Exception as e:
            self.logger.error(f"Failed to apply learning adjustments: {e}")
            return base_score
    
    def _update_provider_stats(self, signal_id: str):
        """Update provider statistics after signal outcome"""
        try:
            # This would update cached provider statistics
            # For now, we'll just invalidate the cache
            self.provider_stats_cache.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to update provider stats: {e}")
    
    def _learn_from_outcome(self, signal_id: str, outcome: SignalOutcome):
        """Learn from signal outcome to improve future predictions"""
        try:
            # This is a placeholder for learning algorithms
            # In a full implementation, this would update model parameters
            
            self.logger.debug(f"Learning from outcome: {signal_id} -> {outcome.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to learn from outcome: {e}")
    
    def get_confidence_level(self, score: float) -> ConfidenceLevel:
        """Convert confidence score to confidence level"""
        if score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.75:
            return ConfidenceLevel.HIGH
        elif score >= 0.6:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.4:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def should_execute_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Determine if signal should be executed based on confidence"""
        confidence_score = self.calculate_confidence_score(signal_data)
        threshold = self.config.get('min_confidence_threshold', 0.5)
        
        return confidence_score >= threshold
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            cursor = self.db.execute('''
                SELECT 
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN outcome IN ('tp1_hit', 'tp2_hit', 'tp3_hit') THEN 1 ELSE 0 END) as successful_signals,
                    AVG(initial_confidence) as avg_confidence,
                    AVG(pnl_pips) as avg_pnl_pips
                FROM signal_performance 
                WHERE outcome IS NOT NULL
                AND signal_time >= datetime('now', '-30 days')
            ''')
            
            row = cursor.fetchone()
            
            if row:
                total_signals = row[0] or 0
                successful_signals = row[1] or 0
                
                return {
                    'total_signals': total_signals,
                    'successful_signals': successful_signals,
                    'win_rate': successful_signals / total_signals if total_signals > 0 else 0.0,
                    'avg_confidence': row[2] or 0.0,
                    'avg_pnl_pips': row[3] or 0.0,
                    'providers_tracked': len(self.provider_stats_cache)
                }
            
            return {'total_signals': 0, 'successful_signals': 0, 'win_rate': 0.0}
            
        except Exception as e:
            self.logger.error(f"Failed to get system stats: {e}")
            return {}
    
    def cleanup(self):
        """Cleanup resources"""
        if self.db:
            self.db.close()
        self.logger.info("Confidence system cleanup completed")

# Example usage
if __name__ == "__main__":
    system = SignalConfidenceSystem()
    
    # Test signal data
    signal_data = {
        'provider': 'TestProvider',
        'symbol': 'EURUSD',
        'direction': 'BUY',
        'entry_price': 1.0850,
        'stop_loss': 1.0800,
        'take_profits': [1.0900, 1.0950],
        'confidence': 0.75,
        'parsing_method': 'ai_model'
    }
    
    # Record signal
    signal_id = system.record_signal(signal_data)
    print(f"Recorded signal: {signal_id}")
    
    # Calculate confidence
    confidence = system.calculate_confidence_score(signal_data)
    print(f"Confidence score: {confidence:.3f}")
    
    # Check if should execute
    should_execute = system.should_execute_signal(signal_data)
    print(f"Should execute: {should_execute}")
    
    # Get stats
    stats = system.get_system_stats()
    print(f"System stats: {stats}")
    
    system.cleanup()