#!/usr/bin/env python3
"""
Configuration-based Signal Parser for SignalOS Desktop Application

Regex-based fallback parser that uses configuration patterns for signal parsing.
This serves as the backup when AI parsing fails or is not available.
"""

import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

class PatternType(Enum):
    """Pattern types for signal parsing"""
    SYMBOL = "symbol"
    DIRECTION = "direction"
    ENTRY = "entry"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    RANGE = "range"
    ORDER_TYPE = "order_type"

@dataclass
class ParsePattern:
    """Individual parsing pattern"""
    pattern_type: PatternType
    regex: str
    confidence: float
    language: str = "en"
    description: str = ""
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []

@dataclass
class ParseResult:
    """Result of pattern-based parsing"""
    matched_value: str
    confidence: float
    pattern_used: str
    position: Tuple[int, int]
    language: str

class ConfigParser:
    """Configuration-based regex parser for signal parsing"""
    
    def __init__(self, config_file: str = "config.json", patterns_file: str = "config/parser_patterns.json"):
        self.config_file = config_file
        self.patterns_file = patterns_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Load parsing patterns
        self.patterns = self._load_patterns()
        self.compiled_patterns = self._compile_patterns()
        
        # Statistics
        self.stats = {
            "total_parses": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "pattern_hits": {},
            "confidence_distribution": {"high": 0, "medium": 0, "low": 0}
        }
        
        self.logger.info("Configuration parser initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('config_parser', {
                    'min_confidence': 0.7,
                    'enable_fuzzy_matching': True,
                    'case_sensitive': False,
                    'max_patterns_per_type': 50
                })
        except Exception as e:
            logging.warning(f"Failed to load config: {e}")
            return {'min_confidence': 0.7, 'enable_fuzzy_matching': True, 'case_sensitive': False}
    
    def _setup_logging(self):
        """Setup logging"""
        self.logger = logging.getLogger('ConfigParser')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            log_path = Path("logs/config_parser.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            handler = logging.FileHandler(log_path)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _load_patterns(self) -> Dict[PatternType, List[ParsePattern]]:
        """Load parsing patterns from configuration"""
        patterns = {pattern_type: [] for pattern_type in PatternType}
        
        try:
            # Try to load from file first
            if Path(self.patterns_file).exists():
                with open(self.patterns_file, 'r') as f:
                    pattern_data = json.load(f)
                    
                    for pattern_type_str, pattern_list in pattern_data.items():
                        pattern_type = PatternType(pattern_type_str)
                        for pattern_dict in pattern_list:
                            pattern = ParsePattern(
                                pattern_type=pattern_type,
                                regex=pattern_dict['regex'],
                                confidence=pattern_dict.get('confidence', 0.5),
                                language=pattern_dict.get('language', 'en'),
                                description=pattern_dict.get('description', ''),
                                examples=pattern_dict.get('examples', [])
                            )
                            patterns[pattern_type].append(pattern)
            
            # If no file exists, create default patterns
            if not any(patterns.values()):
                patterns = self._create_default_patterns()
                self._save_patterns(patterns)
                
        except Exception as e:
            self.logger.error(f"Failed to load patterns: {e}")
            patterns = self._create_default_patterns()
        
        return patterns
    
    def _create_default_patterns(self) -> Dict[PatternType, List[ParsePattern]]:
        """Create default parsing patterns"""
        patterns = {pattern_type: [] for pattern_type in PatternType}
        
        # Symbol patterns
        patterns[PatternType.SYMBOL] = [
            ParsePattern(PatternType.SYMBOL, r'\b(EUR/USD|EURUSD|EUR-USD)\b', 0.95, 'en', 'EURUSD pair'),
            ParsePattern(PatternType.SYMBOL, r'\b(GBP/USD|GBPUSD|GBP-USD)\b', 0.95, 'en', 'GBPUSD pair'),
            ParsePattern(PatternType.SYMBOL, r'\b(USD/JPY|USDJPY|USD-JPY)\b', 0.95, 'en', 'USDJPY pair'),
            ParsePattern(PatternType.SYMBOL, r'\b(XAU/USD|XAUUSD|GOLD|Au)\b', 0.90, 'en', 'Gold'),
            ParsePattern(PatternType.SYMBOL, r'\b(XAG/USD|XAGUSD|SILVER|Ag)\b', 0.90, 'en', 'Silver'),
            ParsePattern(PatternType.SYMBOL, r'\b(US\s?30|US30|DOW)\b', 0.85, 'en', 'Dow Jones'),
            ParsePattern(PatternType.SYMBOL, r'\b(NAS\s?100|NAS100|NASDAQ)\b', 0.85, 'en', 'Nasdaq'),
            ParsePattern(PatternType.SYMBOL, r'\b(BTC/USD|BTCUSD|BITCOIN)\b', 0.85, 'en', 'Bitcoin'),
        ]
        
        # Direction patterns
        patterns[PatternType.DIRECTION] = [
            ParsePattern(PatternType.DIRECTION, r'\b(BUY|LONG|BULL|B)\b', 0.95, 'en', 'Buy direction'),
            ParsePattern(PatternType.DIRECTION, r'\b(SELL|SHORT|BEAR|S)\b', 0.95, 'en', 'Sell direction'),
            ParsePattern(PatternType.DIRECTION, r'\b(COMPRAR|LARGO)\b', 0.90, 'es', 'Buy in Spanish'),
            ParsePattern(PatternType.DIRECTION, r'\b(VENDER|CORTO)\b', 0.90, 'es', 'Sell in Spanish'),
            ParsePattern(PatternType.DIRECTION, r'\b(شراء|شري|طويل)\b', 0.90, 'ar', 'Buy in Arabic'),
            ParsePattern(PatternType.DIRECTION, r'\b(بيع|قصير)\b', 0.90, 'ar', 'Sell in Arabic'),
        ]
        
        # Entry patterns
        patterns[PatternType.ENTRY] = [
            ParsePattern(PatternType.ENTRY, r'(?:ENTRY|ENTER|@|AT|PRICE)[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'en', 'Entry price'),
            ParsePattern(PatternType.ENTRY, r'(?:ENTRADA|PRECIO)[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'es', 'Entry price Spanish'),
            ParsePattern(PatternType.ENTRY, r'(?:دخول|سعر)[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'ar', 'Entry price Arabic'),
            ParsePattern(PatternType.ENTRY, r'(?:进入|价格)[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'zh', 'Entry price Chinese'),
            ParsePattern(PatternType.ENTRY, r'(?:ENTRÉE|PRIX)[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'fr', 'Entry price French'),
        ]
        
        # Stop Loss patterns
        patterns[PatternType.STOP_LOSS] = [
            ParsePattern(PatternType.STOP_LOSS, r'(?:SL|S\.L|STOP\s*LOSS|STOP)[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'en', 'Stop loss'),
            ParsePattern(PatternType.STOP_LOSS, r'(?:PARE|PERDIDA)[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'es', 'Stop loss Spanish'),
            ParsePattern(PatternType.STOP_LOSS, r'(?:وقف|خسارة)[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'ar', 'Stop loss Arabic'),
            ParsePattern(PatternType.STOP_LOSS, r'(?:止损|停止)[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'zh', 'Stop loss Chinese'),
            ParsePattern(PatternType.STOP_LOSS, r'(?:ARRÊT|PERTE)[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'fr', 'Stop loss French'),
        ]
        
        # Take Profit patterns
        patterns[PatternType.TAKE_PROFIT] = [
            ParsePattern(PatternType.TAKE_PROFIT, r'(?:TP\s*[1-9]?|T\.P\s*[1-9]?|TAKE\s*PROFIT\s*[1-9]?|TARGET\s*[1-9]?)[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'en', 'Take profit'),
            ParsePattern(PatternType.TAKE_PROFIT, r'(?:OBJETIVO|BENEFICIO)\s*[1-9]?[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'es', 'Take profit Spanish'),
            ParsePattern(PatternType.TAKE_PROFIT, r'(?:هدف|ربح)\s*[1-9]?[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'ar', 'Take profit Arabic'),
            ParsePattern(PatternType.TAKE_PROFIT, r'(?:目标|获利)\s*[1-9]?[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'zh', 'Take profit Chinese'),
            ParsePattern(PatternType.TAKE_PROFIT, r'(?:OBJECTIF|PROFIT)\s*[1-9]?[\s:]*([0-9]+\.?[0-9]*)', 0.90, 'fr', 'Take profit French'),
        ]
        
        # Range patterns
        patterns[PatternType.RANGE] = [
            ParsePattern(PatternType.RANGE, r'([0-9]+\.?[0-9]*)\s*[-–—]\s*([0-9]+\.?[0-9]*)', 0.75, 'en', 'Price range'),
            ParsePattern(PatternType.RANGE, r'([0-9]+\.?[0-9]*)\s*(?:to|TO|a|À)\s*([0-9]+\.?[0-9]*)', 0.80, 'en', 'Range with "to"'),
            ParsePattern(PatternType.RANGE, r'(?:between|entre|بين|之间)\s*([0-9]+\.?[0-9]*)\s*(?:and|y|و|和)\s*([0-9]+\.?[0-9]*)', 0.85, 'multi', 'Range with "between"'),
        ]
        
        # Order Type patterns
        patterns[PatternType.ORDER_TYPE] = [
            ParsePattern(PatternType.ORDER_TYPE, r'\b(MARKET|MKT)\b', 0.90, 'en', 'Market order'),
            ParsePattern(PatternType.ORDER_TYPE, r'\b(LIMIT|LMT)\b', 0.90, 'en', 'Limit order'),
            ParsePattern(PatternType.ORDER_TYPE, r'\b(STOP|STP)\b', 0.90, 'en', 'Stop order'),
            ParsePattern(PatternType.ORDER_TYPE, r'\b(PENDING|PEND)\b', 0.85, 'en', 'Pending order'),
        ]
        
        return patterns
    
    def _compile_patterns(self) -> Dict[PatternType, List[Tuple[re.Pattern, ParsePattern]]]:
        """Compile regex patterns for performance"""
        compiled = {pattern_type: [] for pattern_type in PatternType}
        
        flags = re.IGNORECASE if not self.config.get('case_sensitive', False) else 0
        
        for pattern_type, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                try:
                    compiled_regex = re.compile(pattern.regex, flags)
                    compiled[pattern_type].append((compiled_regex, pattern))
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern: {pattern.regex} - {e}")
        
        return compiled
    
    def _save_patterns(self, patterns: Dict[PatternType, List[ParsePattern]]):
        """Save patterns to file"""
        try:
            Path(self.patterns_file).parent.mkdir(parents=True, exist_ok=True)
            
            pattern_data = {}
            for pattern_type, pattern_list in patterns.items():
                pattern_data[pattern_type.value] = [
                    {
                        'regex': p.regex,
                        'confidence': p.confidence,
                        'language': p.language,
                        'description': p.description,
                        'examples': p.examples
                    }
                    for p in pattern_list
                ]
            
            with open(self.patterns_file, 'w') as f:
                json.dump(pattern_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save patterns: {e}")
    
    def parse_signal(self, signal_text: str) -> Dict[str, Any]:
        """
        Parse signal using configuration patterns
        
        Args:
            signal_text: Raw signal text
            
        Returns:
            Dictionary with parsed signal data
        """
        self.stats["total_parses"] += 1
        
        # Clean text
        cleaned_text = self._clean_text(signal_text)
        
        # Parse each component
        results = {}
        overall_confidence = 0.0
        successful_parses = 0
        
        # Parse symbol
        symbol_result = self._parse_component(cleaned_text, PatternType.SYMBOL)
        if symbol_result:
            results['symbol'] = self._normalize_symbol(symbol_result.matched_value)
            overall_confidence += symbol_result.confidence
            successful_parses += 1
        
        # Parse direction
        direction_result = self._parse_component(cleaned_text, PatternType.DIRECTION)
        if direction_result:
            results['direction'] = self._normalize_direction(direction_result.matched_value)
            overall_confidence += direction_result.confidence
            successful_parses += 1
        
        # Parse entry
        entry_result = self._parse_component(cleaned_text, PatternType.ENTRY)
        if entry_result:
            results['entry_price'] = float(entry_result.matched_value)
            overall_confidence += entry_result.confidence
            successful_parses += 1
        
        # Parse stop loss
        sl_result = self._parse_component(cleaned_text, PatternType.STOP_LOSS)
        if sl_result:
            results['stop_loss'] = float(sl_result.matched_value)
            overall_confidence += sl_result.confidence
            successful_parses += 1
        
        # Parse take profits
        tp_results = self._parse_multiple_component(cleaned_text, PatternType.TAKE_PROFIT)
        if tp_results:
            results['take_profits'] = [float(tp.matched_value) for tp in tp_results]
            overall_confidence += max(tp.confidence for tp in tp_results)
            successful_parses += 1
        
        # Parse range
        range_result = self._parse_component(cleaned_text, PatternType.RANGE)
        if range_result:
            range_match = re.search(r'([0-9]+\.?[0-9]*)\s*[-–—to]\s*([0-9]+\.?[0-9]*)', range_result.matched_value)
            if range_match:
                results['entry_range'] = [float(range_match.group(1)), float(range_match.group(2))]
                overall_confidence += range_result.confidence * 0.5  # Lower weight for range
        
        # Parse order type
        order_type_result = self._parse_component(cleaned_text, PatternType.ORDER_TYPE)
        if order_type_result:
            results['order_type'] = order_type_result.matched_value.upper()
            overall_confidence += order_type_result.confidence * 0.3  # Lower weight for order type
        
        # Calculate final confidence
        if successful_parses > 0:
            results['confidence'] = overall_confidence / successful_parses
            self.stats["successful_parses"] += 1
        else:
            results['confidence'] = 0.0
            self.stats["failed_parses"] += 1
        
        # Update confidence distribution
        if results['confidence'] >= 0.8:
            self.stats["confidence_distribution"]["high"] += 1
        elif results['confidence'] >= 0.6:
            self.stats["confidence_distribution"]["medium"] += 1
        else:
            self.stats["confidence_distribution"]["low"] += 1
        
        # Add metadata
        results['parse_method'] = 'config_regex'
        results['timestamp'] = datetime.now().isoformat()
        
        return results
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Normalize common symbols
        text = text.replace('–', '-').replace('—', '-').replace('→', '->')
        
        # Remove emojis and special characters that might interfere
        text = re.sub(r'[^\w\s\.\-\/:@#]', ' ', text)
        
        return text
    
    def _parse_component(self, text: str, pattern_type: PatternType) -> Optional[ParseResult]:
        """Parse a single component from text"""
        best_result = None
        best_confidence = 0.0
        
        for compiled_regex, pattern in self.compiled_patterns[pattern_type]:
            match = compiled_regex.search(text)
            if match:
                confidence = pattern.confidence
                
                # Apply fuzzy matching adjustments
                if self.config.get('enable_fuzzy_matching', True):
                    confidence = self._adjust_confidence_fuzzy(match, text, confidence)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_result = ParseResult(
                        matched_value=match.group(1) if match.groups() else match.group(0),
                        confidence=confidence,
                        pattern_used=pattern.regex,
                        position=match.span(),
                        language=pattern.language
                    )
                    
                    # Track pattern usage
                    pattern_key = f"{pattern_type.value}_{pattern.regex[:20]}"
                    self.stats["pattern_hits"][pattern_key] = self.stats["pattern_hits"].get(pattern_key, 0) + 1
        
        return best_result
    
    def _parse_multiple_component(self, text: str, pattern_type: PatternType) -> List[ParseResult]:
        """Parse multiple occurrences of a component"""
        results = []
        
        for compiled_regex, pattern in self.compiled_patterns[pattern_type]:
            matches = compiled_regex.finditer(text)
            for match in matches:
                confidence = pattern.confidence
                
                if self.config.get('enable_fuzzy_matching', True):
                    confidence = self._adjust_confidence_fuzzy(match, text, confidence)
                
                result = ParseResult(
                    matched_value=match.group(1) if match.groups() else match.group(0),
                    confidence=confidence,
                    pattern_used=pattern.regex,
                    position=match.span(),
                    language=pattern.language
                )
                results.append(result)
        
        # Sort by confidence and remove duplicates
        results = sorted(results, key=lambda x: x.confidence, reverse=True)
        unique_results = []
        seen_values = set()
        
        for result in results:
            if result.matched_value not in seen_values:
                unique_results.append(result)
                seen_values.add(result.matched_value)
        
        return unique_results
    
    def _adjust_confidence_fuzzy(self, match: re.Match, text: str, base_confidence: float) -> float:
        """Adjust confidence based on fuzzy matching factors"""
        # Context-based adjustments
        context_before = text[max(0, match.start()-20):match.start()]
        context_after = text[match.end():match.end()+20]
        
        # Boost confidence if surrounded by trading keywords
        trading_keywords = ['signal', 'trade', 'forex', 'position', 'market', 'analysis']
        if any(keyword in context_before.lower() or keyword in context_after.lower() for keyword in trading_keywords):
            base_confidence *= 1.1
        
        # Reduce confidence if surrounded by non-trading content
        non_trading_keywords = ['weather', 'sports', 'news', 'politics', 'entertainment']
        if any(keyword in context_before.lower() or keyword in context_after.lower() for keyword in non_trading_keywords):
            base_confidence *= 0.8
        
        return min(base_confidence, 1.0)
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to standard format"""
        symbol = symbol.upper().replace('/', '').replace('-', '')
        
        # Handle common aliases
        aliases = {
            'GOLD': 'XAUUSD',
            'SILVER': 'XAGUSD',
            'OIL': 'USOIL',
            'BITCOIN': 'BTCUSD',
            'NASDAQ': 'NAS100',
            'DOW': 'US30'
        }
        
        return aliases.get(symbol, symbol)
    
    def _normalize_direction(self, direction: str) -> str:
        """Normalize direction to standard format"""
        direction = direction.upper()
        
        buy_variants = ['BUY', 'LONG', 'BULL', 'B', 'COMPRAR', 'LARGO', 'شراء', 'شري']
        sell_variants = ['SELL', 'SHORT', 'BEAR', 'S', 'VENDER', 'CORTO', 'بيع']
        
        if direction in buy_variants:
            return 'BUY'
        elif direction in sell_variants:
            return 'SELL'
        else:
            return direction
    
    def get_stats(self) -> Dict[str, Any]:
        """Get parser statistics"""
        return self.stats.copy()
    
    def add_custom_pattern(self, pattern_type: PatternType, regex: str, confidence: float, 
                          language: str = 'en', description: str = '') -> bool:
        """Add a custom parsing pattern"""
        try:
            # Validate regex
            re.compile(regex)
            
            # Create pattern
            pattern = ParsePattern(
                pattern_type=pattern_type,
                regex=regex,
                confidence=confidence,
                language=language,
                description=description
            )
            
            # Add to patterns
            self.patterns[pattern_type].append(pattern)
            
            # Recompile patterns
            self.compiled_patterns = self._compile_patterns()
            
            # Save to file
            self._save_patterns(self.patterns)
            
            self.logger.info(f"Added custom pattern: {regex}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add custom pattern: {e}")
            return False

if __name__ == "__main__":
    # Example usage
    parser = ConfigParser()
    
    # Test parsing
    test_signals = [
        "EURUSD BUY @ 1.0850 SL: 1.0800 TP1: 1.0900 TP2: 1.0950",
        "GOLD SELL LIMIT 1950 SL 1960 TP 1940",
        "COMPRAR GBPUSD ENTRADA 1.2500 PARE 1.2450 OBJETIVO 1.2550"
    ]
    
    for signal in test_signals:
        result = parser.parse_signal(signal)
        print(f"Signal: {signal}")
        print(f"Result: {result}")
        print("---")
    
    print(f"Stats: {parser.get_stats()}")