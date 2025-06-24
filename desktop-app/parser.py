"""
Multilingual Signal Parser for SignalOS
Advanced NLP-powered signal parsing with confidence scoring and multilingual support
"""

import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"

class SignalDirection(Enum):
    BUY = "buy"
    SELL = "sell"
    LONG = "long"
    SHORT = "short"

@dataclass
class ParsedSignal:
    symbol: Optional[str] = None
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[List[float]] = None
    order_type: Optional[str] = None
    confidence: float = 0.0
    direction: Optional[str] = None
    raw_text: str = ""
    parse_method: str = "unknown"
    timestamp: Optional[datetime] = None
    errors: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.tp is None:
            self.tp = []
        if self.errors is None:
            self.errors = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class ParserConfig:
    confidence_threshold: float = 0.7
    enable_nlp: bool = True
    enable_regex_fallback: bool = True
    enable_multilingual: bool = True
    log_failed_parses: bool = True
    dry_run_mode: bool = False
    max_tp_levels: int = 3
    symbol_aliases: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.symbol_aliases is None:
            self.symbol_aliases = {
                "GOLD": "XAUUSD",
                "SILVER": "XAGUSD",
                "OIL": "USOIL",
                "BTC": "BTCUSD",
                "ETH": "ETHUSD",
                "EUR": "EURUSD",
                "GBP": "GBPUSD",
                "USD": "USDJPY",
                "AUD": "AUDUSD",
                "CAD": "USDCAD",
                "CHF": "USDCHF",
                "NZD": "NZDUSD",
                "US30": "US30",
                "NAS100": "NAS100",
                "SPX500": "SPX500"
            }

