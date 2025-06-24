"""
Symbol Mapper for SignalOS
Maps general signal symbols to broker-specific equivalents
Supports dynamic overrides and case-insensitive mapping
"""

import json
import logging
from typing import Dict, Optional, Set
from pathlib import Path

class SymbolMapper:
    """Broker symbol normalizer and mapper"""
    
    def __init__(self, config_file: str = "config/symbol_map.json"):
        self.config_file = config_file
        self.logger = self._setup_logging()
        
        # Load symbol mappings
        self.symbol_map = self._load_symbol_map()
        self.user_overrides = {}
        
        # Statistics
        self.mapping_stats = {
            'total_lookups': 0,
            'successful_mappings': 0,
            'user_override_usage': 0,
            'unknown_symbols': set()
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for symbol mapper"""
        logger = logging.getLogger('SymbolMapper')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_symbol_map(self) -> Dict[str, str]:
        """Load symbol mapping configuration"""
        try:
            config_path = Path(self.config_file)
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    symbol_map = data.get('symbol_mappings', {})
                    self.logger.info(f"Loaded {len(symbol_map)} symbol mappings from {self.config_file}")
                    return symbol_map
            else:
                # Create default mapping file
                return self._create_default_symbol_map()
                
        except Exception as e:
            self.logger.error(f"Failed to load symbol map: {e}")
            return self._get_fallback_symbol_map()
    
    def _create_default_symbol_map(self) -> Dict[str, str]:
        """Create default symbol mapping file"""
        default_mappings = self._get_fallback_symbol_map()
        
        try:
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                "symbol_mappings": default_mappings,
                "description": "Symbol mapping configuration for SignalOS",
                "version": "1.0",
                "last_updated": "2025-01-25"
            }
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            self.logger.info(f"Created default symbol mapping file: {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to create default symbol map: {e}")
        
        return default_mappings
    
    def _get_fallback_symbol_map(self) -> Dict[str, str]:
        """Get fallback symbol mappings (built-in defaults)"""
        return {
            # Metals
            "GOLD": "XAUUSD",
            "SILVER": "XAGUSD", 
            "XAU": "XAUUSD",
            "XAG": "XAGUSD",
            "XAUSD": "XAUUSD",
            "XAGUSD": "XAGUSD",
            
            # Commodities
            "OIL": "USOIL",
            "CRUDE": "USOIL",
            "USOIL": "USOIL",
            "BRENT": "UKOIL",
            "UKOIL": "UKOIL",
            "WTI": "USOIL",
            
            # US Indices
            "DOW": "US30",
            "DJIA": "US30",
            "US30": "US30",
            "NASDAQ": "NAS100",
            "NAS": "NAS100", 
            "NAS100": "NAS100",
            "SPX": "SPX500",
            "SP500": "SPX500",
            "SPX500": "SPX500",
            "S&P500": "SPX500",
            
            # European Indices
            "DAX": "GER30",
            "GER30": "GER30",
            "DE30": "GER30",
            "FTSE": "UK100",
            "UK100": "UK100",
            "FTSE100": "UK100",
            "CAC": "FRA40",
            "FRA40": "FRA40",
            "CAC40": "FRA40",
            
            # Asian Indices
            "NIKKEI": "JPN225",
            "JPN225": "JPN225",
            "N225": "JPN225",
            "HSI": "HK50",
            "HANGSENG": "HK50",
            "ASX": "AUS200",
            "AUS200": "AUS200",
            
            # Crypto (if supported by broker)
            "BITCOIN": "BTCUSD",
            "BTC": "BTCUSD",
            "BTCUSD": "BTCUSD",
            "ETHEREUM": "ETHUSD",
            "ETH": "ETHUSD",
            "ETHUSD": "ETHUSD",
            "LITECOIN": "LTCUSD",
            "LTC": "LTCUSD",
            "LTCUSD": "LTCUSD",
            
            # Forex Majors (usually no mapping needed)
            "EUR/USD": "EURUSD",
            "GBP/USD": "GBPUSD",
            "USD/JPY": "USDJPY",
            "USD/CHF": "USDCHF",
            "AUD/USD": "AUDUSD",
            "NZD/USD": "NZDUSD",
            "USD/CAD": "USDCAD",
            
            # Energy
            "NATGAS": "NGAS",
            "NATURALGAS": "NGAS",
            "GAS": "NGAS",
            
            # Agricultural
            "WHEAT": "WHEAT",
            "CORN": "CORN",
            "SOYBEAN": "SOYBEAN",
            
            # Broker-specific mappings (examples)
            "GOLD.cash": "XAUUSD",
            "SILVER.cash": "XAGUSD",
            "US30.cash": "US30",
            "NAS100.cash": "NAS100",
            "SPX500.cash": "SPX500",
            "GER30.cash": "GER30",
            "UK100.cash": "UK100",
            "OIL.WTI": "USOIL",
            "OIL.BRENT": "UKOIL"
        }
    
    def normalize_symbol(self, input_symbol: str) -> str:
        """
        Normalize input symbol to broker-specific equivalent
        
        Args:
            input_symbol: Input symbol from signal
            
        Returns:
            Normalized broker symbol
        """
        self.mapping_stats['total_lookups'] += 1
        
        if not input_symbol:
            return ""
        
        # Clean and normalize input
        clean_symbol = input_symbol.strip().upper()
        
        # Check user overrides first
        if clean_symbol in self.user_overrides:
            self.mapping_stats['user_override_usage'] += 1
            self.mapping_stats['successful_mappings'] += 1
            mapped_symbol = self.user_overrides[clean_symbol]
            self.logger.debug(f"User override mapping: {input_symbol} -> {mapped_symbol}")
            return mapped_symbol
        
        # Check main symbol map (case-insensitive)
        for key, value in self.symbol_map.items():
            if key.upper() == clean_symbol:
                self.mapping_stats['successful_mappings'] += 1
                self.logger.debug(f"Symbol mapping: {input_symbol} -> {value}")
                return value
        
        # Try partial matches for complex symbols
        mapped_symbol = self._try_partial_mapping(clean_symbol)
        if mapped_symbol != clean_symbol:
            self.mapping_stats['successful_mappings'] += 1
            self.logger.debug(f"Partial mapping: {input_symbol} -> {mapped_symbol}")
            return mapped_symbol
        
        # No mapping found - return original symbol
        self.mapping_stats['unknown_symbols'].add(clean_symbol)
        self.logger.debug(f"No mapping found for: {input_symbol}, returning as-is")
        return clean_symbol
    
    def _try_partial_mapping(self, symbol: str) -> str:
        """Try partial matching for complex symbols"""
        # Remove common suffixes/prefixes
        clean_patterns = [
            ('.CASH', ''), ('.cash', ''),
            ('.CFD', ''), ('.cfd', ''),
            ('_', ''), ('-', ''), (' ', ''),
            ('FUT', ''), ('SPOT', '')
        ]
        
        for suffix, replacement in clean_patterns:
            if suffix in symbol:
                cleaned = symbol.replace(suffix, replacement)
                if cleaned in self.symbol_map:
                    return self.symbol_map[cleaned]
        
        # Try prefix matching for indices
        index_prefixes = {
            'US': ['US30', 'US500', 'US100'],
            'GER': ['GER30', 'GER40'],
            'UK': ['UK100'],
            'FRA': ['FRA40'],
            'JPN': ['JPN225'],
            'AUS': ['AUS200']
        }
        
        for prefix, possible_symbols in index_prefixes.items():
            if symbol.startswith(prefix):
                for possible in possible_symbols:
                    if possible in self.symbol_map:
                        return self.symbol_map[possible]
        
        return symbol
    
    def add_user_override(self, input_symbol: str, mapped_symbol: str) -> bool:
        """
        Add user-specific symbol override
        
        Args:
            input_symbol: Original symbol
            mapped_symbol: Target mapped symbol
            
        Returns:
            True if successfully added
        """
        try:
            clean_input = input_symbol.strip().upper()
            self.user_overrides[clean_input] = mapped_symbol
            self.logger.info(f"Added user override: {clean_input} -> {mapped_symbol}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add user override: {e}")
            return False
    
    def remove_user_override(self, input_symbol: str) -> bool:
        """Remove user override for symbol"""
        try:
            clean_input = input_symbol.strip().upper()
            if clean_input in self.user_overrides:
                del self.user_overrides[clean_input]
                self.logger.info(f"Removed user override for: {clean_input}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to remove user override: {e}")
            return False
    
    def get_user_overrides(self) -> Dict[str, str]:
        """Get all user overrides"""
        return self.user_overrides.copy()
    
    def save_user_overrides(self, file_path: str = "config/user_symbol_overrides.json") -> bool:
        """Save user overrides to file"""
        try:
            override_path = Path(file_path)
            override_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(override_path, 'w') as f:
                json.dump(self.user_overrides, f, indent=4)
            
            self.logger.info(f"Saved {len(self.user_overrides)} user overrides to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save user overrides: {e}")
            return False
    
    def load_user_overrides(self, file_path: str = "config/user_symbol_overrides.json") -> bool:
        """Load user overrides from file"""
        try:
            override_path = Path(file_path)
            
            if override_path.exists():
                with open(override_path, 'r') as f:
                    self.user_overrides = json.load(f)
                
                self.logger.info(f"Loaded {len(self.user_overrides)} user overrides from {file_path}")
                return True
            else:
                self.logger.info(f"No user overrides file found at {file_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to load user overrides: {e}")
            return False
    
    def get_available_symbols(self) -> Set[str]:
        """Get all available input symbols"""
        return set(self.symbol_map.keys()) | set(self.user_overrides.keys())
    
    def get_mapped_symbols(self) -> Set[str]:
        """Get all possible output symbols"""
        return set(self.symbol_map.values()) | set(self.user_overrides.values())
    
    def get_mapping_statistics(self) -> Dict[str, any]:
        """Get symbol mapping statistics"""
        return {
            'total_lookups': self.mapping_stats['total_lookups'],
            'successful_mappings': self.mapping_stats['successful_mappings'],
            'user_override_usage': self.mapping_stats['user_override_usage'],
            'unknown_symbols_count': len(self.mapping_stats['unknown_symbols']),
            'unknown_symbols': list(self.mapping_stats['unknown_symbols']),
            'success_rate': (
                self.mapping_stats['successful_mappings'] / self.mapping_stats['total_lookups']
                if self.mapping_stats['total_lookups'] > 0 else 0
            ),
            'total_mappings': len(self.symbol_map),
            'user_overrides_count': len(self.user_overrides)
        }
    
    def bulk_normalize(self, symbols: list) -> Dict[str, str]:
        """Normalize multiple symbols at once"""
        result = {}
        for symbol in symbols:
            result[symbol] = self.normalize_symbol(symbol)
        return result
    
    def add_bulk_mappings(self, mappings: Dict[str, str]) -> int:
        """Add multiple symbol mappings"""
        added_count = 0
        for input_symbol, mapped_symbol in mappings.items():
            try:
                clean_input = input_symbol.strip().upper()
                self.symbol_map[clean_input] = mapped_symbol
                added_count += 1
            except Exception as e:
                self.logger.warning(f"Failed to add mapping {input_symbol}: {e}")
        
        self.logger.info(f"Added {added_count} bulk mappings")
        return added_count
    
    def clear_statistics(self):
        """Clear mapping statistics"""
        self.mapping_stats = {
            'total_lookups': 0,
            'successful_mappings': 0,
            'user_override_usage': 0,
            'unknown_symbols': set()
        }
        self.logger.info("Mapping statistics cleared")


# Global instance for easy access
_symbol_mapper = None

def normalize_symbol(input_symbol: str) -> str:
    """
    Global function to normalize symbol
    
    Args:
        input_symbol: Input symbol from signal
        
    Returns:
        Normalized broker symbol
    """
    global _symbol_mapper
    
    if _symbol_mapper is None:
        _symbol_mapper = SymbolMapper()
    
    return _symbol_mapper.normalize_symbol(input_symbol)

def add_symbol_override(input_symbol: str, mapped_symbol: str) -> bool:
    """Global function to add symbol override"""
    global _symbol_mapper
    
    if _symbol_mapper is None:
        _symbol_mapper = SymbolMapper()
    
    return _symbol_mapper.add_user_override(input_symbol, mapped_symbol)

def get_symbol_stats() -> Dict[str, any]:
    """Get global symbol mapping statistics"""
    global _symbol_mapper
    
    if _symbol_mapper is None:
        _symbol_mapper = SymbolMapper()
    
    return _symbol_mapper.get_mapping_statistics()