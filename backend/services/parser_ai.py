"""
AI-powered signal parsing service with fallback mechanisms
"""

import re
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

from utils.logging_config import get_logger

logger = get_logger("parser.ai")


class SignalType(Enum):
    """Signal types"""
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"
    MODIFY = "MODIFY"


class ConfidenceLevel(Enum):
    """Confidence levels for parsing"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class ParsedSignal:
    """Parsed signal data structure"""
    symbol: str
    signal_type: SignalType
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[List[float]] = None
    lot_size: Optional[float] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNCERTAIN
    raw_text: str = ""
    parsing_method: str = "unknown"
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.take_profit is None:
            self.take_profit = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['signal_type'] = self.signal_type.value
        data['confidence'] = self.confidence.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


class RegexFallbackParser:
    """Regex-based fallback parser for when AI fails"""
    
    def __init__(self):
        # Common trading symbols pattern
        self.symbol_pattern = r'(?:EUR/USD|GBP/USD|USD/JPY|AUD/USD|USD/CHF|NZD/USD|USD/CAD|XAU/USD|GOLD|SILVER|BTC|ETH|[A-Z]{6})'
        
        # Signal type patterns
        self.buy_patterns = [
            r'\b(?:BUY|LONG|BULL)\b',
            r'🔵|📈|⬆️|🟢'
        ]
        
        self.sell_patterns = [
            r'\b(?:SELL|SHORT|BEAR)\b',
            r'🔴|📉|⬇️|🔻'
        ]
        
        # Price patterns
        self.price_pattern = r'\b\d+\.?\d*\b'
        self.tp_pattern = r'(?:TP|Take\s*Profit|Target)[:\s]*(\d+\.?\d*)'
        self.sl_pattern = r'(?:SL|Stop\s*Loss|Stop)[:\s]*(\d+\.?\d*)'
        self.entry_pattern = r'(?:Entry|Enter|Price)[:\s]*(\d+\.?\d*)'
    
    def parse_signal(self, text: str) -> Optional[ParsedSignal]:
        """Parse signal using regex patterns"""
        try:
            text_upper = text.upper()
            
            # Extract symbol
            symbol_match = re.search(self.symbol_pattern, text_upper)
            if not symbol_match:
                logger.debug("No symbol found in text")
                return None
            
            symbol = symbol_match.group()
            
            # Determine signal type
            signal_type = None
            if any(re.search(pattern, text_upper) for pattern in self.buy_patterns):
                signal_type = SignalType.BUY
            elif any(re.search(pattern, text_upper) for pattern in self.sell_patterns):
                signal_type = SignalType.SELL
            
            if not signal_type:
                logger.debug("No signal type detected")
                return None
            
            # Extract prices
            entry_price = self._extract_price(text, self.entry_pattern)
            stop_loss = self._extract_price(text, self.sl_pattern)
            take_profit_prices = self._extract_multiple_tp(text)
            
            signal = ParsedSignal(
                symbol=symbol,
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit_prices,
                confidence=ConfidenceLevel.MEDIUM,
                raw_text=text,
                parsing_method="regex_fallback"
            )
            
            logger.info(f"Regex fallback parsed signal: {symbol} {signal_type.value}")
            return signal
            
        except Exception as e:
            logger.error(f"Regex fallback parsing error: {e}")
            return None
    
    def _extract_price(self, text: str, pattern: str) -> Optional[float]:
        """Extract single price value"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                pass
        return None
    
    def _extract_multiple_tp(self, text: str) -> List[float]:
        """Extract multiple take profit levels"""
        tp_prices = []
        matches = re.findall(self.tp_pattern, text, re.IGNORECASE)
        
        for match in matches:
            try:
                tp_prices.append(float(match))
            except ValueError:
                continue
        
        return tp_prices


