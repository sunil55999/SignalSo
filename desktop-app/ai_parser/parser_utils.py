#!/usr/bin/env python3
"""
Parser Utilities for SignalOS
Sanitization, validation, and utility functions for safe signal parsing
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path


class SignalValidator:
    """Validates parsed signal data"""
    
    def __init__(self):
        self.required_fields = ["pair", "direction", "entry", "sl", "tp"]
        self.optional_fields = ["confidence", "risk_reward", "lot_size", "parser_method"]
        
        # Valid trading pairs
        self.valid_pairs = [
            "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
            "EURJPY", "EURGBP", "EURCHF", "EURAUD", "EURCAD", "EURNZD",
            "GBPJPY", "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD",
            "XAUUSD", "XAGUSD", "USOIL", "UK100", "US30", "NAS100", "SPX500"
        ]
        
        # Valid directions
        self.valid_directions = ["BUY", "SELL", "LONG", "SHORT"]
        
        # Price validation ranges
        self.price_ranges = {
            "EURUSD": (0.9000, 1.5000),
            "GBPUSD": (1.0000, 2.0000),
            "USDJPY": (80.00, 160.00),
            "USDCHF": (0.8000, 1.2000),
            "AUDUSD": (0.5000, 1.0000),
            "USDCAD": (1.0000, 1.6000),
            "NZDUSD": (0.4000, 0.9000),
            "XAUUSD": (1500.00, 3000.00),
            "XAGUSD": (15.00, 50.00)
        }


def sanitize_signal(raw_text: str) -> str:
    """
    Sanitize raw signal text by removing emojis and normalizing format
    
    Args:
        raw_text: Raw signal text from Telegram or other source
        
    Returns:
        Sanitized text ready for parsing
    """
    if not raw_text:
        return ""
        
    # Remove common emojis and symbols
    emoji_patterns = [
        r'🟢', r'🔴', r'⚡', r'💰', r'🚀', r'📈', r'📉', r'✅', r'❌',
        r'🎯', r'💪', r'🔥', r'⭐', r'💎', r'🌟', r'🏆', r'💯',
        r'👑', r'🎉', r'🔔', r'📢', r'📣', r'💸', r'💵', r'💴'
    ]
    
    sanitized = raw_text
    for pattern in emoji_patterns:
        sanitized = re.sub(pattern, '', sanitized)
        
    # Normalize common abbreviations and terms
    replacements = {
        'SL': 'Stop Loss',
        'TP': 'Take Profit',
        'TP1': 'Take Profit 1',
        'TP2': 'Take Profit 2', 
        'TP3': 'Take Profit 3',
        'Entry': 'Entry Price',
        'EP': 'Entry Price',
        'BE': 'Break Even',
        'RR': 'Risk Reward',
        'R:R': 'Risk Reward',
        'LOT': 'Lot Size',
        'LOTS': 'Lot Size'
    }
    
    for old, new in replacements.items():
        sanitized = re.sub(rf'\b{old}\b', new, sanitized, flags=re.IGNORECASE)
        
    # Clean up extra whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized.strip())
    
    return sanitized


def clean_text_input(text: str) -> str:
    """
    Clean and normalize text input for parsing
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
        
    # Remove HTML tags if present
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove excessive punctuation
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[?]{2,}', '?', text)
    text = re.sub(r'[.]{3,}', '...', text)
    
    # Normalize quotes
    text = re.sub(r'["""]', '"', text)
    text = re.sub(r"[''']", "'", text)
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    return text


def normalize_pair_symbol(symbol: str) -> str:
    """
    Normalize trading pair symbol to standard format
    
    Args:
        symbol: Raw symbol string
        
    Returns:
        Normalized symbol (e.g., "EURUSD")
    """
    if not symbol:
        return ""
        
    # Remove common separators and normalize
    normalized = re.sub(r'[/\-_\s]', '', symbol.upper())
    
    # Handle common variations
    symbol_mappings = {
        'GOLD': 'XAUUSD',
        'XAUSD': 'XAUUSD',
        'SILVER': 'XAGUSD',
        'XAGSD': 'XAGUSD',
        'OIL': 'USOIL',
        'CRUDE': 'USOIL',
        'WTI': 'USOIL',
        'BRENT': 'UKOIL',
        'SPX': 'SPX500',
        'SP500': 'SPX500',
        'NASDAQ': 'NAS100',
        'DOW': 'US30',
        'FTSE': 'UK100'
    }
    
    if normalized in symbol_mappings:
        return symbol_mappings[normalized]
        
    return normalized


