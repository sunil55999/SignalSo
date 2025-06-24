"""
Entrypoint Range Handler for SignalOS
Implements advanced multi-entry parsing and selection logic for trading signals
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import json
import statistics


class EntrySelectionMode(Enum):
    AVERAGE = "average"
    BEST = "best" 
    SECOND = "second"
    FIRST = "first"  # Fallback mode


@dataclass
class EntryRangeData:
    entries: List[float]
    mode: EntrySelectionMode
    original_text: str
    confidence: float
    parsed_at: datetime


class EntrypointRangeHandler:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/trade_errors.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Module references
        self.market_data: Optional[Any] = None
        self.signal_parser: Optional[Any] = None
        
        # Entry parsing patterns
        self.entry_patterns = self._initialize_entry_patterns()
        
        # Statistics
        self.parsing_stats = {
            'total_parsed': 0,
            'successful_resolutions': 0,
            'fallback_used': 0,
            'mode_usage': {mode.value: 0 for mode in EntrySelectionMode}
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('entrypoint_range', {
                    'default_mode': 'best',
                    'max_entries': 5,
                    'precision_digits': 5,
                    'fallback_to_first': True,
                    'min_confidence_threshold': 0.7,
                    'price_tolerance_pips': 2.0,
                    'enable_logging': True
                })
        except FileNotFoundError:
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        default_config = {
            'entrypoint_range': {
                'default_mode': 'best',
                'max_entries': 5,
                'precision_digits': 5,
                'fallback_to_first': True,
                'min_confidence_threshold': 0.7,
                'price_tolerance_pips': 2.0,
                'enable_logging': True
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
        except Exception as e:
            logging.warning(f"Could not create config file: {e}")
            
        return default_config['entrypoint_range']

    def _setup_logging(self):
        """Setup logging for entrypoint range operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('EntrypointRangeHandler')

    def _initialize_entry_patterns(self) -> List[Dict[str, Any]]:
        """Initialize regex patterns for parsing entry ranges"""
        return [
            # Range patterns with dash or hyphen
            {
                'pattern': r'(?:entry|entries?):\s*(\d+\.\d+)\s*[-–]\s*(\d+\.\d+)',
                'type': 'range',
                'confidence': 0.9
            },
            # Multiple entries separated by commas
            {
                'pattern': r'(?:entry|entries?):\s*((?:\d+\.\d+\s*,\s*)+\d+\.\d+)',
                'type': 'list',
                'confidence': 0.95
            },
            # Range with "to" keyword
            {
                'pattern': r'(?:entry|entries?):\s*(\d+\.\d+)\s+to\s+(\d+\.\d+)',
                'type': 'range',
                'confidence': 0.85
            },
            # Range with "between" keyword
            {
                'pattern': r'between\s+(\d+\.\d+)\s+(?:and|&)\s+(\d+\.\d+)',
                'type': 'range',
                'confidence': 0.8
            },
            # Multiple entries with slashes
            {
                'pattern': r'(?:entry|entries?):\s*((?:\d+\.\d+\s*/\s*)+\d+\.\d+)',
                'type': 'list_slash',
                'confidence': 0.85
            },
            # Zone entries
            {
                'pattern': r'(?:entry\s+)?zone:\s*(\d+\.\d+)\s*[-–]\s*(\d+\.\d+)',
                'type': 'range',
                'confidence': 0.8
            },
            # Single entry (fallback)
            {
                'pattern': r'(?:entry|entries?):\s*(\d+\.\d+)',
                'type': 'single',
                'confidence': 0.7
            }
        ]

    def inject_modules(self, market_data=None, signal_parser=None):
        """Inject module references for market data and signal parsing"""
        self.market_data = market_data
        self.signal_parser = signal_parser

    def parse_entry_text(self, signal_text: str, mode: Optional[str] = None) -> Optional[EntryRangeData]:
        """
        Parse entry information from signal text
        
        Args:
            signal_text: Raw signal text to parse
            mode: Selection mode override (average, best, second)
            
        Returns:
            EntryRangeData object or None if parsing fails
        """
        if not signal_text:
            return None

        signal_text = signal_text.lower().strip()
        
        # Determine selection mode
        selection_mode = self._determine_selection_mode(signal_text, mode)
        
        # Try each pattern until we find a match
        for pattern_info in self.entry_patterns:
            match = re.search(pattern_info['pattern'], signal_text, re.IGNORECASE)
            if match:
                entries = self._extract_entries_from_match(match, pattern_info['type'])
                if entries:
                    self.parsing_stats['total_parsed'] += 1
                    
                    return EntryRangeData(
                        entries=entries,
                        mode=selection_mode,
                        original_text=signal_text,
                        confidence=pattern_info['confidence'],
                        parsed_at=datetime.now()
                    )
        
        self._log_parsing_failure(signal_text)
        return None

    def _determine_selection_mode(self, signal_text: str, mode_override: Optional[str] = None) -> EntrySelectionMode:
        """Determine the entry selection mode from text or override"""
        if mode_override:
            try:
                return EntrySelectionMode(mode_override.lower())
            except ValueError:
                pass
        
        # Check for mode keywords in signal text
        if any(word in signal_text for word in ['average', 'avg', 'mean']):
            return EntrySelectionMode.AVERAGE
        elif any(word in signal_text for word in ['best', 'optimal', 'closest']):
            return EntrySelectionMode.BEST
        elif any(word in signal_text for word in ['second', '2nd']):
            return EntrySelectionMode.SECOND
        
        # Use default from config
        default_mode = self.config.get('default_mode', 'best')
        try:
            return EntrySelectionMode(default_mode)
        except ValueError:
            return EntrySelectionMode.BEST

    def _extract_entries_from_match(self, match, pattern_type: str) -> List[float]:
        """Extract entry prices from regex match based on pattern type"""
        try:
            if pattern_type == 'range':
                # Two prices defining a range
                price1 = float(match.group(1))
                price2 = float(match.group(2))
                
                # Generate 3 entries across the range
                min_price = min(price1, price2)
                max_price = max(price1, price2)
                mid_price = (min_price + max_price) / 2
                
                entries = [
                    round(min_price, self.config['precision_digits']),
                    round(mid_price, self.config['precision_digits']),
                    round(max_price, self.config['precision_digits'])
                ]
                
                return entries
                
            elif pattern_type == 'list':
                # Comma-separated list of entries
                entries_text = match.group(1)
                price_strings = [p.strip() for p in entries_text.split(',')]
                entries = []
                
                for price_str in price_strings:
                    try:
                        price = float(price_str)
                        entries.append(round(price, self.config['precision_digits']))
                    except ValueError:
                        continue
                
                # Limit to max entries and sort
                entries = sorted(entries)[:self.config['max_entries']]
                return entries
                
            elif pattern_type == 'list_slash':
                # Slash-separated list of entries
                entries_text = match.group(1)
                price_strings = [p.strip() for p in entries_text.split('/')]
                entries = []
                
                for price_str in price_strings:
                    try:
                        price = float(price_str)
                        entries.append(round(price, self.config['precision_digits']))
                    except ValueError:
                        continue
                
                entries = sorted(entries)[:self.config['max_entries']]
                return entries
                
            elif pattern_type == 'single':
                # Single entry point
                price = float(match.group(1))
                return [round(price, self.config['precision_digits'])]
                
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Failed to extract entries from match: {e}")
            
        return []

    def resolve_entry(self, entry_list: List[float], mode: str, current_price: float) -> float:
        """
        Resolve final entry price from list based on selection mode
        
        Args:
            entry_list: List of possible entry prices
            mode: Selection mode (average, best, second)
            current_price: Current market price for reference
            
        Returns:
            Selected entry price
        """
        if not entry_list:
            self._log_fallback_event("Empty entry list", current_price)
            return current_price
        
        if len(entry_list) == 1:
            return entry_list[0]
        
        try:
            selection_mode = EntrySelectionMode(mode.lower())
        except ValueError:
            selection_mode = EntrySelectionMode.BEST
        
        # Update mode usage statistics
        self.parsing_stats['mode_usage'][selection_mode.value] += 1
        
        try:
            if selection_mode == EntrySelectionMode.AVERAGE:
                result = round(statistics.mean(entry_list), self.config['precision_digits'])
                
            elif selection_mode == EntrySelectionMode.BEST:
                # Best = closest to current market price
                result = min(entry_list, key=lambda x: abs(x - current_price))
                
            elif selection_mode == EntrySelectionMode.SECOND:
                # Second entry (index 1) if available
                if len(entry_list) >= 2:
                    sorted_entries = sorted(entry_list)
                    result = sorted_entries[1]
                else:
                    # Fallback to first entry
                    result = entry_list[0]
                    self._log_fallback_event(f"Second entry requested but only {len(entry_list)} entries available", current_price)
                    
            else:  # FIRST or unknown
                result = entry_list[0]
            
            self.parsing_stats['successful_resolutions'] += 1
            return result
            
        except Exception as e:
            self.logger.error(f"Entry resolution failed: {e}")
            self._log_fallback_event(f"Resolution error: {e}", current_price)
            
            # Fallback to first entry
            if self.config.get('fallback_to_first', True) and entry_list:
                self.parsing_stats['fallback_used'] += 1
                return entry_list[0]
            
            return current_price

    def process_signal_entries(self, signal_text: str, current_price: float, 
                             mode_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete processing pipeline for signal entry parsing and resolution
        
        Args:
            signal_text: Raw signal text
            current_price: Current market price
            mode_override: Optional mode override
            
        Returns:
            Dictionary with processing results
        """
        result = {
            'success': False,
            'entry_price': current_price,
            'mode_used': 'fallback',
            'entries_found': [],
            'confidence': 0.0,
            'fallback_reason': None
        }
        
        try:
            # Parse entry data from text
            entry_data = self.parse_entry_text(signal_text, mode_override)
            
            if not entry_data:
                result['fallback_reason'] = 'No entries found in signal text'
                self._log_fallback_event(result['fallback_reason'], current_price)
                return result
            
            # Check confidence threshold
            if entry_data.confidence < self.config.get('min_confidence_threshold', 0.7):
                result['fallback_reason'] = f'Low confidence: {entry_data.confidence:.2f}'
                self._log_fallback_event(result['fallback_reason'], current_price)
                return result
            
            # Resolve final entry price
            final_entry = self.resolve_entry(
                entry_data.entries, 
                entry_data.mode.value, 
                current_price
            )
            
            # Validate result
            if self._validate_entry_price(final_entry, current_price):
                result.update({
                    'success': True,
                    'entry_price': final_entry,
                    'mode_used': entry_data.mode.value,
                    'entries_found': entry_data.entries,
                    'confidence': entry_data.confidence
                })
            else:
                result['fallback_reason'] = f'Entry price validation failed: {final_entry}'
                self._log_fallback_event(result['fallback_reason'], current_price)
            
        except Exception as e:
            result['fallback_reason'] = f'Processing error: {e}'
            self.logger.error(f"Signal entry processing failed: {e}")
            self._log_fallback_event(result['fallback_reason'], current_price)
        
        return result

    def _validate_entry_price(self, entry_price: float, current_price: float) -> bool:
        """Validate that entry price is reasonable relative to current price"""
        if entry_price <= 0:
            return False
        
        # Check if entry is within reasonable tolerance
        tolerance_pips = self.config.get('price_tolerance_pips', 2.0)
        pip_value = 0.0001  # Default pip value, should be symbol-specific
        max_diff = tolerance_pips * pip_value * 1000  # Allow larger range for validation
        
        price_diff = abs(entry_price - current_price)
        
        # Be permissive in validation - allow wide ranges
        if price_diff > current_price * 0.1:  # 10% difference threshold
            return False
        
        return True

    def _log_fallback_event(self, reason: str, current_price: float):
        """Log fallback events to error log"""
        if not self.config.get('enable_logging', True):
            return
        
        try:
            timestamp = datetime.now().isoformat()
            log_entry = f"[{timestamp}] ENTRYPOINT_FALLBACK: {reason} | Current Price: {current_price:.5f}\n"
            
            with open(self.log_file, 'a') as f:
                f.write(log_entry)
                
        except Exception as e:
            self.logger.warning(f"Failed to write fallback log: {e}")

    def _log_parsing_failure(self, signal_text: str):
        """Log parsing failures for analysis"""
        if not self.config.get('enable_logging', True):
            return
        
        try:
            timestamp = datetime.now().isoformat()
            log_entry = f"[{timestamp}] PARSING_FAILED: {signal_text[:100]}...\n"
            
            with open(self.log_file, 'a') as f:
                f.write(log_entry)
                
        except Exception as e:
            self.logger.warning(f"Failed to write parsing failure log: {e}")

    def get_parsing_statistics(self) -> Dict[str, Any]:
        """Get statistics about entry parsing performance"""
        total_parsed = self.parsing_stats['total_parsed']
        
        return {
            'total_signals_parsed': total_parsed,
            'successful_resolutions': self.parsing_stats['successful_resolutions'],
            'fallback_usage_count': self.parsing_stats['fallback_used'],
            'success_rate': (self.parsing_stats['successful_resolutions'] / total_parsed * 100) if total_parsed > 0 else 0,
            'fallback_rate': (self.parsing_stats['fallback_used'] / total_parsed * 100) if total_parsed > 0 else 0,
            'mode_usage_distribution': self.parsing_stats['mode_usage'].copy(),
            'supported_patterns': len(self.entry_patterns),
            'configuration': {
                'default_mode': self.config.get('default_mode'),
                'max_entries': self.config.get('max_entries'),
                'precision_digits': self.config.get('precision_digits'),
                'confidence_threshold': self.config.get('min_confidence_threshold')
            }
        }

    def update_configuration(self, new_config: Dict[str, Any]) -> bool:
        """Update configuration parameters"""
        try:
            self.config.update(new_config)
            
            # Save updated config to file
            full_config = {}
            try:
                with open(self.config_file, 'r') as f:
                    full_config = json.load(f)
            except FileNotFoundError:
                pass
            
            full_config['entrypoint_range'] = self.config
            
            with open(self.config_file, 'w') as f:
                json.dump(full_config, f, indent=2)
            
            self.logger.info("Configuration updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False

    def test_entry_parsing(self, test_signals: List[str], current_price: float = 1.10000) -> Dict[str, Any]:
        """Test entry parsing with provided signals for validation"""
        test_results = []
        
        for i, signal in enumerate(test_signals):
            result = self.process_signal_entries(signal, current_price)
            test_results.append({
                'signal_index': i,
                'signal_text': signal[:50] + '...' if len(signal) > 50 else signal,
                'success': result['success'],
                'entry_price': result['entry_price'],
                'mode_used': result['mode_used'],
                'entries_found': result['entries_found'],
                'confidence': result['confidence'],
                'fallback_reason': result.get('fallback_reason')
            })
        
        success_count = sum(1 for r in test_results if r['success'])
        
        return {
            'test_summary': {
                'total_tests': len(test_signals),
                'successful_parses': success_count,
                'success_rate': (success_count / len(test_signals) * 100) if test_signals else 0
            },
            'individual_results': test_results,
            'overall_statistics': self.get_parsing_statistics()
        }


# Legacy compatibility function for existing integrations
def resolve_entry(entry_list: List[float], mode: str, current_price: float) -> float:
    """
    Legacy compatibility function for direct usage
    """
    handler = EntrypointRangeHandler()
    return handler.resolve_entry(entry_list, mode, current_price)


# Example usage and testing
async def main():
    """Example usage of Entrypoint Range Handler"""
    handler = EntrypointRangeHandler()
    
    # Test signals with various entry formats
    test_signals = [
        "BUY EURUSD\nEntry: 1.1010 – 1.1050\nSL: 1.0980\nTP: 1.1100",
        "SELL GBPUSD\nEntries: 1.2980, 1.3025, 1.3070\nSL: 1.3120\nTP: 1.2900",
        "BUY USDJPY\nEntry zone: 110.20 - 110.50\nStop: 109.80\nTarget: 111.00",
        "SELL EURUSD\nEntry: 1.0950 to 1.0980 (average)\nSL: 1.1020\nTP: 1.0900",
        "BUY GBPUSD\nBest entry between 1.2500 and 1.2530\nSL: 1.2450\nTP: 1.2600"
    ]
    
    current_price = 1.10250
    
    print("Testing Entrypoint Range Handler:")
    print("=" * 50)
    
    for i, signal in enumerate(test_signals, 1):
        print(f"\nTest {i}:")
        print(f"Signal: {signal.split()[1] if len(signal.split()) > 1 else 'Unknown'}")
        
        result = handler.process_signal_entries(signal, current_price)
        
        if result['success']:
            print(f"✓ Entry: {result['entry_price']:.5f}")
            print(f"  Mode: {result['mode_used']}")
            print(f"  Found entries: {result['entries_found']}")
            print(f"  Confidence: {result['confidence']:.2f}")
        else:
            print(f"✗ Failed: {result['fallback_reason']}")
            print(f"  Fallback price: {result['entry_price']:.5f}")
    
    # Get overall statistics
    stats = handler.get_parsing_statistics()
    print(f"\nOverall Statistics:")
    print(f"Success rate: {stats['success_rate']:.1f}%")
    print(f"Mode usage: {stats['mode_usage_distribution']}")


if __name__ == "__main__":
    asyncio.run(main())