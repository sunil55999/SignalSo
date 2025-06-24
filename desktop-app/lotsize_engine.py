"""
Lotsize Engine for SignalOS
Extracts position sizing data from signal messages and calculates optimal lot sizes
based on risk parameters and account balance
"""

import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

try:
    from pip_value_calculator import get_pip_value
except ImportError:
    # Fallback if pip_value_calculator is not available
    def get_pip_value(symbol: str, account_currency: str = "USD") -> float:
        default_values = {
            "EURUSD": 10.0, "GBPUSD": 10.0, "USDJPY": 9.09, "USDCHF": 10.20,
            "AUDUSD": 10.0, "NZDUSD": 10.0, "USDCAD": 7.69, "XAUUSD": 10.0,
            "XAGUSD": 50.0, "US30": 1.0, "SPX500": 1.0, "NAS100": 1.0
        }
        return default_values.get(symbol.upper(), 10.0)

class RiskMode(Enum):
    FIXED_LOT = "fixed_lot"
    FIXED_CASH = "fixed_cash" 
    RISK_PERCENT = "risk_percent"
    PIP_VALUE = "pip_value"
    BALANCE_PERCENT = "balance_percent"

class RiskKeyword(Enum):
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"

@dataclass
class LotsizeConfig:
    default_mode: RiskMode = RiskMode.RISK_PERCENT
    default_risk_percent: float = 1.0
    min_lot_size: float = 0.01
    max_lot_size: float = 10.0
    precision_digits: int = 2
    pip_value_usd: float = 10.0  # Default for standard lot
    balance_fallback: float = 10000.0
    risk_multipliers: Dict[str, float] = None
    symbol_pip_values: Dict[str, float] = None
    
    def __post_init__(self):
        if self.risk_multipliers is None:
            self.risk_multipliers = {
                "low": 0.5,
                "conservative": 0.5,
                "medium": 1.0,
                "normal": 1.0,
                "high": 2.0,
                "aggressive": 2.5,
                "max": 3.0
            }
        if self.symbol_pip_values is None:
            self.symbol_pip_values = {
                "EURUSD": 10.0,
                "GBPUSD": 10.0,
                "USDJPY": 9.09,
                "USDCHF": 10.20,
                "AUDUSD": 10.0,
                "NZDUSD": 10.0,
                "USDCAD": 7.69,
                "XAUUSD": 10.0,
                "XAGUSD": 50.0
            }

@dataclass
class LotsizeResult:
    calculated_lot: float
    original_lot: Optional[float]
    risk_mode: RiskMode
    risk_percent: Optional[float]
    risk_multiplier: float
    symbol: str
    account_balance: float
    pip_value: float
    stop_loss_pips: Optional[float]
    confidence: float
    reasoning: str
    timestamp: datetime

