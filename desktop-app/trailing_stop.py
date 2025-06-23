"""
Trailing Stop Engine for SignalOS
Implements dynamic trailing stop loss functionality with multiple trailing methods
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import math


class TrailingMethod(Enum):
    FIXED_PIPS = "fixed_pips"
    PERCENTAGE = "percentage"
    ATR_BASED = "atr_based"
    BREAKEVEN_PLUS = "breakeven_plus"


class TradeDirection(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class TrailingStopConfig:
    method: TrailingMethod
    trail_distance: float  # Pips, percentage, or ATR multiplier
    activation_threshold: float  # Minimum profit before trailing starts (pips)
    step_size: float = 1.0  # Minimum move required to trail (pips)
    max_trail_distance: Optional[float] = None  # Maximum trailing distance
    use_breakeven_lock: bool = True  # Lock in breakeven when possible


@dataclass
class TrailingPosition:
    ticket: int
    symbol: str
    direction: TradeDirection
    entry_price: float
    original_sl: Optional[float]
    current_sl: Optional[float]
    lot_size: float
    config: TrailingStopConfig
    last_update: datetime
    highest_profit_price: Optional[float] = None  # Best price achieved
    trailing_active: bool = False
    breakeven_locked: bool = False


@dataclass
class TrailingUpdate:
    ticket: int
    new_sl: float
    old_sl: Optional[float]
    current_price: float
    profit_pips: float
    trailing_distance: float
    reason: str
    timestamp: datetime


class TrailingStopEngine:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/trailing_stop_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Module references
        self.mt5_bridge: Optional[Any] = None
        self.market_data: Optional[Any] = None
        
        # Active trailing positions
        self.trailing_positions: Dict[int, TrailingPosition] = {}
        self.update_history: List[TrailingUpdate] = []
        
        # Monitoring settings
        self.update_interval = self.config.get('update_interval_seconds', 30)
        self.is_running = False
        self._load_trailing_history()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('trailing_stop', {
                    'update_interval_seconds': 30,
                    'min_profit_to_start_pips': 5.0,
                    'default_trail_distance_pips': 10.0,
                    'pip_values': {
                        'EURUSD': 0.0001,
                        'GBPUSD': 0.0001,
                        'USDJPY': 0.01,
                        'USDCHF': 0.0001,
                        'default': 0.0001
                    },
                    'max_positions_to_trail': 50
                })
        except FileNotFoundError:
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        default_config = {
            'trailing_stop': {
                'update_interval_seconds': 30,
                'min_profit_to_start_pips': 5.0,
                'default_trail_distance_pips': 10.0,
                'pip_values': {
                    'EURUSD': 0.0001,
                    'GBPUSD': 0.0001,
                    'USDJPY': 0.01,
                    'USDCHF': 0.0001,
                    'default': 0.0001
                },
                'max_positions_to_trail': 50
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
        except Exception as e:
            logging.warning(f"Could not create config file: {e}")
            
        return default_config['trailing_stop']

    def _setup_logging(self):
        """Setup logging for trailing stop operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('TrailingStopEngine')

    def _load_trailing_history(self):
        """Load existing trailing history from log file"""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
                # Convert back to dataclass objects
                self.update_history = []
                for entry in data:
                    update = TrailingUpdate(
                        ticket=entry['ticket'],
                        new_sl=entry['new_sl'],
                        old_sl=entry.get('old_sl'),
                        current_price=entry['current_price'],
                        profit_pips=entry['profit_pips'],
                        trailing_distance=entry['trailing_distance'],
                        reason=entry['reason'],
                        timestamp=datetime.fromisoformat(entry['timestamp'])
                    )
                    self.update_history.append(update)
        except FileNotFoundError:
            self.update_history = []
            self._save_trailing_history()

    def _save_trailing_history(self):
        """Save trailing history to log file"""
        try:
            data = []
            for update in self.update_history:
                data.append({
                    'ticket': update.ticket,
                    'new_sl': update.new_sl,
                    'old_sl': update.old_sl,
                    'current_price': update.current_price,
                    'profit_pips': update.profit_pips,
                    'trailing_distance': update.trailing_distance,
                    'reason': update.reason,
                    'timestamp': update.timestamp.isoformat()
                })
            
            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save trailing history: {e}")

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

    def add_trailing_position(self, ticket: int, symbol: str, direction: TradeDirection, 
                            entry_price: float, current_sl: Optional[float], 
                            lot_size: float, config: TrailingStopConfig) -> bool:
        """Add position to trailing stop monitoring"""
        try:
            position = TrailingPosition(
                ticket=ticket,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                original_sl=current_sl,
                current_sl=current_sl,
                lot_size=lot_size,
                config=config,
                last_update=datetime.now(),
                highest_profit_price=entry_price,
                trailing_active=False,
                breakeven_locked=False
            )
            
            self.trailing_positions[ticket] = position
            self.logger.info(f"Added trailing stop for ticket {ticket} ({symbol})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add trailing position {ticket}: {e}")
            return False

    def remove_trailing_position(self, ticket: int) -> bool:
        """Remove position from trailing stop monitoring"""
        if ticket in self.trailing_positions:
            del self.trailing_positions[ticket]
            self.logger.info(f"Removed trailing stop for ticket {ticket}")
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

    def calculate_new_trailing_sl(self, position: TrailingPosition, current_price: float) -> Optional[float]:
        """Calculate new trailing stop loss based on configuration"""
        if position.direction == TradeDirection.BUY:
            profit_pips = self.calculate_pips(position.symbol, current_price - position.entry_price)
            
            # Check if profit threshold is met
            if profit_pips < position.config.activation_threshold:
                return None
            
            # Update highest profit price
            if position.highest_profit_price is None or current_price > position.highest_profit_price:
                position.highest_profit_price = current_price
            
            # Calculate trailing SL based on method
            if position.config.method == TrailingMethod.FIXED_PIPS:
                trail_price = self.pips_to_price(position.symbol, position.config.trail_distance)
                new_sl = position.highest_profit_price - trail_price
                
            elif position.config.method == TrailingMethod.PERCENTAGE:
                trail_amount = position.highest_profit_price * (position.config.trail_distance / 100)
                new_sl = position.highest_profit_price - trail_amount
                
            elif position.config.method == TrailingMethod.BREAKEVEN_PLUS:
                breakeven_buffer = self.pips_to_price(position.symbol, position.config.trail_distance)
                new_sl = position.entry_price + breakeven_buffer
                
            else:  # ATR_BASED
                # Simplified ATR calculation - would need historical data for full implementation
                atr_estimate = self.pips_to_price(position.symbol, 20.0)  # Estimate
                new_sl = position.highest_profit_price - (atr_estimate * position.config.trail_distance)
            
        else:  # SELL
            profit_pips = self.calculate_pips(position.symbol, position.entry_price - current_price)
            
            # Check if profit threshold is met
            if profit_pips < position.config.activation_threshold:
                return None
            
            # Update highest profit price (lowest price for sells)
            if position.highest_profit_price is None or current_price < position.highest_profit_price:
                position.highest_profit_price = current_price
            
            # Calculate trailing SL based on method
            if position.config.method == TrailingMethod.FIXED_PIPS:
                trail_price = self.pips_to_price(position.symbol, position.config.trail_distance)
                new_sl = position.highest_profit_price + trail_price
                
            elif position.config.method == TrailingMethod.PERCENTAGE:
                trail_amount = position.highest_profit_price * (position.config.trail_distance / 100)
                new_sl = position.highest_profit_price + trail_amount
                
            elif position.config.method == TrailingMethod.BREAKEVEN_PLUS:
                breakeven_buffer = self.pips_to_price(position.symbol, position.config.trail_distance)
                new_sl = position.entry_price - breakeven_buffer
                
            else:  # ATR_BASED
                atr_estimate = self.pips_to_price(position.symbol, 20.0)  # Estimate
                new_sl = position.highest_profit_price + (atr_estimate * position.config.trail_distance)
        
        # Ensure new SL is better than current SL
        if position.current_sl is not None:
            if position.direction == TradeDirection.BUY and new_sl <= position.current_sl:
                return None
            elif position.direction == TradeDirection.SELL and new_sl >= position.current_sl:
                return None
        
        # Check step size requirement
        if position.current_sl is not None:
            sl_move_pips = self.calculate_pips(position.symbol, abs(new_sl - position.current_sl))
            if sl_move_pips < position.config.step_size:
                return None
        
        return new_sl

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

    async def process_trailing_updates(self):
        """Process all trailing positions and update stop losses"""
        update_count = 0
        
        for ticket, position in list(self.trailing_positions.items()):
            try:
                # Get current price
                current_price = await self.get_current_price(position.symbol)
                if current_price is None:
                    continue
                
                # Calculate new trailing SL
                new_sl = self.calculate_new_trailing_sl(position, current_price)
                if new_sl is None:
                    continue
                
                # Update stop loss
                if await self.update_stop_loss(ticket, new_sl):
                    # Calculate profit
                    if position.direction == TradeDirection.BUY:
                        profit_pips = self.calculate_pips(position.symbol, current_price - position.entry_price)
                    else:
                        profit_pips = self.calculate_pips(position.symbol, position.entry_price - current_price)
                    
                    # Log the update
                    update = TrailingUpdate(
                        ticket=ticket,
                        new_sl=new_sl,
                        old_sl=position.current_sl,
                        current_price=current_price,
                        profit_pips=profit_pips,
                        trailing_distance=position.config.trail_distance,
                        reason=f"Trailing {position.config.method.value}",
                        timestamp=datetime.now()
                    )
                    
                    self.update_history.append(update)
                    
                    # Update position
                    position.current_sl = new_sl
                    position.last_update = datetime.now()
                    position.trailing_active = True
                    
                    # Check breakeven lock
                    if position.config.use_breakeven_lock and not position.breakeven_locked:
                        if position.direction == TradeDirection.BUY and new_sl >= position.entry_price:
                            position.breakeven_locked = True
                        elif position.direction == TradeDirection.SELL and new_sl <= position.entry_price:
                            position.breakeven_locked = True
                    
                    update_count += 1
                    self.logger.info(f"Updated trailing SL for {ticket}: {new_sl:.5f}")
                
            except Exception as e:
                self.logger.error(f"Error processing trailing for ticket {ticket}: {e}")
        
        if update_count > 0:
            self._save_trailing_history()
            self.logger.info(f"Processed {update_count} trailing stop updates")

    async def start_trailing_monitor(self):
        """Start the trailing stop monitoring loop"""
        if self.is_running:
            self.logger.warning("Trailing monitor already running")
            return
        
        self.is_running = True
        self.logger.info("Starting trailing stop monitor")
        
        try:
            while self.is_running:
                await self.process_trailing_updates()
                await asyncio.sleep(self.update_interval)
                
        except Exception as e:
            self.logger.error(f"Trailing monitor error: {e}")
        finally:
            self.is_running = False
            self.logger.info("Trailing stop monitor stopped")

    def stop_trailing_monitor(self):
        """Stop the trailing stop monitoring loop"""
        self.is_running = False
        self.logger.info("Stopping trailing stop monitor")

    def get_trailing_statistics(self) -> Dict[str, Any]:
        """Get statistics about trailing stop operations"""
        total_updates = len(self.update_history)
        active_positions = len(self.trailing_positions)
        
        if total_updates == 0:
            return {
                'total_updates': 0,
                'active_positions': active_positions,
                'average_profit_at_update': 0.0,
                'most_common_method': None,
                'total_positions_trailed': 0
            }
        
        # Calculate statistics
        total_profit = sum(update.profit_pips for update in self.update_history)
        avg_profit = total_profit / total_updates
        
        methods = [pos.config.method.value for pos in self.trailing_positions.values()]
        most_common_method = max(set(methods), key=methods.count) if methods else None
        
        unique_tickets = len(set(update.ticket for update in self.update_history))
        
        return {
            'total_updates': total_updates,
            'active_positions': active_positions,
            'average_profit_at_update': avg_profit,
            'most_common_method': most_common_method,
            'total_positions_trailed': unique_tickets
        }

    def get_position_status(self, ticket: int) -> Optional[Dict[str, Any]]:
        """Get status of specific trailing position"""
        if ticket not in self.trailing_positions:
            return None
        
        position = self.trailing_positions[ticket]
        
        return {
            'ticket': ticket,
            'symbol': position.symbol,
            'direction': position.direction.value,
            'entry_price': position.entry_price,
            'current_sl': position.current_sl,
            'original_sl': position.original_sl,
            'trailing_method': position.config.method.value,
            'trail_distance': position.config.trail_distance,
            'trailing_active': position.trailing_active,
            'breakeven_locked': position.breakeven_locked,
            'last_update': position.last_update.isoformat(),
            'highest_profit_price': position.highest_profit_price
        }

    def get_recent_updates(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent trailing stop updates"""
        recent_updates = self.update_history[-limit:] if self.update_history else []
        
        return [{
            'ticket': update.ticket,
            'new_sl': update.new_sl,
            'old_sl': update.old_sl,
            'current_price': update.current_price,
            'profit_pips': update.profit_pips,
            'trailing_distance': update.trailing_distance,
            'reason': update.reason,
            'timestamp': update.timestamp.isoformat()
        } for update in recent_updates]


# Example usage and testing
async def main():
    """Example usage of Trailing Stop Engine"""
    engine = TrailingStopEngine()
    
    # Create test configuration
    config = TrailingStopConfig(
        method=TrailingMethod.FIXED_PIPS,
        trail_distance=10.0,
        activation_threshold=5.0,
        step_size=1.0,
        use_breakeven_lock=True
    )
    
    # Add test position
    engine.add_trailing_position(
        ticket=12345,
        symbol="EURUSD",
        direction=TradeDirection.BUY,
        entry_price=1.2000,
        current_sl=1.1980,
        lot_size=1.0,
        config=config
    )
    
    print("Trailing Stop Engine initialized")
    print(f"Active positions: {len(engine.trailing_positions)}")
    print(f"Configuration: {config}")
    
    # Get statistics
    stats = engine.get_trailing_statistics()
    print(f"Statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(main())