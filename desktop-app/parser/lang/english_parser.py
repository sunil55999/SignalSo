#!/usr/bin/env python3
"""
English Language Parser
Specialized parser for English trading signals
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path


class EnglishSignalParser:
    """Specialized parser for English trading signals"""
    
    def __init__(self):
        self.setup_logging()
        self.patterns = self._load_patterns()
        
    def setup_logging(self):
        """Setup logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / "english_parser.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _load_patterns(self) -> Dict[str, Any]:
        """Load English-specific patterns"""
        return {
            "buy_patterns": [
                r'\b(buy|long|call|bullish|go long|entry long|purchase)\b',
                r'\b(bull|up|upward|rise|rising|increase)\b'
            ],
            "sell_patterns": [
                r'\b(sell|short|put|bearish|go short|entry short|exit)\b',
                r'\b(bear|down|downward|fall|falling|decrease)\b'
            ],
            "currency_patterns": [
                r'\b([A-Z]{3}[A-Z]{3})\b',  # EURUSD format
                r'\b([A-Z]{3}\/[A-Z]{3})\b',  # EUR/USD format
                r'\b([A-Z]{3}\-[A-Z]{3})\b'   # EUR-USD format
            ],
            "price_patterns": [
                r'(?:at|@|price|entry)\s*:?\s*([0-9]+\.?[0-9]*)',
                r'([0-9]+\.?[0-9]*)\s*(?:level|price|entry)'
            ],
            "tp_patterns": [
                r'(?:tp|take profit|target|profit)\s*:?\s*([0-9]+\.?[0-9]*)',
                r'(?:tp[1-9]?)\s*:?\s*([0-9]+\.?[0-9]*)'
            ],
            "sl_patterns": [
                r'(?:sl|stop loss|stop)\s*:?\s*([0-9]+\.?[0-9]*)',
                r'(?:loss|stoploss)\s*:?\s*([0-9]+\.?[0-9]*)'
            ],
            "lot_patterns": [
                r'(?:lot|size|volume)\s*:?\s*([0-9]+\.?[0-9]*)',
                r'([0-9]+\.?[0-9]*)\s*lots?'
            ]
        }
        
    def extract_signal_type(self, text: str) -> Optional[str]:
        """Extract signal type (BUY/SELL)"""
        text_lower = text.lower()
        
        # Check for buy signals
        for pattern in self.patterns["buy_patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return "BUY"
                
        # Check for sell signals
        for pattern in self.patterns["sell_patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return "SELL"
                
        return None
        
    def extract_currency_pair(self, text: str) -> Optional[str]:
        """Extract currency pair"""
        for pattern in self.patterns["currency_patterns"]:
            match = re.search(pattern, text.upper())
            if match:
                pair = match.group(1)
                # Normalize format
                pair = pair.replace('/', '').replace('-', '')
                if len(pair) == 6:
                    return pair
                    
        return None
        
    def extract_prices(self, text: str) -> Dict[str, Any]:
        """Extract entry price, TP, and SL"""
        result = {
            "entry_price": None,
            "take_profit_levels": [],
            "stop_loss": None,
            "lot_size": None
        }
        
        # Extract entry price
        for pattern in self.patterns["price_patterns"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result["entry_price"] = float(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
                    
        # Extract take profit levels
        for pattern in self.patterns["tp_patterns"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    tp_value = float(match.group(1))
                    if tp_value not in result["take_profit_levels"]:
                        result["take_profit_levels"].append(tp_value)
                except (ValueError, IndexError):
                    continue
                    
        # Extract stop loss
        for pattern in self.patterns["sl_patterns"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result["stop_loss"] = float(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
                    
        # Extract lot size
        for pattern in self.patterns["lot_patterns"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result["lot_size"] = float(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
                    
        return result
        
    def extract_advanced_features(self, text: str) -> Dict[str, Any]:
        """Extract advanced trading features"""
        result = {
            "risk_reward_ratio": None,
            "confidence_level": None,
            "time_frame": None,
            "market_condition": None,
            "news_impact": None
        }
        
        # Risk-reward ratio
        rr_match = re.search(r'(?:rr|risk\s*reward|r:r)\s*:?\s*([0-9]+\.?[0-9]*)', text, re.IGNORECASE)
        if rr_match:
            try:
                result["risk_reward_ratio"] = float(rr_match.group(1))
            except ValueError:
                pass
                
        # Confidence level
        conf_match = re.search(r'(?:confidence|certainty)\s*:?\s*([0-9]+)%?', text, re.IGNORECASE)
        if conf_match:
            try:
                result["confidence_level"] = int(conf_match.group(1))
            except ValueError:
                pass
                
        # Time frame
        tf_patterns = [
            r'\b(M[1-9][0-9]*|m[1-9][0-9]*)\b',  # M1, M5, M15, etc.
            r'\b(H[1-9][0-9]*|h[1-9][0-9]*)\b',  # H1, H4, etc.
            r'\b(D[1-9]?|d[1-9]?)\b',            # D1, daily
            r'\b(W[1-9]?|w[1-9]?)\b'             # W1, weekly
        ]
        
        for pattern in tf_patterns:
            match = re.search(pattern, text)
            if match:
                result["time_frame"] = match.group(1).upper()
                break
                
        # Market condition
        if re.search(r'\b(trending|trend|breakout|momentum)\b', text, re.IGNORECASE):
            result["market_condition"] = "trending"
        elif re.search(r'\b(ranging|range|consolidation|sideways)\b', text, re.IGNORECASE):
            result["market_condition"] = "ranging"
        elif re.search(r'\b(volatile|volatility|choppy)\b', text, re.IGNORECASE):
            result["market_condition"] = "volatile"
            
        # News impact
        if re.search(r'\b(news|economic|fundamental|event)\b', text, re.IGNORECASE):
            if re.search(r'\b(high|important|major)\b', text, re.IGNORECASE):
                result["news_impact"] = "high"
            else:
                result["news_impact"] = "medium"
                
        return result
        
    def calculate_confidence(self, parsed_data: Dict[str, Any]) -> float:
        """Calculate parsing confidence score"""
        confidence = 0.0
        
        # Signal type identified
        if parsed_data.get("signal_type"):
            confidence += 0.3
            
        # Currency pair identified
        if parsed_data.get("currency_pair"):
            confidence += 0.3
            
        # Entry price identified
        if parsed_data.get("entry_price"):
            confidence += 0.2
            
        # TP levels identified
        if parsed_data.get("take_profit_levels"):
            confidence += 0.1
            
        # Stop loss identified
        if parsed_data.get("stop_loss"):
            confidence += 0.1
            
        return min(confidence, 1.0)
        
    def parse_signal(self, text: str) -> Dict[str, Any]:
        """
        Complete signal parsing for English text
        
        Args:
            text: Raw signal text in English
            
        Returns:
            Parsed signal data
        """
        self.logger.info(f"Parsing English signal: {text[:100]}...")
        
        # Extract basic elements
        signal_type = self.extract_signal_type(text)
        currency_pair = self.extract_currency_pair(text)
        prices = self.extract_prices(text)
        advanced = self.extract_advanced_features(text)
        
        # Combine results
        result = {
            "signal_type": signal_type,
            "currency_pair": currency_pair,
            "entry_price": prices["entry_price"],
            "take_profit_levels": prices["take_profit_levels"],
            "stop_loss": prices["stop_loss"],
            "lot_size": prices["lot_size"],
            "risk_reward_ratio": advanced["risk_reward_ratio"],
            "confidence_level": advanced["confidence_level"],
            "time_frame": advanced["time_frame"],
            "market_condition": advanced["market_condition"],
            "news_impact": advanced["news_impact"],
            "language": "english",
            "parser": "english_parser"
        }
        
        # Calculate confidence
        result["parsing_confidence"] = self.calculate_confidence(result)
        
        # Log results
        self.logger.info(f"Parsing complete - Type: {signal_type}, Pair: {currency_pair}, Confidence: {result['parsing_confidence']:.3f}")
        
        return result


def main():
    """Test the English parser"""
    print("🇺🇸 Testing English Signal Parser")
    print("=" * 50)
    
    parser = EnglishSignalParser()
    
    test_signals = [
        "BUY EURUSD at 1.0850, TP: 1.0900, SL: 1.0800, RR: 1:2",
        "SELL GBPUSD entry 1.2500, take profit 1.2450, stop loss 1.2550, lot size 0.1",
        "Long USDJPY @ 150.00, TP1: 150.50, TP2: 151.00, SL: 149.50, H4 timeframe",
        "Short EUR/USD at 1.0800, target 1.0750, stop 1.0850, trending market",
        "BUY signal AUDUSD 0.6800, profit target 0.6850, risk 0.6750, confidence 85%"
    ]
    
    for i, signal in enumerate(test_signals, 1):
        print(f"\n📊 Test Signal {i}:")
        print(f"   Input: {signal}")
        
        result = parser.parse_signal(signal)
        
        print(f"   Type: {result['signal_type']}")
        print(f"   Pair: {result['currency_pair']}")
        print(f"   Entry: {result['entry_price']}")
        print(f"   TP: {result['take_profit_levels']}")
        print(f"   SL: {result['stop_loss']}")
        print(f"   Confidence: {result['parsing_confidence']:.3f}")


if __name__ == "__main__":
    main()