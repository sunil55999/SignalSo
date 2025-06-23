"""
Break Even Engine for SignalOS
Implements automatic break-even functionality to move stop loss to entry price when profit thresholds are reached
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import math


class BreakEvenTrigger(Enum):
    FIXED_PIPS = "fixed_pips"
    PERCENTAGE = "percentage"
    TIME_BASED = "time_based"
    RATIO_BASED = "ratio_based"


class TradeDirection(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class BreakEvenConfig:
    trigger: BreakEvenTrigger
    threshold_value: float  # Pips, percentage, or minutes
    buffer_pips: float = 0.0  # Additional pips above/below entry
    min_profit_pips: float = 5.0  # Minimum profit before activation
    only_when_profitable: bool = True  # Only move SL when in profit


@dataclass
class BreakEvenPosition:
    ticket: int
    symbol: str
    direction: TradeDirection
    entry_price: float
    entry_time: datetime
    original_sl: Optional[float]
    current_sl: Optional[float]
    lot_size: float
    config: BreakEvenConfig
    last_update: datetime
    break_even_triggered: bool = False
    max_profit_achieved: float = 0.0  # Track maximum profit in pips


@dataclass
class BreakEvenUpdate:
    ticket: int
    new_sl: float
    old_sl: Optional[float]
    entry_price: float
    trigger_price: float
    profit_pips: float
    buffer_applied: float
    trigger_reason: str
    timestamp: datetime


class BreakEvenEngine:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/break_even_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Module references
        self.mt5_bridge: Optional[Any] = None
        self.market_data: Optional[Any] = None
        
        # Active break-even positions
        self.break_even_positions: Dict[int, BreakEvenPosition] = {}
        self.update_history: List[BreakEvenUpdate] = []
        
        # Monitoring settings
        self.update_interval = self.config.get('update_interval_seconds', 15)
        self.is_running = False
        self._load_break_even_history()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('break_even', {
                    'update_interval_seconds': 15,
                    'default_trigger_pips': 10.0,
                    'default_buffer_pips': 1.0,
                    'min_profit_threshold_pips': 5.0,
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
            'break_even': {
                'update_interval_seconds': 15,
                'default_trigger_pips': 10.0,
                'default_buffer_pips': 1.0,
                'min_profit_threshold_pips': 5.0,
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
            
        return default_config['break_even']

    def _setup_logging(self):
        """Setup logging for break even operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('BreakEvenEngine')

    def _load_break_even_history(self):
        """Load existing break even history from log file"""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
                # Convert back to dataclass objects
                self.update_history = []
                for entry in data:
                    update = BreakEvenUpdate(
                        ticket=entry['ticket'],
                        new_sl=entry['new_sl'],
                        old_sl=entry.get('old_sl'),
                        entry_price=entry['entry_price'],
                        trigger_price=entry['trigger_price'],
                        profit_pips=entry['profit_pips'],
                        buffer_applied=entry['buffer_applied'],
                        trigger_reason=entry['trigger_reason'],
                        timestamp=datetime.fromisoformat(entry['timestamp'])
                    )
                    self.update_history.append(update)
        except FileNotFoundError:
            self.update_history = []
            self._save_break_even_history()

    def _save_break_even_history(self):
        """Save break even history to log file"""
        try:
            data = []
            for update in self.update_history:
                data.append({
                    'ticket': update.ticket,
                    'new_sl': update.new_sl,
                    'old_sl': update.old_sl,
                    'entry_price': update.entry_price,
                    'trigger_price': update.trigger_price,
                    'profit_pips': update.profit_pips,
                    'buffer_applied': update.buffer_applied,
                    'trigger_reason': update.trigger_reason,
                    'timestamp': update.timestamp.isoformat()
                })
            
            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save break even history: {e}")

    def inject_modules(self, mt5_bridge=None, market_data=None):
        """Inject module references for MT5 operations and market data"""
        self.mt5_bridge = mt5_bridge
        self.market_data = market_data

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

    def add_break_even_position(self, ticket: int, symbol: str, direction: TradeDirection,
                               entry_price: float, entry_time: datetime, current_sl: Optional[float],
                               lot_size: float, config: BreakEvenConfig) -> bool:
        """Add position to break even monitoring"""
        try:
            position = BreakEvenPosition(
                ticket=ticket,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                entry_time=entry_time,
                original_sl=current_sl,
                current_sl=current_sl,
                lot_size=lot_size,
                config=config,
                last_update=datetime.now(),
                break_even_triggered=False,
                max_profit_achieved=0.0
            )
            
            self.break_even_positions[ticket] = position
            self.logger.info(f"Added break even monitoring for ticket {ticket} ({symbol})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add break even position {ticket}: {e}")
            return False

    def remove_break_even_position(self, ticket: int) -> bool:
        """Remove position from break even monitoring"""
        if ticket in self.break_even_positions:
            del self.break_even_positions[ticket]
            self.logger.info(f"Removed break even monitoring for ticket {ticket}")
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

    def should_trigger_break_even(self, position: BreakEvenPosition, current_price: float) -> Tuple[bool, str]:
        """Check if break even should be triggered for position"""
        if position.break_even_triggered:
            return False, "Already triggered"
        
        # Calculate current profit
        if position.direction == TradeDirection.BUY:
            profit_pips = self.calculate_pips(position.symbol, current_price - position.entry_price)
        else:
            profit_pips = self.calculate_pips(position.symbol, position.entry_price - current_price)
        
        # Update max profit achieved
        if profit_pips > position.max_profit_achieved:
            position.max_profit_achieved = profit_pips
        
        # Check minimum profit requirement
        if position.config.only_when_profitable and profit_pips < position.config.min_profit_pips:
            return False, f"Insufficient profit: {profit_pips:.1f} < {position.config.min_profit_pips} pips"
        
        # Check trigger conditions based on method
        if position.config.trigger == BreakEvenTrigger.FIXED_PIPS:
            if profit_pips >= position.config.threshold_value:
                return True, f"Fixed pips threshold reached: {profit_pips:.1f} >= {position.config.threshold_value} pips"
        
        elif position.config.trigger == BreakEvenTrigger.PERCENTAGE:
            profit_percentage = (profit_pips * self.get_pip_value(position.symbol)) / position.entry_price * 100
            if profit_percentage >= position.config.threshold_value:
                return True, f"Percentage threshold reached: {profit_percentage:.2f}% >= {position.config.threshold_value}%"
        
        elif position.config.trigger == BreakEvenTrigger.TIME_BASED:
            time_elapsed = (datetime.now() - position.entry_time).total_seconds() / 60  # minutes
            if time_elapsed >= position.config.threshold_value and profit_pips > 0:
                return True, f"Time threshold reached: {time_elapsed:.1f} >= {position.config.threshold_value} minutes"
        
        elif position.config.trigger == BreakEvenTrigger.RATIO_BASED:
            # Trigger when profit reaches X:1 ratio of initial risk
            if position.original_sl is not None:
                risk_pips = self.calculate_pips(position.symbol, abs(position.entry_price - position.original_sl))
                if risk_pips > 0:
                    current_ratio = profit_pips / risk_pips
                    if current_ratio >= position.config.threshold_value:
                        return True, f"Risk-reward ratio reached: {current_ratio:.1f}:1 >= {position.config.threshold_value}:1"
        
        return False, "Trigger conditions not met"

    def calculate_break_even_sl(self, position: BreakEvenPosition) -> float:
        """Calculate the break even stop loss price"""
        buffer_price = self.pips_to_price(position.symbol, position.config.buffer_pips)
        
        if position.direction == TradeDirection.BUY:
            # For BUY positions, SL goes above entry by buffer amount
            return position.entry_price + buffer_price
        else:
            # For SELL positions, SL goes below entry by buffer amount
            return position.entry_price - buffer_price

    async def update_stop_loss(self, ticket: int, new_sl: float) -> bool:
        """Update stop loss via MT5 bridge"""
        if not self.mt5_bridge:
            self.logger.error("MT5 bridge not available for SL update")
            return False
        
        try:
            if hasattr(self.mt5_bridge, 'modify_position'):
                result = await self.mt5_bridge.modify_position(
                    ticket=ticket,
                    stop_loss=new_sl
                )
            elif hasattr(self.mt5_bridge, 'modify_trade'):
                result = await self.mt5_bridge.modify_trade(
                    ticket=ticket,
                    new_sl=new_sl
                )
            else:
                self.logger.error("No MT5 modification method available")
                return False
            
            return result.get('success', False)
            
        except Exception as e:
            self.logger.error(f"Failed to update SL for ticket {ticket}: {e}")
            return False

    async def process_break_even_updates(self):
        """Process all break even positions and update stop losses"""
        update_count = 0
        
        for ticket, position in list(self.break_even_positions.items()):
            try:
                # Skip if already triggered
                if position.break_even_triggered:
                    continue
                
                # Get current price
                current_price = await self.get_current_price(position.symbol)
                if current_price is None:
                    continue
                
                # Check if break even should be triggered
                should_trigger, reason = self.should_trigger_break_even(position, current_price)
                if not should_trigger:
                    continue
                
                # Calculate new break even SL
                new_sl = self.calculate_break_even_sl(position)
                
                # Ensure new SL is better than current SL
                if position.current_sl is not None:
                    if position.direction == TradeDirection.BUY and new_sl <= position.current_sl:
                        self.logger.info(f"Break even SL {new_sl:.5f} not better than current {position.current_sl:.5f} for {ticket}")
                        continue
                    elif position.direction == TradeDirection.SELL and new_sl >= position.current_sl:
                        self.logger.info(f"Break even SL {new_sl:.5f} not better than current {position.current_sl:.5f} for {ticket}")
                        continue
                
                # Update stop loss
                if await self.update_stop_loss(ticket, new_sl):
                    # Calculate profit at trigger
                    if position.direction == TradeDirection.BUY:
                        profit_pips = self.calculate_pips(position.symbol, current_price - position.entry_price)
                    else:
                        profit_pips = self.calculate_pips(position.symbol, position.entry_price - current_price)
                    
                    # Log the update
                    update = BreakEvenUpdate(
                        ticket=ticket,
                        new_sl=new_sl,
                        old_sl=position.current_sl,
                        entry_price=position.entry_price,
                        trigger_price=current_price,
                        profit_pips=profit_pips,
                        buffer_applied=position.config.buffer_pips,
                        trigger_reason=reason,
                        timestamp=datetime.now()
                    )
                    
                    self.update_history.append(update)
                    
                    # Update position
                    position.current_sl = new_sl
                    position.last_update = datetime.now()
                    position.break_even_triggered = True
                    
                    update_count += 1
                    self.logger.info(f"Break even triggered for {ticket}: {new_sl:.5f} - {reason}")
                
            except Exception as e:
                self.logger.error(f"Error processing break even for ticket {ticket}: {e}")
        
        if update_count > 0:
            self._save_break_even_history()
            self.logger.info(f"Processed {update_count} break even updates")

    async def start_break_even_monitor(self):
        """Start the break even monitoring loop"""
        if self.is_running:
            self.logger.warning("Break even monitor already running")
            return
        
        self.is_running = True
        self.logger.info("Starting break even monitor")
        
        try:
            while self.is_running:
                await self.process_break_even_updates()
                await asyncio.sleep(self.update_interval)
                
        except Exception as e:
            self.logger.error(f"Break even monitor error: {e}")
        finally:
            self.is_running = False
            self.logger.info("Break even monitor stopped")

    def stop_break_even_monitor(self):
        """Stop the break even monitoring loop"""
        self.is_running = False
        self.logger.info("Stopping break even monitor")

    def get_break_even_statistics(self) -> Dict[str, Any]:
        """Get statistics about break even operations"""
        total_updates = len(self.update_history)
        active_positions = len([p for p in self.break_even_positions.values() if not p.break_even_triggered])
        triggered_positions = len([p for p in self.break_even_positions.values() if p.break_even_triggered])
        
        if total_updates == 0:
            return {
                'total_break_even_triggers': 0,
                'active_positions': active_positions,
                'triggered_positions': triggered_positions,
                'average_profit_at_trigger': 0.0,
                'most_common_trigger': None,
                'total_positions_monitored': len(self.break_even_positions)
            }
        
        # Calculate statistics
        total_profit = sum(update.profit_pips for update in self.update_history)
        avg_profit = total_profit / total_updates
        
        triggers = [p.config.trigger.value for p in self.break_even_positions.values()]
        most_common_trigger = max(set(triggers), key=triggers.count) if triggers else None
        
        return {
            'total_break_even_triggers': total_updates,
            'active_positions': active_positions,
            'triggered_positions': triggered_positions,
            'average_profit_at_trigger': avg_profit,
            'most_common_trigger': most_common_trigger,
            'total_positions_monitored': len(self.break_even_positions)
        }

    def get_position_status(self, ticket: int) -> Optional[Dict[str, Any]]:
        """Get status of specific break even position"""
        if ticket not in self.break_even_positions:
            return None
        
        position = self.break_even_positions[ticket]
        
        return {
            'ticket': ticket,
            'symbol': position.symbol,
            'direction': position.direction.value,
            'entry_price': position.entry_price,
            'entry_time': position.entry_time.isoformat(),
            'current_sl': position.current_sl,
            'original_sl': position.original_sl,
            'break_even_triggered': position.break_even_triggered,
            'trigger_method': position.config.trigger.value,
            'threshold_value': position.config.threshold_value,
            'buffer_pips': position.config.buffer_pips,
            'max_profit_achieved': position.max_profit_achieved,
            'last_update': position.last_update.isoformat()
        }

    def get_recent_updates(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent break even updates"""
        recent_updates = self.update_history[-limit:] if self.update_history else []
        
        return [{
            'ticket': update.ticket,
            'new_sl': update.new_sl,
            'old_sl': update.old_sl,
            'entry_price': update.entry_price,
            'trigger_price': update.trigger_price,
            'profit_pips': update.profit_pips,
            'buffer_applied': update.buffer_applied,
            'trigger_reason': update.trigger_reason,
            'timestamp': update.timestamp.isoformat()
        } for update in recent_updates]


# Example usage and testing
async def main():
    """Example usage of Break Even Engine"""
    engine = BreakEvenEngine()
    
    # Create test configuration
    config = BreakEvenConfig(
        trigger=BreakEvenTrigger.FIXED_PIPS,
        threshold_value=10.0,
        buffer_pips=1.0,
        min_profit_pips=5.0,
        only_when_profitable=True
    )
    
    # Add test position
    engine.add_break_even_position(
        ticket=12345,
        symbol="EURUSD",
        direction=TradeDirection.BUY,
        entry_price=1.2000,
        entry_time=datetime.now(),
        current_sl=1.1980,
        lot_size=1.0,
        config=config
    )
    
    print("Break Even Engine initialized")
    print(f"Active positions: {len(engine.break_even_positions)}")
    print(f"Configuration: {config}")
    
    # Get statistics
    stats = engine.get_break_even_statistics()
    print(f"Statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(main())