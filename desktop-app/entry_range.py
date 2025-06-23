"""
Entry Range Engine for SignalOS
Implements entry range functionality for pending orders with upper and lower bounds
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import math


class EntryRangeType(Enum):
    LIMIT_RANGE = "limit_range"
    STOP_RANGE = "stop_range"
    MIXED_RANGE = "mixed_range"


class EntryLogic(Enum):
    AVERAGE_ENTRY = "average_entry"
    BEST_ENTRY = "best_entry"
    SECOND_ENTRY = "second_entry"
    SCALE_IN = "scale_in"


class TradeDirection(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class EntryRangeConfig:
    range_type: EntryRangeType
    entry_logic: EntryLogic
    upper_bound: float
    lower_bound: float
    total_lot_size: float
    max_entries: int = 3
    scale_factor: float = 1.0  # For scaling position sizes
    timeout_minutes: int = 60
    allow_partial_fills: bool = True


@dataclass
class EntryRangePosition:
    signal_id: int
    symbol: str
    direction: TradeDirection
    config: EntryRangeConfig
    created_at: datetime
    entries: List[Dict[str, Any]]  # List of executed entries
    pending_orders: List[int]  # List of pending order tickets
    total_filled_lots: float = 0.0
    average_entry_price: float = 0.0
    range_completed: bool = False
    expired: bool = False
    last_update: datetime = None


@dataclass
class EntryExecution:
    ticket: int
    price: float
    lot_size: float
    execution_time: datetime
    order_type: str  # "limit" or "stop"
    fill_quality: float  # Distance from optimal entry (0-1)


class EntryRangeEngine:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/entry_range_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Module references
        self.mt5_bridge: Optional[Any] = None
        self.market_data: Optional[Any] = None
        self.signal_parser: Optional[Any] = None
        
        # Active entry range positions
        self.entry_range_positions: Dict[int, EntryRangePosition] = {}
        self.execution_history: List[EntryExecution] = []
        
        # Monitoring settings
        self.update_interval = self.config.get('update_interval_seconds', 10)
        self.is_running = False
        self._load_entry_range_history()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('entry_range', {
                    'update_interval_seconds': 10,
                    'default_range_pips': 20.0,
                    'max_range_entries': 5,
                    'default_timeout_minutes': 60,
                    'pip_values': {
                        'EURUSD': 0.0001,
                        'GBPUSD': 0.0001,
                        'USDJPY': 0.01,
                        'USDCHF': 0.0001,
                        'default': 0.0001
                    },
                    'max_positions_to_monitor': 50
                })
        except FileNotFoundError:
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        default_config = {
            'entry_range': {
                'update_interval_seconds': 10,
                'default_range_pips': 20.0,
                'max_range_entries': 5,
                'default_timeout_minutes': 60,
                'pip_values': {
                    'EURUSD': 0.0001,
                    'GBPUSD': 0.0001,
                    'USDJPY': 0.01,
                    'USDCHF': 0.0001,
                    'default': 0.0001
                },
                'max_positions_to_monitor': 50
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
        except Exception as e:
            logging.warning(f"Could not create config file: {e}")
            
        return default_config['entry_range']

    def _setup_logging(self):
        """Setup logging for entry range operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('EntryRangeEngine')

    def _load_entry_range_history(self):
        """Load existing entry range history from log file"""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
                self.execution_history = []
                for entry in data:
                    execution = EntryExecution(
                        ticket=entry['ticket'],
                        price=entry['price'],
                        lot_size=entry['lot_size'],
                        execution_time=datetime.fromisoformat(entry['execution_time']),
                        order_type=entry['order_type'],
                        fill_quality=entry['fill_quality']
                    )
                    self.execution_history.append(execution)
        except FileNotFoundError:
            self.execution_history = []
            self._save_entry_range_history()

    def _save_entry_range_history(self):
        """Save entry range history to log file"""
        try:
            data = []
            for execution in self.execution_history:
                data.append({
                    'ticket': execution.ticket,
                    'price': execution.price,
                    'lot_size': execution.lot_size,
                    'execution_time': execution.execution_time.isoformat(),
                    'order_type': execution.order_type,
                    'fill_quality': execution.fill_quality
                })
            
            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save entry range history: {e}")

    def inject_modules(self, mt5_bridge=None, market_data=None, signal_parser=None):
        """Inject module references for MT5 operations and market data"""
        self.mt5_bridge = mt5_bridge
        self.market_data = market_data
        self.signal_parser = signal_parser

    def get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol"""
        return self.config['pip_values'].get(symbol, self.config['pip_values']['default'])

    def calculate_pips(self, symbol: str, price_diff: float) -> float:
        """Calculate pips from price difference"""
        pip_value = self.get_pip_value(symbol)
        return abs(price_diff) / pip_value

    def pips_to_price(self, symbol: str, pips: float) -> float:
        """Convert pips to price difference"""
        pip_value = self.get_pip_value(symbol)
        return pips * pip_value

    def parse_entry_range_command(self, command: str, symbol: str, direction: TradeDirection, 
                                 base_lot_size: float) -> Optional[EntryRangeConfig]:
        """
        Parse entry range command from text
        Examples:
        - "ENTRY RANGE 1.2000-1.2020 AVERAGE"
        - "RANGE 1.1950/1.1970 SCALE"
        - "BEST ENTRY 1.2010 TO 1.2030"
        """
        if not command:
            return None

        command = command.strip().upper()
        
        # Extract range bounds
        range_patterns = [
            r'(?:ENTRY\s+)?RANGE\s+(\d+\.\d+)[-/](\d+\.\d+)',
            r'(?:ENTRY\s+)?(\d+\.\d+)\s+TO\s+(\d+\.\d+)',
            r'BETWEEN\s+(\d+\.\d+)\s+AND\s+(\d+\.\d+)'
        ]
        
        bounds = None
        for pattern in range_patterns:
            import re
            match = re.search(pattern, command)
            if match:
                price1, price2 = float(match.group(1)), float(match.group(2))
                # Ensure upper_bound > lower_bound
                upper_bound = max(price1, price2)
                lower_bound = min(price1, price2)
                bounds = (upper_bound, lower_bound)
                break
        
        if not bounds:
            return None
        
        upper_bound, lower_bound = bounds
        
        # Determine entry logic
        entry_logic = EntryLogic.AVERAGE_ENTRY  # Default
        if 'AVERAGE' in command or 'AVG' in command:
            entry_logic = EntryLogic.AVERAGE_ENTRY
        elif 'BEST' in command:
            entry_logic = EntryLogic.BEST_ENTRY
        elif 'SECOND' in command:
            entry_logic = EntryLogic.SECOND_ENTRY
        elif 'SCALE' in command or 'SCALING' in command:
            entry_logic = EntryLogic.SCALE_IN
        
        # Determine range type based on direction and bounds
        range_type = EntryRangeType.LIMIT_RANGE
        if direction == TradeDirection.BUY:
            # For BUY: limit orders below current price, stop orders above
            range_type = EntryRangeType.LIMIT_RANGE
        else:
            # For SELL: limit orders above current price, stop orders below
            range_type = EntryRangeType.LIMIT_RANGE
        
        return EntryRangeConfig(
            range_type=range_type,
            entry_logic=entry_logic,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            total_lot_size=base_lot_size,
            max_entries=3,
            scale_factor=1.0,
            timeout_minutes=60,
            allow_partial_fills=True
        )

    def create_entry_range_position(self, signal_id: int, symbol: str, direction: TradeDirection,
                                   config: EntryRangeConfig) -> bool:
        """Create new entry range position with pending orders"""
        try:
            position = EntryRangePosition(
                signal_id=signal_id,
                symbol=symbol,
                direction=direction,
                config=config,
                created_at=datetime.now(),
                entries=[],
                pending_orders=[],
                total_filled_lots=0.0,
                average_entry_price=0.0,
                range_completed=False,
                expired=False,
                last_update=datetime.now()
            )
            
            self.entry_range_positions[signal_id] = position
            
            # Place initial pending orders based on entry logic
            asyncio.create_task(self._place_range_orders(position))
            
            self.logger.info(f"Created entry range position for signal {signal_id} ({symbol})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create entry range position {signal_id}: {e}")
            return False

    async def _place_range_orders(self, position: EntryRangePosition):
        """Place pending orders for entry range"""
        try:
            if position.config.entry_logic == EntryLogic.AVERAGE_ENTRY:
                await self._place_average_entry_orders(position)
            elif position.config.entry_logic == EntryLogic.BEST_ENTRY:
                await self._place_best_entry_orders(position)
            elif position.config.entry_logic == EntryLogic.SECOND_ENTRY:
                await self._place_second_entry_orders(position)
            elif position.config.entry_logic == EntryLogic.SCALE_IN:
                await self._place_scale_in_orders(position)
                
        except Exception as e:
            self.logger.error(f"Failed to place range orders for signal {position.signal_id}: {e}")

    async def _place_average_entry_orders(self, position: EntryRangePosition):
        """Place orders for average entry strategy"""
        # Place orders at multiple levels for averaging
        config = position.config
        num_orders = min(config.max_entries, 3)
        
        price_step = (config.upper_bound - config.lower_bound) / (num_orders - 1)
        lot_per_order = config.total_lot_size / num_orders
        
        for i in range(num_orders):
            price = config.lower_bound + (i * price_step)
            
            # Determine order type based on direction and price level
            if position.direction == TradeDirection.BUY:
                order_type = "limit" if price < await self._get_current_price(position.symbol) else "stop"
            else:
                order_type = "limit" if price > await self._get_current_price(position.symbol) else "stop"
            
            ticket = await self._place_pending_order(
                symbol=position.symbol,
                direction=position.direction,
                price=price,
                lot_size=lot_per_order,
                order_type=order_type
            )
            
            if ticket:
                position.pending_orders.append(ticket)

    async def _place_best_entry_orders(self, position: EntryRangePosition):
        """Place orders for best entry strategy"""
        config = position.config
        
        # Place order at the most favorable price in the range
        if position.direction == TradeDirection.BUY:
            best_price = config.lower_bound  # Best buy price is lowest
        else:
            best_price = config.upper_bound  # Best sell price is highest
        
        current_price = await self._get_current_price(position.symbol)
        
        # Determine order type
        if position.direction == TradeDirection.BUY:
            order_type = "limit" if best_price < current_price else "stop"
        else:
            order_type = "limit" if best_price > current_price else "stop"
        
        ticket = await self._place_pending_order(
            symbol=position.symbol,
            direction=position.direction,
            price=best_price,
            lot_size=config.total_lot_size,
            order_type=order_type
        )
        
        if ticket:
            position.pending_orders.append(ticket)

    async def _place_second_entry_orders(self, position: EntryRangePosition):
        """Place orders for second entry strategy"""
        config = position.config
        
        # Place order at second-best price in the range
        range_size = config.upper_bound - config.lower_bound
        second_best_offset = range_size * 0.25  # 25% into the range
        
        if position.direction == TradeDirection.BUY:
            second_price = config.lower_bound + second_best_offset
        else:
            second_price = config.upper_bound - second_best_offset
        
        current_price = await self._get_current_price(position.symbol)
        
        # Determine order type
        if position.direction == TradeDirection.BUY:
            order_type = "limit" if second_price < current_price else "stop"
        else:
            order_type = "limit" if second_price > current_price else "stop"
        
        ticket = await self._place_pending_order(
            symbol=position.symbol,
            direction=position.direction,
            price=second_price,
            lot_size=config.total_lot_size,
            order_type=order_type
        )
        
        if ticket:
            position.pending_orders.append(ticket)

    async def _place_scale_in_orders(self, position: EntryRangePosition):
        """Place orders for scale-in strategy"""
        config = position.config
        num_orders = min(config.max_entries, 5)
        
        # Calculate progressive lot sizes (scaling)
        total_weight = sum(config.scale_factor ** i for i in range(num_orders))
        
        price_step = (config.upper_bound - config.lower_bound) / (num_orders - 1)
        
        for i in range(num_orders):
            price = config.lower_bound + (i * price_step)
            
            # Calculate scaled lot size
            weight = config.scale_factor ** i
            lot_size = (config.total_lot_size * weight) / total_weight
            
            current_price = await self._get_current_price(position.symbol)
            
            # Determine order type
            if position.direction == TradeDirection.BUY:
                order_type = "limit" if price < current_price else "stop"
            else:
                order_type = "limit" if price > current_price else "stop"
            
            ticket = await self._place_pending_order(
                symbol=position.symbol,
                direction=position.direction,
                price=price,
                lot_size=lot_size,
                order_type=order_type
            )
            
            if ticket:
                position.pending_orders.append(ticket)

    async def _place_pending_order(self, symbol: str, direction: TradeDirection, price: float,
                                  lot_size: float, order_type: str) -> Optional[int]:
        """Place pending order via MT5 bridge"""
        if not self.mt5_bridge:
            self.logger.error("MT5 bridge not available for order placement")
            return None
        
        try:
            if hasattr(self.mt5_bridge, 'place_pending_order'):
                result = await self.mt5_bridge.place_pending_order(
                    symbol=symbol,
                    direction=direction.value,
                    price=price,
                    lot_size=lot_size,
                    order_type=order_type
                )
            elif hasattr(self.mt5_bridge, 'place_order'):
                result = await self.mt5_bridge.place_order(
                    symbol=symbol,
                    action=direction.value,
                    price=price,
                    lot_size=lot_size,
                    order_type=order_type
                )
            else:
                self.logger.error("No MT5 order placement method available")
                return None
            
            if result.get('success'):
                return result.get('ticket')
            else:
                self.logger.error(f"Failed to place pending order: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to place pending order: {e}")
            return None

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol"""
        try:
            if self.market_data and hasattr(self.market_data, 'get_current_price'):
                return await self.market_data.get_current_price(symbol)
            elif self.mt5_bridge and hasattr(self.mt5_bridge, 'get_current_price'):
                return await self.mt5_bridge.get_current_price(symbol)
            else:
                self.logger.warning(f"No market data source available for {symbol}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get current price for {symbol}: {e}")
            return None

    async def process_order_fill(self, ticket: int, fill_price: float, fill_lots: float):
        """Process order fill and update entry range position"""
        # Find the position that contains this ticket
        position = None
        for pos in self.entry_range_positions.values():
            if ticket in pos.pending_orders:
                position = pos
                break
        
        if not position:
            self.logger.warning(f"No position found for filled ticket {ticket}")
            return
        
        try:
            # Calculate fill quality (how good is this entry relative to the range)
            range_size = position.config.upper_bound - position.config.lower_bound
            if position.direction == TradeDirection.BUY:
                # For BUY: lower price = better quality
                distance_from_best = fill_price - position.config.lower_bound
            else:
                # For SELL: higher price = better quality
                distance_from_best = position.config.upper_bound - fill_price
            
            fill_quality = max(0.0, 1.0 - (distance_from_best / range_size))
            
            # Record the execution
            execution = EntryExecution(
                ticket=ticket,
                price=fill_price,
                lot_size=fill_lots,
                execution_time=datetime.now(),
                order_type="filled",
                fill_quality=fill_quality
            )
            
            self.execution_history.append(execution)
            
            # Update position
            position.entries.append({
                'ticket': ticket,
                'price': fill_price,
                'lot_size': fill_lots,
                'execution_time': datetime.now().isoformat(),
                'fill_quality': fill_quality
            })
            
            # Update average entry price
            total_value = position.average_entry_price * position.total_filled_lots
            total_value += fill_price * fill_lots
            position.total_filled_lots += fill_lots
            position.average_entry_price = total_value / position.total_filled_lots
            
            # Remove from pending orders
            position.pending_orders.remove(ticket)
            position.last_update = datetime.now()
            
            # Check if range is completed
            if (position.total_filled_lots >= position.config.total_lot_size or 
                len(position.pending_orders) == 0):
                position.range_completed = True
                await self._cancel_remaining_orders(position)
            
            self.logger.info(f"Processed fill for signal {position.signal_id}: {fill_lots} lots at {fill_price}")
            
        except Exception as e:
            self.logger.error(f"Error processing order fill for ticket {ticket}: {e}")

    async def _cancel_remaining_orders(self, position: EntryRangePosition):
        """Cancel remaining pending orders when range is completed"""
        for ticket in position.pending_orders[:]:  # Copy list to avoid modification during iteration
            try:
                if self.mt5_bridge and hasattr(self.mt5_bridge, 'cancel_order'):
                    result = await self.mt5_bridge.cancel_order(ticket)
                    if result.get('success'):
                        position.pending_orders.remove(ticket)
                        self.logger.info(f"Cancelled pending order {ticket}")
            except Exception as e:
                self.logger.error(f"Failed to cancel order {ticket}: {e}")

    async def monitor_entry_ranges(self):
        """Monitor entry range positions for timeouts and updates"""
        for signal_id, position in list(self.entry_range_positions.items()):
            try:
                # Check for timeout
                elapsed_time = datetime.now() - position.created_at
                if elapsed_time.total_seconds() > position.config.timeout_minutes * 60:
                    position.expired = True
                    await self._cancel_remaining_orders(position)
                    self.logger.info(f"Entry range {signal_id} expired after timeout")
                
                # Clean up completed or expired positions
                if position.range_completed or position.expired:
                    if len(position.pending_orders) == 0:
                        del self.entry_range_positions[signal_id]
                        self.logger.info(f"Cleaned up entry range position {signal_id}")
                
            except Exception as e:
                self.logger.error(f"Error monitoring entry range {signal_id}: {e}")

    async def start_entry_range_monitor(self):
        """Start the entry range monitoring loop"""
        if self.is_running:
            self.logger.warning("Entry range monitor already running")
            return
        
        self.is_running = True
        self.logger.info("Starting entry range monitor")
        
        try:
            while self.is_running:
                await self.monitor_entry_ranges()
                await asyncio.sleep(self.update_interval)
                
        except Exception as e:
            self.logger.error(f"Entry range monitor error: {e}")
        finally:
            self.is_running = False
            self.logger.info("Entry range monitor stopped")

    def stop_entry_range_monitor(self):
        """Stop the entry range monitoring loop"""
        self.is_running = False
        self.logger.info("Stopping entry range monitor")

    def get_entry_range_statistics(self) -> Dict[str, Any]:
        """Get statistics about entry range operations"""
        total_positions = len(self.entry_range_positions)
        completed_positions = len([p for p in self.entry_range_positions.values() if p.range_completed])
        active_positions = len([p for p in self.entry_range_positions.values() if not p.range_completed and not p.expired])
        expired_positions = len([p for p in self.entry_range_positions.values() if p.expired])
        
        total_executions = len(self.execution_history)
        if total_executions > 0:
            avg_fill_quality = sum(ex.fill_quality for ex in self.execution_history) / total_executions
            total_volume = sum(ex.lot_size for ex in self.execution_history)
        else:
            avg_fill_quality = 0.0
            total_volume = 0.0
        
        return {
            'total_positions': total_positions,
            'completed_positions': completed_positions,
            'active_positions': active_positions,
            'expired_positions': expired_positions,
            'total_executions': total_executions,
            'average_fill_quality': avg_fill_quality,
            'total_volume_traded': total_volume
        }

    def get_position_status(self, signal_id: int) -> Optional[Dict[str, Any]]:
        """Get status of specific entry range position"""
        if signal_id not in self.entry_range_positions:
            return None
        
        position = self.entry_range_positions[signal_id]
        
        return {
            'signal_id': signal_id,
            'symbol': position.symbol,
            'direction': position.direction.value,
            'entry_logic': position.config.entry_logic.value,
            'upper_bound': position.config.upper_bound,
            'lower_bound': position.config.lower_bound,
            'total_lot_size': position.config.total_lot_size,
            'total_filled_lots': position.total_filled_lots,
            'average_entry_price': position.average_entry_price,
            'pending_orders': len(position.pending_orders),
            'completed_entries': len(position.entries),
            'range_completed': position.range_completed,
            'expired': position.expired,
            'created_at': position.created_at.isoformat(),
            'last_update': position.last_update.isoformat() if position.last_update else None
        }

    def get_recent_executions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent entry range executions"""
        recent_executions = self.execution_history[-limit:] if self.execution_history else []
        
        return [{
            'ticket': execution.ticket,
            'price': execution.price,
            'lot_size': execution.lot_size,
            'execution_time': execution.execution_time.isoformat(),
            'order_type': execution.order_type,
            'fill_quality': execution.fill_quality
        } for execution in recent_executions]


# Example usage and testing
async def main():
    """Example usage of Entry Range Engine"""
    engine = EntryRangeEngine()
    
    # Test command parsing
    test_commands = [
        ("ENTRY RANGE 1.2000-1.2020 AVERAGE", "EURUSD", TradeDirection.BUY, 1.0),
        ("RANGE 1.1950/1.1970 SCALE", "EURUSD", TradeDirection.SELL, 2.0),
        ("BEST ENTRY 1.2010 TO 1.2030", "GBPUSD", TradeDirection.BUY, 1.5),
    ]
    
    print("Testing entry range command parsing:")
    for cmd, symbol, direction, lot_size in test_commands:
        config = engine.parse_entry_range_command(cmd, symbol, direction, lot_size)
        if config:
            print(f"✓ '{cmd}' -> {config.entry_logic.value}: {config.lower_bound}-{config.upper_bound}")
        else:
            print(f"✗ '{cmd}' -> Invalid command")
    
    # Get statistics
    stats = engine.get_entry_range_statistics()
    print(f"\nCurrent statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(main())