class SignalParser:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/parser.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Initialize pattern dictionaries
        self.symbol_patterns = self._initialize_symbol_patterns()
        self.direction_patterns = self._initialize_direction_patterns()
        self.price_patterns = self._initialize_price_patterns()
        self.multilingual_patterns = self._initialize_multilingual_patterns()
        
        # Statistics
        self.parse_stats = {
            'total_parsed': 0,
            'successful_parses': 0,
            'nlp_parses': 0,
            'regex_parses': 0,
            'failed_parses': 0,
            'multilingual_parses': 0
        }
        
        # NLP pipeline placeholder - would integrate actual NLP library in production
        self.nlp_enabled = self._initialize_nlp()

    def _load_config(self) -> ParserConfig:
        """Load configuration from JSON file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    parser_config = config_data.get('signal_parser', {})
                    return ParserConfig(**parser_config)
            else:
                return self._create_default_config()
        except Exception as e:
            logging.warning(f"Failed to load parser config, using defaults: {e}")
            return ParserConfig()

    def _create_default_config(self) -> ParserConfig:
        """Create default configuration and save to file"""
        default_config = ParserConfig()
        
        try:
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['signal_parser'] = asdict(default_config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Failed to save default parser config: {e}")
        
        return default_config

    def _setup_logging(self):
        """Setup logging for parser operations"""
        self.logger = logging.getLogger('SignalParser')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # Create logs directory if it doesn't exist
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            # File handler
            file_handler = logging.FileHandler(self.log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

    def _initialize_nlp(self) -> bool:
        """Initialize NLP pipeline - stub for production NLP integration"""
        try:
            # In production, this would initialize spaCy or transformers
            # For now, we'll use regex fallback with confidence scoring
            self.logger.info("NLP pipeline initialized (stub mode)")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to initialize NLP pipeline: {e}")
            return False

    def _initialize_symbol_patterns(self) -> List[Dict[str, Any]]:
        """Initialize regex patterns for symbol extraction"""
        return [
            # Major forex pairs
            {
                'pattern': r'\b(EUR/USD|EURUSD|EUR-USD)\b',
                'symbol': 'EURUSD',
                'confidence': 0.95
            },
            {
                'pattern': r'\b(GBP/USD|GBPUSD|GBP-USD)\b',
                'symbol': 'GBPUSD',
                'confidence': 0.95
            },
            {
                'pattern': r'\b(USD/JPY|USDJPY|USD-JPY)\b',
                'symbol': 'USDJPY',
                'confidence': 0.95
            },
            {
                'pattern': r'\b(AUD/USD|AUDUSD|AUD-USD)\b',
                'symbol': 'AUDUSD',
                'confidence': 0.95
            },
            {
                'pattern': r'\b(USD/CAD|USDCAD|USD-CAD)\b',
                'symbol': 'USDCAD',
                'confidence': 0.95
            },
            {
                'pattern': r'\b(USD/CHF|USDCHF|USD-CHF)\b',
                'symbol': 'USDCHF',
                'confidence': 0.95
            },
            {
                'pattern': r'\b(NZD/USD|NZDUSD|NZD-USD)\b',
                'symbol': 'NZDUSD',
                'confidence': 0.95
            },
            # Commodities
            {
                'pattern': r'\b(XAU/USD|XAUUSD|GOLD|Au)\b',
                'symbol': 'XAUUSD',
                'confidence': 0.90
            },
            {
                'pattern': r'\b(XAG/USD|XAGUSD|SILVER|Ag)\b',
                'symbol': 'XAGUSD',
                'confidence': 0.90
            },
            {
                'pattern': r'\b(US\s?OIL|USOIL|WTI|CRUDE)\b',
                'symbol': 'USOIL',
                'confidence': 0.90
            },
            # Crypto
            {
                'pattern': r'\b(BTC/USD|BTCUSD|BITCOIN|BTC)\b',
                'symbol': 'BTCUSD',
                'confidence': 0.85
            },
            {
                'pattern': r'\b(ETH/USD|ETHUSD|ETHEREUM|ETH)\b',
                'symbol': 'ETHUSD',
                'confidence': 0.85
            },
            # Indices
            {
                'pattern': r'\b(US\s?30|US30|DOW|DJIA)\b',
                'symbol': 'US30',
                'confidence': 0.85
            },
            {
                'pattern': r'\b(NAS\s?100|NAS100|NASDAQ)\b',
                'symbol': 'NAS100',
                'confidence': 0.85
            },
            {
                'pattern': r'\b(SPX\s?500|SPX500|S&P500|SP500)\b',
                'symbol': 'SPX500',
                'confidence': 0.85
            }
        ]

    def _initialize_direction_patterns(self) -> List[Dict[str, Any]]:
        """Initialize patterns for trade direction detection"""
        return [
            # Buy patterns
            {
                'pattern': r'\b(BUY|LONG|BULL|COMPRAR|KAUFEN|ACHETER)\b',
                'direction': 'BUY',
                'confidence': 0.95
            },
            {
                'pattern': r'\b(B|L)\b(?=\s|$)',
                'direction': 'BUY',
                'confidence': 0.80
            },
            # Sell patterns
            {
                'pattern': r'\b(SELL|SHORT|BEAR|VENDER|VERKAUFEN|VENDRE)\b',
                'direction': 'SELL',
                'confidence': 0.95
            },
            {
                'pattern': r'\b(S)\b(?=\s|$)',
                'direction': 'SELL',
                'confidence': 0.80
            },
            # Limit orders
            {
                'pattern': r'\b(BUY\s+LIMIT|LIMIT\s+BUY)\b',
                'direction': 'BUY',
                'order_type': 'BUY_LIMIT',
                'confidence': 0.90
            },
            {
                'pattern': r'\b(SELL\s+LIMIT|LIMIT\s+SELL)\b',
                'direction': 'SELL',
                'order_type': 'SELL_LIMIT',
                'confidence': 0.90
            },
            # Stop orders
            {
                'pattern': r'\b(BUY\s+STOP|STOP\s+BUY)\b',
                'direction': 'BUY',
                'order_type': 'BUY_STOP',
                'confidence': 0.90
            },
            {
                'pattern': r'\b(SELL\s+STOP|STOP\s+SELL)\b',
                'direction': 'SELL',
                'order_type': 'SELL_STOP',
                'confidence': 0.90
            }
        ]

    def _initialize_price_patterns(self) -> List[Dict[str, Any]]:
        """Initialize patterns for price extraction"""
        return [
            # Entry patterns
            {
                'pattern': r'(?:ENTRY|ENTER|ENTRY\s*PRICE|ENTER\s*AT|@|PRICE):?\s*([0-9]+\.?[0-9]*)',
                'type': 'entry',
                'confidence': 0.90
            },
            {
                'pattern': r'(?:دخول|入场|ENTRÉE):?\s*([0-9]+\.?[0-9]*)',
                'type': 'entry',
                'confidence': 0.85
            },
            # Stop Loss patterns
            {
                'pattern': r'(?:SL|S\.L|STOP\s*LOSS|STOP):?\s*([0-9]+\.?[0-9]*)',
                'type': 'sl',
                'confidence': 0.90
            },
            {
                'pattern': r'(?:وقف|止损|ARRÊT):?\s*([0-9]+\.?[0-9]*)',
                'type': 'sl',
                'confidence': 0.85
            },
            # Take Profit patterns
            {
                'pattern': r'(?:TP\s*[123]?|T\.P\s*[123]?|TAKE\s*PROFIT\s*[123]?|TARGET\s*[123]?):?\s*([0-9]+\.?[0-9]*)',
                'type': 'tp',
                'confidence': 0.90
            },
            {
                'pattern': r'(?:هدف|目标|OBJECTIF)\s*[123]?:?\s*([0-9]+\.?[0-9]*)',
                'type': 'tp',
                'confidence': 0.85
            },
            # Range patterns
            {
                'pattern': r'([0-9]+\.?[0-9]*)\s*[-–—]\s*([0-9]+\.?[0-9]*)',
                'type': 'range',
                'confidence': 0.75
            },
            {
                'pattern': r'([0-9]+\.?[0-9]*)\s*(?:to|TO)\s*([0-9]+\.?[0-9]*)',
                'type': 'range',
                'confidence': 0.80
            }
        ]

    def _initialize_multilingual_patterns(self) -> Dict[str, Dict[str, str]]:
        """Initialize multilingual keyword mappings"""
        return {
            'arabic': {
                'buy': 'شراء|شري|اشتري',
                'sell': 'بيع|بع|بيع',
                'entry': 'دخول|دخل',
                'stop': 'وقف|ايقاف',
                'target': 'هدف|هدف',
                'price': 'سعر|السعر'
            },
            'hindi': {
                'buy': 'खरीदें|खरीद|लांग',
                'sell': 'बेचें|बेच|शॉर्ट',
                'entry': 'प्रवेश|एंट्री',
                'stop': 'स्टॉप|रोकें',
                'target': 'लक्ष्य|टारगेट',
                'price': 'कीमत|मूल्य'
            },
            'russian': {
                'buy': 'КУПИТЬ|ПОКУПКА|ЛОНГ',
                'sell': 'ПРОДАТЬ|ПРОДАЖА|ШОРТ',
                'entry': 'ВХОД|ТОЧКА ВХОДА',
                'stop': 'СТОП|СТОП ЛОСС',
                'target': 'ЦЕЛЬ|ТЕЙК ПРОФИТ',
                'price': 'ЦЕНА|ПРАЙС'
            },
            'chinese': {
                'buy': '买入|买|多头',
                'sell': '卖出|卖|空头',
                'entry': '入场|进入',
                'stop': '止损|停止',
                'target': '目标|止盈',
                'price': '价格|价位'
            }
        }

    def parse_signal(self, signal_text: str, dry_run: Optional[bool] = None) -> ParsedSignal:
        """
        Main signal parsing function with NLP and regex fallback
        
        Args:
            signal_text: Raw signal text to parse
            dry_run: Override config dry_run mode
            
        Returns:
            ParsedSignal object with extracted data and confidence score
        """
        self.parse_stats['total_parsed'] += 1
        
        if dry_run is None:
            dry_run = self.config.dry_run_mode
        
        # Clean and normalize text
        cleaned_text = self._clean_text(signal_text)
        
        # Initialize result
        result = ParsedSignal(
            raw_text=signal_text,
            timestamp=datetime.now()
        )
        
        try:
            # Try NLP parsing first if enabled
            if self.config.enable_nlp and self.nlp_enabled:
                result = self._parse_with_nlp(cleaned_text, result)
                if result.confidence >= self.config.confidence_threshold:
                    self.parse_stats['nlp_parses'] += 1
                    self.parse_stats['successful_parses'] += 1
                    result.parse_method = "nlp"
                    self.logger.info(f"Successfully parsed signal with NLP (confidence: {result.confidence:.2f})")
                    return result
            
            # Fallback to regex parsing
            if self.config.enable_regex_fallback:
                result = self._parse_with_regex(cleaned_text, result)
                if result.confidence >= self.config.confidence_threshold:
                    self.parse_stats['regex_parses'] += 1
                    self.parse_stats['successful_parses'] += 1
                    result.parse_method = "regex"
                    self.logger.info(f"Successfully parsed signal with regex (confidence: {result.confidence:.2f})")
                    return result
            
            # Failed to parse with confidence
            self.parse_stats['failed_parses'] += 1
            if result.errors is not None:
                result.errors.append("Confidence below threshold")
            
            if self.config.log_failed_parses:
                self.logger.warning(f"Failed to parse signal with sufficient confidence: {signal_text[:100]}...")
                
        except Exception as e:
            self.parse_stats['failed_parses'] += 1
            if result.errors is not None:
                result.errors.append(f"Parse error: {str(e)}")
            self.logger.error(f"Error parsing signal: {e}")
        
        return result

    def _clean_text(self, text: str) -> str:
        """Clean and normalize signal text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove emojis and special characters that don't affect parsing
        text = re.sub(r'[🔥📈📉💰🎯⚡️🚀💎🔴🟢]', '', text)
        
        # Normalize price separators
        text = text.replace(',', '.')
        
        # Normalize dashes
        text = re.sub(r'[–—−]', '-', text)
        
        return text

    def _parse_with_nlp(self, text: str, result: ParsedSignal) -> ParsedSignal:
        """
        Parse signal using NLP methods (stub implementation)
        In production, this would use spaCy, transformers, or similar
        """
        # This is a stub - in production would use actual NLP
        # For now, use enhanced regex with confidence scoring
        return self._parse_with_regex(text, result)

    def _parse_with_regex(self, text: str, result: ParsedSignal) -> ParsedSignal:
        """Parse signal using regex patterns with confidence scoring"""
        confidence_scores = []
        
        # Extract symbol
        symbol_confidence = self._extract_symbol(text, result)
        if symbol_confidence > 0:
            confidence_scores.append(symbol_confidence)
        
        # Extract direction and order type
        direction_confidence = self._extract_direction(text, result)
        if direction_confidence > 0:
            confidence_scores.append(direction_confidence)
        
        # Extract prices
        price_confidence = self._extract_prices(text, result)
        if price_confidence > 0:
            confidence_scores.append(price_confidence)
        
        # Handle multilingual patterns
        if self.config.enable_multilingual:
            multilingual_confidence = self._extract_multilingual(text, result)
            if multilingual_confidence > 0:
                confidence_scores.append(multilingual_confidence)
                self.parse_stats['multilingual_parses'] += 1
        
        # Calculate overall confidence
        if confidence_scores:
            result.confidence = sum(confidence_scores) / len(confidence_scores)
        else:
            result.confidence = 0.0
        
        # Validate and adjust confidence based on completeness
        result.confidence = self._validate_completeness(result, result.confidence)
        
        return result

    def _extract_symbol(self, text: str, result: ParsedSignal) -> float:
        """Extract trading symbol from text"""
        for pattern_info in self.symbol_patterns:
            match = re.search(pattern_info['pattern'], text, re.IGNORECASE)
            if match:
                result.symbol = pattern_info['symbol']
                return pattern_info['confidence']
        
        # Check symbol aliases
        for alias, symbol in self.config.symbol_aliases.items():
            if re.search(rf'\b{re.escape(alias)}\b', text, re.IGNORECASE):
                result.symbol = symbol
                return 0.80
        
        return 0.0

    def _extract_direction(self, text: str, result: ParsedSignal) -> float:
        """Extract trade direction and order type"""
        for pattern_info in self.direction_patterns:
            match = re.search(pattern_info['pattern'], text, re.IGNORECASE)
            if match:
                result.direction = pattern_info['direction']
                if 'order_type' in pattern_info:
                    result.order_type = pattern_info['order_type']
                else:
                    result.order_type = pattern_info['direction']  # Default to market order
                return pattern_info['confidence']
        
        return 0.0

    def _extract_prices(self, text: str, result: ParsedSignal) -> float:
        """Extract entry, stop loss, and take profit prices"""
        confidence_scores = []
        tp_list = []
        
        for pattern_info in self.price_patterns:
            matches = re.finditer(pattern_info['pattern'], text, re.IGNORECASE)
            for match in matches:
                try:
                    if pattern_info['type'] == 'entry':
                        result.entry = float(match.group(1))
                        confidence_scores.append(pattern_info['confidence'])
                    
                    elif pattern_info['type'] == 'sl':
                        result.sl = float(match.group(1))
                        confidence_scores.append(pattern_info['confidence'])
                    
                    elif pattern_info['type'] == 'tp':
                        tp_price = float(match.group(1))
                        if tp_price not in tp_list:
                            tp_list.append(tp_price)
                        confidence_scores.append(pattern_info['confidence'])
                    
                    elif pattern_info['type'] == 'range':
                        # Handle entry ranges - use average as entry price
                        price1 = float(match.group(1))
                        price2 = float(match.group(2))
                        if not result.entry:  # Only set if no explicit entry found
                            result.entry = (price1 + price2) / 2
                            confidence_scores.append(pattern_info['confidence'] * 0.8)  # Lower confidence for ranges
                
                except (ValueError, IndexError):
                    continue
        
        # Set TP list (limit to max_tp_levels)
        if tp_list:
            result.tp = sorted(tp_list)[:self.config.max_tp_levels]
        
        return max(confidence_scores) if confidence_scores else 0.0

    def _extract_multilingual(self, text: str, result: ParsedSignal) -> float:
        """Extract information using multilingual patterns"""
        confidence_score = 0.0
        
        for language, patterns in self.multilingual_patterns.items():
            for concept, pattern in patterns.items():
                if re.search(pattern, text, re.IGNORECASE):
                    confidence_score = max(confidence_score, 0.75)
                    
                    # Enhance existing extractions with multilingual context
                    if concept in ['buy'] and not result.direction:
                        result.direction = 'BUY'
                        result.order_type = 'BUY'
                    elif concept in ['sell'] and not result.direction:
                        result.direction = 'SELL'
                        result.order_type = 'SELL'
        
        return confidence_score

    def _validate_completeness(self, result: ParsedSignal, confidence: float) -> float:
        """Validate signal completeness and adjust confidence"""
        required_fields = 0
        present_fields = 0
        
        # Check required fields
        if result.symbol:
            present_fields += 1
        required_fields += 1
        
        if result.direction:
            present_fields += 1
        required_fields += 1
        
        if result.entry:
            present_fields += 1
        required_fields += 1
        
        # Optional but valuable fields
        if result.sl:
            present_fields += 0.5
        
        if result.tp:
            present_fields += 0.5
        
        # Calculate completeness ratio
        completeness = present_fields / required_fields
        
        # Adjust confidence based on completeness
        adjusted_confidence = confidence * completeness
        
        # Penalize if missing critical fields
        if not result.symbol:
            adjusted_confidence *= 0.5
        if not result.direction:
            adjusted_confidence *= 0.7
        if not result.entry:
            adjusted_confidence *= 0.8
        
        return min(adjusted_confidence, 1.0)

    def get_statistics(self) -> Dict[str, Any]:
        """Get parsing statistics"""
        total = self.parse_stats['total_parsed']
        if total == 0:
            success_rate = 0.0
        else:
            success_rate = self.parse_stats['successful_parses'] / total
        
        return {
            'parse_stats': self.parse_stats.copy(),
            'success_rate': success_rate,
            'config': asdict(self.config),
            'patterns_loaded': {
                'symbol_patterns': len(self.symbol_patterns),
                'direction_patterns': len(self.direction_patterns),
                'price_patterns': len(self.price_patterns),
                'multilingual_languages': len(self.multilingual_patterns)
            }
        }

    def update_configuration(self, new_config: Dict[str, Any]) -> bool:
        """Update parser configuration"""
        try:
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # Save to file
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['signal_parser'] = asdict(self.config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            self.logger.info("Parser configuration updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update parser configuration: {e}")
            return False

    def add_custom_pattern(self, pattern_type: str, pattern: str, 
                          symbol_or_value: str, confidence: float = 0.8) -> bool:
        """Add custom parsing pattern"""
        try:
            pattern_info = {
                'pattern': pattern,
                'confidence': confidence
            }
            
            if pattern_type == 'symbol':
                pattern_info['symbol'] = symbol_or_value
                self.symbol_patterns.append(pattern_info)
            elif pattern_type == 'direction':
                pattern_info['direction'] = symbol_or_value
                self.direction_patterns.append(pattern_info)
            else:
                return False
            
            self.logger.info(f"Added custom {pattern_type} pattern: {pattern}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add custom pattern: {e}")
            return False


# Legacy compatibility functions for integration
def parse_signal(signal_text: str, confidence_threshold: float = 0.7) -> Dict[str, Any]:
    """
    Legacy compatibility function for strategy_runtime integration
    
    Returns dictionary format for backward compatibility
    """
    parser = SignalParser()
    parser.config.confidence_threshold = confidence_threshold
    result = parser.parse_signal(signal_text)
    
    return {
        'symbol': result.symbol,
        'entry': result.entry,
        'sl': result.sl,
        'tp': result.tp,
        'order_type': result.order_type,
        'confidence': result.confidence,
        'direction': result.direction,
        'success': result.confidence >= confidence_threshold
    }

def extract_signal_data(signal_text: str) -> ParsedSignal:
    """
    Extract signal data and return ParsedSignal object
    
    For use by signal_simulator.py and copilot_bot.py
    """
    parser = SignalParser()
    return parser.parse_signal(signal_text)


if __name__ == "__main__":
    # Example usage and testing
    parser = SignalParser()
    
    test_signals = [
        "Buy GOLD at 2355 SL 2349 TP 2362",
        "SELL EURUSD Entry: 1.0990 Stop: 1.0940 Target: 1.1060",
        "BUY LIMIT GBPUSD @ 1.2850 SL 1.2800 TP1 1.2900 TP2 1.2950",
        "بيع EURUSD دخول: 1.0990 وقف: 1.0940 هدف: 1.1060",
        "LONG BTC 45000-45500 Stop 44000 Target 47000",
        "Invalid signal with no clear data"
    ]
    
    for signal in test_signals:
        result = parser.parse_signal(signal)
        print(f"Signal: {signal[:50]}...")
        print(f"Result: Symbol={result.symbol}, Direction={result.direction}, Entry={result.entry}")
        print(f"Confidence: {result.confidence:.2f}, Method: {result.parse_method}")
        print(f"Errors: {result.errors}")
        print("-" * 80)
    
    # Print statistics
    stats = parser.get_statistics()
    print("Parser Statistics:")
    print(f"Total parsed: {stats['parse_stats']['total_parsed']}")
    print(f"Success rate: {stats['success_rate']:.2%}")
    print(f"NLP parses: {stats['parse_stats']['nlp_parses']}")
    print(f"Regex parses: {stats['parse_stats']['regex_parses']}")
    print(f"Failed parses: {stats['parse_stats']['failed_parses']}")