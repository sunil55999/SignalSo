#!/usr/bin/env python3
"""
Fallback Regex Parser for SignalOS
Last resort parser using regex patterns when AI fails
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from .parser_utils import normalize_pair_symbol, normalize_direction, extract_numeric_values


class FallbackRegexParser:
    """Regex-based fallback parser for when AI parsing fails"""
    
    def __init__(self):
        self.setup_logging()
        self.setup_patterns()
        
    def setup_logging(self):
        """Setup logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / "fallback_parser.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_patterns(self):
        """Setup regex patterns for signal extraction"""
        
        # Trading pair patterns
        self.pair_patterns = [
            r'\b([A-Z]{6})\b',  # Standard 6-letter pairs like EURUSD
            r'\b([A-Z]{3}/[A-Z]{3})\b',  # Pairs with slash like EUR/USD
            r'\b(XAU/?USD)\b',  # Gold variations
            r'\b(XAG/?USD)\b',  # Silver variations
            r'\b(GOLD|SILVER|OIL)\b',  # Commodity names
            r'\b([A-Z]{2,4})\b'  # Generic symbol pattern
        ]
        
        # Direction patterns
        self.direction_patterns = [
            r'\b(BUY|SELL|LONG|SHORT|BULL|BEAR)\b',
            r'\b(B|S|L)\b(?=\s)',  # Single letter directions
            r'(↗|↙|🔼|🔽)',  # Arrow symbols
        ]
        
        # Price patterns
        self.price_patterns = [
            r'(?:entry|ep|e|@|at)[\s:]*(\d+\.?\d*)',  # Entry price
            r'(?:stop\s*loss|sl|s)[\s:]*(\d+\.?\d*)',  # Stop loss
            r'(?:take\s*profit|tp|t)[\s:]*(\d+\.?\d*)',  # Take profit
            r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)',  # Price ranges
            r'(\d{1,4}\.\d{2,5})',  # General price format
        ]
        
        # Multi-TP patterns
        self.multi_tp_patterns = [
            r'(?:tp1|tp\s*1)[\s:]*(\d+\.?\d*)',
            r'(?:tp2|tp\s*2)[\s:]*(\d+\.?\d*)', 
            r'(?:tp3|tp\s*3)[\s:]*(\d+\.?\d*)',
            r'(?:tp4|tp\s*4)[\s:]*(\d+\.?\d*)',
            r'(?:tp5|tp\s*5)[\s:]*(\d+\.?\d*)',
        ]
        
        # Entry range patterns
        self.entry_range_patterns = [
            r'(?:entry|ep)[\s:]*(\d+\.?\d*)\s*-\s*(\d+\.?\d*)',
            r'(?:between|range)[\s:]*(\d+\.?\d*)\s*(?:and|to|\-)\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)',  # Price1/Price2 format
        ]
        
    def extract_trading_pair(self, text: str) -> Optional[str]:
        """Extract trading pair from text using regex"""
        text_upper = text.upper()
        
        for pattern in self.pair_patterns:
            matches = re.findall(pattern, text_upper, re.IGNORECASE)
            if matches:
                for match in matches:
                    normalized = normalize_pair_symbol(match)
                    if len(normalized) >= 6:  # Valid pair length
                        return normalized
                        
        return None
        
    def extract_direction(self, text: str) -> Optional[str]:
        """Extract trading direction from text using regex"""
        text_upper = text.upper()
        
        for pattern in self.direction_patterns:
            matches = re.findall(pattern, text_upper, re.IGNORECASE)
            if matches:
                for match in matches:
                    normalized = normalize_direction(match)
                    if normalized in ["BUY", "SELL"]:
                        return normalized
                        
        # Fallback: analyze context
        if any(word in text_upper for word in ["LONG", "BULL", "UP", "CALL", "GREEN"]):
            return "BUY"
        elif any(word in text_upper for word in ["SHORT", "BEAR", "DOWN", "PUT", "RED"]):
            return "SELL"
            
        return None
        
    def extract_entry_prices(self, text: str) -> List[float]:
        """Extract entry price(s) from text"""
        entry_prices = []
        
        # Try entry range patterns first
        for pattern in self.entry_range_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    try:
                        if isinstance(match, tuple):
                            price1, price2 = float(match[0]), float(match[1])
                            entry_prices.extend([price1, price2])
                        else:
                            entry_prices.append(float(match))
                    except ValueError:
                        continue
                        
        if entry_prices:
            return sorted(set(entry_prices))  # Remove duplicates and sort
            
        # Try single entry patterns
        entry_pattern = r'(?:entry|ep|e|@|at)[\s:]*(\d+\.?\d*)'
        matches = re.findall(entry_pattern, text, re.IGNORECASE)
        
        for match in matches:
            try:
                entry_prices.append(float(match))
            except ValueError:
                continue
                
        if entry_prices:
            return sorted(set(entry_prices))
            
        # Fallback: extract first reasonable price
        all_numbers = extract_numeric_values(text)
        if all_numbers:
            # Filter reasonable price ranges
            reasonable_prices = [p for p in all_numbers if 0.1 <= p <= 10000]
            if reasonable_prices:
                return [reasonable_prices[0]]
                
        return []
        
    def extract_stop_loss(self, text: str) -> Optional[float]:
        """Extract stop loss from text"""
        sl_pattern = r'(?:stop\s*loss|sl|s)[\s:]*(\d+\.?\d*)'
        matches = re.findall(sl_pattern, text, re.IGNORECASE)
        
        if matches:
            try:
                return float(matches[0])
            except ValueError:
                pass
                
        # Fallback: look for "stop" keyword near numbers
        stop_pattern = r'stop[\s:]*(\d+\.?\d*)'
        matches = re.findall(stop_pattern, text, re.IGNORECASE)
        
        if matches:
            try:
                return float(matches[0])
            except ValueError:
                pass
                
        return None
        
    def extract_take_profits(self, text: str) -> List[float]:
        """Extract take profit level(s) from text"""
        take_profits = []
        
        # Try multi-TP patterns
        for pattern in self.multi_tp_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    take_profits.append(float(match))
                except ValueError:
                    continue
                    
        if take_profits:
            return sorted(set(take_profits))
            
        # Try general TP patterns
        tp_pattern = r'(?:take\s*profit|tp|t)[\s:]*(\d+\.?\d*)'
        matches = re.findall(tp_pattern, text, re.IGNORECASE)
        
        for match in matches:
            try:
                take_profits.append(float(match))
            except ValueError:
                continue
                
        if take_profits:
            return sorted(set(take_profits))
            
        # Fallback: look for "target" or "profit" near numbers
        target_pattern = r'(?:target|profit|goal)[\s:]*(\d+\.?\d*)'
        matches = re.findall(target_pattern, text, re.IGNORECASE)
        
        for match in matches:
            try:
                take_profits.append(float(match))
            except ValueError:
                continue
                
        return sorted(set(take_profits)) if take_profits else []
        
    def parse_signal_regex(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse signal using regex patterns as fallback method
        
        Args:
            text: Cleaned signal text
            
        Returns:
            Parsed signal dictionary or None if parsing failed
        """
        try:
            self.logger.info(f"Attempting regex fallback parse: {text[:100]}...")
            
            # Extract components
            pair = self.extract_trading_pair(text)
            direction = self.extract_direction(text)
            entry_prices = self.extract_entry_prices(text)
            stop_loss = self.extract_stop_loss(text)
            take_profits = self.extract_take_profits(text)
            
            # Validate minimum requirements
            if not pair:
                self.logger.warning("No trading pair found in text")
                return None
                
            if not direction:
                self.logger.warning("No trading direction found in text")
                return None
                
            if not entry_prices:
                self.logger.warning("No entry prices found in text")
                return None
                
            # Use fallback values if SL/TP not found
            if not stop_loss:
                # Generate reasonable SL based on entry and direction
                avg_entry = sum(entry_prices) / len(entry_prices)
                if direction == "BUY":
                    stop_loss = avg_entry * 0.995  # 0.5% below entry
                else:
                    stop_loss = avg_entry * 1.005  # 0.5% above entry
                    
                self.logger.warning(f"No stop loss found, using calculated: {stop_loss}")
                
            if not take_profits:
                # Generate reasonable TP based on entry and direction
                avg_entry = sum(entry_prices) / len(entry_prices)
                if direction == "BUY":
                    take_profits = [avg_entry * 1.01, avg_entry * 1.02]  # 1% and 2% above
                else:
                    take_profits = [avg_entry * 0.99, avg_entry * 0.98]  # 1% and 2% below
                    
                self.logger.warning(f"No take profits found, using calculated: {take_profits}")
                
            # Build result
            result = {
                "pair": pair,
                "direction": direction,
                "entry": entry_prices,
                "sl": stop_loss,
                "tp": take_profits,
                "confidence": 0.6,  # Lower confidence for regex parsing
                "parser_method": "fallback_regex"
            }
            
            self.logger.info(f"Regex parser success: {pair} {direction}")
            return result
            
        except Exception as e:
            self.logger.error(f"Regex parser failed: {e}")
            return None
            
    def parse_structured_signal(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse well-structured signals with clear formatting
        
        Args:
            text: Signal text
            
        Returns:
            Parsed signal or None
        """
        try:
            # Pattern for well-structured signals
            structured_patterns = [
                # Pattern: "BUY EURUSD @ 1.0850, SL: 1.0800, TP: 1.0900"
                r'(BUY|SELL)\s+([A-Z]{6})\s+@?\s*(\d+\.?\d*),?\s*SL:?\s*(\d+\.?\d*),?\s*TP:?\s*(\d+\.?\d*)',
                
                # Pattern: "EURUSD BUY Entry: 1.0850 SL: 1.0800 TP: 1.0900"
                r'([A-Z]{6})\s+(BUY|SELL)\s+Entry:?\s*(\d+\.?\d*)\s+SL:?\s*(\d+\.?\d*)\s+TP:?\s*(\d+\.?\d*)',
                
                # Pattern: "Symbol: EURUSD Direction: BUY Entry: 1.0850 Stop: 1.0800 Target: 1.0900"
                r'Symbol:?\s*([A-Z]{6}).*?Direction:?\s*(BUY|SELL).*?Entry:?\s*(\d+\.?\d*).*?Stop:?\s*(\d+\.?\d*).*?Target:?\s*(\d+\.?\d*)',
            ]
            
            for pattern in structured_patterns:
                match = re.search(pattern, text.upper(), re.IGNORECASE | re.DOTALL)
                if match:
                    groups = match.groups()
                    
                    # Parse based on pattern structure
                    if len(groups) >= 5:
                        if groups[0] in ["BUY", "SELL"]:
                            # First pattern format
                            direction, pair, entry, sl, tp = groups[:5]
                        else:
                            # Second pattern format
                            pair, direction, entry, sl, tp = groups[:5]
                            
                        try:
                            result = {
                                "pair": normalize_pair_symbol(pair),
                                "direction": normalize_direction(direction),
                                "entry": [float(entry)],
                                "sl": float(sl),
                                "tp": [float(tp)],
                                "confidence": 0.8,  # Higher confidence for structured signals
                                "parser_method": "structured_regex"
                            }
                            
                            self.logger.info(f"Structured parser success: {result['pair']} {result['direction']}")
                            return result
                            
                        except ValueError as e:
                            self.logger.warning(f"Structured parser value error: {e}")
                            continue
                            
            return None
            
        except Exception as e:
            self.logger.error(f"Structured parser failed: {e}")
            return None


# Global parser instance
_fallback_parser: Optional[FallbackRegexParser] = None


def get_fallback_parser() -> FallbackRegexParser:
    """Get global fallback parser instance"""
    global _fallback_parser
    if _fallback_parser is None:
        _fallback_parser = FallbackRegexParser()
    return _fallback_parser


def fallback_parser(text: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function for fallback regex parsing
    
    Args:
        text: Signal text to parse
        
    Returns:
        Parsed signal dictionary or None
    """
    parser = get_fallback_parser()
    
    # Try structured parsing first
    result = parser.parse_structured_signal(text)
    if result:
        return result
        
    # Fall back to general regex parsing
    return parser.parse_signal_regex(text)


# Testing function
def test_fallback_parser():
    """Test the fallback regex parser"""
    test_signals = [
        "BUY EURUSD @ 1.0850, SL: 1.0800, TP: 1.0900",
        "🟢 SELL XAUUSD Entry: 2345 SL: 2350 TP1: 2339 TP2: 2333",
        "GBPUSD LONG now! Entry range 1.2500-1.2520, Stop Loss 1.2450, Take Profit 1.2600",
        "Signal: USDJPY Direction: SELL Entry: 145.50 Stop: 146.00 Target: 144.50",
        "Gold sell at 2340, sl 2345, tp 2330",
        "Invalid text without proper signal format"
    ]
    
    parser = FallbackRegexParser()
    
    print("🧪 Testing Fallback Regex Parser")
    print("=" * 50)
    
    for i, signal in enumerate(test_signals, 1):
        print(f"\nTest {i}: {signal}")
        
        # Try structured parsing
        structured_result = parser.parse_structured_signal(signal)
        if structured_result:
            print(f"✅ Structured: {structured_result['pair']} {structured_result['direction']}")
            print(f"   Entry: {structured_result['entry']}, SL: {structured_result['sl']}, TP: {structured_result['tp']}")
            continue
            
        # Try general regex parsing
        regex_result = parser.parse_signal_regex(signal)
        if regex_result:
            print(f"✅ Regex: {regex_result['pair']} {regex_result['direction']}")
            print(f"   Entry: {regex_result['entry']}, SL: {regex_result['sl']}, TP: {regex_result['tp']}")
        else:
            print("❌ Parsing failed")
            
    print(f"\n✅ Fallback parser testing complete")


if __name__ == "__main__":
    test_fallback_parser()