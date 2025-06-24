"""
Magic Number Hider for SignalOS
Generates consistent but obfuscated magic numbers for MT5 trades to avoid prop firm detection
"""

import hashlib
import logging
import json
import random
from datetime import datetime
from typing import Dict, Optional, Tuple
from pathlib import Path


class MagicNumberHider:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/magic.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self.magic_history: Dict[str, int] = {}
        
        self._setup_logging()
        self._load_magic_history()
        
        # Injected modules
        self.mt5_bridge = None
        self.strategy_runtime = None

    def _load_config(self) -> Dict[str, any]:
        """Load configuration from JSON file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    return config_data.get('magic_number_hider', self._create_default_config())
            else:
                return self._create_default_config()
        except Exception as e:
            logging.warning(f"Failed to load magic number config: {e}")
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, any]:
        """Create default magic number configuration"""
        default_config = {
            'base_magic_range': [100000, 999999],
            'stealth_mode': True,
            'random_suffix_enabled': True,
            'random_suffix_range': [10, 99],
            'per_user_salt': True,
            'hash_algorithm': 'md5',
            'log_magic_numbers': True
        }
        
        try:
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['magic_number_hider'] = default_config
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            logging.error(f"Failed to save default magic number config: {e}")
        
        return default_config

    def _setup_logging(self):
        """Setup logging for magic number operations"""
        self.logger = logging.getLogger('MagicNumberHider')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _load_magic_history(self):
        """Load magic number history from log file"""
        try:
            if Path(self.log_file).exists():
                with open(self.log_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            try:
                                data = json.loads(line.strip())
                                key = f"{data['symbol']}_{data['user_id']}"
                                self.magic_history[key] = data['magic_number']
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            self.logger.warning(f"Failed to load magic number history: {e}")

    def _save_magic_number_log(self, symbol: str, user_id: str, magic_number: int):
        """Save magic number to log file"""
        if not self.config.get('log_magic_numbers', True):
            return
            
        try:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'user_id': user_id,
                'magic_number': magic_number,
                'stealth_mode': self.config.get('stealth_mode', True)
            }
            
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to save magic number log: {e}")

    def inject_modules(self, mt5_bridge=None, strategy_runtime=None):
        """Inject module references"""
        self.mt5_bridge = mt5_bridge
        self.strategy_runtime = strategy_runtime
        self.logger.info("Magic number hider modules injected")

    def generate_magic_number(self, symbol: str, user_id: str) -> int:
        """
        Generate consistent 5-6 digit hash for same symbol/user combo
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            user_id: User identifier
            
        Returns:
            Consistent magic number for the symbol/user combination
        """
        # Create cache key
        cache_key = f"{symbol}_{user_id}"
        
        # Return cached magic number if exists
        if cache_key in self.magic_history:
            cached_magic = self.magic_history[cache_key]
            self.logger.debug(f"Using cached magic number {cached_magic} for {cache_key}")
            return cached_magic
        
        # Generate new magic number
        magic_number = self._calculate_magic_number(symbol, user_id)
        
        # Cache the result
        self.magic_history[cache_key] = magic_number
        
        # Log the magic number
        self._save_magic_number_log(symbol, user_id, magic_number)
        
        self.logger.info(f"Generated magic number {magic_number} for {symbol} (user: {user_id})")
        
        return magic_number

    def _calculate_magic_number(self, symbol: str, user_id: str) -> int:
        """Calculate deterministic magic number from symbol and user ID"""
        # Create consistent input string
        if self.config.get('per_user_salt', True):
            input_string = f"{symbol}_{user_id}_{self.config.get('hash_algorithm', 'md5')}"
        else:
            input_string = f"{symbol}_{self.config.get('hash_algorithm', 'md5')}"
        
        # Generate hash
        hash_algorithm = self.config.get('hash_algorithm', 'md5')
        if hash_algorithm == 'md5':
            hash_obj = hashlib.md5(input_string.encode())
        elif hash_algorithm == 'sha256':
            hash_obj = hashlib.sha256(input_string.encode())
        else:
            hash_obj = hashlib.md5(input_string.encode())  # Fallback to md5
        
        # Convert hash to integer within range
        hash_hex = hash_obj.hexdigest()
        hash_int = int(hash_hex[:8], 16)  # Use first 8 hex chars
        
        # Map to configured range
        min_magic, max_magic = self.config.get('base_magic_range', [100000, 999999])
        magic_base = min_magic + (hash_int % (max_magic - min_magic + 1))
        
        # Add random suffix if stealth mode enabled
        if self.config.get('stealth_mode', True) and self.config.get('random_suffix_enabled', True):
            # Use symbol as seed for reproducible randomness
            random.seed(hash_int)
            suffix_min, suffix_max = self.config.get('random_suffix_range', [10, 99])
            random_suffix = random.randint(suffix_min, suffix_max)
            
            # Combine base magic with suffix
            magic_number = int(f"{magic_base}{random_suffix}")
            
            # Ensure within 5-6 digit range
            while magic_number > 999999:
                magic_number = int(str(magic_number)[:-1])
            while magic_number < 100000:
                magic_number = magic_number * 10
                
        else:
            magic_number = magic_base
        
        return magic_number

    def get_magic_for_trade(self, symbol: str, user_id: str, trade_type: str = "standard") -> int:
        """Get magic number for a specific trade with optional type differentiation"""
        if trade_type != "standard":
            # For different trade types, append type to input
            modified_symbol = f"{symbol}_{trade_type}"
            return self.generate_magic_number(modified_symbol, user_id)
        
        return self.generate_magic_number(symbol, user_id)

    def clear_magic_cache(self, symbol: Optional[str] = None, user_id: Optional[str] = None):
        """Clear magic number cache for specific symbol/user or all"""
        if symbol and user_id:
            cache_key = f"{symbol}_{user_id}"
            if cache_key in self.magic_history:
                del self.magic_history[cache_key]
                self.logger.info(f"Cleared magic cache for {cache_key}")
        else:
            self.magic_history.clear()
            self.logger.info("Cleared all magic number cache")

    def get_magic_statistics(self) -> Dict[str, any]:
        """Get statistics about generated magic numbers"""
        if not self.magic_history:
            return {
                'total_generated': 0,
                'unique_symbols': 0,
                'unique_users': 0,
                'range_distribution': {}
            }
        
        symbols = set()
        users = set()
        magic_values = list(self.magic_history.values())
        
        for key in self.magic_history.keys():
            symbol, user = key.split('_', 1)
            symbols.add(symbol)
            users.add(user)
        
        # Analyze magic number distribution
        range_100k = sum(1 for m in magic_values if 100000 <= m < 200000)
        range_200k = sum(1 for m in magic_values if 200000 <= m < 300000)
        range_300k = sum(1 for m in magic_values if 300000 <= m < 400000)
        range_400k_plus = sum(1 for m in magic_values if m >= 400000)
        
        return {
            'total_generated': len(self.magic_history),
            'unique_symbols': len(symbols),
            'unique_users': len(users),
            'range_distribution': {
                '100k-199k': range_100k,
                '200k-299k': range_200k,
                '300k-399k': range_300k,
                '400k+': range_400k_plus
            },
            'stealth_mode_enabled': self.config.get('stealth_mode', True),
            'random_suffix_enabled': self.config.get('random_suffix_enabled', True)
        }


# Global instance for easy access
magic_number_hider = MagicNumberHider()


def generate_magic_number(symbol: str, user_id: str) -> int:
    """Convenience function for generating magic numbers"""
    return magic_number_hider.generate_magic_number(symbol, user_id)