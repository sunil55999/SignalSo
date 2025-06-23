"""
Partial Trade Close Engine for SignalOS
Handles partial closure of MT5 trades with percentage and lot-based commands
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import re


class CloseType(Enum):
    PERCENTAGE = "percentage"
    LOT_SIZE = "lot_size"
    INVALID = "invalid"


@dataclass
class PartialCloseRequest:
    signal_id: int
    ticket: int
    close_type: CloseType
    close_value: float  # Percentage (0-100) or lot size
    symbol: str
    original_lots: float
    current_price: Optional[float] = None
    comment: str = ""


@dataclass
class PartialCloseResult:
    success: bool
    new_ticket: Optional[int] = None
    closed_lots: float = 0.0
    remaining_lots: float = 0.0
    close_price: Optional[float] = None
    error_message: str = ""
    execution_time: Optional[datetime] = None


class PartialCloseEngine:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/partial_close_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Module references
        self.mt5_bridge: Optional[Any] = None
        self.signal_parser: Optional[Any] = None
        
        # Execution history
        self.close_history: List[Dict[str, Any]] = []
        self._load_close_history()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('partial_close', {
                    'min_lot_size': 0.01,
                    'max_percentage': 95.0,
                    'min_percentage': 5.0,
                    'precision_digits': 2,
                    'max_retries': 3,
                    'retry_delay': 1.0
                })
        except FileNotFoundError:
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        default_config = {
            'partial_close': {
                'min_lot_size': 0.01,
                'max_percentage': 95.0,
                'min_percentage': 5.0,
                'precision_digits': 2,
                'max_retries': 3,
                'retry_delay': 1.0
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
        except Exception as e:
            logging.warning(f"Could not create config file: {e}")
            
        return default_config['partial_close']

    def _setup_logging(self):
        """Setup logging for partial close operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('PartialCloseEngine')

    def _load_close_history(self):
        """Load existing close history from log file"""
        try:
            with open(self.log_file, 'r') as f:
                self.close_history = json.load(f)
        except FileNotFoundError:
            self.close_history = []
            self._save_close_history()

    def _save_close_history(self):
        """Save close history to log file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.close_history, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save close history: {e}")

    def inject_modules(self, mt5_bridge=None, signal_parser=None):
        """Inject module references for MT5 operations"""
        self.mt5_bridge = mt5_bridge
        self.signal_parser = signal_parser

    def parse_close_command(self, command: str) -> Optional[PartialCloseRequest]:
        """
        Parse partial close command from text
        Examples:
        - /CLOSE 50%
        - /CLOSE 25%
        - /CLOSE 1.0 lot
        - CLOSE 0.5
        """
        if not command:
            return None

        # Clean and normalize command
        command = command.strip().upper()
        
        # Percentage patterns
        percentage_patterns = [
            r'/CLOSE\s+(\d+(?:\.\d+)?)%',
            r'CLOSE\s+(\d+(?:\.\d+)?)%',
            r'/PARTIAL\s+(\d+(?:\.\d+)?)%',
            r'PARTIAL\s+(\d+(?:\.\d+)?)%'
        ]
        
        for pattern in percentage_patterns:
            match = re.search(pattern, command)
            if match:
                percentage = float(match.group(1))
                if self.config['min_percentage'] <= percentage <= self.config['max_percentage']:
                    return PartialCloseRequest(
                        signal_id=0,  # Will be set by caller
                        ticket=0,     # Will be set by caller
                        close_type=CloseType.PERCENTAGE,
                        close_value=percentage,
                        symbol="",    # Will be set by caller
                        original_lots=0.0,  # Will be set by caller
                        comment=f"Partial close {percentage}%"
                    )
        
        # Lot size patterns
        lot_patterns = [
            r'/CLOSE\s+(\d+(?:\.\d+)?)\s*(?:LOT|LOTS?)?',
            r'CLOSE\s+(\d+(?:\.\d+)?)\s*(?:LOT|LOTS?)?',
            r'/PARTIAL\s+(\d+(?:\.\d+)?)\s*(?:LOT|LOTS?)?',
            r'PARTIAL\s+(\d+(?:\.\d+)?)\s*(?:LOT|LOTS?)?'
        ]
        
        for pattern in lot_patterns:
            match = re.search(pattern, command)
            if match:
                lot_size = float(match.group(1))
                if lot_size >= self.config['min_lot_size']:
                    return PartialCloseRequest(
                        signal_id=0,  # Will be set by caller
                        ticket=0,     # Will be set by caller
                        close_type=CloseType.LOT_SIZE,
                        close_value=lot_size,
                        symbol="",    # Will be set by caller
                        original_lots=0.0,  # Will be set by caller
                        comment=f"Partial close {lot_size} lots"
                    )
        
        return None

    def calculate_close_lots(self, request: PartialCloseRequest, current_lots: float) -> float:
        """Calculate the actual lot size to close"""
        if request.close_type == CloseType.PERCENTAGE:
            close_lots = (request.close_value / 100.0) * current_lots
        elif request.close_type == CloseType.LOT_SIZE:
            close_lots = min(request.close_value, current_lots)
        else:
            return 0.0
        
        # Round to broker precision
        precision = self.config['precision_digits']
        close_lots = round(close_lots, precision)
        
        # Ensure minimum lot size
        if close_lots < self.config['min_lot_size']:
            close_lots = self.config['min_lot_size']
        
        # Ensure we don't close more than available
        if close_lots > current_lots:
            close_lots = current_lots
        
        return close_lots

    async def execute_partial_close(self, request: PartialCloseRequest) -> PartialCloseResult:
        """Execute partial close via MT5 bridge"""
        if not self.mt5_bridge:
            return PartialCloseResult(
                success=False,
                error_message="MT5 bridge not available"
            )
        
        try:
            # Get current position info
            position_info = await self._get_position_info(request.ticket)
            if not position_info or not position_info.get('success', False):
                return PartialCloseResult(
                    success=False,
                    error_message="Could not retrieve position information"
                )
            
            current_lots = position_info['data']['lots']
            current_price = position_info['data']['current_price']
            
            # Calculate lots to close
            close_lots = self.calculate_close_lots(request, current_lots)
            
            if close_lots <= 0:
                return PartialCloseResult(
                    success=False,
                    error_message="Invalid close amount calculated"
                )
            
            # Execute partial close
            close_result = await self._execute_mt5_partial_close(
                request.ticket,
                close_lots,
                current_price,
                request.comment
            )
            
            if close_result['success']:
                remaining_lots = current_lots - close_lots
                
                result = PartialCloseResult(
                    success=True,
                    new_ticket=close_result.get('new_ticket'),
                    closed_lots=close_lots,
                    remaining_lots=remaining_lots,
                    close_price=current_price,
                    execution_time=datetime.now()
                )
                
                # Log the operation
                self._log_close_operation(request, result)
                return result
            else:
                return PartialCloseResult(
                    success=False,
                    error_message=close_result.get('error', 'Unknown MT5 error')
                )
                
        except Exception as e:
            self.logger.error(f"Partial close execution failed: {e}")
            return PartialCloseResult(
                success=False,
                error_message=str(e)
            )

    async def _get_position_info(self, ticket: int) -> Dict[str, Any]:
        """Get current position information from MT5"""
        try:
            if self.mt5_bridge and hasattr(self.mt5_bridge, 'get_position_info'):
                return await self.mt5_bridge.get_position_info(ticket)
            elif self.mt5_bridge and hasattr(self.mt5_bridge, 'get_position_by_ticket'):
                # Fallback method
                return await self.mt5_bridge.get_position_by_ticket(ticket)
            else:
                return {'success': False, 'error': 'MT5 bridge method not available'}
        except Exception as e:
            self.logger.error(f"Failed to get position info for ticket {ticket}: {e}")
            return {'success': False, 'error': str(e)}

    async def _execute_mt5_partial_close(self, ticket: int, close_lots: float, price: float, comment: str) -> Dict[str, Any]:
        """Execute partial close via MT5 bridge with retry logic"""
        max_retries = self.config['max_retries']
        retry_delay = self.config['retry_delay']
        
        for attempt in range(max_retries):
            try:
                if self.mt5_bridge and hasattr(self.mt5_bridge, 'partial_close_position'):
                    result = await self.mt5_bridge.partial_close_position(
                        ticket=ticket,
                        lots=close_lots,
                        price=price,
                        comment=comment
                    )
                elif self.mt5_bridge and hasattr(self.mt5_bridge, 'close_trade'):
                    # Fallback to standard close method
                    result = await self.mt5_bridge.close_trade(
                        ticket=ticket,
                        lots=close_lots,
                        price=price,
                        comment=comment
                    )
                else:
                    return {'success': False, 'error': 'MT5 bridge method not available'}
                
                if result.get('success'):
                    return result
                
                if attempt < max_retries - 1:
                    self.logger.warning(f"Partial close attempt {attempt + 1} failed, retrying...")
                    await asyncio.sleep(retry_delay)
                
            except Exception as e:
                self.logger.error(f"MT5 partial close attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
        
        return {'success': False, 'error': 'All retry attempts failed'}

    def _log_close_operation(self, request: PartialCloseRequest, result: PartialCloseResult):
        """Log partial close operation to history"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'signal_id': request.signal_id,
            'original_ticket': request.ticket,
            'new_ticket': result.new_ticket,
            'close_type': request.close_type.value,
            'close_value': request.close_value,
            'closed_lots': result.closed_lots,
            'remaining_lots': result.remaining_lots,
            'close_price': result.close_price,
            'success': result.success,
            'error_message': result.error_message,
            'comment': request.comment
        }
        
        self.close_history.append(log_entry)
        self._save_close_history()
        
        self.logger.info(f"Partial close logged: {log_entry}")

    def get_close_statistics(self) -> Dict[str, Any]:
        """Get statistics about partial close operations"""
        if not self.close_history:
            return {
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'success_rate': 0.0,
                'total_lots_closed': 0.0,
                'most_common_close_type': None
            }
        
        total_ops = len(self.close_history)
        successful_ops = sum(1 for op in self.close_history if op['success'])
        failed_ops = total_ops - successful_ops
        success_rate = (successful_ops / total_ops) * 100 if total_ops > 0 else 0.0
        
        total_lots_closed = sum(op['closed_lots'] for op in self.close_history if op['success'])
        
        # Most common close type
        close_types = [op['close_type'] for op in self.close_history]
        most_common_type = max(set(close_types), key=close_types.count) if close_types else None
        
        return {
            'total_operations': total_ops,
            'successful_operations': successful_ops,
            'failed_operations': failed_ops,
            'success_rate': success_rate,
            'total_lots_closed': total_lots_closed,
            'most_common_close_type': most_common_type
        }

    def get_recent_closes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent partial close operations"""
        return self.close_history[-limit:] if self.close_history else []


# Example usage and testing
async def main():
    """Example usage of Partial Close Engine"""
    engine = PartialCloseEngine()
    
    # Test command parsing
    test_commands = [
        "/CLOSE 50%",
        "CLOSE 25%",
        "/CLOSE 1.5 lots",
        "PARTIAL 0.5",
        "/CLOSE 75%"
    ]
    
    print("Testing command parsing:")
    for cmd in test_commands:
        parsed = engine.parse_close_command(cmd)
        if parsed:
            print(f"✓ '{cmd}' -> {parsed.close_type.value}: {parsed.close_value}")
        else:
            print(f"✗ '{cmd}' -> Invalid command")
    
    # Test lot calculation
    print("\nTesting lot calculations:")
    test_request = PartialCloseRequest(
        signal_id=1,
        ticket=12345,
        close_type=CloseType.PERCENTAGE,
        close_value=50.0,
        symbol="EURUSD",
        original_lots=1.0
    )
    
    calculated_lots = engine.calculate_close_lots(test_request, 1.0)
    print(f"50% of 1.0 lots = {calculated_lots} lots")
    
    # Print statistics
    stats = engine.get_close_statistics()
    print(f"\nCurrent statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(main())