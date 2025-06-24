"""
Pip Value Calculator for SignalOS
Provides pip values per symbol for accurate lot size calculations
Supports broker-specific values and dynamic pip value determination
"""

import json
import logging
from typing import Dict, Optional, Any
from pathlib import Path

class PipValueCalculator:
    """Calculator for pip values across different trading symbols"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.logger = self._setup_logging()
        self.pip_values = self._load_pip_values()
        
        # Injected modules
        self.mt5_bridge = None
        self.market_data = None
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for pip value calculator"""
        logger = logging.getLogger('PipValueCalculator')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_pip_values(self) -> Dict[str, float]:
        """Load pip values from configuration file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    return config_data.get('pip_values', self._get_default_pip_values())
            else:
                return self._get_default_pip_values()
        except Exception as e:
            self.logger.warning(f"Failed to load pip values config: {e}")
            return self._get_default_pip_values()
    
    def _get_default_pip_values(self) -> Dict[str, float]:
        """Get default pip values for common trading symbols"""
        return {
            # Major Forex Pairs
            "EURUSD": 10.0,
            "GBPUSD": 10.0,
            "USDJPY": 9.09,
            "USDCHF": 10.20,
            "AUDUSD": 10.0,
            "NZDUSD": 10.0,
            "USDCAD": 7.69,
            
            # Minor Forex Pairs
            "EURGBP": 12.87,
            "EURJPY": 9.09,
            "GBPJPY": 9.09,
            "EURCHF": 10.20,
            "AUDCAD": 7.69,
            "NZDCAD": 7.69,
            
            # Commodities
            "XAUUSD": 10.0,    # Gold
            "XAGUSD": 50.0,    # Silver
            "USOIL": 10.0,     # Crude Oil
            "UKOIL": 10.0,     # Brent Oil
            
            # Indices
            "US30": 1.0,       # Dow Jones
            "SPX500": 1.0,     # S&P 500
            "NAS100": 1.0,     # Nasdaq
            "UK100": 1.0,      # FTSE 100
            "GER30": 1.0,      # DAX
            "FRA40": 1.0,      # CAC 40
            "JPN225": 1.0,     # Nikkei
            "AUS200": 1.0,     # ASX 200
            
            # Crypto (if supported)
            "BTCUSD": 1.0,
            "ETHUSD": 1.0,
            "LTCUSD": 1.0,
            "XRPUSD": 1.0,
            
            # Exotic Pairs
            "USDZAR": 0.67,    # USD/ZAR
            "USDTRY": 1.15,    # USD/TRY
            "USDSEK": 0.96,    # USD/SEK
            "USDNOK": 0.92,    # USD/NOK
            "USDDKK": 1.37,    # USD/DKK
        }
    
    def inject_modules(self, mt5_bridge=None, market_data=None):
        """Inject module references for live data"""
        self.mt5_bridge = mt5_bridge
        self.market_data = market_data
    
    def get_pip_value(self, symbol: str, account_currency: str = "USD") -> float:
        """
        Get pip value for a specific symbol
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD", "XAUUSD", "US30")
            account_currency: Account currency (default: USD)
            
        Returns:
            Pip value in account currency
        """
        symbol = symbol.upper().strip()
        
        # Try to get from MT5 if available
        if self.mt5_bridge:
            try:
                symbol_info = self.mt5_bridge.get_symbol_info(symbol)
                if symbol_info and 'pip_value' in symbol_info:
                    pip_value = symbol_info['pip_value']
                    self.logger.debug(f"Got pip value from MT5: {symbol} = {pip_value}")
                    return pip_value
            except Exception as e:
                self.logger.debug(f"Failed to get pip value from MT5: {e}")
        
        # Try configured values
        if symbol in self.pip_values:
            pip_value = self.pip_values[symbol]
            self.logger.debug(f"Got pip value from config: {symbol} = {pip_value}")
            return pip_value
        
        # Try symbol aliases
        alias_pip_value = self._get_pip_value_by_alias(symbol)
        if alias_pip_value:
            return alias_pip_value
        
        # Calculate dynamic pip value if possible
        dynamic_pip_value = self._calculate_dynamic_pip_value(symbol, account_currency)
        if dynamic_pip_value:
            return dynamic_pip_value
        
        # Fallback to default
        default_value = 10.0
        self.logger.warning(f"No pip value found for {symbol}, using default: {default_value}")
        return default_value
    
    def _get_pip_value_by_alias(self, symbol: str) -> Optional[float]:
        """Get pip value using symbol aliases"""
        aliases = {
            "GOLD": "XAUUSD",
            "SILVER": "XAGUSD",
            "OIL": "USOIL",
            "BRENT": "UKOIL",
            "DOW": "US30",
            "NASDAQ": "NAS100",
            "SPX": "SPX500",
            "DAX": "GER30",
            "FTSE": "UK100",
            "CAC": "FRA40",
            "NIKKEI": "JPN225",
            "ASX": "AUS200",
            "BITCOIN": "BTCUSD",
            "ETHEREUM": "ETHUSD",
            "LITECOIN": "LTCUSD",
            "RIPPLE": "XRPUSD"
        }
        
        if symbol in aliases:
            actual_symbol = aliases[symbol]
            if actual_symbol in self.pip_values:
                pip_value = self.pip_values[actual_symbol]
                self.logger.debug(f"Got pip value via alias: {symbol} -> {actual_symbol} = {pip_value}")
                return pip_value
        
        return None
    
    def _calculate_dynamic_pip_value(self, symbol: str, account_currency: str) -> Optional[float]:
        """Calculate pip value dynamically based on symbol characteristics"""
        try:
            # For forex pairs
            if len(symbol) == 6 and symbol.isalpha():
                base_currency = symbol[:3]
                quote_currency = symbol[3:]
                
                if quote_currency == account_currency:
                    # Direct quote (e.g., EURUSD for USD account)
                    return 10.0
                elif base_currency == account_currency:
                    # Indirect quote (e.g., USDCAD for USD account)
                    return 7.69  # Approximate
                else:
                    # Cross currency - would need exchange rates
                    return 10.0  # Default approximation
            
            # For indices and commodities
            if symbol.startswith(('US', 'UK', 'GER', 'FRA', 'JPN', 'AUS', 'NAS', 'SPX')):
                return 1.0  # Most indices have $1 per point
            
            # For metals
            if symbol.startswith('XAU'):  # Gold
                return 10.0
            elif symbol.startswith('XAG'):  # Silver
                return 50.0
            
            # For crypto
            if symbol.endswith('USD') and len(symbol) > 6:
                return 1.0
            
        except Exception as e:
            self.logger.debug(f"Failed to calculate dynamic pip value for {symbol}: {e}")
        
        return None
    
    def get_contract_size(self, symbol: str) -> float:
        """Get contract size for symbol"""
        symbol = symbol.upper().strip()
        
        # Try to get from MT5 if available
        if self.mt5_bridge:
            try:
                symbol_info = self.mt5_bridge.get_symbol_info(symbol)
                if symbol_info and 'contract_size' in symbol_info:
                    return symbol_info['contract_size']
            except Exception:
                pass
        
        # Default contract sizes
        contract_sizes = {
            # Forex pairs
            'EURUSD': 100000, 'GBPUSD': 100000, 'USDJPY': 100000,
            'USDCHF': 100000, 'AUDUSD': 100000, 'NZDUSD': 100000,
            'USDCAD': 100000,
            
            # Metals
            'XAUUSD': 100,     # Gold
            'XAGUSD': 5000,    # Silver
            
            # Indices
            'US30': 1, 'SPX500': 1, 'NAS100': 1, 'UK100': 1,
            'GER30': 1, 'FRA40': 1, 'JPN225': 1, 'AUS200': 1,
            
            # Oil
            'USOIL': 1000, 'UKOIL': 1000,
            
            # Crypto
            'BTCUSD': 1, 'ETHUSD': 1, 'LTCUSD': 1, 'XRPUSD': 1
        }
        
        return contract_sizes.get(symbol, 100000)  # Default to standard lot
    
    def add_custom_pip_value(self, symbol: str, pip_value: float, save_to_config: bool = True) -> bool:
        """Add or update custom pip value for a symbol"""
        try:
            symbol = symbol.upper().strip()
            self.pip_values[symbol] = pip_value
            
            if save_to_config:
                self._save_pip_values()
            
            self.logger.info(f"Added custom pip value: {symbol} = {pip_value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add custom pip value: {e}")
            return False
    
    def _save_pip_values(self):
        """Save pip values to configuration file"""
        try:
            config_data = {}
            
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['pip_values'] = self.pip_values
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            self.logger.debug("Pip values saved to config file")
            
        except Exception as e:
            self.logger.error(f"Failed to save pip values: {e}")
    
    def get_all_pip_values(self) -> Dict[str, float]:
        """Get all configured pip values"""
        return self.pip_values.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get calculator statistics"""
        return {
            'total_symbols': len(self.pip_values),
            'has_mt5_integration': self.mt5_bridge is not None,
            'has_market_data': self.market_data is not None,
            'supported_symbol_types': {
                'forex': len([s for s in self.pip_values.keys() if len(s) == 6 and s.isalpha()]),
                'metals': len([s for s in self.pip_values.keys() if s.startswith(('XAU', 'XAG'))]),
                'indices': len([s for s in self.pip_values.keys() if s.startswith(('US', 'UK', 'GER', 'FRA', 'JPN', 'AUS', 'NAS', 'SPX'))]),
                'crypto': len([s for s in self.pip_values.keys() if s.endswith('USD') and len(s) > 6])
            }
        }


