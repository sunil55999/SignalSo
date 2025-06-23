"""
TP Manager Engine for SignalOS
Implements advanced take profit management with multiple TP levels and automated partial closes
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import math


class TPHitAction(Enum):
    PARTIAL_CLOSE = "partial_close"
    MOVE_SL = "move_sl"
    CLOSE_ALL = "close_all"
    SCALE_OUT = "scale_out"


class TPStatus(Enum):
    PENDING = "pending"
    HIT = "hit"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TradeDirection(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class TPLevel:
    level: int  # TP1, TP2, TP3, etc.
    price: float
    close_percentage: float  # What % of position to close (0.0-1.0)
    action: TPHitAction = TPHitAction.PARTIAL_CLOSE
    status: TPStatus = TPStatus.PENDING
    hit_time: Optional[datetime] = None
    executed_lots: float = 0.0
    move_sl_to: Optional[float] = None  # New SL when this TP is hit


@dataclass
class TPConfiguration:
    auto_partial_close: bool = True
    move_sl_on_tp1: bool = True  # Move SL to breakeven on TP1
    move_sl_on_tp2: bool = True  # Move SL to TP1 on TP2
    cascade_tp_management: bool = True  # Automatically manage subsequent TPs
    min_lots_remaining: float = 0.01  # Minimum lots to keep open
    max_tp_levels: int = 5
    tp_buffer_pips: float = 2.0  # Buffer before TP level


@dataclass
class TPManagedPosition:
    ticket: int
    symbol: str
    direction: TradeDirection
    entry_price: float
    entry_time: datetime
    original_lot_size: float
    current_lot_size: float
    original_sl: Optional[float]
    current_sl: Optional[float]
    tp_levels: List[TPLevel] = field(default_factory=list)
    config: TPConfiguration = field(default_factory=TPConfiguration)
    last_price_check: datetime = field(default_factory=datetime.now)
    position_closed: bool = False
    total_closed_lots: float = 0.0
    realized_profit: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TPExecution:
    ticket: int
    tp_level: int
    execution_price: float
    closed_lots: float
    remaining_lots: float
    profit_pips: float
    profit_amount: float
    execution_time: datetime
    action_taken: TPHitAction
    new_sl: Optional[float] = None


class TPManager:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/tp_manager_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Module references
        self.mt5_bridge: Optional[Any] = None
        self.market_data: Optional[Any] = None
        self.partial_close_engine: Optional[Any] = None
        self.break_even_engine: Optional[Any] = None
        
        # Active TP managed positions
        self.tp_positions: Dict[int, TPManagedPosition] = {}
        self.execution_history: List[TPExecution] = []
        
        # Monitoring settings
        self.update_interval = self.config.get('update_interval_seconds', 5)
        self.is_running = False
        self._load_tp_history()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('tp_manager', {
                    'update_interval_seconds': 5,
                    'max_tp_levels': 5,
                    'default_tp_percentages': [25, 25, 25, 25],  # TP1-TP4 close percentages
                    'auto_move_sl': True,
                    'tp_buffer_pips': 2.0,
                    'min_lots_remaining': 0.01,
                    'pip_values': {
                        'EURUSD': 0.0001,
                        'GBPUSD': 0.0001,
                        'USDJPY': 0.01,
                        'USDCHF': 0.0001,
                        'default': 0.0001
                    },
                    'max_positions_to_monitor': 100
                })
        except FileNotFoundError:
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        default_config = {
            'tp_manager': {
                'update_interval_seconds': 5,
                'max_tp_levels': 5,
                'default_tp_percentages': [25, 25, 25, 25],
                'auto_move_sl': True,
                'tp_buffer_pips': 2.0,
                'min_lots_remaining': 0.01,
                'pip_values': {
                    'EURUSD': 0.0001,
                    'GBPUSD': 0.0001,
                    'USDJPY': 0.01,
                    'USDCHF': 0.0001,
                    'default': 0.0001
                },
                'max_positions_to_monitor': 100
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
        except Exception as e:
            logging.warning(f"Could not create config file: {e}")
            
        return default_config['tp_manager']

    def _setup_logging(self):
        """Setup logging for TP management operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('TPManager')

    def _load_tp_history(self):
        """Load existing TP execution history from log file"""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
                self.execution_history = []
                for entry in data:
                    execution = TPExecution(
                        ticket=entry['ticket'],
                        tp_level=entry['tp_level'],
                        execution_price=entry['execution_price'],
                        closed_lots=entry['closed_lots'],
                        remaining_lots=entry['remaining_lots'],
                        profit_pips=entry['profit_pips'],
                        profit_amount=entry['profit_amount'],
                        execution_time=datetime.fromisoformat(entry['execution_time']),
                        action_taken=TPHitAction(entry['action_taken']),
                        new_sl=entry.get('new_sl')
                    )
                    self.execution_history.append(execution)
        except FileNotFoundError:
            self.execution_history = []
            self._save_tp_history()

    def _save_tp_history(self):
        """Save TP execution history to log file"""
        try:
            data = []
            for execution in self.execution_history:
                data.append({
                    'ticket': execution.ticket,
                    'tp_level': execution.tp_level,
                    'execution_price': execution.execution_price,
                    'closed_lots': execution.closed_lots,
                    'remaining_lots': execution.remaining_lots,
                    'profit_pips': execution.profit_pips,
                    'profit_amount': execution.profit_amount,
                    'execution_time': execution.execution_time.isoformat(),
                    'action_taken': execution.action_taken.value,
                    'new_sl': execution.new_sl
                })
            
            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save TP history: {e}")

    def inject_modules(self, mt5_bridge=None, market_data=None, partial_close_engine=None, break_even_engine=None):
        """Inject module references for trading operations"""
        self.mt5_bridge = mt5_bridge
        self.market_data = market_data
        self.partial_close_engine = partial_close_engine
        self.break_even_engine = break_even_engine

    def get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol"""
        return self.config['pip_values'].get(symbol, self.config['pip_values']['default'])

    def calculate_pips(self, symbol: str, price_diff: float, direction: TradeDirection) -> float:
        """Calculate pips from price difference considering direction"""
        pip_value = self.get_pip_value(symbol)
        pips = abs(price_diff) / pip_value
        
        # Apply direction sign
        if direction == TradeDirection.BUY:
            return pips if price_diff > 0 else -pips
        else:  # SELL
            return pips if price_diff < 0 else -pips

    def pips_to_price(self, symbol: str, pips: float) -> float:
        """Convert pips to price difference"""
        pip_value = self.get_pip_value(symbol)
        return pips * pip_value

    def parse_tp_levels_from_signal(self, signal_text: str, symbol: str, direction: TradeDirection,
                                   entry_price: float) -> List[TPLevel]:
        """
        Parse TP levels from signal text
        Examples:
        - "TP1: 1.2050 TP2: 1.2080 TP3: 1.2120"
        - "Take Profit 1.2050, 1.2080, 1.2120"
        - "TP 1.2050 (25%), 1.2080 (25%), 1.2120 (50%)"
        """
        tp_levels = []
        
        if not signal_text:
            return tp_levels
        
        import re
        signal_text = signal_text.upper()
        
        # Pattern 1: TP1: price TP2: price format
        tp_pattern1 = r'TP(\d+)[:\s]+(\d+\.\d+)'
        matches1 = re.findall(tp_pattern1, signal_text)
        
        if matches1:
            default_percentages = self.config.get('default_tp_percentages', [25, 25, 25, 25])
            for i, (level_str, price_str) in enumerate(matches1):
                level = int(level_str)
                price = float(price_str)
                
                # Get percentage (default if not specified)
                percentage = default_percentages[i] if i < len(default_percentages) else 25
                
                tp_level = TPLevel(
                    level=level,
                    price=price,
                    close_percentage=percentage / 100.0,
                    action=TPHitAction.PARTIAL_CLOSE
                )
                tp_levels.append(tp_level)
        
        # Pattern 2: Comma-separated prices
        if not tp_levels:
            price_pattern = r'(?:TAKE\s+PROFIT|TP)[:\s]*(\d+\.\d+(?:\s*,\s*\d+\.\d+)*)'
            price_match = re.search(price_pattern, signal_text)
            
            if price_match:
                prices_str = price_match.group(1)
                prices = [float(p.strip()) for p in prices_str.split(',')]
                
                default_percentages = self.config.get('default_tp_percentages', [25, 25, 25, 25])
                for i, price in enumerate(prices):
                    percentage = default_percentages[i] if i < len(default_percentages) else 25
                    
                    tp_level = TPLevel(
                        level=i + 1,
                        price=price,
                        close_percentage=percentage / 100.0,
                        action=TPHitAction.PARTIAL_CLOSE
                    )
                    tp_levels.append(tp_level)
        
        # Pattern 3: TP with percentages
        tp_percentage_pattern = r'TP\s*(\d+\.\d+)\s*\((\d+)%\)'
        matches3 = re.findall(tp_percentage_pattern, signal_text)
        
        if matches3:
            tp_levels = []  # Reset if we found percentage format
            for i, (price_str, percentage_str) in enumerate(matches3):
                price = float(price_str)
                percentage = float(percentage_str)
                
                tp_level = TPLevel(
                    level=i + 1,
                    price=price,
                    close_percentage=percentage / 100.0,
                    action=TPHitAction.PARTIAL_CLOSE
                )
                tp_levels.append(tp_level)
        
        # Validate TP levels against direction
        valid_tp_levels = []
        for tp_level in tp_levels:
            if self._validate_tp_price(tp_level.price, entry_price, direction):
                valid_tp_levels.append(tp_level)
            else:
                self.logger.warning(f"Invalid TP{tp_level.level} price {tp_level.price} for {direction.value} at {entry_price}")
        
        return valid_tp_levels

    def _validate_tp_price(self, tp_price: float, entry_price: float, direction: TradeDirection) -> bool:
        """Validate that TP price is in correct direction from entry"""
        if direction == TradeDirection.BUY:
            return tp_price > entry_price
        else:  # SELL
            return tp_price < entry_price

    def add_tp_managed_position(self, ticket: int, symbol: str, direction: TradeDirection,
                               entry_price: float, lot_size: float, tp_levels: List[TPLevel],
                               current_sl: Optional[float] = None,
                               config: Optional[TPConfiguration] = None) -> bool:
        """Add position to TP management"""
        try:
            if config is None:
                config = TPConfiguration()
            
            position = TPManagedPosition(
                ticket=ticket,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                entry_time=datetime.now(),
                original_lot_size=lot_size,
                current_lot_size=lot_size,
                original_sl=current_sl,
                current_sl=current_sl,
                tp_levels=tp_levels,
                config=config
            )
            
            self.tp_positions[ticket] = position
            
            self.logger.info(f"Added TP managed position {ticket} ({symbol}) with {len(tp_levels)} TP levels")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add TP managed position {ticket}: {e}")
            return False

    def remove_tp_managed_position(self, ticket: int) -> bool:
        """Remove position from TP management"""
        if ticket in self.tp_positions:
            del self.tp_positions[ticket]
            self.logger.info(f"Removed TP managed position {ticket}")
            return True
        return False

    async def get_current_price(self, symbol: str) -> Optional[float]:
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

    async def check_tp_levels(self, position: TPManagedPosition, current_price: float) -> List[TPLevel]:
        """Check which TP levels have been hit"""
        hit_tp_levels = []
        
        for tp_level in position.tp_levels:
            if tp_level.status != TPStatus.PENDING:
                continue
            
            # Check if TP level is hit based on direction
            tp_hit = False
            if position.direction == TradeDirection.BUY:
                tp_hit = current_price >= tp_level.price
            else:  # SELL
                tp_hit = current_price <= tp_level.price
            
            if tp_hit:
                tp_level.status = TPStatus.HIT
                tp_level.hit_time = datetime.now()
                hit_tp_levels.append(tp_level)
                
                self.logger.info(f"TP{tp_level.level} hit for position {position.ticket} at {current_price}")
        
        return hit_tp_levels

    async def execute_tp_action(self, position: TPManagedPosition, tp_level: TPLevel, current_price: float) -> bool:
        """Execute action when TP level is hit"""
        try:
            if tp_level.action == TPHitAction.PARTIAL_CLOSE:
                return await self._execute_partial_close(position, tp_level, current_price)
            elif tp_level.action == TPHitAction.MOVE_SL:
                return await self._execute_move_sl(position, tp_level, current_price)
            elif tp_level.action == TPHitAction.CLOSE_ALL:
                return await self._execute_close_all(position, tp_level, current_price)
            elif tp_level.action == TPHitAction.SCALE_OUT:
                return await self._execute_scale_out(position, tp_level, current_price)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to execute TP action for {position.ticket}: {e}")
            return False

    async def _execute_partial_close(self, position: TPManagedPosition, tp_level: TPLevel, current_price: float) -> bool:
        """Execute partial close at TP level"""
        # Calculate lots to close
        lots_to_close = position.current_lot_size * tp_level.close_percentage
        lots_to_close = max(0.01, round(lots_to_close, 2))  # Minimum 0.01 lots
        
        # Ensure we don't close more than available
        lots_to_close = min(lots_to_close, position.current_lot_size)
        
        # Check minimum remaining lots
        remaining_lots = position.current_lot_size - lots_to_close
        if remaining_lots > 0 and remaining_lots < position.config.min_lots_remaining:
            # Close all if remaining would be too small
            lots_to_close = position.current_lot_size
            remaining_lots = 0.0
        
        # Execute partial close
        success = False
        if self.partial_close_engine and hasattr(self.partial_close_engine, 'execute_partial_close'):
            result = await self.partial_close_engine.execute_partial_close(
                ticket=position.ticket,
                close_lots=lots_to_close,
                close_price=current_price
            )
            success = result.get('success', False)
        elif self.mt5_bridge and hasattr(self.mt5_bridge, 'partial_close_position'):
            result = await self.mt5_bridge.partial_close_position(
                ticket=position.ticket,
                lots=lots_to_close
            )
            success = result.get('success', False)
        
        if success:
            # Update position
            position.current_lot_size = remaining_lots
            position.total_closed_lots += lots_to_close
            tp_level.executed_lots = lots_to_close
            
            # Calculate profit
            profit_pips = self.calculate_pips(position.symbol, current_price - position.entry_price, position.direction)
            profit_amount = profit_pips * lots_to_close * 10  # Rough calculation
            position.realized_profit += profit_amount
            
            # Record execution
            execution = TPExecution(
                ticket=position.ticket,
                tp_level=tp_level.level,
                execution_price=current_price,
                closed_lots=lots_to_close,
                remaining_lots=remaining_lots,
                profit_pips=profit_pips,
                profit_amount=profit_amount,
                execution_time=datetime.now(),
                action_taken=TPHitAction.PARTIAL_CLOSE
            )
            self.execution_history.append(execution)
            
            # Auto-move SL if configured
            if position.config.auto_partial_close:
                await self._auto_move_sl_on_tp(position, tp_level)
            
            # Mark position as closed if no lots remaining
            if remaining_lots == 0:
                position.position_closed = True
            
            self.logger.info(f"Executed partial close: {lots_to_close} lots at TP{tp_level.level} ({current_price})")
            return True
        
        return False

    async def _execute_move_sl(self, position: TPManagedPosition, tp_level: TPLevel, current_price: float) -> bool:
        """Execute stop loss move when TP is hit"""
        if tp_level.move_sl_to is None:
            return False
        
        new_sl = tp_level.move_sl_to
        
        # Execute SL modification
        success = False
        if self.mt5_bridge and hasattr(self.mt5_bridge, 'modify_position'):
            result = await self.mt5_bridge.modify_position(
                ticket=position.ticket,
                new_sl=new_sl
            )
            success = result.get('success', False)
        
        if success:
            position.current_sl = new_sl
            
            # Record execution
            execution = TPExecution(
                ticket=position.ticket,
                tp_level=tp_level.level,
                execution_price=current_price,
                closed_lots=0.0,
                remaining_lots=position.current_lot_size,
                profit_pips=self.calculate_pips(position.symbol, current_price - position.entry_price, position.direction),
                profit_amount=0.0,
                execution_time=datetime.now(),
                action_taken=TPHitAction.MOVE_SL,
                new_sl=new_sl
            )
            self.execution_history.append(execution)
            
            self.logger.info(f"Moved SL to {new_sl} on TP{tp_level.level} hit")
            return True
        
        return False

    async def _execute_close_all(self, position: TPManagedPosition, tp_level: TPLevel, current_price: float) -> bool:
        """Execute full position close when TP is hit"""
        success = False
        if self.mt5_bridge and hasattr(self.mt5_bridge, 'close_position'):
            result = await self.mt5_bridge.close_position(position.ticket)
            success = result.get('success', False)
        
        if success:
            # Calculate final profit
            profit_pips = self.calculate_pips(position.symbol, current_price - position.entry_price, position.direction)
            profit_amount = profit_pips * position.current_lot_size * 10
            
            # Record execution
            execution = TPExecution(
                ticket=position.ticket,
                tp_level=tp_level.level,
                execution_price=current_price,
                closed_lots=position.current_lot_size,
                remaining_lots=0.0,
                profit_pips=profit_pips,
                profit_amount=profit_amount,
                execution_time=datetime.now(),
                action_taken=TPHitAction.CLOSE_ALL
            )
            self.execution_history.append(execution)
            
            # Mark position as closed
            position.position_closed = True
            position.total_closed_lots = position.original_lot_size
            position.realized_profit += profit_amount
            
            self.logger.info(f"Closed full position at TP{tp_level.level} ({current_price})")
            return True
        
        return False

    async def _execute_scale_out(self, position: TPManagedPosition, tp_level: TPLevel, current_price: float) -> bool:
        """Execute scale out strategy when TP is hit"""
        # Scale out reduces position size progressively
        scale_factor = 0.5  # Reduce by 50%
        lots_to_close = position.current_lot_size * scale_factor
        lots_to_close = max(0.01, round(lots_to_close, 2))
        
        return await self._execute_partial_close(position, tp_level, current_price)

    async def _auto_move_sl_on_tp(self, position: TPManagedPosition, hit_tp_level: TPLevel):
        """Automatically move SL when TP levels are hit"""
        if not position.config.move_sl_on_tp1 and not position.config.move_sl_on_tp2:
            return
        
        new_sl = None
        
        if hit_tp_level.level == 1 and position.config.move_sl_on_tp1:
            # Move SL to breakeven on TP1
            new_sl = position.entry_price
        elif hit_tp_level.level == 2 and position.config.move_sl_on_tp2:
            # Move SL to TP1 price on TP2
            tp1 = next((tp for tp in position.tp_levels if tp.level == 1), None)
            if tp1:
                new_sl = tp1.price
        
        if new_sl and new_sl != position.current_sl:
            # Validate SL direction
            valid_sl = False
            if position.direction == TradeDirection.BUY:
                valid_sl = new_sl < position.entry_price or new_sl > position.current_sl
            else:  # SELL
                valid_sl = new_sl > position.entry_price or new_sl < position.current_sl
            
            if valid_sl and self.mt5_bridge and hasattr(self.mt5_bridge, 'modify_position'):
                result = await self.mt5_bridge.modify_position(
                    ticket=position.ticket,
                    new_sl=new_sl
                )
                if result.get('success'):
                    position.current_sl = new_sl
                    self.logger.info(f"Auto-moved SL to {new_sl} after TP{hit_tp_level.level}")

    async def monitor_tp_positions(self):
        """Monitor all TP managed positions for TP hits"""
        for ticket, position in list(self.tp_positions.items()):
            if position.position_closed:
                continue
            
            try:
                current_price = await self.get_current_price(position.symbol)
                if current_price is None:
                    continue
                
                position.last_price_check = datetime.now()
                
                # Check for TP hits
                hit_tp_levels = await self.check_tp_levels(position, current_price)
                
                # Execute actions for hit TP levels
                for tp_level in hit_tp_levels:
                    await self.execute_tp_action(position, tp_level, current_price)
                
                # Clean up closed positions
                if position.position_closed:
                    self.logger.info(f"Position {ticket} fully closed, removing from monitoring")
                    # Keep in dict for history but mark as closed
                
            except Exception as e:
                self.logger.error(f"Error monitoring TP position {ticket}: {e}")

    async def start_tp_monitor(self):
        """Start the TP monitoring loop"""
        if self.is_running:
            self.logger.warning("TP monitor already running")
            return
        
        self.is_running = True
        self.logger.info("Starting TP monitor")
        
        try:
            while self.is_running:
                await self.monitor_tp_positions()
                await asyncio.sleep(self.update_interval)
                
        except Exception as e:
            self.logger.error(f"TP monitor error: {e}")
        finally:
            self.is_running = False
            self.logger.info("TP monitor stopped")

    def stop_tp_monitor(self):
        """Stop the TP monitoring loop"""
        self.is_running = False
        self.logger.info("Stopping TP monitor")

    def get_tp_statistics(self) -> Dict[str, Any]:
        """Get statistics about TP management operations"""
        total_positions = len(self.tp_positions)
        active_positions = len([p for p in self.tp_positions.values() if not p.position_closed])
        closed_positions = len([p for p in self.tp_positions.values() if p.position_closed])
        
        total_executions = len(self.execution_history)
        if total_executions > 0:
            total_profit = sum(ex.profit_amount for ex in self.execution_history)
            avg_profit_per_execution = total_profit / total_executions
            total_volume_closed = sum(ex.closed_lots for ex in self.execution_history)
        else:
            total_profit = 0.0
            avg_profit_per_execution = 0.0
            total_volume_closed = 0.0
        
        # TP level hit statistics
        tp_level_hits = {}
        for execution in self.execution_history:
            level = execution.tp_level
            if level not in tp_level_hits:
                tp_level_hits[level] = 0
            tp_level_hits[level] += 1
        
        return {
            'total_positions': total_positions,
            'active_positions': active_positions,
            'closed_positions': closed_positions,
            'total_executions': total_executions,
            'total_profit': total_profit,
            'average_profit_per_execution': avg_profit_per_execution,
            'total_volume_closed': total_volume_closed,
            'tp_level_hit_count': tp_level_hits
        }

    def get_position_status(self, ticket: int) -> Optional[Dict[str, Any]]:
        """Get status of specific TP managed position"""
        if ticket not in self.tp_positions:
            return None
        
        position = self.tp_positions[ticket]
        
        tp_levels_status = []
        for tp_level in position.tp_levels:
            tp_levels_status.append({
                'level': tp_level.level,
                'price': tp_level.price,
                'close_percentage': tp_level.close_percentage * 100,
                'status': tp_level.status.value,
                'hit_time': tp_level.hit_time.isoformat() if tp_level.hit_time else None,
                'executed_lots': tp_level.executed_lots
            })
        
        return {
            'ticket': ticket,
            'symbol': position.symbol,
            'direction': position.direction.value,
            'entry_price': position.entry_price,
            'original_lot_size': position.original_lot_size,
            'current_lot_size': position.current_lot_size,
            'total_closed_lots': position.total_closed_lots,
            'current_sl': position.current_sl,
            'position_closed': position.position_closed,
            'realized_profit': position.realized_profit,
            'tp_levels': tp_levels_status,
            'created_at': position.created_at.isoformat(),
            'last_price_check': position.last_price_check.isoformat()
        }

    def get_recent_executions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent TP executions"""
        recent_executions = self.execution_history[-limit:] if self.execution_history else []
        
        return [{
            'ticket': execution.ticket,
            'tp_level': execution.tp_level,
            'execution_price': execution.execution_price,
            'closed_lots': execution.closed_lots,
            'remaining_lots': execution.remaining_lots,
            'profit_pips': execution.profit_pips,
            'profit_amount': execution.profit_amount,
            'execution_time': execution.execution_time.isoformat(),
            'action_taken': execution.action_taken.value,
            'new_sl': execution.new_sl
        } for execution in recent_executions]


# Example usage and testing
async def main():
    """Example usage of TP Manager"""
    manager = TPManager()
    
    # Test TP level parsing
    test_signals = [
        "TP1: 1.2050 TP2: 1.2080 TP3: 1.2120",
        "Take Profit 1.2050, 1.2080, 1.2120",
        "TP 1.2050 (25%), 1.2080 (25%), 1.2120 (50%)"
    ]
    
    print("Testing TP level parsing:")
    for signal in test_signals:
        tp_levels = manager.parse_tp_levels_from_signal(signal, "EURUSD", TradeDirection.BUY, 1.2000)
        print(f"Signal: '{signal}'")
        for tp in tp_levels:
            print(f"  TP{tp.level}: {tp.price} ({tp.close_percentage*100}%)")
        print()
    
    # Get statistics
    stats = manager.get_tp_statistics()
    print(f"Current statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(main())