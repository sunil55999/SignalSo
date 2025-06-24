"""
Signal Simulator for SignalOS
Provides dry-run execution preview of signal processing logic without sending real trades
Simulates entry selection, lot size calculation, and SL/TP adjustment logic
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from lotsize_engine import LotsizeEngine, calculate_lot
    from entry_range import EntryRangeHandler
    from symbol_mapper import normalize_symbol
except ImportError:
    # Handle import errors gracefully
    pass

@dataclass
class SimulationResult:
    """Result of signal simulation"""
    entry: float
    sl: Optional[float]
    tp: List[float]
    lot: float
    mode: str
    valid: bool
    symbol: str
    direction: str
    reasoning: str
    warnings: List[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

@dataclass
class SimulationConfig:
    """Configuration for signal simulation"""
    enable_logging: bool = True
    log_file: str = "logs/simulation.log"
    shadow_mode: bool = False  # Hide SL in shadow mode
    default_tp_count: int = 2
    default_lot_size: float = 0.1
    min_lot_size: float = 0.01
    max_lot_size: float = 10.0
    validate_prices: bool = True
    apply_spread_adjustment: bool = False
    spread_buffer_pips: float = 0.5

class SignalSimulator:
    """Dry-run signal execution simulator"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Injected modules (for real trading engine integration)
        self.lotsize_engine = None
        self.entry_handler = None
        self.market_data = None
        self.spread_checker = None
        
        # Initialize components
        self._initialize_components()
        
        # Statistics
        self.simulation_stats = {
            'total_simulations': 0,
            'valid_simulations': 0,
            'invalid_simulations': 0,
            'mode_usage': {'normal': 0, 'shadow': 0},
            'symbol_frequency': {}
        }
    
    def _load_config(self) -> SimulationConfig:
        """Load simulation configuration"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    sim_config = config_data.get('signal_simulator', {})
                    return SimulationConfig(**sim_config)
            else:
                return self._create_default_config()
        except Exception as e:
            self.logger.warning(f"Failed to load config, using defaults: {e}")
            return SimulationConfig()
    
    def _create_default_config(self) -> SimulationConfig:
        """Create default configuration and save to file"""
        default_config = SimulationConfig()
        
        try:
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['signal_simulator'] = asdict(default_config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Failed to save default config: {e}")
        
        return default_config
    
    def _setup_logging(self):
        """Setup logging for simulation operations"""
        self.logger = logging.getLogger('SignalSimulator')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Setup file logging if enabled
        if self.config.enable_logging:
            self._setup_file_logging()
    
    def _setup_file_logging(self):
        """Setup file logging for simulation results"""
        try:
            log_path = Path(self.config.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(self.config.log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            self.logger.warning(f"Failed to setup file logging: {e}")
    
    def _initialize_components(self):
        """Initialize internal components"""
        try:
            self.lotsize_engine = LotsizeEngine()
        except Exception:
            self.logger.warning("LotsizeEngine not available for simulation")
        
        try:
            self.entry_handler = EntryRangeHandler()
        except Exception:
            self.logger.warning("EntryRangeHandler not available for simulation")
    
    def inject_modules(self, lotsize_engine=None, entry_handler=None, 
                      market_data=None, spread_checker=None):
        """Inject external modules for enhanced simulation"""
        if lotsize_engine:
            self.lotsize_engine = lotsize_engine
        if entry_handler:
            self.entry_handler = entry_handler
        if market_data:
            self.market_data = market_data
        if spread_checker:
            self.spread_checker = spread_checker
    
    def simulate_signal(self, parsed_signal: Dict[str, Any], 
                       strategy_config: Dict[str, Any]) -> SimulationResult:
        """
        Simulate signal execution with strategy configuration
        
        Args:
            parsed_signal: Dictionary containing parsed signal data
            strategy_config: Strategy configuration for execution
            
        Returns:
            SimulationResult with dry-run execution details
        """
        self.simulation_stats['total_simulations'] += 1
        warnings = []
        
        try:
            # Extract signal components
            symbol = self._normalize_symbol(parsed_signal.get('symbol', 'UNKNOWN'))
            direction = parsed_signal.get('direction', 'BUY').upper()
            entry_prices = parsed_signal.get('entry', [])
            stop_loss = parsed_signal.get('stop_loss')
            take_profits = parsed_signal.get('take_profit', [])
            
            # Update symbol frequency stats
            self.simulation_stats['symbol_frequency'][symbol] = \
                self.simulation_stats['symbol_frequency'].get(symbol, 0) + 1
            
            # Determine simulation mode
            mode = strategy_config.get('simulation_mode', 'normal')
            if self.config.shadow_mode:
                mode = 'shadow'
            
            self.simulation_stats['mode_usage'][mode] = \
                self.simulation_stats['mode_usage'].get(mode, 0) + 1
            
            # Simulate entry selection
            entry = self._simulate_entry_selection(entry_prices, direction, symbol, warnings)
            
            # Simulate lot size calculation
            lot_size = self._simulate_lot_calculation(
                parsed_signal, strategy_config, symbol, stop_loss, entry, warnings
            )
            
            # Simulate SL/TP adjustment
            adjusted_sl, adjusted_tp = self._simulate_sl_tp_adjustment(
                stop_loss, take_profits, strategy_config, symbol, entry, direction, warnings
            )
            
            # Apply shadow mode if enabled
            if mode == 'shadow':
                adjusted_sl = None
                warnings.append("SL hidden in shadow mode")
            
            # Validate simulation result
            is_valid = self._validate_simulation_result(
                entry, adjusted_sl, adjusted_tp, lot_size, symbol, direction, warnings
            )
            
            if is_valid:
                self.simulation_stats['valid_simulations'] += 1
            else:
                self.simulation_stats['invalid_simulations'] += 1
            
            # Create simulation result
            result = SimulationResult(
                entry=entry,
                sl=adjusted_sl,
                tp=adjusted_tp,
                lot=lot_size,
                mode=mode,
                valid=is_valid,
                symbol=symbol,
                direction=direction,
                reasoning=f"Simulated {direction} {symbol} at {entry} with {lot_size} lots",
                warnings=warnings,
                timestamp=datetime.now()
            )
            
            # Log simulation result
            if self.config.enable_logging:
                self._log_simulation_result(result)
            
            self.logger.info(f"Simulated {symbol} {direction}: entry={entry}, lot={lot_size}, valid={is_valid}")
            return result
            
        except Exception as e:
            self.simulation_stats['invalid_simulations'] += 1
            error_msg = f"Simulation failed: {str(e)}"
            self.logger.error(error_msg)
            
            return SimulationResult(
                entry=0.0,
                sl=None,
                tp=[],
                lot=self.config.default_lot_size,
                mode='error',
                valid=False,
                symbol=symbol if 'symbol' in locals() else 'UNKNOWN',
                direction=direction if 'direction' in locals() else 'BUY',
                reasoning=error_msg,
                warnings=[error_msg],
                timestamp=datetime.now()
            )
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol using symbol mapper if available"""
        try:
            return normalize_symbol(symbol)
        except:
            # Fallback normalization
            symbol_map = {
                'GOLD': 'XAUUSD',
                'SILVER': 'XAGUSD',
                'OIL': 'USOIL',
                'GER30': 'GER30',
                'UK100': 'UK100',
                'US30': 'US30',
                'NAS100': 'NAS100',
                'SPX500': 'SPX500'
            }
            return symbol_map.get(symbol.upper(), symbol.upper())
    
    def _simulate_entry_selection(self, entry_prices: List[float], direction: str, 
                                 symbol: str, warnings: List[str]) -> float:
        """Simulate entry price selection logic"""
        if not entry_prices:
            warnings.append("No entry prices provided, using default")
            return 1.0000  # Default fallback
        
        if len(entry_prices) == 1:
            return entry_prices[0]
        
        # Use entry handler if available
        if self.entry_handler:
            try:
                return self.entry_handler.select_entry_price(entry_prices, direction)
            except Exception as e:
                warnings.append(f"Entry handler failed: {e}")
        
        # Fallback selection logic
        if direction.upper() == 'BUY':
            return min(entry_prices)  # Best entry for BUY is lowest price
        else:
            return max(entry_prices)  # Best entry for SELL is highest price
    
    def _simulate_lot_calculation(self, parsed_signal: Dict[str, Any], 
                                 strategy_config: Dict[str, Any], symbol: str,
                                 stop_loss: Optional[float], entry: float,
                                 warnings: List[str]) -> float:
        """Simulate lot size calculation"""
        try:
            # Calculate SL distance in pips
            sl_pips = None
            if stop_loss and entry:
                pip_size = self._get_pip_size(symbol)
                sl_pips = abs(entry - stop_loss) / pip_size
            
            # Use calculate_lot function if available
            if 'calculate_lot' in globals():
                account_balance = strategy_config.get('account_balance', 10000.0)
                lot_size = calculate_lot(
                    strategy_config=strategy_config,
                    signal_data=parsed_signal,
                    account_balance=account_balance,
                    sl_pips=sl_pips or 50.0,  # Default 50 pips
                    symbol=symbol
                )
                return self._constrain_lot_size(lot_size)
            
            # Fallback lot calculation
            explicit_lot = parsed_signal.get('lot_size')
            if explicit_lot:
                return self._constrain_lot_size(explicit_lot)
            
            warnings.append("Using default lot size")
            return self.config.default_lot_size
            
        except Exception as e:
            warnings.append(f"Lot calculation failed: {e}")
            return self.config.default_lot_size
    
    def _simulate_sl_tp_adjustment(self, stop_loss: Optional[float], 
                                  take_profits: List[float], strategy_config: Dict[str, Any],
                                  symbol: str, entry: float, direction: str,
                                  warnings: List[str]) -> tuple:
        """Simulate SL/TP adjustment logic"""
        adjusted_sl = stop_loss
        adjusted_tp = take_profits.copy() if take_profits else []
        
        # Apply spread adjustment if enabled
        if self.config.apply_spread_adjustment:
            spread_pips = self._get_spread_adjustment(symbol)
            pip_size = self._get_pip_size(symbol)
            spread_adjustment = spread_pips * pip_size
            
            if direction.upper() == 'BUY':
                if adjusted_sl:
                    adjusted_sl -= spread_adjustment
                adjusted_tp = [tp + spread_adjustment for tp in adjusted_tp]
            else:
                if adjusted_sl:
                    adjusted_sl += spread_adjustment
                adjusted_tp = [tp - spread_adjustment for tp in adjusted_tp]
            
            warnings.append(f"Applied {spread_pips} pip spread adjustment")
        
        # Handle TP override from strategy
        strategy_tp_override = strategy_config.get('tp_override')
        if strategy_tp_override:
            if isinstance(strategy_tp_override, list):
                adjusted_tp = strategy_tp_override
            else:
                adjusted_tp = [strategy_tp_override]
            warnings.append("Applied TP override from strategy")
        
        # Ensure minimum TP count if required
        if len(adjusted_tp) < self.config.default_tp_count and adjusted_tp:
            base_tp = adjusted_tp[0]
            pip_size = self._get_pip_size(symbol)
            
            while len(adjusted_tp) < self.config.default_tp_count:
                if direction.upper() == 'BUY':
                    next_tp = adjusted_tp[-1] + (20 * pip_size)  # Add 20 pips
                else:
                    next_tp = adjusted_tp[-1] - (20 * pip_size)  # Subtract 20 pips
                adjusted_tp.append(next_tp)
            
            warnings.append(f"Extended TP levels to {self.config.default_tp_count}")
        
        return adjusted_sl, adjusted_tp
    
    def _get_pip_size(self, symbol: str) -> float:
        """Get pip size for symbol"""
        # Standard pip sizes
        pip_sizes = {
            'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'AUDUSD': 0.0001, 'NZDUSD': 0.0001,
            'USDCAD': 0.0001, 'USDCHF': 0.0001, 'USDJPY': 0.01,
            'XAUUSD': 0.01, 'XAGUSD': 0.001,  # Metals
            'US30': 1.0, 'NAS100': 1.0, 'SPX500': 1.0,  # Indices
            'USOIL': 0.01, 'UKOIL': 0.01  # Commodities
        }
        return pip_sizes.get(symbol, 0.0001)  # Default to 0.0001
    
    def _get_spread_adjustment(self, symbol: str) -> float:
        """Get spread adjustment in pips for symbol"""
        if self.spread_checker:
            try:
                return self.spread_checker.get_average_spread(symbol)
            except:
                pass
        
        # Default spread adjustments (conservative estimates)
        spreads = {
            'EURUSD': 0.5, 'GBPUSD': 0.8, 'USDJPY': 0.5, 'USDCHF': 0.8,
            'AUDUSD': 0.7, 'NZDUSD': 1.0, 'USDCAD': 0.7,
            'XAUUSD': 1.5, 'XAGUSD': 2.0,
            'US30': 2.0, 'NAS100': 1.5, 'SPX500': 0.5
        }
        return spreads.get(symbol, self.config.spread_buffer_pips)
    
    def _constrain_lot_size(self, lot_size: float) -> float:
        """Apply lot size constraints"""
        return max(self.config.min_lot_size, 
                  min(self.config.max_lot_size, lot_size))
    
    def _validate_simulation_result(self, entry: float, sl: Optional[float], 
                                   tp: List[float], lot: float, symbol: str,
                                   direction: str, warnings: List[str]) -> bool:
        """Validate simulation result for logical consistency"""
        if not self.config.validate_prices:
            return True
        
        try:
            # Basic validations
            if entry <= 0:
                warnings.append("Invalid entry price")
                return False
            
            if lot <= 0:
                warnings.append("Invalid lot size")
                return False
            
            # Price relationship validations
            if sl and direction.upper() == 'BUY' and sl >= entry:
                warnings.append("BUY signal: SL should be below entry")
                return False
            
            if sl and direction.upper() == 'SELL' and sl <= entry:
                warnings.append("SELL signal: SL should be above entry")
                return False
            
            # TP validations
            for i, tp_level in enumerate(tp):
                if direction.upper() == 'BUY' and tp_level <= entry:
                    warnings.append(f"BUY signal: TP{i+1} should be above entry")
                    return False
                
                if direction.upper() == 'SELL' and tp_level >= entry:
                    warnings.append(f"SELL signal: TP{i+1} should be below entry")
                    return False
            
            return True
            
        except Exception as e:
            warnings.append(f"Validation error: {e}")
            return False
    
    def _log_simulation_result(self, result: SimulationResult):
        """Log simulation result to file"""
        try:
            log_entry = {
                'timestamp': result.timestamp.isoformat(),
                'symbol': result.symbol,
                'direction': result.direction,
                'entry': result.entry,
                'sl': result.sl,
                'tp': result.tp,
                'lot': result.lot,
                'mode': result.mode,
                'valid': result.valid,
                'warnings': result.warnings
            }
            
            log_path = Path(self.config.log_file)
            with open(log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            self.logger.warning(f"Failed to log simulation result: {e}")
    
    def get_simulation_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics"""
        return {
            'stats': self.simulation_stats.copy(),
            'config': asdict(self.config),
            'components_available': {
                'lotsize_engine': self.lotsize_engine is not None,
                'entry_handler': self.entry_handler is not None,
                'market_data': self.market_data is not None,
                'spread_checker': self.spread_checker is not None
            }
        }
    
    def batch_simulate(self, signals_and_configs: List[tuple]) -> List[SimulationResult]:
        """Simulate multiple signals in batch"""
        results = []
        
        for parsed_signal, strategy_config in signals_and_configs:
            result = self.simulate_signal(parsed_signal, strategy_config)
            results.append(result)
        
        self.logger.info(f"Completed batch simulation of {len(results)} signals")
        return results
    
    def clear_statistics(self):
        """Clear simulation statistics"""
        self.simulation_stats = {
            'total_simulations': 0,
            'valid_simulations': 0,
            'invalid_simulations': 0,
            'mode_usage': {'normal': 0, 'shadow': 0},
            'symbol_frequency': {}
        }
        self.logger.info("Simulation statistics cleared")


# Global instance for easy access
_signal_simulator = None

def simulate_signal(parsed_signal: Dict[str, Any], 
                   strategy_config: Dict[str, Any]) -> SimulationResult:
    """
    Global function to simulate signal execution
    
    Args:
        parsed_signal: Parsed signal data
        strategy_config: Strategy configuration
        
    Returns:
        SimulationResult with dry-run execution details
    """
    global _signal_simulator
    
    if _signal_simulator is None:
        _signal_simulator = SignalSimulator()
    
    return _signal_simulator.simulate_signal(parsed_signal, strategy_config)

def get_simulation_stats() -> Dict[str, Any]:
    """Get global simulation statistics"""
    global _signal_simulator
    
    if _signal_simulator is None:
        _signal_simulator = SignalSimulator()
    
    return _signal_simulator.get_simulation_statistics()