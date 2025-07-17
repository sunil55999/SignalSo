#!/usr/bin/env python3
"""
Advanced AI Signal Parser Core Engine for SignalOS Desktop Application

Core parser engine that switches between AI model (Phi-3, Mistral via Ollama) 
and fallback regex parsing with confidence scoring, OCR support, and learning loop.
"""

import re
import json
import logging
import asyncio
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import hashlib
import sqlite3

# Local imports
from parser.multilingual_parser import MultilingualSignalParser, LanguageDetection
from parser.ocr_engine import OCREngine

class ParsingMethod(Enum):
    """Available parsing methods"""
    AI_MODEL = "ai_model"
    REGEX_FALLBACK = "regex_fallback"
    HYBRID = "hybrid"
    OCR_FIRST = "ocr_first"

class SignalType(Enum):
    """Signal input types"""
    TEXT = "text"
    IMAGE = "image"
    MIXED = "mixed"

class ConfidenceLevel(Enum):
    """Confidence level categories"""
    VERY_HIGH = "very_high"  # 90-100%
    HIGH = "high"           # 75-89%
    MEDIUM = "medium"       # 60-74%
    LOW = "low"            # 40-59%
    VERY_LOW = "very_low"  # 0-39%

@dataclass
class ParsedSignalAdvanced:
    """Advanced parsed signal structure with confidence scoring"""
    # Core signal data
    symbol: Optional[str] = None
    entry_price: Optional[float] = None
    entry_range: Optional[Tuple[float, float]] = None
    stop_loss: Optional[float] = None
    take_profits: List[float] = None
    direction: Optional[str] = None
    order_type: Optional[str] = None
    
    # Advanced features
    confidence_score: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.VERY_LOW
    parsing_method: ParsingMethod = ParsingMethod.REGEX_FALLBACK
    language_detected: Optional[str] = None
    
    # Signal metadata
    provider: Optional[str] = None
    signal_id: Optional[str] = None
    timestamp: datetime = None
    expiry_time: Optional[datetime] = None
    
    # Parsing details
    raw_text: str = ""
    ocr_text: Optional[str] = None
    ai_model_used: Optional[str] = None
    processing_time: float = 0.0
    
    # Quality metrics
    parse_errors: List[str] = None
    validation_warnings: List[str] = None
    risk_score: float = 0.0
    
    # Learning data
    outcome: Optional[str] = None  # "tp1", "tp2", "tp3", "sl", "breakeven"
    actual_result: Optional[Dict[str, Any]] = None
    learning_feedback: Optional[str] = None
    
    def __post_init__(self):
        if self.take_profits is None:
            self.take_profits = []
        if self.parse_errors is None:
            self.parse_errors = []
        if self.validation_warnings is None:
            self.validation_warnings = []
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # Auto-calculate confidence level
        self.confidence_level = self._calculate_confidence_level()
    
    def _calculate_confidence_level(self) -> ConfidenceLevel:
        """Calculate confidence level based on score"""
        if self.confidence_score >= 0.90:
            return ConfidenceLevel.VERY_HIGH
        elif self.confidence_score >= 0.75:
            return ConfidenceLevel.HIGH
        elif self.confidence_score >= 0.60:
            return ConfidenceLevel.MEDIUM
        elif self.confidence_score >= 0.40:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['confidence_level'] = self.confidence_level.value
        data['parsing_method'] = self.parsing_method.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.expiry_time:
            data['expiry_time'] = self.expiry_time.isoformat()
        return data

@dataclass
class AIModelConfig:
    """AI model configuration"""
    model_name: str = "phi3"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    temperature: float = 0.1
    max_tokens: int = 1000
    system_prompt: str = """You are a professional trading signal parser. Extract trading information from the given text and return structured JSON data with the following fields:
- symbol: trading symbol (e.g., "EURUSD", "XAUUSD")
- entry_price: entry price as float
- entry_range: [min_price, max_price] if range given
- stop_loss: stop loss price as float
- take_profits: array of take profit prices as floats
- direction: "BUY" or "SELL"
- order_type: "MARKET", "LIMIT", "STOP", etc.
- confidence: confidence score 0.0-1.0

Always return valid JSON. If information is missing, use null values."""