# Global instance for easy access
_pip_calculator = None

def get_pip_value(symbol: str, account_currency: str = "USD") -> float:
    """
    Global function to get pip value for a symbol
    
    Args:
        symbol: Trading symbol (e.g., "EURUSD", "XAUUSD", "US30")
        account_currency: Account currency (default: USD)
        
    Returns:
        Pip value in account currency
    """
    global _pip_calculator
    
    if _pip_calculator is None:
        _pip_calculator = PipValueCalculator()
    
    return _pip_calculator.get_pip_value(symbol, account_currency)

def get_contract_size(symbol: str) -> float:
    """
    Global function to get contract size for a symbol
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Contract size for the symbol
    """
    global _pip_calculator
    
    if _pip_calculator is None:
        _pip_calculator = PipValueCalculator()
    
    return _pip_calculator.get_contract_size(symbol)

def add_custom_pip_value(symbol: str, pip_value: float) -> bool:
    """
    Global function to add custom pip value
    
    Args:
        symbol: Trading symbol
        pip_value: Pip value to set
        
    Returns:
        True if successful, False otherwise
    """
    global _pip_calculator
    
    if _pip_calculator is None:
        _pip_calculator = PipValueCalculator()
    
    return _pip_calculator.add_custom_pip_value(symbol, pip_value)