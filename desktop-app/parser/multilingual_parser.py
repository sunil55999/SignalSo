#!/usr/bin/env python3
"""
Multilingual Signal Parser for SignalOS Desktop Application

Implements multilingual signal parsing using langdetect and polyglot libraries.
Supports automatic language detection and parsing in multiple languages.
"""

import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

try:
    from langdetect import detect, detect_langs
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logging.warning("langdetect not available")

@dataclass
class LanguageDetection:
    """Language detection result"""
    language: str
    confidence: float
    alternatives: List[Tuple[str, float]]

@dataclass
class MultilingualSignal:
    """Multilingual signal structure"""
    original_text: str
    detected_language: str
    confidence: float
    parsed_data: Dict[str, Any]
    translation: Optional[str] = None
    parsing_method: str = "pattern_based"

class SupportedLanguage(Enum):
    """Supported languages for signal parsing"""
    ENGLISH = "en"
    ARABIC = "ar"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"

class MultilingualSignalParser:
    """Multilingual signal parser with automatic language detection"""
    
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/multilingual_parser.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Language patterns for different languages
        self.language_patterns = self._load_language_patterns()
        
        # Currency symbol mappings for different languages
        self.currency_mappings = self._load_currency_mappings()
        
        # Number format patterns for different languages
        self.number_formats = self._load_number_formats()
        
        # Statistics
        self.stats = {
            "total_parsed": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "languages_detected": {},
            "parsing_methods": {},
            "average_confidence": 0.0
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Load multilingual parser configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('multilingual_parser', self._get_default_config())
        except FileNotFoundError:
            return self._create_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default parser configuration"""
        return {
            "enabled": True,
            "supported_languages": ["en", "ar", "es", "fr", "de", "it", "pt", "ru"],
            "default_language": "en",
            "confidence_threshold": 0.7,
            "enable_translation": False,
            "translation_service": "google",  # google, deepl, azure
            "pattern_matching": {
                "enable_fuzzy_matching": True,
                "fuzzy_threshold": 0.8,
                "enable_synonym_detection": True
            },
            "number_parsing": {
                "decimal_separators": {"en": ".", "fr": ",", "de": ",", "es": ","},
                "thousand_separators": {"en": ",", "fr": " ", "de": ".", "es": "."}
            }
        }
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration and save to file"""
        default_config = {
            "multilingual_parser": self._get_default_config()
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
            
        return default_config["multilingual_parser"]
    
    def _setup_logging(self):
        """Setup logging for multilingual parser"""
        self.logger = logging.getLogger('MultilingualParser')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # Ensure log directory exists
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
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
    
    def _load_language_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Load signal patterns for different languages"""
        return {
            "en": {
                "entry": [
                    r"(?:entry|buy|sell|open)\s*:?\s*([0-9.,]+)",
                    r"(?:at|@)\s*([0-9.,]+)",
                    r"(?:price|level)\s*:?\s*([0-9.,]+)"
                ],
                "stop_loss": [
                    r"(?:sl|stop|stop\s*loss)\s*:?\s*([0-9.,]+)",
                    r"(?:stop\s*at)\s*([0-9.,]+)"
                ],
                "take_profit": [
                    r"(?:tp|take\s*profit|target)\s*:?\s*([0-9.,]+)",
                    r"(?:profit\s*at)\s*([0-9.,]+)"
                ],
                "direction": [
                    r"(?:buy|long)",
                    r"(?:sell|short)"
                ]
            },
            "ar": {
                "entry": [
                    r"(?:دخول|شراء|بيع|فتح)\s*:?\s*([0-9.,]+)",
                    r"(?:عند|@)\s*([0-9.,]+)",
                    r"(?:سعر|مستوى)\s*:?\s*([0-9.,]+)"
                ],
                "stop_loss": [
                    r"(?:وقف\s*خسارة|إيقاف)\s*:?\s*([0-9.,]+)",
                    r"(?:وقف\s*عند)\s*([0-9.,]+)"
                ],
                "take_profit": [
                    r"(?:هدف|جني\s*ربح)\s*:?\s*([0-9.,]+)",
                    r"(?:ربح\s*عند)\s*([0-9.,]+)"
                ],
                "direction": [
                    r"(?:شراء)",
                    r"(?:بيع)"
                ]
            },
            "es": {
                "entry": [
                    r"(?:entrada|comprar|vender|abrir)\s*:?\s*([0-9.,]+)",
                    r"(?:en|@)\s*([0-9.,]+)",
                    r"(?:precio|nivel)\s*:?\s*([0-9.,]+)"
                ],
                "stop_loss": [
                    r"(?:sl|stop|stop\s*loss|parada)\s*:?\s*([0-9.,]+)",
                    r"(?:parar\s*en)\s*([0-9.,]+)"
                ],
                "take_profit": [
                    r"(?:tp|take\s*profit|objetivo|ganancia)\s*:?\s*([0-9.,]+)",
                    r"(?:ganancia\s*en)\s*([0-9.,]+)"
                ],
                "direction": [
                    r"(?:comprar|largo)",
                    r"(?:vender|corto)"
                ]
            },
            "fr": {
                "entry": [
                    r"(?:entrée|acheter|vendre|ouvrir)\s*:?\s*([0-9.,]+)",
                    r"(?:à|@)\s*([0-9.,]+)",
                    r"(?:prix|niveau)\s*:?\s*([0-9.,]+)"
                ],
                "stop_loss": [
                    r"(?:sl|stop|stop\s*loss|arrêt)\s*:?\s*([0-9.,]+)",
                    r"(?:arrêter\s*à)\s*([0-9.,]+)"
                ],
                "take_profit": [
                    r"(?:tp|take\s*profit|objectif|profit)\s*:?\s*([0-9.,]+)",
                    r"(?:profit\s*à)\s*([0-9.,]+)"
                ],
                "direction": [
                    r"(?:acheter|long)",
                    r"(?:vendre|court)"
                ]
            },
            "de": {
                "entry": [
                    r"(?:einstieg|kaufen|verkaufen|öffnen)\s*:?\s*([0-9.,]+)",
                    r"(?:bei|@)\s*([0-9.,]+)",
                    r"(?:preis|niveau)\s*:?\s*([0-9.,]+)"
                ],
                "stop_loss": [
                    r"(?:sl|stop|stop\s*loss|stopp)\s*:?\s*([0-9.,]+)",
                    r"(?:stopp\s*bei)\s*([0-9.,]+)"
                ],
                "take_profit": [
                    r"(?:tp|take\s*profit|ziel|gewinn)\s*:?\s*([0-9.,]+)",
                    r"(?:gewinn\s*bei)\s*([0-9.,]+)"
                ],
                "direction": [
                    r"(?:kaufen|long)",
                    r"(?:verkaufen|short)"
                ]
            }
        }
    
    def _load_currency_mappings(self) -> Dict[str, Dict[str, str]]:
        """Load currency symbol mappings for different languages"""
        return {
            "en": {
                "EURUSD": ["EURUSD", "EUR/USD", "EUR-USD", "Euro Dollar"],
                "GBPUSD": ["GBPUSD", "GBP/USD", "GBP-USD", "Pound Dollar", "Cable"],
                "USDJPY": ["USDJPY", "USD/JPY", "USD-JPY", "Dollar Yen"],
                "AUDUSD": ["AUDUSD", "AUD/USD", "AUD-USD", "Aussie Dollar"],
                "USDCAD": ["USDCAD", "USD/CAD", "USD-CAD", "Dollar CAD"],
                "XAUUSD": ["XAUUSD", "XAU/USD", "GOLD", "Gold"]
            },
            "ar": {
                "EURUSD": ["يورو دولار", "اليورو الدولار", "EUR/USD"],
                "GBPUSD": ["جنيه دولار", "الجنيه الاسترليني", "GBP/USD"],
                "USDJPY": ["دولار ين", "الدولار الياباني", "USD/JPY"],
                "XAUUSD": ["ذهب", "الذهب", "GOLD"]
            },
            "es": {
                "EURUSD": ["Euro Dólar", "EUR/USD"],
                "GBPUSD": ["Libra Dólar", "GBP/USD"],
                "USDJPY": ["Dólar Yen", "USD/JPY"],
                "XAUUSD": ["Oro", "GOLD"]
            },
            "fr": {
                "EURUSD": ["Euro Dollar", "EUR/USD"],
                "GBPUSD": ["Livre Dollar", "GBP/USD"],
                "USDJPY": ["Dollar Yen", "USD/JPY"],
                "XAUUSD": ["Or", "GOLD"]
            },
            "de": {
                "EURUSD": ["Euro Dollar", "EUR/USD"],
                "GBPUSD": ["Pfund Dollar", "GBP/USD"],
                "USDJPY": ["Dollar Yen", "USD/JPY"],
                "XAUUSD": ["Gold", "GOLD"]
            }
        }
    
    def _load_number_formats(self) -> Dict[str, Dict[str, str]]:
        """Load number format patterns for different languages"""
        return {
            "en": {
                "decimal_separator": ".",
                "thousand_separator": ",",
                "patterns": [r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", r"(\d+\.\d+)", r"(\d+)"]
            },
            "fr": {
                "decimal_separator": ",",
                "thousand_separator": " ",
                "patterns": [r"(\d{1,3}(?: \d{3})*(?:,\d+)?)", r"(\d+,\d+)", r"(\d+)"]
            },
            "de": {
                "decimal_separator": ",",
                "thousand_separator": ".",
                "patterns": [r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)", r"(\d+,\d+)", r"(\d+)"]
            },
            "es": {
                "decimal_separator": ",",
                "thousand_separator": ".",
                "patterns": [r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)", r"(\d+,\d+)", r"(\d+)"]
            }
        }
    
    def detect_language(self, text: str) -> LanguageDetection:
        """Detect language of the input text"""
        if not LANGDETECT_AVAILABLE:
            # Fallback to pattern-based detection
            return self._pattern_based_language_detection(text)
        
        try:
            # Use langdetect for language detection
            detected_lang = detect(text)
            lang_probs = detect_langs(text)
            
            # Extract confidence and alternatives
            confidence = 0.0
            alternatives = []
            
            for lang_prob in lang_probs:
                if lang_prob.lang == detected_lang:
                    confidence = lang_prob.prob
                alternatives.append((lang_prob.lang, lang_prob.prob))
            
            # Sort alternatives by confidence
            alternatives.sort(key=lambda x: x[1], reverse=True)
            
            return LanguageDetection(
                language=detected_lang,
                confidence=confidence,
                alternatives=alternatives[:3]  # Top 3 alternatives
            )
            
        except Exception as e:
            self.logger.warning(f"Language detection failed: {e}, using fallback")
            return self._pattern_based_language_detection(text)
    
    def _pattern_based_language_detection(self, text: str) -> LanguageDetection:
        """Fallback pattern-based language detection"""
        # Simple pattern-based detection
        language_indicators = {
            "ar": [r"[\u0600-\u06FF]", r"(?:شراء|بيع|دخول|هدف|وقف)"],
            "es": [r"(?:comprar|vender|entrada|objetivo|parada)"],
            "fr": [r"(?:acheter|vendre|entrée|objectif|arrêt)"],
            "de": [r"(?:kaufen|verkaufen|einstieg|ziel|stopp)"],
            "en": [r"(?:buy|sell|entry|target|stop)"]  # Default to English
        }
        
        scores = {}
        for lang, patterns in language_indicators.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            scores[lang] = score / len(text) if text else 0
        
        # Find best match
        best_lang = max(scores, key=scores.get) if scores else "en"
        confidence = scores.get(best_lang, 0.5)
        
        # Create alternatives list
        alternatives = [(lang, score) for lang, score in scores.items()]
        alternatives.sort(key=lambda x: x[1], reverse=True)
        
        return LanguageDetection(
            language=best_lang,
            confidence=min(confidence * 10, 1.0),  # Scale confidence
            alternatives=alternatives[:3]
        )
    
    def _normalize_number(self, number_str: str, language: str) -> Optional[float]:
        """Normalize number string according to language format"""
        try:
            number_format = self.number_formats.get(language, self.number_formats["en"])
            decimal_sep = number_format["decimal_separator"]
            thousand_sep = number_format["thousand_separator"]
            
            # Remove thousand separators
            normalized = number_str.replace(thousand_sep, "")
            
            # Convert decimal separator to standard dot
            if decimal_sep != ".":
                normalized = normalized.replace(decimal_sep, ".")
            
            return float(normalized)
            
        except (ValueError, AttributeError):
            return None
    
    def _extract_symbol(self, text: str, language: str) -> Optional[str]:
        """Extract currency symbol from text"""
        currency_map = self.currency_mappings.get(language, {})
        
        for symbol, variations in currency_map.items():
            for variation in variations:
                if variation.lower() in text.lower():
                    return symbol
        
        # Fallback to standard symbol patterns
        symbol_patterns = [
            r"(EUR\/USD|EURUSD|EUR-USD)",
            r"(GBP\/USD|GBPUSD|GBP-USD)",
            r"(USD\/JPY|USDJPY|USD-JPY)",
            r"(AUD\/USD|AUDUSD|AUD-USD)",
            r"(USD\/CAD|USDCAD|USD-CAD)",
            r"(XAU\/USD|XAUUSD|GOLD)"
        ]
        
        for pattern in symbol_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).replace("/", "").replace("-", "").upper()
        
        return None
    
    def _extract_direction(self, text: str, language: str) -> Optional[str]:
        """Extract trade direction from text"""
        patterns = self.language_patterns.get(language, {}).get("direction", [])
        
        buy_found = False
        sell_found = False
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                match_lower = match.lower()
                if any(word in match_lower for word in ["buy", "long", "شراء", "comprar", "acheter", "kaufen"]):
                    buy_found = True
                elif any(word in match_lower for word in ["sell", "short", "بيع", "vender", "vendre", "verkaufen"]):
                    sell_found = True
        
        if buy_found and not sell_found:
            return "BUY"
        elif sell_found and not buy_found:
            return "SELL"
        else:
            return None
    
    def _extract_prices(self, text: str, language: str, price_type: str) -> List[float]:
        """Extract prices from text based on type (entry, stop_loss, take_profit)"""
        patterns = self.language_patterns.get(language, {}).get(price_type, [])
        prices = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                price_str = match.group(1)
                price = self._normalize_number(price_str, language)
                if price is not None and price > 0:
                    prices.append(price)
        
        return list(set(prices))  # Remove duplicates
    
    def parse_signal(self, text: str, force_language: Optional[str] = None) -> MultilingualSignal:
        """Parse multilingual trading signal"""
        try:
            self.stats["total_parsed"] += 1
            
            # Detect language
            if force_language and force_language in [lang.value for lang in SupportedLanguage]:
                language_detection = LanguageDetection(
                    language=force_language,
                    confidence=1.0,
                    alternatives=[(force_language, 1.0)]
                )
            else:
                language_detection = self.detect_language(text)
            
            detected_lang = language_detection.language
            
            # Update language statistics
            if detected_lang not in self.stats["languages_detected"]:
                self.stats["languages_detected"][detected_lang] = 0
            self.stats["languages_detected"][detected_lang] += 1
            
            # Extract signal components
            signal_data = {
                "symbol": self._extract_symbol(text, detected_lang),
                "direction": self._extract_direction(text, detected_lang),
                "entry_prices": self._extract_prices(text, detected_lang, "entry"),
                "stop_loss": self._extract_prices(text, detected_lang, "stop_loss"),
                "take_profit": self._extract_prices(text, detected_lang, "take_profit"),
                "confidence": language_detection.confidence,
                "raw_text": text,
                "detected_language": detected_lang
            }
            
            # Calculate parsing confidence
            components_found = sum([
                1 if signal_data["symbol"] else 0,
                1 if signal_data["direction"] else 0,
                1 if signal_data["entry_prices"] else 0
            ])
            
            parsing_confidence = (components_found / 3) * language_detection.confidence
            
            # Update statistics
            if parsing_confidence > 0.5:
                self.stats["successful_parses"] += 1
            else:
                self.stats["failed_parses"] += 1
            
            # Update average confidence
            total_parsed = self.stats["total_parsed"]
            current_avg = self.stats["average_confidence"]
            self.stats["average_confidence"] = ((current_avg * (total_parsed - 1)) + parsing_confidence) / total_parsed
            
            # Update parsing method statistics
            method = "pattern_based"
            if method not in self.stats["parsing_methods"]:
                self.stats["parsing_methods"][method] = 0
            self.stats["parsing_methods"][method] += 1
            
            multilingual_signal = MultilingualSignal(
                original_text=text,
                detected_language=detected_lang,
                confidence=parsing_confidence,
                parsed_data=signal_data,
                parsing_method=method
            )
            
            self.logger.info(f"Parsed signal in {detected_lang} with confidence {parsing_confidence:.2f}")
            return multilingual_signal
            
        except Exception as e:
            self.stats["failed_parses"] += 1
            self.logger.error(f"Error parsing signal: {e}")
            
            return MultilingualSignal(
                original_text=text,
                detected_language="unknown",
                confidence=0.0,
                parsed_data={},
                parsing_method="error"
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get parser statistics"""
        return {
            **self.stats,
            "supported_languages": [lang.value for lang in SupportedLanguage],
            "langdetect_available": LANGDETECT_AVAILABLE,
            "configuration": self.config
        }


# Example usage and testing
def main():
    """Example usage of multilingual parser"""
    parser = MultilingualSignalParser()
    
    # Test signals in different languages
    test_signals = [
        "Buy EURUSD at 1.1200, SL: 1.1150, TP: 1.1250",
        "شراء يورو دولار عند 1.1200، وقف خسارة: 1.1150، هدف: 1.1250",
        "Comprar EURUSD en 1.1200, SL: 1.1150, TP: 1.1250",
        "Acheter EURUSD à 1,1200, SL: 1,1150, TP: 1,1250",
        "Kaufen EURUSD bei 1,1200, SL: 1,1150, TP: 1,1250"
    ]
    
    for signal_text in test_signals:
        result = parser.parse_signal(signal_text)
        print(f"Text: {signal_text}")
        print(f"Language: {result.detected_language} (confidence: {result.confidence:.2f})")
        print(f"Parsed: {result.parsed_data}")
        print("-" * 50)
    
    # Show statistics
    stats = parser.get_statistics()
    print(f"Parser Statistics: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    main()