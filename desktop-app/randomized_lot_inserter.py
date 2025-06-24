"""
Randomized Lot Inserter for SignalOS
Implements stealth lot size randomization to avoid prop firm detection algorithms
"""

import json
import logging
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class LotRandomizationConfig:
    enabled: bool = True
    variance_range: float = 0.003  # ±0.003 variance
    min_lot_size: float = 0.01
    max_lot_size: float = 10.0
    rounding_enabled: bool = True
    rounding_precision: int = 3  # Round to 3 decimal places
    avoid_repeats: bool = True
    max_repeat_history: int = 50
    per_symbol_variance: bool = False
    log_randomization: bool = True
    notify_copilot: bool = False

@dataclass
class LotRandomizationResult:
    original_lot: float
    randomized_lot: float
    variance_applied: float
    seed_used: str
    timestamp: datetime
    symbol: str
    signal_id: Optional[str] = None
    reason: str = ""

class RandomizedLotInserter:
    def __init__(self, config_file: str = "config.json", history_file: str = "logs/lot_randomization_log.json"):
        self.config_file = config_file
        self.history_file = history_file
        self.config = self._load_config()
        self.randomization_history: List[LotRandomizationResult] = []
        self.recent_lots: Dict[str, List[float]] = {}  # Symbol -> recent lot sizes
        
        self._setup_logging()
        self._load_history()
        
        # Injected modules
        self.mt5_bridge = None
        self.copilot_bot = None
    
    def _load_config(self) -> LotRandomizationConfig:
        """Load randomization configuration from JSON file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    lot_config = config_data.get('randomized_lot_inserter', {})
                    return LotRandomizationConfig(**lot_config)
            else:
                return self._create_default_config()
        except Exception as e:
            self.logger.warning(f"Failed to load config, using defaults: {e}")
            return LotRandomizationConfig()
    
    def _create_default_config(self) -> LotRandomizationConfig:
        """Create default configuration and save to file"""
        default_config = LotRandomizationConfig()
        
        try:
            # Load existing config file or create new
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['randomized_lot_inserter'] = asdict(default_config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Failed to save default config: {e}")
        
        return default_config
    
    def _setup_logging(self):
        """Setup logging for lot randomization operations"""
        self.logger = logging.getLogger('RandomizedLotInserter')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _load_history(self):
        """Load randomization history from log file"""
        try:
            if Path(self.history_file).exists():
                with open(self.history_file, 'r') as f:
                    history_data = json.load(f)
                    
                for entry in history_data.get('randomizations', []):
                    result = LotRandomizationResult(
                        original_lot=entry['original_lot'],
                        randomized_lot=entry['randomized_lot'],
                        variance_applied=entry['variance_applied'],
                        seed_used=entry['seed_used'],
                        timestamp=datetime.fromisoformat(entry['timestamp']),
                        symbol=entry['symbol'],
                        signal_id=entry.get('signal_id'),
                        reason=entry.get('reason', '')
                    )
                    self.randomization_history.append(result)
                    
                    # Rebuild recent lots cache
                    symbol = result.symbol
                    if symbol not in self.recent_lots:
                        self.recent_lots[symbol] = []
                    self.recent_lots[symbol].append(result.randomized_lot)
        except Exception as e:
            self.logger.warning(f"Failed to load randomization history: {e}")
    
    def _save_history(self):
        """Save randomization history to log file"""
        try:
            # Ensure logs directory exists
            Path(self.history_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Keep only recent history to prevent file bloat
            recent_history = self.randomization_history[-1000:] if len(self.randomization_history) > 1000 else self.randomization_history
            
            history_data = {
                'randomizations': [
                    {
                        'original_lot': r.original_lot,
                        'randomized_lot': r.randomized_lot,
                        'variance_applied': r.variance_applied,
                        'seed_used': r.seed_used,
                        'timestamp': r.timestamp.isoformat(),
                        'symbol': r.symbol,
                        'signal_id': r.signal_id,
                        'reason': r.reason
                    }
                    for r in recent_history
                ],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save randomization history: {e}")
    
    def inject_modules(self, mt5_bridge=None, copilot_bot=None):
        """Inject module references for MT5 operations and notifications"""
        self.mt5_bridge = mt5_bridge
        self.copilot_bot = copilot_bot
        self.logger.info("Modules injected successfully")
    
    def _generate_deterministic_seed(self, signal_data: Dict[str, Any]) -> str:
        """Generate deterministic but unique seed from signal data"""
        # Create seed from signal characteristics to ensure reproducibility in tests
        seed_components = [
            str(signal_data.get('symbol', 'UNKNOWN')),
            str(signal_data.get('entry', 0)),
            str(signal_data.get('timestamp', datetime.now().isoformat())),
            str(signal_data.get('action', 'UNKNOWN'))
        ]
        
        seed_string = "|".join(seed_components)
        return hashlib.md5(seed_string.encode()).hexdigest()[:8]
    
    def _calculate_variance(self, original_lot: float, symbol: str, seed: str) -> float:
        """Calculate variance amount based on configuration"""
        # Use deterministic random based on seed for testability
        random.seed(seed)
        
        # Get variance range (per-symbol or global)
        variance_range = self.config.variance_range
        if self.config.per_symbol_variance:
            # Could extend to have per-symbol variance ranges in config
            pass
        
        # Generate variance within range (-variance_range to +variance_range)
        variance_multiplier = random.uniform(-1.0, 1.0)
        variance_amount = variance_multiplier * variance_range
        
        return variance_amount
    
    def _apply_rounding(self, lot_size: float) -> float:
        """Apply rounding if enabled"""
        if self.config.rounding_enabled:
            return round(lot_size, self.config.rounding_precision)
        return lot_size
    
    def _validate_lot_size(self, lot_size: float) -> Tuple[bool, str]:
        """Validate lot size is within acceptable bounds"""
        if lot_size < self.config.min_lot_size:
            return False, f"Lot size {lot_size} below minimum {self.config.min_lot_size}"
        
        if lot_size > self.config.max_lot_size:
            return False, f"Lot size {lot_size} above maximum {self.config.max_lot_size}"
        
        return True, "Valid"
    
    def _avoid_recent_repeats(self, symbol: str, proposed_lot: float, tolerance: float = 0.001) -> bool:
        """Check if proposed lot size is too similar to recent lots"""
        if not self.config.avoid_repeats:
            return True
        
        recent_lots = self.recent_lots.get(symbol, [])
        if not recent_lots:
            return True
        
        # Check last N lots for this symbol
        recent_count = min(len(recent_lots), self.config.max_repeat_history)
        for recent_lot in recent_lots[-recent_count:]:
            if abs(proposed_lot - recent_lot) < tolerance:
                return False
        
        return True
    
    def randomize_lot_size(self, signal_data: Dict[str, Any]) -> LotRandomizationResult:
        """
        Main function to randomize lot size for a signal
        
        Args:
            signal_data: Dictionary containing signal information including:
                - lot_size: Original lot size
                - symbol: Trading symbol
                - timestamp: Signal timestamp
                - signal_id: Optional signal identifier
                
        Returns:
            LotRandomizationResult with original and randomized lot sizes
        """
        original_lot = signal_data.get('lot_size', 0.01)
        symbol = signal_data.get('symbol', 'UNKNOWN')
        signal_id = signal_data.get('signal_id')
        
        # Check if randomization is enabled
        if not self.config.enabled:
            result = LotRandomizationResult(
                original_lot=original_lot,
                randomized_lot=original_lot,
                variance_applied=0.0,
                seed_used="disabled",
                timestamp=datetime.now(),
                symbol=symbol,
                signal_id=signal_id,
                reason="Randomization disabled"
            )
            return result
        
        # Generate deterministic seed
        seed = self._generate_deterministic_seed(signal_data)
        
        # Calculate variance
        variance = self._calculate_variance(original_lot, symbol, seed)
        
        # Apply variance
        randomized_lot = original_lot + variance
        
        # Apply rounding
        randomized_lot = self._apply_rounding(randomized_lot)
        
        # Validate lot size
        is_valid, validation_message = self._validate_lot_size(randomized_lot)
        if not is_valid:
            self.logger.warning(f"Randomized lot size invalid: {validation_message}")
            randomized_lot = max(self.config.min_lot_size, min(randomized_lot, self.config.max_lot_size))
            randomized_lot = self._apply_rounding(randomized_lot)
        
        # Check for recent repeats and adjust if necessary
        max_attempts = 5
        attempt = 0
        while not self._avoid_recent_repeats(symbol, randomized_lot) and attempt < max_attempts:
            # Generate new variance with modified seed
            modified_seed = f"{seed}_{attempt}"
            variance = self._calculate_variance(original_lot, symbol, modified_seed)
            randomized_lot = original_lot + variance
            randomized_lot = self._apply_rounding(randomized_lot)
            
            # Validate again
            is_valid, _ = self._validate_lot_size(randomized_lot)
            if not is_valid:
                randomized_lot = max(self.config.min_lot_size, min(randomized_lot, self.config.max_lot_size))
                randomized_lot = self._apply_rounding(randomized_lot)
            
            attempt += 1
        
        # Create result
        result = LotRandomizationResult(
            original_lot=original_lot,
            randomized_lot=randomized_lot,
            variance_applied=randomized_lot - original_lot,
            seed_used=seed,
            timestamp=datetime.now(),
            symbol=symbol,
            signal_id=signal_id,
            reason=f"Applied {variance:.6f} variance" + (f" (attempt {attempt})" if attempt > 0 else "")
        )
        
        # Update recent lots tracking
        if symbol not in self.recent_lots:
            self.recent_lots[symbol] = []
        self.recent_lots[symbol].append(randomized_lot)
        
        # Keep only recent history per symbol
        if len(self.recent_lots[symbol]) > self.config.max_repeat_history:
            self.recent_lots[symbol] = self.recent_lots[symbol][-self.config.max_repeat_history:]
        
        # Add to history
        self.randomization_history.append(result)
        
        # Log if enabled
        if self.config.log_randomization:
            self.logger.info(
                f"Lot randomization: {symbol} {original_lot:.3f} -> {randomized_lot:.3f} "
                f"(variance: {result.variance_applied:+.6f}, seed: {seed})"
            )
        
        # Save history
        self._save_history()
        
        # Notify copilot if enabled
        if self.config.notify_copilot and self.copilot_bot:
            self._send_copilot_notification(result)
        
        return result
    
    def _send_copilot_notification(self, result: LotRandomizationResult):
        """Send notification to Copilot Bot about lot randomization"""
        try:
            message = (
                f"🎲 Lot Randomized: {result.symbol}\n"
                f"Original: {result.original_lot:.3f}\n"
                f"Final: {result.randomized_lot:.3f}\n"
                f"Variance: {result.variance_applied:+.6f}"
            )
            
            # This would be the actual copilot bot call
            # await self.copilot_bot.send_alert(message)
            self.logger.info(f"Copilot notification sent: {message}")
            
        except Exception as e:
            self.logger.error(f"Failed to send copilot notification: {e}")
    
    def get_randomization_statistics(self) -> Dict[str, Any]:
        """Get statistics about lot randomization operations"""
        if not self.randomization_history:
            return {
                "total_randomizations": 0,
                "average_variance": 0.0,
                "symbols_processed": 0,
                "last_randomization": None
            }
        
        total_randomizations = len(self.randomization_history)
        total_variance = sum(abs(r.variance_applied) for r in self.randomization_history)
        average_variance = total_variance / total_randomizations
        
        symbols_processed = len(set(r.symbol for r in self.randomization_history))
        last_randomization = self.randomization_history[-1].timestamp.isoformat()
        
        # Variance distribution
        positive_variances = [r.variance_applied for r in self.randomization_history if r.variance_applied > 0]
        negative_variances = [r.variance_applied for r in self.randomization_history if r.variance_applied < 0]
        
        return {
            "total_randomizations": total_randomizations,
            "average_variance": round(average_variance, 6),
            "symbols_processed": symbols_processed,
            "last_randomization": last_randomization,
            "positive_variances": len(positive_variances),
            "negative_variances": len(negative_variances),
            "variance_range_config": self.config.variance_range,
            "enabled": self.config.enabled,
            "recent_symbols": list(self.recent_lots.keys())
        }

    def maybe_randomize_lot(self, lot_size: float, symbol: str = "EURUSD", 
                           signal_id: Optional[str] = None) -> float:
        """
        Simple integration function for strategy_runtime.py
        Returns randomized lot size if enabled, original lot size if disabled
        """
        if not self.config.enabled:
            return lot_size
        
        try:
            signal_data = {
                'symbol': symbol,
                'lot_size': lot_size,
                'signal_id': signal_id or f"auto_{datetime.now().isoformat()}"
            }
            
            result = self.randomize_lot_size(signal_data)
            return result.randomized_lot
            
        except Exception as e:
            self.logger.error(f"Lot randomization failed, using original: {e}")
            return lot_size


# Global instance for easy integration
_randomizer_instance = None

def get_randomizer_instance():
    """Get global randomizer instance"""
    global _randomizer_instance
    if _randomizer_instance is None:
        _randomizer_instance = RandomizedLotInserter()
    return _randomizer_instance

def maybe_randomize_lot(lot_size: float, symbol: str = "EURUSD", 
                       signal_id: Optional[str] = None) -> float:
    """
    Standalone function for strategy_runtime integration
    Randomizes lot size if enabled in config
    """
    randomizer = get_randomizer_instance()
    return randomizer.maybe_randomize_lot(lot_size, symbol, signal_id)
    
    def get_recent_randomizations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent randomization results"""
        recent = self.randomization_history[-limit:] if self.randomization_history else []
        return [
            {
                "symbol": r.symbol,
                "original_lot": r.original_lot,
                "randomized_lot": r.randomized_lot,
                "variance_applied": r.variance_applied,
                "timestamp": r.timestamp.isoformat(),
                "reason": r.reason,
                "signal_id": r.signal_id
            }
            for r in recent
        ]
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update configuration parameters"""
        try:
            # Update config object
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # Save to file
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['randomized_lot_inserter'] = asdict(self.config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            self.logger.info(f"Configuration updated: {new_config}")
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
    
    def clear_history(self):
        """Clear randomization history"""
        self.randomization_history.clear()
        self.recent_lots.clear()
        self._save_history()
        self.logger.info("Randomization history cleared")

# Example usage and integration
async def main():
    """Example usage of Randomized Lot Inserter"""
    inserter = RandomizedLotInserter()
    
    # Mock MT5 bridge for demonstration
    class MockMT5Bridge:
        def execute_trade(self, trade_data):
            print(f"Executing trade: {trade_data}")
    
    # Inject modules
    mt5_bridge = MockMT5Bridge()
    inserter.inject_modules(mt5_bridge=mt5_bridge)
    
    # Example signal data
    signal_data = {
        'symbol': 'EURUSD',
        'lot_size': 0.10,
        'entry': 1.0850,
        'action': 'BUY',
        'timestamp': datetime.now().isoformat(),
        'signal_id': 'signal_001'
    }
    
    # Randomize lot size
    result = inserter.randomize_lot_size(signal_data)
    
    print(f"Original lot: {result.original_lot}")
    print(f"Randomized lot: {result.randomized_lot}")
    print(f"Variance applied: {result.variance_applied:+.6f}")
    print(f"Reason: {result.reason}")
    
    # Update signal data with randomized lot
    signal_data['lot_size'] = result.randomized_lot
    
    # Execute trade with randomized lot
    mt5_bridge.execute_trade(signal_data)
    
    # Get statistics
    stats = inserter.get_randomization_statistics()
    print(f"Statistics: {stats}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())