class AISignalParser:
    """AI-powered signal parser with intelligent processing"""
    
    def __init__(self):
        self.fallback_parser = RegexFallbackParser()
        self.confidence_threshold = 0.8
        
        # Simulated AI model responses for demo
        self.model_patterns = {
            "buy_signals": [
                "buy", "long", "bull", "up", "green", "buy limit", "buy stop"
            ],
            "sell_signals": [
                "sell", "short", "bear", "down", "red", "sell limit", "sell stop"
            ]
        }
    
    async def parse_signal(self, text: str, image_data: Optional[bytes] = None) -> Optional[ParsedSignal]:
        """
        Parse trading signal from text or image using AI with fallback
        """
        try:
            # Primary AI parsing attempt
            signal = await self._ai_parse_signal(text, image_data)
            
            if signal and signal.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]:
                logger.info(f"AI successfully parsed signal with {signal.confidence.value} confidence")
                return signal
            
            # Fallback to regex parsing
            logger.info("AI parsing failed or low confidence, using regex fallback")
            fallback_signal = self.fallback_parser.parse_signal(text)
            
            if fallback_signal:
                fallback_signal.confidence = ConfidenceLevel.LOW
                return fallback_signal
            
            logger.warning("Both AI and regex parsing failed")
            return None
            
        except Exception as e:
            logger.error(f"Signal parsing error: {e}")
            return None
    
    async def _ai_parse_signal(self, text: str, image_data: Optional[bytes] = None) -> Optional[ParsedSignal]:
        """
        Simulated AI parsing (in production, would use actual LLM)
        """
        await asyncio.sleep(0.1)  # Simulate AI processing time
        
        try:
            # Simulate AI analysis
            text_lower = text.lower()
            
            # Detect signal type
            signal_type = None
            confidence_score = 0.0
            
            buy_indicators = sum(1 for pattern in self.model_patterns["buy_signals"] if pattern in text_lower)
            sell_indicators = sum(1 for pattern in self.model_patterns["sell_signals"] if pattern in text_lower)
            
            if buy_indicators > sell_indicators:
                signal_type = SignalType.BUY
                confidence_score = min(0.9, 0.5 + (buy_indicators * 0.1))
            elif sell_indicators > buy_indicators:
                signal_type = SignalType.SELL
                confidence_score = min(0.9, 0.5 + (sell_indicators * 0.1))
            
            if not signal_type:
                return None
            
            # Extract trading data using improved pattern matching
            symbol = self._extract_ai_symbol(text)
            entry_price = self._extract_ai_price(text, "entry")
            stop_loss = self._extract_ai_price(text, "stop")
            take_profits = self._extract_ai_take_profits(text)
            
            # Determine confidence level
            if confidence_score >= 0.8:
                confidence = ConfidenceLevel.HIGH
            elif confidence_score >= 0.6:
                confidence = ConfidenceLevel.MEDIUM
            else:
                confidence = ConfidenceLevel.LOW
            
            signal = ParsedSignal(
                symbol=symbol or "UNKNOWN",
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profits,
                confidence=confidence,
                raw_text=text,
                parsing_method="ai_primary"
            )
            
            logger.debug(f"AI parsed signal with confidence {confidence_score:.2f}")
            return signal
            
        except Exception as e:
            logger.error(f"AI parsing error: {e}")
            return None
    
    def _extract_ai_symbol(self, text: str) -> Optional[str]:
        """Extract trading symbol using AI-like logic"""
        # Enhanced symbol detection
        symbol_patterns = [
            r'\b(EUR/USD|EURUSD)\b',
            r'\b(GBP/USD|GBPUSD)\b',
            r'\b(USD/JPY|USDJPY)\b',
            r'\b(XAU/USD|XAUUSD|GOLD)\b',
            r'\b([A-Z]{3}/[A-Z]{3})\b',
            r'\b([A-Z]{6})\b'
        ]
        
        for pattern in symbol_patterns:
            match = re.search(pattern, text.upper())
            if match:
                return match.group(1)
        
        return None
    
    def _extract_ai_price(self, text: str, price_type: str) -> Optional[float]:
        """Extract price using AI-enhanced pattern matching"""
        type_patterns = {
            "entry": [r'(?:entry|enter|price)[:\s]*(\d+\.?\d*)', r'@\s*(\d+\.?\d*)'],
            "stop": [r'(?:sl|stop\s*loss|stop)[:\s]*(\d+\.?\d*)']
        }
        
        patterns = type_patterns.get(price_type, [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_ai_take_profits(self, text: str) -> List[float]:
        """Extract take profit levels using AI logic"""
        tp_patterns = [
            r'(?:tp|take\s*profit|target)\s*[1-9]?[:\s]*(\d+\.?\d*)',
            r'target[:\s]*(\d+\.?\d*)'
        ]
        
        tp_prices = []
        for pattern in tp_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    price = float(match)
                    if price not in tp_prices:  # Avoid duplicates
                        tp_prices.append(price)
                except ValueError:
                    continue
        
        return sorted(tp_prices)


class SignalProcessor:
    """Main signal processing orchestrator"""
    
    def __init__(self):
        self.ai_parser = AISignalParser()
        self.processed_signals = []
        self.processing_stats = {
            "total_processed": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "ai_successes": 0,
            "fallback_uses": 0
        }
    
    async def process_signal(self, raw_input: str, image_data: Optional[bytes] = None) -> Optional[ParsedSignal]:
        """Process incoming signal"""
        self.processing_stats["total_processed"] += 1
        
        try:
            # Clean and preprocess input
            cleaned_input = self._preprocess_input(raw_input)
            
            # Parse signal
            signal = await self.ai_parser.parse_signal(cleaned_input, image_data)
            
            if signal:
                self.processing_stats["successful_parses"] += 1
                
                if signal.parsing_method == "ai_primary":
                    self.processing_stats["ai_successes"] += 1
                else:
                    self.processing_stats["fallback_uses"] += 1
                
                # Store processed signal
                self.processed_signals.append(signal)
                
                logger.info(f"Successfully processed signal: {signal.symbol} {signal.signal_type.value}")
                return signal
            else:
                self.processing_stats["failed_parses"] += 1
                logger.warning("Failed to parse signal")
                return None
                
        except Exception as e:
            self.processing_stats["failed_parses"] += 1
            logger.error(f"Signal processing error: {e}")
            return None
    
    def _preprocess_input(self, raw_input: str) -> str:
        """Clean and preprocess input text"""
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', raw_input.strip())
        
        # Remove common noise
        noise_patterns = [
            r'@\w+',  # Remove mentions
            r'#\w+',  # Remove hashtags
            r'http[s]?://\S+',  # Remove URLs
        ]
        
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        return cleaned.strip()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        stats = self.processing_stats.copy()
        if stats["total_processed"] > 0:
            stats["success_rate"] = stats["successful_parses"] / stats["total_processed"]
            stats["ai_success_rate"] = stats["ai_successes"] / stats["total_processed"]
        else:
            stats["success_rate"] = 0.0
            stats["ai_success_rate"] = 0.0
        
        return stats