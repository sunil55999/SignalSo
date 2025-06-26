"""
Secure Signal Parser for SignalOS
Addresses unsafe signal parsing with comprehensive validation
"""

import re
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import html

class ParseResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SUSPICIOUS = "suspicious"

@dataclass
class ParsedSignal:
    symbol: str
    action: str
    entry: Optional[str] = None
    stop_loss: Optional[str] = None
    take_profit_1: Optional[str] = None
    take_profit_2: Optional[str] = None
    take_profit_3: Optional[str] = None
    confidence: float = 0.0
    raw_message: str = ""
    parse_result: ParseResult = ParseResult.FAILED
    validation_errors: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.metadata is None:
            self.metadata = {}

class SecureSignalParser:
    """Secure signal parser with comprehensive validation and sanitization"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        
        # Load configuration and patterns
        self._load_config()
        self._compile_patterns()
        
        # Security tracking
        self.security_stats = {
            'total_parsed': 0,
            'suspicious_attempts': 0,
            'blocked_patterns': 0,
            'validation_failures': 0
        }
        
    def _load_config(self):
        """Load configuration with secure defaults"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.config = config.get('signal_parser', {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.warning(f"Config load failed: {e}, using defaults")
            self.config = {}
            
        # Set secure defaults
        self.config.setdefault('max_message_length', 2000)
        self.config.setdefault('allowed_symbols', [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            'EURJPY', 'EURGBP', 'EURCHF', 'EURAUD', 'EURCAD', 'GBPJPY', 'GBPCHF',
            'GBPAUD', 'GBPCAD', 'AUDJPY', 'AUDCHF', 'AUDCAD', 'CADJPY', 'CHFJPY',
            'NZDJPY', 'NZDCHF', 'NZDCAD'
        ])
        self.config.setdefault('blocked_patterns', [
            r'<script.*?</script>',
            r'javascript:',
            r'data:text/html',
            r'eval\s*\(',
            r'exec\s*\(',
            r'system\s*\(',
            r'import\s+os',
            r'__import__',
            r'file://',
            r'http://[^s]',  # Allow only https
        ])
        self.config.setdefault('max_price_deviation', 10.0)  # 10% max price deviation
        
    def _compile_patterns(self):
        """Compile regex patterns for signal parsing"""
        self.patterns = {
            'action': re.compile(r'\b(BUY|SELL|LONG|SHORT)\b', re.IGNORECASE),
            'symbol': re.compile(r'\b([A-Z]{6,8})\b'),
            'entry': re.compile(r'(?:ENTRY|E|ENTER|@)\s*:?\s*([0-9]+\.?[0-9]*)', re.IGNORECASE),
            'stop_loss': re.compile(r'(?:SL|STOP\s*LOSS|STOPLOSS)\s*:?\s*([0-9]+\.?[0-9]*)', re.IGNORECASE),
            'take_profit': re.compile(r'(?:TP|TAKE\s*PROFIT|TAKEPROFIT)([1-5])?\s*:?\s*([0-9]+\.?[0-9]*)', re.IGNORECASE),
            'price_range': re.compile(r'([0-9]+\.?[0-9]*)\s*[-–]\s*([0-9]+\.?[0-9]*)'),
        }
        
        # Compile security patterns
        self.security_patterns = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL) 
            for pattern in self.config['blocked_patterns']
        ]
        
    def parse_signal_safely(self, raw_message: str, source_info: Dict[str, Any] = None) -> ParsedSignal:
        """
        Parse signal with comprehensive security validation
        
        Args:
            raw_message: Raw signal message
            source_info: Information about signal source
            
        Returns:
            ParsedSignal object with validation results
        """
        start_time = time.time()
        self.security_stats['total_parsed'] += 1
        
        # Initialize result
        result = ParsedSignal(
            symbol="",
            action="",
            raw_message=raw_message,
            metadata={
                'parse_time': datetime.now().isoformat(),
                'source_info': source_info or {},
                'parser_version': '2.0.0'
            }
        )
        
        try:
            # Step 1: Input validation and sanitization
            sanitized_message = self._sanitize_input(raw_message)
            if not sanitized_message:
                result.validation_errors.append("Message failed sanitization")
                return result
                
            # Step 2: Security pattern detection
            if self._detect_malicious_patterns(sanitized_message):
                result.parse_result = ParseResult.SUSPICIOUS
                self.security_stats['suspicious_attempts'] += 1
                return result
                
            # Step 3: Extract signal components
            action = self._extract_action(sanitized_message)
            symbol = self._extract_symbol(sanitized_message)
            
            if not action or not symbol:
                result.validation_errors.append("Missing required action or symbol")
                return result
                
            # Step 4: Validate symbol against whitelist
            if not self._validate_symbol(symbol):
                result.validation_errors.append(f"Symbol not allowed: {symbol}")
                return result
                
            # Step 5: Extract price levels
            entry = self._extract_entry_price(sanitized_message)
            stop_loss = self._extract_stop_loss(sanitized_message)
            take_profits = self._extract_take_profits(sanitized_message)
            
            # Step 6: Validate price levels
            if not self._validate_price_levels(symbol, entry, stop_loss, take_profits):
                result.validation_errors.append("Price levels validation failed")
                return result
                
            # Step 7: Build result
            result.symbol = symbol
            result.action = action
            result.entry = entry
            result.stop_loss = stop_loss
            
            if take_profits:
                result.take_profit_1 = take_profits.get('tp1')
                result.take_profit_2 = take_profits.get('tp2')
                result.take_profit_3 = take_profits.get('tp3')
                
            # Step 8: Calculate confidence score
            result.confidence = self._calculate_confidence(result)
            
            # Step 9: Final validation
            if result.confidence > 0.5:
                result.parse_result = ParseResult.SUCCESS
            elif result.confidence > 0.2:
                result.parse_result = ParseResult.PARTIAL
            else:
                result.parse_result = ParseResult.FAILED
                
            # Add performance metadata
            result.metadata['parse_duration_ms'] = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            self.logger.error(f"Signal parsing error: {e}")
            result.validation_errors.append(f"Parsing exception: {str(e)}")
            self.security_stats['validation_failures'] += 1
            return result
            
    def _sanitize_input(self, message: str) -> Optional[str]:
        """Sanitize input message for safe processing"""
        if not message or not isinstance(message, str):
            return None
            
        # Check length limit
        if len(message) > self.config['max_message_length']:
            self.logger.warning(f"Message too long: {len(message)} chars")
            return None
            
        # HTML decode and escape
        message = html.unescape(message)
        
        # Remove null bytes and control characters
        message = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', message)
        
        # Normalize whitespace
        message = re.sub(r'\s+', ' ', message.strip())
        
        return message
        
    def _detect_malicious_patterns(self, message: str) -> bool:
        """Detect potentially malicious patterns in message"""
        for pattern in self.security_patterns:
            if pattern.search(message):
                self.logger.warning(f"Blocked malicious pattern in message")
                self.security_stats['blocked_patterns'] += 1
                return True
                
        # Check for excessive special characters (potential encoding attacks)
        special_char_ratio = len(re.findall(r'[^\w\s\.\-:@]', message)) / len(message)
        if special_char_ratio > 0.3:
            self.logger.warning(f"High special character ratio: {special_char_ratio}")
            return True
            
        return False
        
    def _extract_action(self, message: str) -> Optional[str]:
        """Extract trading action from message"""
        match = self.patterns['action'].search(message)
        if match:
            action = match.group(1).upper()
            # Normalize action
            if action in ['LONG']:
                return 'BUY'
            elif action in ['SHORT']:
                return 'SELL'
            elif action in ['BUY', 'SELL']:
                return action
                
        return None
        
    def _extract_symbol(self, message: str) -> Optional[str]:
        """Extract currency pair symbol from message"""
        matches = self.patterns['symbol'].findall(message)
        
        for match in matches:
            symbol = match.upper()
            # Basic symbol format validation
            if len(symbol) >= 6 and len(symbol) <= 8:
                # Check if it looks like a currency pair
                if re.match(r'^[A-Z]{6,8}$', symbol):
                    return symbol
                    
        return None
        
    def _validate_symbol(self, symbol: str) -> bool:
        """Validate symbol against allowed list"""
        return symbol.upper() in self.config['allowed_symbols']
        
    def _extract_entry_price(self, message: str) -> Optional[str]:
        """Extract entry price from message"""
        match = self.patterns['entry'].search(message)
        if match:
            price = match.group(1)
            if self._is_valid_price_format(price):
                return price
                
        return None
        
    def _extract_stop_loss(self, message: str) -> Optional[str]:
        """Extract stop loss price from message"""
        match = self.patterns['stop_loss'].search(message)
        if match:
            price = match.group(1)
            if self._is_valid_price_format(price):
                return price
                
        return None
        
    def _extract_take_profits(self, message: str) -> Dict[str, str]:
        """Extract take profit levels from message"""
        take_profits = {}
        
        for match in self.patterns['take_profit'].finditer(message):
            level = match.group(1) or '1'  # Default to TP1 if no number
            price = match.group(2)
            
            if self._is_valid_price_format(price):
                tp_key = f'tp{level}'
                if tp_key not in take_profits:  # Only first occurrence
                    take_profits[tp_key] = price
                    
        return take_profits
        
    def _is_valid_price_format(self, price_str: str) -> bool:
        """Validate price format"""
        try:
            price = float(price_str)
            # Basic sanity checks
            return 0.0001 <= price <= 100000.0
        except (ValueError, TypeError):
            return False
            
    def _validate_price_levels(self, symbol: str, entry: Optional[str], 
                             stop_loss: Optional[str], take_profits: Dict[str, str]) -> bool:
        """Validate price level relationships"""
        try:
            if not entry:
                return False
                
            entry_price = float(entry)
            
            # Validate stop loss relationship
            if stop_loss:
                sl_price = float(stop_loss)
                # Stop loss should be different from entry
                if abs(entry_price - sl_price) < 0.0001:
                    return False
                    
            # Validate take profit relationships
            for tp_key, tp_value in take_profits.items():
                tp_price = float(tp_value)
                # Take profit should be different from entry
                if abs(entry_price - tp_price) < 0.0001:
                    return False
                    
            return True
            
        except (ValueError, TypeError):
            return False
            
    def _calculate_confidence(self, signal: ParsedSignal) -> float:
        """Calculate confidence score for parsed signal"""
        score = 0.0
        
        # Base score for having required fields
        if signal.symbol and signal.action:
            score += 0.3
            
        # Entry price adds confidence
        if signal.entry:
            score += 0.2
            
        # Stop loss adds confidence
        if signal.stop_loss:
            score += 0.2
            
        # Take profit levels add confidence
        tp_count = sum(1 for tp in [signal.take_profit_1, signal.take_profit_2, signal.take_profit_3] if tp)
        score += min(tp_count * 0.1, 0.3)
        
        # Symbol in common pairs gets bonus
        if signal.symbol in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']:
            score += 0.1
            
        # Penalty for validation errors
        if signal.validation_errors:
            score -= len(signal.validation_errors) * 0.1
            
        return max(0.0, min(1.0, score))
        
    def get_parser_statistics(self) -> Dict[str, Any]:
        """Get parser performance and security statistics"""
        return {
            'total_parsed': self.security_stats['total_parsed'],
            'suspicious_attempts': self.security_stats['suspicious_attempts'],
            'blocked_patterns': self.security_stats['blocked_patterns'],
            'validation_failures': self.security_stats['validation_failures'],
            'security_ratio': (self.security_stats['suspicious_attempts'] + self.security_stats['blocked_patterns']) / max(1, self.security_stats['total_parsed']) * 100,
            'allowed_symbols_count': len(self.config['allowed_symbols']),
            'blocked_patterns_count': len(self.config['blocked_patterns']),
            'config': {
                'max_message_length': self.config['max_message_length'],
                'max_price_deviation': self.config['max_price_deviation']
            }
        }

# Global parser instance
secure_parser = SecureSignalParser()

def parse_signal_securely(message: str, source_info: Dict[str, Any] = None) -> ParsedSignal:
    """Global function for secure signal parsing"""
    return secure_parser.parse_signal_safely(message, source_info)

def get_parser_stats() -> Dict[str, Any]:
    """Global function to get parser statistics"""
    return secure_parser.get_parser_statistics()