class LotsizeEngine:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/lotsize_engine.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Injected modules
        self.mt5_bridge = None
        self.market_data = None
        self.parser = None
        
        # Lot extraction patterns
        self.lot_patterns = self._initialize_lot_patterns()
        self.risk_patterns = self._initialize_risk_patterns()
        
        # Statistics
        self.extraction_stats = {
            'total_processed': 0,
            'lots_extracted': 0,
            'risk_detected': 0,
            'mode_usage': {mode.value: 0 for mode in RiskMode}
        }

    def _load_config(self) -> LotsizeConfig:
        """Load configuration from JSON file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    lotsize_config = config_data.get('lotsize_engine', {})
                    return LotsizeConfig(**lotsize_config)
            else:
                return self._create_default_config()
        except Exception as e:
            self.logger.warning(f"Failed to load config, using defaults: {e}")
            return LotsizeConfig()

    def _create_default_config(self) -> LotsizeConfig:
        """Create default configuration and save to file"""
        default_config = LotsizeConfig()
        
        try:
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['lotsize_engine'] = asdict(default_config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Failed to save default config: {e}")
        
        return default_config

    def _setup_logging(self):
        """Setup logging for lotsize operations"""
        self.logger = logging.getLogger('LotsizeEngine')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _initialize_lot_patterns(self) -> List[Dict[str, Any]]:
        """Initialize regex patterns for lot size extraction"""
        return [
            # Direct lot specifications
            {
                'pattern': r'(?:lot(?:s|size)?:?\s*|use\s+)(\d+\.?\d*)\s*lot(?:s)?',
                'type': 'fixed_lot',
                'confidence': 0.95
            },
            # Risk percentage specifications
            {
                'pattern': r'(?:risk:?\s*|use\s+)(\d+\.?\d*)%',
                'type': 'risk_percent',
                'confidence': 0.90
            },
            # Cash amount specifications
            {
                'pattern': r'(?:risk:?\s*|invest\s+)[\$€£]?(\d+(?:,\d{3})*(?:\.\d{2})?)',
                'type': 'fixed_cash',
                'confidence': 0.85
            },
            # Per pip value specifications
            {
                'pattern': r'(\d+\.?\d*)\s*(?:per\s+pip|pip\s+value|\$/pip)',
                'type': 'pip_value',
                'confidence': 0.80
            },
            # Balance percentage
            {
                'pattern': r'(\d+\.?\d*)%\s*(?:of\s+)?(?:balance|account|capital)',
                'type': 'balance_percent',
                'confidence': 0.85
            }
        ]

    def _initialize_risk_patterns(self) -> Dict[str, float]:
        """Initialize risk keyword patterns and multipliers"""
        return {
            r'\b(?:low|conservative|safe)\s*risk\b': 0.5,
            r'\b(?:medium|normal|standard)\s*risk\b': 1.0,
            r'\b(?:high|aggressive|risky)\s*risk\b': 2.0,
            r'\bmax\s*risk\b': 3.0,
            r'\bconservative\b': 0.5,
            r'\baggressive\b': 2.0,
            r'\bhigh\s*confidence\b': 1.5,
            r'\blow\s*confidence\b': 0.7
        }

    def inject_modules(self, mt5_bridge=None, market_data=None, parser=None):
        """Inject module references for MT5 and market data"""
        self.mt5_bridge = mt5_bridge
        self.market_data = market_data
        self.parser = parser

    def extract_lotsize(self, signal_text: str, risk_mode: str, account_balance: float, 
                       symbol: str = "EURUSD", stop_loss_pips: Optional[float] = None) -> LotsizeResult:
        """
        Extract lot size from signal text or calculate based on risk parameters
        
        Args:
            signal_text: Raw signal text to analyze
            risk_mode: Risk calculation mode
            account_balance: Current account balance
            symbol: Trading symbol for pip value calculation
            stop_loss_pips: Stop loss distance in pips
            
        Returns:
            LotsizeResult with calculated lot size and metadata
        """
        self.extraction_stats['total_processed'] += 1
        
        try:
            mode = RiskMode(risk_mode.lower())
        except ValueError:
            mode = self.config.default_mode
        
        self.extraction_stats['mode_usage'][mode.value] += 1
        
        # Extract explicit lot size from text
        extracted_lot = self._extract_lot_from_text(signal_text)
        
        # Extract risk keywords and multipliers
        risk_multiplier = self._extract_risk_multiplier(signal_text)
        
        # Get pip value for symbol
        pip_value = self._get_pip_value(symbol)
        
        # Calculate final lot size
        if extracted_lot and extracted_lot['type'] == 'fixed_lot':
            final_lot = extracted_lot['value'] * risk_multiplier
            confidence = extracted_lot['confidence']
            reasoning = f"Extracted {extracted_lot['value']} lots from text, applied {risk_multiplier}x multiplier"
            self.extraction_stats['lots_extracted'] += 1
        else:
            final_lot = self._calculate_lot_by_mode(
                mode, account_balance, pip_value, stop_loss_pips, risk_multiplier
            )
            confidence = 0.7
            reasoning = f"Calculated using {mode.value} mode with {risk_multiplier}x risk multiplier"
        
        # Apply constraints
        final_lot = self._apply_lot_constraints(final_lot)
        
        result = LotsizeResult(
            calculated_lot=final_lot,
            original_lot=extracted_lot['value'] if extracted_lot else None,
            risk_mode=mode,
            risk_percent=self.config.default_risk_percent if mode == RiskMode.RISK_PERCENT else None,
            risk_multiplier=risk_multiplier,
            symbol=symbol,
            account_balance=account_balance,
            pip_value=pip_value,
            stop_loss_pips=stop_loss_pips,
            confidence=confidence,
            reasoning=reasoning,
            timestamp=datetime.now()
        )
        
        self.logger.info(f"Calculated lot size: {final_lot} for {symbol} (mode: {mode.value})")
        return result

    def _extract_lot_from_text(self, signal_text: str) -> Optional[Dict[str, Any]]:
        """Extract explicit lot size from signal text"""
        if not signal_text:
            return None
        
        signal_text = signal_text.lower().strip()
        
        for pattern_info in self.lot_patterns:
            match = re.search(pattern_info['pattern'], signal_text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(',', ''))
                    
                    # Convert based on pattern type
                    if pattern_info['type'] == 'fixed_lot':
                        lot_value = value
                    elif pattern_info['type'] == 'risk_percent':
                        # Will be handled by mode calculation
                        continue
                    elif pattern_info['type'] == 'fixed_cash':
                        # Convert cash to approximate lot size (rough estimate)
                        lot_value = value / 100000  # Assume 1 lot = $100k exposure
                    elif pattern_info['type'] == 'pip_value':
                        # Convert pip value to lot size (rough estimate)
                        lot_value = value / 10  # Assume $10 per pip for 1 lot
                    elif pattern_info['type'] == 'balance_percent':
                        # Will be handled by mode calculation
                        continue
                    else:
                        continue
                    
                    return {
                        'value': lot_value,
                        'type': pattern_info['type'],
                        'confidence': pattern_info['confidence']
                    }
                    
                except (ValueError, IndexError):
                    continue
        
        return None

    def _extract_risk_multiplier(self, signal_text: str) -> float:
        """Extract risk multiplier from signal text keywords"""
        if not signal_text:
            return 1.0
        
        signal_text = signal_text.lower()
        
        for pattern, multiplier in self.risk_patterns.items():
            if re.search(pattern, signal_text, re.IGNORECASE):
                self.extraction_stats['risk_detected'] += 1
                return multiplier
        
        return 1.0

    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol in USD"""
        # Try to get from MT5 if available
        if self.mt5_bridge:
            try:
                symbol_info = self.mt5_bridge.get_symbol_info(symbol)
                if symbol_info and 'pip_value' in symbol_info:
                    return symbol_info['pip_value']
            except Exception:
                pass
        
        # Try pip_value_calculator if available
        try:
            return get_pip_value(symbol)
        except Exception:
            pass
        
        # Fall back to configured values
        return self.config.symbol_pip_values.get(symbol, self.config.pip_value_usd)

    def _calculate_lot_by_mode(self, mode: RiskMode, account_balance: float, 
                              pip_value: float, stop_loss_pips: Optional[float], 
                              risk_multiplier: float) -> float:
        """Calculate lot size based on risk mode"""
        if mode == RiskMode.FIXED_LOT:
            return 0.1 * risk_multiplier  # Default fixed lot
        
        elif mode == RiskMode.RISK_PERCENT:
            if stop_loss_pips and stop_loss_pips > 0:
                risk_amount = account_balance * (self.config.default_risk_percent / 100) * risk_multiplier
                lot_size = risk_amount / (stop_loss_pips * pip_value)
                return lot_size
            else:
                # Fallback to balance percentage if no SL
                return account_balance * 0.0001 * risk_multiplier  # 0.01% of balance
        
        elif mode == RiskMode.BALANCE_PERCENT:
            # Risk a percentage of balance
            risk_amount = account_balance * 0.01 * risk_multiplier  # 1% default
            if stop_loss_pips and stop_loss_pips > 0:
                return risk_amount / (stop_loss_pips * pip_value)
            else:
                return risk_amount / 1000  # Assume $10 risk per 0.01 lot
        
        elif mode == RiskMode.FIXED_CASH:
            fixed_amount = 100 * risk_multiplier  # $100 default
            if stop_loss_pips and stop_loss_pips > 0:
                return fixed_amount / (stop_loss_pips * pip_value)
            else:
                return fixed_amount / 1000
        
        elif mode == RiskMode.PIP_VALUE:
            target_pip_value = 10 * risk_multiplier  # $10 per pip default
            return target_pip_value / pip_value
        
        else:
            return 0.1 * risk_multiplier

    def _apply_lot_constraints(self, lot_size: float) -> float:
        """Apply minimum/maximum lot size constraints"""
        constrained = max(self.config.min_lot_size, 
                         min(self.config.max_lot_size, lot_size))
        
        # Round to precision
        return round(constrained, self.config.precision_digits)

    def calculate_position_value(self, lot_size: float, symbol: str, 
                               current_price: Optional[float] = None) -> Dict[str, float]:
        """Calculate position value and exposure"""
        if current_price is None and self.market_data:
            try:
                current_price = self.market_data.get_current_price(symbol)
            except Exception:
                current_price = 1.0  # Fallback
        
        if current_price is None:
            current_price = 1.0
        
        # Standard lot size calculation
        contract_size = 100000  # Standard for forex
        if symbol.startswith('XAU'):  # Gold
            contract_size = 100
        elif symbol.startswith('XAG'):  # Silver
            contract_size = 5000
        
        position_value = lot_size * contract_size * current_price
        pip_value = self._get_pip_value(symbol) * lot_size
        
        return {
            'position_value': position_value,
            'pip_value': pip_value,
            'contract_size': contract_size,
            'lot_size': lot_size,
            'current_price': current_price
        }

    def validate_lot_size(self, lot_size: float, account_balance: float, 
                         margin_requirement: Optional[float] = None) -> Dict[str, Any]:
        """Validate if lot size is safe for account"""
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # Check minimum/maximum constraints
        if lot_size < self.config.min_lot_size:
            validation['errors'].append(f"Lot size {lot_size} below minimum {self.config.min_lot_size}")
            validation['is_valid'] = False
        
        if lot_size > self.config.max_lot_size:
            validation['errors'].append(f"Lot size {lot_size} exceeds maximum {self.config.max_lot_size}")
            validation['is_valid'] = False
        
        # Check margin requirements
        if margin_requirement:
            required_margin = lot_size * margin_requirement
            if required_margin > account_balance * 0.8:  # 80% of balance
                validation['warnings'].append(f"High margin usage: {required_margin:.2f}")
                validation['recommendations'].append("Consider reducing position size")
        
        # Check position size relative to balance
        position_value = lot_size * 100000  # Assume forex
        if position_value > account_balance * 100:  # 100x leverage warning
            validation['warnings'].append("Very high leverage detected")
            validation['recommendations'].append("Verify risk management settings")
        
        return validation

    def get_statistics(self) -> Dict[str, Any]:
        """Get extraction and calculation statistics"""
        return {
            'extraction_stats': self.extraction_stats.copy(),
            'config_summary': {
                'default_mode': self.config.default_mode.value,
                'default_risk_percent': self.config.default_risk_percent,
                'min_lot_size': self.config.min_lot_size,
                'max_lot_size': self.config.max_lot_size
            },
            'supported_modes': [mode.value for mode in RiskMode],
            'pip_values_configured': len(self.config.symbol_pip_values)
        }

    def update_configuration(self, new_config: Dict[str, Any]) -> bool:
        """Update configuration parameters"""
        try:
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # Save to file
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['lotsize_engine'] = asdict(self.config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            self.logger.info("Configuration updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False


def calculate_lot(strategy_config: dict, signal_data: dict, account_balance: float, 
                 sl_pips: float, symbol: str) -> float:
    """
    Calculate lot size based on strategy configuration and signal data
    
    Args:
        strategy_config: Strategy configuration dictionary containing:
            - mode: "fixed" | "risk_percent" | "cash_per_trade" | "pip_value" | "text_override"
            - base_risk: float (base risk amount/percentage)
            - override_keywords: List of keywords for risk multipliers
        signal_data: Signal data dictionary containing:
            - text: Raw signal text
            - Other signal metadata
        account_balance: Current account balance
        sl_pips: Stop loss distance in pips
        symbol: Trading symbol
        
    Returns:
        Calculated lot size as float
    """
    # Create engine instance
    engine = LotsizeEngine()
    
    # Map strategy config mode to engine mode
    mode_mapping = {
        "fixed": "fixed_lot",
        "risk_percent": "risk_percent", 
        "cash_per_trade": "fixed_cash",
        "pip_value": "pip_value",
        "text_override": "fixed_lot"  # Will extract from text
    }
    
    # Get mode from strategy config
    mode = mode_mapping.get(strategy_config.get('mode', 'risk_percent'), 'risk_percent')
    
    # Get signal text
    signal_text = signal_data.get('text', '')
    
    # Use engine to calculate lot size
    result = engine.extract_lotsize(
        signal_text=signal_text,
        risk_mode=mode,
        account_balance=account_balance,
        symbol=symbol,
        stop_loss_pips=sl_pips
    )
    
    return result.calculated_lot


# Legacy compatibility function for strategy_runtime integration
def extract_lotsize(signal_text: str, risk_mode: str = "risk_percent", 
                   account_balance: float = 10000, symbol: str = "EURUSD",
                   stop_loss_pips: Optional[float] = None) -> float:
    """
    Legacy compatibility function for strategy_runtime integration
    
    Returns just the calculated lot size for backward compatibility
    """
    engine = LotsizeEngine()
    result = engine.extract_lotsize(signal_text, risk_mode, account_balance, symbol, stop_loss_pips)
    return result.calculated_lot