def normalize_direction(direction: str) -> str:
    """
    Normalize trading direction to standard format
    
    Args:
        direction: Raw direction string
        
    Returns:
        Normalized direction ("BUY" or "SELL")
    """
    if not direction:
        return ""
        
    direction_upper = direction.upper().strip()
    
    # Map common variations
    buy_variations = ['BUY', 'LONG', 'BULL', 'UP', 'CALL', 'B', 'L']
    sell_variations = ['SELL', 'SHORT', 'BEAR', 'DOWN', 'PUT', 'S']
    
    if any(var in direction_upper for var in buy_variations):
        return "BUY"
    elif any(var in direction_upper for var in sell_variations):
        return "SELL"
        
    return direction_upper


def parse_price_list(price_text: str) -> List[float]:
    """
    Parse price text into list of float values
    
    Args:
        price_text: Text containing price information
        
    Returns:
        List of price values
    """
    if not price_text:
        return []
        
    # Extract all numeric values that look like prices
    price_pattern = r'(\d+\.?\d*)'
    matches = re.findall(price_pattern, str(price_text))
    
    prices = []
    for match in matches:
        try:
            price = float(match)
            if price > 0:  # Only positive prices
                prices.append(price)
        except ValueError:
            continue
            
    return prices


def validate_result(result: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Validate parsed signal result
    
    Args:
        result: Parsed signal dictionary
        config: Parser configuration
        
    Returns:
        Validated and normalized result
        
    Raises:
        ValueError: If validation fails
    """
    if not result or not isinstance(result, dict):
        raise ValueError("Result must be a non-empty dictionary")
        
    config = config or {}
    validator = SignalValidator()
    
    # Check required fields
    required_fields = config.get("required_fields", validator.required_fields)
    for field in required_fields:
        if field not in result:
            raise ValueError(f"Missing required field: {field}")
            
    # Validate and normalize pair
    pair = normalize_pair_symbol(result.get("pair", ""))
    if not pair:
        raise ValueError("Invalid or missing trading pair")
        
    if pair not in validator.valid_pairs:
        logging.warning(f"Unknown trading pair: {pair}")
        
    result["pair"] = pair
    
    # Validate and normalize direction
    direction = normalize_direction(result.get("direction", ""))
    if direction not in validator.valid_directions:
        raise ValueError(f"Invalid trading direction: {direction}")
        
    result["direction"] = direction
    
    # Validate entry price(s)
    entry = result.get("entry")
    if isinstance(entry, str):
        entry = parse_price_list(entry)
    elif isinstance(entry, (int, float)):
        entry = [float(entry)]
    elif not isinstance(entry, list):
        raise ValueError("Entry price must be a number, string, or list")
        
    if not entry or not all(isinstance(p, (int, float)) and p > 0 for p in entry):
        raise ValueError("Invalid entry price values")
        
    result["entry"] = entry
    
    # Validate stop loss
    sl = result.get("sl")
    if isinstance(sl, str):
        sl_list = parse_price_list(sl)
        sl = sl_list[0] if sl_list else 0
    elif not isinstance(sl, (int, float)):
        sl = 0
        
    if sl <= 0:
        raise ValueError("Stop loss must be a positive number")
        
    result["sl"] = float(sl)
    
    # Validate take profit(s)
    tp = result.get("tp")
    if isinstance(tp, str):
        tp = parse_price_list(tp)
    elif isinstance(tp, (int, float)):
        tp = [float(tp)]
    elif not isinstance(tp, list):
        raise ValueError("Take profit must be a number, string, or list")
        
    if not tp or not all(isinstance(p, (int, float)) and p > 0 for p in tp):
        raise ValueError("Invalid take profit values")
        
    result["tp"] = tp
    
    # Validate price ranges if configured
    if pair in validator.price_ranges:
        min_price, max_price = validator.price_ranges[pair]
        
        # Check entry prices
        for price in entry:
            if not (min_price <= price <= max_price):
                logging.warning(f"Entry price {price} outside expected range for {pair}")
                
        # Check stop loss
        if not (min_price <= sl <= max_price):
            logging.warning(f"Stop loss {sl} outside expected range for {pair}")
            
        # Check take profits
        for price in tp:
            if not (min_price <= price <= max_price):
                logging.warning(f"Take profit {price} outside expected range for {pair}")
                
    # Validate risk/reward logic
    avg_entry = sum(entry) / len(entry)
    avg_tp = sum(tp) / len(tp)
    
    if direction == "BUY":
        if sl >= avg_entry:
            raise ValueError("For BUY orders, stop loss must be below entry price")
        if avg_tp <= avg_entry:
            raise ValueError("For BUY orders, take profit must be above entry price")
    else:  # SELL
        if sl <= avg_entry:
            raise ValueError("For SELL orders, stop loss must be above entry price")
        if avg_tp >= avg_entry:
            raise ValueError("For SELL orders, take profit must be below entry price")
            
    # Calculate risk/reward ratio
    risk = abs(avg_entry - sl)
    reward = abs(avg_tp - avg_entry)
    
    if risk > 0:
        result["risk_reward"] = reward / risk
    else:
        result["risk_reward"] = 0
        
    # Set default values for optional fields
    result.setdefault("confidence", 1.0)
    result.setdefault("lot_size", 0.01)
    result.setdefault("parser_method", "unknown")
    
    return result


def extract_numeric_values(text: str) -> List[float]:
    """
    Extract all numeric values from text
    
    Args:
        text: Text to extract numbers from
        
    Returns:
        List of numeric values found
    """
    if not text:
        return []
        
    # Pattern for decimal numbers with optional thousand separators
    number_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d*\.\d+)'
    matches = re.findall(number_pattern, str(text))
    
    numbers = []
    for match in matches:
        try:
            # Remove commas and convert to float
            number = float(match.replace(',', ''))
            numbers.append(number)
        except ValueError:
            continue
            
    return numbers


def calculate_pip_value(pair: str, account_currency: str = "USD") -> float:
    """
    Calculate pip value for a trading pair
    
    Args:
        pair: Trading pair symbol
        account_currency: Account currency
        
    Returns:
        Pip value in account currency
    """
    # Simplified pip value calculation
    # In production, this would use current exchange rates
    
    pip_values = {
        "EURUSD": 10.0,  # 1 pip = $10 for 1 standard lot
        "GBPUSD": 10.0,
        "AUDUSD": 10.0,
        "NZDUSD": 10.0,
        "USDCAD": 7.5,   # Approximate, varies with CAD rate
        "USDCHF": 10.2,  # Approximate, varies with CHF rate
        "USDJPY": 9.1,   # Approximate, varies with JPY rate
        "XAUUSD": 1.0,   # Gold pip value is different
        "XAGUSD": 0.05   # Silver pip value
    }
    
    return pip_values.get(pair, 10.0)


# Testing function
def test_parser_utils():
    """Test parser utility functions"""
    print("🧪 Testing Parser Utilities")
    print("=" * 40)
    
    # Test sanitization
    raw_signal = "🟢 BUY EURUSD @ 1.0850, SL: 1.0800, TP1: 1.0900, TP2: 1.0950 ⚡"
    sanitized = sanitize_signal(raw_signal)
    print(f"Sanitized: {sanitized}")
    
    # Test validation
    test_result = {
        "pair": "EURUSD",
        "direction": "BUY", 
        "entry": [1.0850],
        "sl": 1.0800,
        "tp": [1.0900, 1.0950]
    }
    
    try:
        validated = validate_result(test_result)
        print(f"✅ Validation passed: R/R = {validated['risk_reward']:.2f}")
    except ValueError as e:
        print(f"❌ Validation failed: {e}")
        
    # Test price parsing
    price_text = "Entry: 1.0850-1.0860, SL: 1.0800, TP: 1.0900/1.0950"
    prices = extract_numeric_values(price_text)
    print(f"Extracted prices: {prices}")
    
    print("✅ Parser utilities test complete")


if __name__ == "__main__":
    test_parser_utils()