#!/usr/bin/env python3
"""
Language Detection Module
Auto-detects signal language and routes to appropriate parsers
"""

import re
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

try:
    from langdetect import detect, detect_langs, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    print("⚠️ langdetect not available. Install with: pip install langdetect")
    LANGDETECT_AVAILABLE = False


class LanguageDetector:
    """Auto-detect trading signal language and route to appropriate parsers"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/lang_patterns.json"
        self.supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ar', 'zh', 'ja', 'ko']
        self.confidence_threshold = 0.6
        self.patterns = self._load_patterns()
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for language detection"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / "lang_detect.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _load_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Load language-specific trading patterns"""
        default_patterns = {
            "en": {
                "buy_signals": ["buy", "long", "call", "bullish", "entry", "purchase"],
                "sell_signals": ["sell", "short", "put", "bearish", "exit", "close"],
                "currency_pairs": ["eurusd", "gbpusd", "usdjpy", "usdchf", "audusd"],
                "take_profit": ["tp", "take profit", "target", "profit"],
                "stop_loss": ["sl", "stop loss", "stop", "loss"]
            },
            "es": {
                "buy_signals": ["comprar", "largo", "alcista", "entrada", "compra"],
                "sell_signals": ["vender", "corto", "bajista", "salida", "venta"],
                "currency_pairs": ["eurusd", "gbpusd", "usdjpy", "usdchf", "audusd"],
                "take_profit": ["tp", "tomar ganancia", "objetivo", "ganancia"],
                "stop_loss": ["sl", "parar pérdida", "parar", "pérdida"]
            },
            "fr": {
                "buy_signals": ["acheter", "long", "haussier", "entrée", "achat"],
                "sell_signals": ["vendre", "court", "baissier", "sortie", "vente"],
                "currency_pairs": ["eurusd", "gbpusd", "usdjpy", "usdchf", "audusd"],
                "take_profit": ["tp", "prendre profit", "objectif", "profit"],
                "stop_loss": ["sl", "arrêter perte", "arrêter", "perte"]
            },
            "de": {
                "buy_signals": ["kaufen", "lang", "bullish", "einstieg", "kauf"],
                "sell_signals": ["verkaufen", "kurz", "bärisch", "ausstieg", "verkauf"],
                "currency_pairs": ["eurusd", "gbpusd", "usdjpy", "usdchf", "audusd"],
                "take_profit": ["tp", "gewinn mitnehmen", "ziel", "gewinn"],
                "stop_loss": ["sl", "verlust stoppen", "stopp", "verlust"]
            },
            "ru": {
                "buy_signals": ["покупать", "длинный", "бычий", "вход", "покупка"],
                "sell_signals": ["продавать", "короткий", "медвежий", "выход", "продажа"],
                "currency_pairs": ["eurusd", "gbpusd", "usdjpy", "usdchf", "audusd"],
                "take_profit": ["тп", "взять прибыль", "цель", "прибыль"],
                "stop_loss": ["сл", "стоп лосс", "стоп", "убыток"]
            },
            "ar": {
                "buy_signals": ["شراء", "طويل", "صاعد", "دخول", "شراء"],
                "sell_signals": ["بيع", "قصير", "هابط", "خروج", "بيع"],
                "currency_pairs": ["eurusd", "gbpusd", "usdjpy", "usdchf", "audusd"],
                "take_profit": ["جني ربح", "هدف", "ربح"],
                "stop_loss": ["وقف خسارة", "وقف", "خسارة"]
            }
        }
        
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_patterns = json.load(f)
                    # Merge with defaults
                    for lang in default_patterns:
                        if lang in loaded_patterns:
                            default_patterns[lang].update(loaded_patterns[lang])
                        
            # Save updated patterns
            self._save_patterns(default_patterns)
            
        except Exception as e:
            self.logger.warning(f"Failed to load patterns: {e}")
            
        return default_patterns
        
    def _save_patterns(self, patterns: Dict[str, Dict[str, List[str]]]):
        """Save language patterns to config file"""
        try:
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(patterns, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.warning(f"Failed to save patterns: {e}")
            
    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect language of trading signal text
        
        Args:
            text: Input text to analyze
            
        Returns:
            Tuple of (language_code, confidence)
        """
        if not text or not text.strip():
            return "en", 0.0
            
        # Clean text for detection
        cleaned_text = self._clean_text(text)
        
        # Try library-based detection first
        if LANGDETECT_AVAILABLE:
            try:
                detected_langs = detect_langs(cleaned_text)
                if detected_langs:
                    lang = detected_langs[0]
                    if lang.lang in self.supported_languages:
                        self.logger.info(f"Detected language: {lang.lang} (confidence: {lang.prob:.3f})")
                        return lang.lang, lang.prob
                        
            except LangDetectException as e:
                self.logger.warning(f"Language detection failed: {e}")
                
        # Fallback to pattern-based detection
        return self._pattern_based_detection(cleaned_text)
        
    def _clean_text(self, text: str) -> str:
        """Clean text for better language detection"""
        # Remove URLs, mentions, hashtags
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#\w+', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove numbers and special characters for language detection
        text = re.sub(r'[0-9\.,\-\+\*\/\=\(\)\[\]]+', ' ', text)
        
        return text
        
    def _pattern_based_detection(self, text: str) -> Tuple[str, float]:
        """Fallback pattern-based language detection"""
        text_lower = text.lower()
        language_scores = {}
        
        for lang_code, patterns in self.patterns.items():
            score = 0
            total_patterns = 0
            
            for pattern_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    total_patterns += 1
                    if pattern.lower() in text_lower:
                        score += 1
                        
            if total_patterns > 0:
                language_scores[lang_code] = score / total_patterns
                
        if language_scores:
            best_lang = max(language_scores, key=language_scores.get)
            confidence = language_scores[best_lang]
            
            self.logger.info(f"Pattern-based detection: {best_lang} (confidence: {confidence:.3f})")
            return best_lang, confidence
            
        # Default to English
        return "en", 0.1
        
    def route_to_parser(self, text: str, detected_lang: str) -> str:
        """
        Route signal to appropriate language-specific parser
        
        Args:
            text: Signal text
            detected_lang: Detected language code
            
        Returns:
            Parser module name to use
        """
        parser_map = {
            "en": "english_parser",
            "es": "spanish_parser", 
            "fr": "french_parser",
            "de": "german_parser",
            "ru": "russian_parser",
            "ar": "arabic_parser",
            "zh": "chinese_parser",
            "ja": "japanese_parser",
            "ko": "korean_parser",
            "pt": "portuguese_parser",
            "it": "italian_parser"
        }
        
        parser_name = parser_map.get(detected_lang, "english_parser")
        self.logger.info(f"Routing to parser: {parser_name} for language: {detected_lang}")
        
        return parser_name
        
    def extract_trading_elements(self, text: str, language: str) -> Dict[str, Any]:
        """
        Extract trading elements using language-specific patterns
        
        Args:
            text: Signal text
            language: Language code
            
        Returns:
            Dictionary of extracted trading elements
        """
        if language not in self.patterns:
            language = "en"  # Fallback to English
            
        patterns = self.patterns[language]
        text_lower = text.lower()
        
        result = {
            "signal_type": None,
            "currency_pair": None,
            "take_profit_levels": [],
            "stop_loss": None,
            "entry_price": None,
            "confidence": 0.0,
            "language": language
        }
        
        # Detect signal type
        for buy_signal in patterns.get("buy_signals", []):
            if buy_signal.lower() in text_lower:
                result["signal_type"] = "BUY"
                result["confidence"] += 0.2
                break
                
        if not result["signal_type"]:
            for sell_signal in patterns.get("sell_signals", []):
                if sell_signal.lower() in text_lower:
                    result["signal_type"] = "SELL"
                    result["confidence"] += 0.2
                    break
                    
        # Find currency pair
        for pair in patterns.get("currency_pairs", []):
            if pair.upper() in text.upper():
                result["currency_pair"] = pair.upper()
                result["confidence"] += 0.3
                break
                
        # Extract numerical values (prices, levels)
        numbers = re.findall(r'\d+\.?\d*', text)
        if numbers:
            result["entry_price"] = float(numbers[0]) if numbers else None
            result["take_profit_levels"] = [float(n) for n in numbers[1:3] if n]
            result["stop_loss"] = float(numbers[-1]) if len(numbers) > 1 else None
            result["confidence"] += 0.3
            
        # Check for TP/SL keywords
        tp_patterns = patterns.get("take_profit", [])
        sl_patterns = patterns.get("stop_loss", [])
        
        for tp_word in tp_patterns:
            if tp_word.lower() in text_lower:
                result["confidence"] += 0.1
                break
                
        for sl_word in sl_patterns:
            if sl_word.lower() in text_lower:
                result["confidence"] += 0.1
                break
                
        return result
        
    def process_signal(self, text: str) -> Dict[str, Any]:
        """
        Complete signal processing with language detection and parsing
        
        Args:
            text: Raw signal text
            
        Returns:
            Processed signal data
        """
        # Detect language
        detected_lang, lang_confidence = self.detect_language(text)
        
        # Extract trading elements
        parsed_data = self.extract_trading_elements(text, detected_lang)
        
        # Get recommended parser
        parser_name = self.route_to_parser(text, detected_lang)
        
        # Combine results
        result = {
            "original_text": text,
            "detected_language": detected_lang,
            "language_confidence": lang_confidence,
            "recommended_parser": parser_name,
            "parsed_data": parsed_data,
            "processing_timestamp": str(Path().cwd()),
            "success": parsed_data["confidence"] > self.confidence_threshold
        }
        
        self.logger.info(f"Processed signal - Language: {detected_lang}, Confidence: {lang_confidence:.3f}, Success: {result['success']}")
        
        return result


def main():
    """Test the language detection system"""
    print("🌍 Testing Multilingual Signal Detection")
    print("=" * 50)
    
    # Initialize detector
    detector = LanguageDetector()
    
    # Test signals in different languages
    test_signals = [
        "BUY EURUSD at 1.0850, TP: 1.0900, SL: 1.0800",
        "COMPRAR GBPUSD en 1.2500, TP: 1.2550, SL: 1.2450",
        "ACHETER USDCAD à 1.3600, TP: 1.3650, SL: 1.3550",
        "KAUFEN USDJPY bei 150.00, TP: 150.50, SL: 149.50",
        "ПОКУПАТЬ EURUSD на 1.0850, ТП: 1.0900, СЛ: 1.0800",
        "شراء GBPUSD عند 1.2500، جني ربح: 1.2550، وقف خسارة: 1.2450"
    ]
    
    print("📊 Processing test signals...")
    for i, signal in enumerate(test_signals, 1):
        print(f"\n🔍 Signal {i}: {signal[:50]}...")
        
        result = detector.process_signal(signal)
        
        print(f"   Language: {result['detected_language']} (confidence: {result['language_confidence']:.3f})")
        print(f"   Parser: {result['recommended_parser']}")
        print(f"   Signal Type: {result['parsed_data']['signal_type']}")
        print(f"   Currency: {result['parsed_data']['currency_pair']}")
        print(f"   Success: {'✅' if result['success'] else '❌'}")
        
    # Test language patterns
    print(f"\n📋 Supported languages: {', '.join(detector.supported_languages)}")
    print(f"💾 Patterns saved to: {detector.config_path}")


if __name__ == "__main__":
    main()