@dataclass
class ParserConfig:
    """Advanced parser configuration"""
    # AI Model settings
    ai_model: AIModelConfig = None
    enable_ai_parsing: bool = True
    ai_fallback_enabled: bool = True
    
    # Parsing thresholds
    confidence_threshold: float = 0.7
    min_confidence_for_execution: float = 0.8
    
    # OCR settings
    enable_ocr: bool = True
    ocr_languages: List[str] = None
    ocr_confidence_threshold: float = 0.6
    
    # Multilingual settings
    enable_multilingual: bool = True
    supported_languages: List[str] = None
    
    # Learning settings
    enable_learning_loop: bool = True
    store_failed_parses: bool = True
    learning_database: str = "logs/learning_data.db"
    
    # Performance settings
    max_processing_time: float = 30.0
    enable_caching: bool = True
    cache_ttl: int = 300
    
    def __post_init__(self):
        if self.ai_model is None:
            self.ai_model = AIModelConfig()
        if self.ocr_languages is None:
            self.ocr_languages = ["en", "ar", "es", "fr", "de", "ru", "zh", "ja"]
        if self.supported_languages is None:
            self.supported_languages = ["en", "ar", "es", "fr", "de", "ru", "zh", "ja"]

class SignalParserCore:
    """Advanced AI Signal Parser Core Engine"""
    
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/parser_core.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Initialize sub-parsers
        self.multilingual_parser = MultilingualSignalParser(config_file)
        self.ocr_engine = OCREngine(config_file) if self.config.enable_ocr else None
        
        # Initialize learning database
        self.learning_db = self._init_learning_database()
        
        # Cache for parsed signals
        self.parse_cache = {}
        
        # Statistics
        self.stats = {
            "total_parsed": 0,
            "ai_parses": 0,
            "regex_parses": 0,
            "ocr_parses": 0,
            "failed_parses": 0,
            "cached_results": 0,
            "learning_feedbacks": 0
        }
        
        self.logger.info("Advanced Signal Parser Core initialized")
    
    def _load_config(self) -> ParserConfig:
        """Load parser configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                parser_config = config_data.get('advanced_parser', {})
                
                # Convert nested dicts to dataclasses
                if 'ai_model' in parser_config:
                    parser_config['ai_model'] = AIModelConfig(**parser_config['ai_model'])
                
                return ParserConfig(**parser_config)
        except Exception as e:
            self.logger.warning(f"Failed to load config, using defaults: {e}")
            return ParserConfig()
    
    def _setup_logging(self):
        """Setup logging for parser core"""
        self.logger = logging.getLogger('ParserCore')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(self.log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def _init_learning_database(self) -> sqlite3.Connection:
        """Initialize learning database for storing parse results"""
        try:
            Path(self.config.learning_database).parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self.config.learning_database)
            
            # Create tables
            db.execute('''
                CREATE TABLE IF NOT EXISTS parsed_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_hash TEXT UNIQUE,
                    raw_text TEXT,
                    parsed_data TEXT,
                    confidence_score REAL,
                    parsing_method TEXT,
                    timestamp TEXT,
                    outcome TEXT,
                    feedback TEXT
                )
            ''')
            
            db.execute('''
                CREATE TABLE IF NOT EXISTS failed_parses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_text TEXT,
                    error_message TEXT,
                    timestamp TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            ''')
            
            db.commit()
            return db
        except Exception as e:
            self.logger.error(f"Failed to initialize learning database: {e}")
            return None
    
    def _get_signal_hash(self, text: str) -> str:
        """Generate hash for signal caching"""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def parse_signal(self, signal_input: Union[str, bytes], 
                          signal_type: SignalType = SignalType.TEXT,
                          provider: Optional[str] = None) -> ParsedSignalAdvanced:
        """
        Main parsing function with AI and fallback support
        
        Args:
            signal_input: Text string or image bytes
            signal_type: Type of signal input
            provider: Signal provider name
            
        Returns:
            ParsedSignalAdvanced object with extracted data
        """
        start_time = datetime.now()
        self.stats["total_parsed"] += 1
        
        # Handle different input types
        if signal_type == SignalType.IMAGE:
            if not self.ocr_engine:
                raise ValueError("OCR engine not available for image parsing")
            
            # Extract text from image using OCR
            ocr_result = await self.ocr_engine.extract_text(signal_input)
            signal_text = ocr_result.get('text', '')
            ocr_confidence = ocr_result.get('confidence', 0.0)
            
            if not signal_text or ocr_confidence < self.config.ocr_confidence_threshold:
                return ParsedSignalAdvanced(
                    raw_text="",
                    ocr_text=signal_text,
                    confidence_score=0.0,
                    parsing_method=ParsingMethod.OCR_FIRST,
                    parse_errors=["OCR extraction failed or low confidence"]
                )
        else:
            signal_text = signal_input
            ocr_confidence = 1.0
        
        # Check cache
        signal_hash = self._get_signal_hash(signal_text)
        if self.config.enable_caching and signal_hash in self.parse_cache:
            cached_result = self.parse_cache[signal_hash]
            if (datetime.now() - cached_result['timestamp']).seconds < self.config.cache_ttl:
                self.stats["cached_results"] += 1
                return cached_result['result']
        
        # Initialize result
        result = ParsedSignalAdvanced(
            raw_text=signal_text,
            ocr_text=signal_text if signal_type == SignalType.IMAGE else None,
            provider=provider,
            signal_id=signal_hash[:8]
        )
        
        try:
            # Method 1: AI Model parsing
            if self.config.enable_ai_parsing:
                result = await self._parse_with_ai(signal_text, result)
                if result.confidence_score >= self.config.confidence_threshold:
                    self.stats["ai_parses"] += 1
                    result.parsing_method = ParsingMethod.AI_MODEL
                    self.logger.info(f"AI parsing successful: {result.confidence_score:.2f}")
                    return self._finalize_result(result, start_time, signal_hash)
            
            # Method 2: Regex fallback
            if self.config.ai_fallback_enabled:
                result = await self._parse_with_regex(signal_text, result)
                if result.confidence_score >= self.config.confidence_threshold:
                    self.stats["regex_parses"] += 1
                    result.parsing_method = ParsingMethod.REGEX_FALLBACK
                    self.logger.info(f"Regex parsing successful: {result.confidence_score:.2f}")
                    return self._finalize_result(result, start_time, signal_hash)
            
            # Failed to parse with sufficient confidence
            self.stats["failed_parses"] += 1
            result.parse_errors.append("All parsing methods failed")
            
            # Store failed parse for learning
            if self.config.store_failed_parses:
                self._store_failed_parse(signal_text, "Low confidence")
            
        except Exception as e:
            self.stats["failed_parses"] += 1
            result.parse_errors.append(f"Parsing error: {str(e)}")
            self.logger.error(f"Parse error: {e}")
        
        return self._finalize_result(result, start_time, signal_hash)
    
    async def _parse_with_ai(self, text: str, result: ParsedSignalAdvanced) -> ParsedSignalAdvanced:
        """Parse signal using AI model (Ollama/Phi-3)"""
        try:
            # Prepare request payload
            payload = {
                "model": self.config.ai_model.model_name,
                "prompt": f"{self.config.ai_model.system_prompt}\n\nSignal text: {text}",
                "stream": False,
                "options": {
                    "temperature": self.config.ai_model.temperature,
                    "num_predict": self.config.ai_model.max_tokens
                }
            }
            
            # Make API request
            response = requests.post(
                f"{self.config.ai_model.base_url}/api/generate",
                json=payload,
                timeout=self.config.ai_model.timeout
            )
            
            if response.status_code == 200:
                ai_response = response.json()
                ai_output = ai_response.get('response', '')
                
                # Try to parse JSON from AI response
                try:
                    # Clean AI response to extract JSON
                    json_start = ai_output.find('{')
                    json_end = ai_output.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = ai_output[json_start:json_end]
                        parsed_data = json.loads(json_str)
                        
                        # Map AI response to result
                        result.symbol = parsed_data.get('symbol')
                        result.entry_price = parsed_data.get('entry_price')
                        result.stop_loss = parsed_data.get('stop_loss')
                        result.take_profits = parsed_data.get('take_profits', [])
                        result.direction = parsed_data.get('direction')
                        result.order_type = parsed_data.get('order_type')
                        result.confidence_score = parsed_data.get('confidence', 0.0)
                        result.ai_model_used = self.config.ai_model.model_name
                        
                        # Handle entry range
                        if parsed_data.get('entry_range'):
                            result.entry_range = tuple(parsed_data['entry_range'])
                        
                        self.logger.info(f"AI parsing successful for {result.symbol}")
                        return result
                
                except json.JSONDecodeError as e:
                    result.parse_errors.append(f"AI response JSON parsing failed: {e}")
                    self.logger.warning(f"AI JSON parse error: {e}")
            
            else:
                result.parse_errors.append(f"AI API request failed: {response.status_code}")
                self.logger.warning(f"AI API error: {response.status_code}")
        
        except Exception as e:
            result.parse_errors.append(f"AI parsing error: {str(e)}")
            self.logger.error(f"AI parsing error: {e}")
        
        return result
    
    async def _parse_with_regex(self, text: str, result: ParsedSignalAdvanced) -> ParsedSignalAdvanced:
        """Parse signal using regex fallback"""
        try:
            # Use multilingual parser for regex parsing
            multilingual_result = self.multilingual_parser.parse_signal(text)
            
            # Map multilingual parser result to advanced result
            result.symbol = multilingual_result.get('symbol')
            result.entry_price = multilingual_result.get('entry_price')
            result.stop_loss = multilingual_result.get('stop_loss')
            result.take_profits = multilingual_result.get('take_profits', [])
            result.direction = multilingual_result.get('direction')
            result.order_type = multilingual_result.get('order_type')
            result.confidence_score = multilingual_result.get('confidence', 0.0)
            result.language_detected = multilingual_result.get('language')
            
            # Calculate confidence based on completeness
            completeness_score = self._calculate_completeness(result)
            result.confidence_score = min(result.confidence_score, completeness_score)
            
            return result
            
        except Exception as e:
            result.parse_errors.append(f"Regex parsing error: {str(e)}")
            self.logger.error(f"Regex parsing error: {e}")
            return result
    
    def _calculate_completeness(self, result: ParsedSignalAdvanced) -> float:
        """Calculate completeness score based on available data"""
        score = 0.0
        max_score = 6.0
        
        if result.symbol:
            score += 1.0
        if result.entry_price or result.entry_range:
            score += 1.5
        if result.stop_loss:
            score += 1.0
        if result.take_profits:
            score += 1.0
        if result.direction:
            score += 1.0
        if result.order_type:
            score += 0.5
        
        return min(score / max_score, 1.0)
    
    def _finalize_result(self, result: ParsedSignalAdvanced, start_time: datetime, signal_hash: str) -> ParsedSignalAdvanced:
        """Finalize parsing result"""
        # Calculate processing time
        result.processing_time = (datetime.now() - start_time).total_seconds()
        
        # Store in cache
        if self.config.enable_caching:
            self.parse_cache[signal_hash] = {
                'result': result,
                'timestamp': datetime.now()
            }
        
        # Store in learning database
        if self.config.enable_learning_loop and self.learning_db:
            self._store_parsed_signal(result, signal_hash)
        
        return result
    
    def _store_parsed_signal(self, result: ParsedSignalAdvanced, signal_hash: str):
        """Store parsed signal in learning database"""
        try:
            if self.learning_db:
                self.learning_db.execute(
                    '''INSERT OR REPLACE INTO parsed_signals 
                       (signal_hash, raw_text, parsed_data, confidence_score, parsing_method, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (signal_hash, result.raw_text, json.dumps(result.to_dict()), 
                     result.confidence_score, result.parsing_method.value, result.timestamp.isoformat())
                )
                self.learning_db.commit()
        except Exception as e:
            self.logger.error(f"Failed to store parsed signal: {e}")
    
    def _store_failed_parse(self, text: str, error: str):
        """Store failed parse for learning"""
        try:
            if self.learning_db:
                self.learning_db.execute(
                    '''INSERT INTO failed_parses (raw_text, error_message, timestamp)
                       VALUES (?, ?, ?)''',
                    (text, error, datetime.now().isoformat())
                )
                self.learning_db.commit()
        except Exception as e:
            self.logger.error(f"Failed to store failed parse: {e}")
    
    def record_signal_outcome(self, signal_id: str, outcome: str, result_data: Dict[str, Any]):
        """Record actual signal outcome for learning"""
        try:
            if self.learning_db:
                self.learning_db.execute(
                    '''UPDATE parsed_signals SET outcome = ?, feedback = ? WHERE signal_hash LIKE ?''',
                    (outcome, json.dumps(result_data), f"{signal_id}%")
                )
                self.learning_db.commit()
                self.stats["learning_feedbacks"] += 1
                self.logger.info(f"Recorded outcome for signal {signal_id}: {outcome}")
        except Exception as e:
            self.logger.error(f"Failed to record outcome: {e}")
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning statistics"""
        try:
            if not self.learning_db:
                return {}
            
            cursor = self.learning_db.cursor()
            
            # Get outcome statistics
            cursor.execute('''
                SELECT outcome, COUNT(*) as count 
                FROM parsed_signals 
                WHERE outcome IS NOT NULL 
                GROUP BY outcome
            ''')
            outcomes = dict(cursor.fetchall())
            
            # Get confidence vs outcome correlation
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN confidence_score >= 0.8 THEN 'high'
                        WHEN confidence_score >= 0.6 THEN 'medium'
                        ELSE 'low'
                    END as confidence_level,
                    outcome,
                    COUNT(*) as count
                FROM parsed_signals 
                WHERE outcome IS NOT NULL 
                GROUP BY confidence_level, outcome
            ''')
            confidence_outcomes = cursor.fetchall()
            
            # Get failed parse count
            cursor.execute('SELECT COUNT(*) FROM failed_parses')
            failed_count = cursor.fetchone()[0]
            
            return {
                'outcomes': outcomes,
                'confidence_outcomes': confidence_outcomes,
                'failed_parses': failed_count,
                'parsing_stats': self.stats
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get learning stats: {e}")
            return {}
    
    def get_parser_stats(self) -> Dict[str, Any]:
        """Get parser statistics"""
        return {
            **self.stats,
            'success_rate': self.stats["total_parsed"] - self.stats["failed_parses"] / max(self.stats["total_parsed"], 1),
            'ai_success_rate': self.stats["ai_parses"] / max(self.stats["total_parsed"], 1),
            'cache_hit_rate': self.stats["cached_results"] / max(self.stats["total_parsed"], 1)
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.learning_db:
            self.learning_db.close()
        self.logger.info("Parser core cleanup completed")

# Configuration example
def create_default_config() -> Dict[str, Any]:
    """Create default configuration for advanced parser"""
    return {
        "advanced_parser": {
            "enable_ai_parsing": True,
            "ai_fallback_enabled": True,
            "confidence_threshold": 0.7,
            "min_confidence_for_execution": 0.8,
            "enable_ocr": True,
            "ocr_confidence_threshold": 0.6,
            "enable_multilingual": True,
            "enable_learning_loop": True,
            "store_failed_parses": True,
            "ai_model": {
                "model_name": "phi3",
                "base_url": "http://localhost:11434",
                "timeout": 30,
                "temperature": 0.1,
                "max_tokens": 1000
            }
        }
    }

if __name__ == "__main__":
    # Example usage
    async def main():
        parser = SignalParserCore()
        
        # Test signal parsing
        test_signal = "EURUSD BUY @ 1.0850 SL: 1.0800 TP1: 1.0900 TP2: 1.0950"
        result = await parser.parse_signal(test_signal)
        
        print(f"Symbol: {result.symbol}")
        print(f"Entry: {result.entry_price}")
        print(f"SL: {result.stop_loss}")
        print(f"TPs: {result.take_profits}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Method: {result.parsing_method.value}")
        
        parser.cleanup()
    
    asyncio.run(main())