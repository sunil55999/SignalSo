"""
Multi TP Manager Engine for SignalOS
Advanced take profit management system supporting up to 100 TP levels with partial closure and dynamic SL shifting
"""

import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os

class TPStatus(Enum):
    PENDING = "pending"
    HIT = "hit"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class SLShiftMode(Enum):
    BREAK_EVEN = "break_even"
    NEXT_TP = "next_tp"
    FIXED_DISTANCE = "fixed_distance"
    PERCENTAGE = "percentage"
    NONE = "none"

@dataclass
class TPLevel:
    level: int  # TP1, TP2, etc.
    price: float
    percentage: float  # Percentage of position to close (0-100)
    status: TPStatus = TPStatus.PENDING
    hit_time: Optional[datetime] = None
    actual_close_price: Optional[float] = None
    closed_volume: Optional[float] = None

@dataclass
class MultiTPConfig:
    tp_levels: List[TPLevel]
    sl_shift_mode: SLShiftMode
    sl_shift_buffer_pips: float = 2.0
    min_remaining_volume: float = 0.01  # Minimum lot size to keep open
    max_slippage_pips: float = 3.0
    enable_auto_monitoring: bool = True
    monitoring_interval: float = 1.0  # seconds
    expire_after_hours: int = 168  # 7 days

@dataclass
class MultiTPTrade:
    ticket: int
    symbol: str
    direction: str  # "buy" or "sell"
    entry_price: float
    initial_volume: float
    remaining_volume: float
    current_sl: Optional[float]
    config: MultiTPConfig
    created_time: datetime
    last_tp_hit: Optional[int] = None  # Last TP level that was hit
    total_closed_volume: float = 0.0
    total_realized_profit: float = 0.0
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket": self.ticket,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "initial_volume": self.initial_volume,
            "remaining_volume": self.remaining_volume,
            "current_sl": self.current_sl,
            "config": {
                "tp_levels": [
                    {
                        "level": tp.level,
                        "price": tp.price,
                        "percentage": tp.percentage,
                        "status": tp.status.value,
                        "hit_time": tp.hit_time.isoformat() if tp.hit_time else None,
                        "actual_close_price": tp.actual_close_price,
                        "closed_volume": tp.closed_volume
                    } for tp in self.config.tp_levels
                ],
                "sl_shift_mode": self.config.sl_shift_mode.value,
                "sl_shift_buffer_pips": self.config.sl_shift_buffer_pips,
                "min_remaining_volume": self.config.min_remaining_volume,
                "max_slippage_pips": self.config.max_slippage_pips,
                "enable_auto_monitoring": self.config.enable_auto_monitoring,
                "monitoring_interval": self.config.monitoring_interval,
                "expire_after_hours": self.config.expire_after_hours
            },
            "created_time": self.created_time.isoformat(),
            "last_tp_hit": self.last_tp_hit,
            "total_closed_volume": self.total_closed_volume,
            "total_realized_profit": self.total_realized_profit,
            "is_active": self.is_active
        }

@dataclass
class TPHitEvent:
    ticket: int
    tp_level: int
    tp_price: float
    actual_price: float
    closed_volume: float
    remaining_volume: float
    profit: float
    new_sl: Optional[float]
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

class MultiTPManager:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/multi_tp_manager.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Active multi-TP trades
        self.active_trades: Dict[int, MultiTPTrade] = {}
        self.tp_hit_history: List[TPHitEvent] = []
        
        # Module dependencies
        self.mt5_bridge = None
        self.ticket_tracker = None
        self.sl_manager = None
        self.tp_manager = None
        
        # Price monitoring
        self.price_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = 1  # seconds
        
        # Background monitoring
        self.monitoring_task = None
        self.is_monitoring = False
        
        # Load existing trades
        self._load_multi_tp_trades()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load multi-TP manager configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "multi_tp_manager" not in config:
                config["multi_tp_manager"] = {
                    "enabled": True,
                    "default_monitoring_interval": 1.0,
                    "default_sl_shift_mode": "break_even",
                    "default_sl_buffer_pips": 2.0,
                    "default_min_remaining_volume": 0.01,
                    "default_max_slippage_pips": 3.0,
                    "default_expire_hours": 168,
                    "max_tp_levels": 100,
                    "enable_partial_close_notifications": True,
                    "symbol_specific_settings": {
                        "EURUSD": {
                            "min_remaining_volume": 0.01,
                            "max_slippage_pips": 2.0,
                            "sl_buffer_pips": 1.5
                        },
                        "GBPUSD": {
                            "min_remaining_volume": 0.01,
                            "max_slippage_pips": 2.5,
                            "sl_buffer_pips": 2.0
                        },
                        "XAUUSD": {
                            "min_remaining_volume": 0.01,
                            "max_slippage_pips": 10.0,
                            "sl_buffer_pips": 5.0
                        }
                    }
                }
                self._save_config(config)
                
            return config.get("multi_tp_manager", {})
            
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            return self._get_default_config()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "enabled": True,
            "default_monitoring_interval": 1.0,
            "default_sl_shift_mode": "break_even",
            "default_sl_buffer_pips": 2.0,
            "default_min_remaining_volume": 0.01,
            "default_max_slippage_pips": 3.0,
            "default_expire_hours": 168,
            "max_tp_levels": 100,
            "enable_partial_close_notifications": True,
            "symbol_specific_settings": {}
        }
        
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for multi-TP manager"""
        logger = logging.getLogger("multi_tp_manager")
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
        return logger
        
    def _load_multi_tp_trades(self):
        """Load existing multi-TP trades from storage"""
        trades_file = self.log_path.replace('.log', '_trades.json')
        try:
            if os.path.exists(trades_file):
                with open(trades_file, 'r') as f:
                    trades_data = json.load(f)
                    
                for trade_data in trades_data.get('multi_tp_trades', []):
                    # Reconstruct TP levels
                    tp_levels = []
                    for tp_data in trade_data['config']['tp_levels']:
                        tp_level = TPLevel(
                            level=tp_data['level'],
                            price=tp_data['price'],
                            percentage=tp_data['percentage'],
                            status=TPStatus(tp_data['status']) if isinstance(tp_data['status'], str) else tp_data['status'],
                            hit_time=datetime.fromisoformat(tp_data['hit_time']) if tp_data.get('hit_time') else None,
                            actual_close_price=tp_data.get('actual_close_price'),
                            closed_volume=tp_data.get('closed_volume')
                        )
                        tp_levels.append(tp_level)
                    
                    # Reconstruct config
                    config = MultiTPConfig(
                        tp_levels=tp_levels,
                        sl_shift_mode=SLShiftMode(trade_data['config']['sl_shift_mode']),
                        sl_shift_buffer_pips=trade_data['config']['sl_shift_buffer_pips'],
                        min_remaining_volume=trade_data['config']['min_remaining_volume'],
                        max_slippage_pips=trade_data['config']['max_slippage_pips'],
                        enable_auto_monitoring=trade_data['config']['enable_auto_monitoring'],
                        monitoring_interval=trade_data['config']['monitoring_interval'],
                        expire_after_hours=trade_data['config']['expire_after_hours']
                    )
                    
                    # Reconstruct trade
                    trade = MultiTPTrade(
                        ticket=trade_data['ticket'],
                        symbol=trade_data['symbol'],
                        direction=trade_data['direction'],
                        entry_price=trade_data['entry_price'],
                        initial_volume=trade_data['initial_volume'],
                        remaining_volume=trade_data['remaining_volume'],
                        current_sl=trade_data.get('current_sl'),
                        config=config,
                        created_time=datetime.fromisoformat(trade_data['created_time']),
                        last_tp_hit=trade_data.get('last_tp_hit'),
                        total_closed_volume=trade_data.get('total_closed_volume', 0.0),
                        total_realized_profit=trade_data.get('total_realized_profit', 0.0),
                        is_active=trade_data.get('is_active', True)
                    )
                    
                    if trade.is_active:
                        self.active_trades[trade.ticket] = trade
                    
                self.logger.info(f"Loaded {len(self.active_trades)} active multi-TP trades from storage")
                
        except Exception as e:
            self.logger.error(f"Error loading multi-TP trades: {e}")
            
    def _save_multi_tp_trades(self):
        """Save multi-TP trades to storage"""
        trades_file = self.log_path.replace('.log', '_trades.json')
        try:
            trades_data = {
                'multi_tp_trades': [trade.to_dict() for trade in self.active_trades.values()],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(trades_file, 'w') as f:
                json.dump(trades_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error saving multi-TP trades: {e}")
            
    def set_dependencies(self, mt5_bridge=None, ticket_tracker=None, sl_manager=None, tp_manager=None):
        """Set module dependencies"""
        self.mt5_bridge = mt5_bridge
        self.ticket_tracker = ticket_tracker
        self.sl_manager = sl_manager
        self.tp_manager = tp_manager
        
    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol"""
        pip_values = {
            "EURUSD": 0.00001, "GBPUSD": 0.00001, "AUDUSD": 0.00001,
            "NZDUSD": 0.00001, "USDCAD": 0.00001, "USDCHF": 0.00001,
            "USDJPY": 0.001, "EURJPY": 0.001, "GBPJPY": 0.001,
            "EURGBP": 0.00001, "EURAUD": 0.00001, "EURCHF": 0.00001,
            "XAUUSD": 0.01, "XAGUSD": 0.001,
            "BTCUSD": 1.0, "ETHUSD": 0.1
        }
        return pip_values.get(symbol, 0.00001)
        
    def _get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current market price for symbol"""
        try:
            # Check cache first
            if symbol in self.price_cache:
                cached_data, cache_time = self.price_cache[symbol]
                if time.time() - cache_time < self.cache_duration:
                    return cached_data
                    
            if not self.mt5_bridge:
                self.logger.warning("MT5 bridge not available")
                return None
                
            # Get tick data from MT5
            tick_data = self.mt5_bridge.get_symbol_tick(symbol)
            if not tick_data:
                return None
                
            price_data = {
                'symbol': symbol,
                'bid': tick_data.get('bid', 0),
                'ask': tick_data.get('ask', 0),
                'last': tick_data.get('last', 0),
                'time': tick_data.get('time', datetime.now())
            }
            
            # Cache the result
            self.price_cache[symbol] = (price_data, time.time())
            return price_data
            
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return None
            
    def _check_tp_hits(self, trade: MultiTPTrade, current_price_data: Dict[str, Any]) -> List[TPLevel]:
        """Check which TP levels have been hit"""
        if not current_price_data:
            return []
            
        hit_tps = []
        current_price = current_price_data.get('bid' if trade.direction == 'sell' else 'ask', 0)
        
        for tp_level in trade.config.tp_levels:
            if tp_level.status == TPStatus.PENDING:
                # Check if TP has been hit
                if trade.direction == 'buy':
                    if current_price >= tp_level.price:
                        hit_tps.append(tp_level)
                else:  # sell
                    if current_price <= tp_level.price:
                        hit_tps.append(tp_level)
                        
        return hit_tps
        
    def _calculate_close_volume(self, trade: MultiTPTrade, tp_level: TPLevel) -> float:
        """Calculate volume to close for this TP level"""
        # Calculate volume based on percentage of initial position
        volume_to_close = (tp_level.percentage / 100.0) * trade.initial_volume
        
        # Ensure we don't close more than remaining volume
        volume_to_close = min(volume_to_close, trade.remaining_volume)
        
        # Round to broker's minimum lot size (typically 0.01)
        volume_to_close = round(volume_to_close, 2)
        
        return volume_to_close
        
    def _calculate_new_sl(self, trade: MultiTPTrade, hit_tp_level: TPLevel) -> Optional[float]:
        """Calculate new SL position after TP hit"""
        if trade.config.sl_shift_mode == SLShiftMode.NONE:
            return trade.current_sl
            
        pip_value = self._get_pip_value(trade.symbol)
        buffer_pips = trade.config.sl_shift_buffer_pips
        
        if trade.config.sl_shift_mode == SLShiftMode.BREAK_EVEN:
            # Move SL to break-even (entry price) + buffer
            if trade.direction == 'buy':
                return trade.entry_price + (buffer_pips * pip_value)
            else:  # sell
                return trade.entry_price - (buffer_pips * pip_value)
                
        elif trade.config.sl_shift_mode == SLShiftMode.NEXT_TP:
            # Move SL to the next TP level or break-even if no next TP
            next_tp = None
            for tp in trade.config.tp_levels:
                if tp.level > hit_tp_level.level and tp.status == TPStatus.PENDING:
                    if next_tp is None or tp.level < next_tp.level:
                        next_tp = tp
                        
            if next_tp:
                if trade.direction == 'buy':
                    return next_tp.price - (buffer_pips * pip_value)
                else:  # sell
                    return next_tp.price + (buffer_pips * pip_value)
            else:
                # No next TP, move to break-even
                if trade.direction == 'buy':
                    return trade.entry_price + (buffer_pips * pip_value)
                else:  # sell
                    return trade.entry_price - (buffer_pips * pip_value)
                    
        elif trade.config.sl_shift_mode == SLShiftMode.FIXED_DISTANCE:
            # Move SL by fixed distance toward entry
            if trade.current_sl:
                distance = buffer_pips * pip_value
                if trade.direction == 'buy':
                    return trade.current_sl + distance
                else:  # sell
                    return trade.current_sl - distance
                    
        return trade.current_sl
        
    async def _execute_partial_close(self, trade: MultiTPTrade, tp_level: TPLevel, close_price: float) -> bool:
        """Execute partial position closure"""
        try:
            volume_to_close = self._calculate_close_volume(trade, tp_level)
            
            if volume_to_close < trade.config.min_remaining_volume:
                self.logger.warning(f"Volume to close {volume_to_close} below minimum, skipping TP {tp_level.level}")
                return False
                
            # Execute partial close through MT5 bridge
            if self.mt5_bridge:
                close_result = await self.mt5_bridge.partial_close_position(
                    ticket=trade.ticket,
                    volume=volume_to_close,
                    price=close_price,
                    deviation=int(trade.config.max_slippage_pips)
                )
                
                if close_result.get('success', False):
                    # Update TP level status
                    tp_level.status = TPStatus.HIT
                    tp_level.hit_time = datetime.now()
                    tp_level.actual_close_price = close_price
                    tp_level.closed_volume = volume_to_close
                    
                    # Update trade
                    trade.remaining_volume -= volume_to_close
                    trade.total_closed_volume += volume_to_close
                    trade.last_tp_hit = tp_level.level
                    
                    # Calculate profit
                    if trade.direction == 'buy':
                        profit = (close_price - trade.entry_price) * volume_to_close
                    else:  # sell
                        profit = (trade.entry_price - close_price) * volume_to_close
                        
                    trade.total_realized_profit += profit
                    
                    self.logger.info(f"Partial close executed: Ticket {trade.ticket}, TP{tp_level.level}, Volume {volume_to_close}, Profit {profit:.2f}")
                    
                    return True
                else:
                    error_msg = close_result.get('error', 'Unknown error')
                    self.logger.error(f"Failed to execute partial close for ticket {trade.ticket}: {error_msg}")
                    return False
            else:
                self.logger.error("MT5 bridge not available for partial close")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing partial close for ticket {trade.ticket}: {e}")
            return False
            
    async def _update_stop_loss(self, trade: MultiTPTrade, new_sl: float) -> bool:
        """Update stop loss for the trade"""
        try:
            if self.sl_manager:
                success = await self.sl_manager.modify_stop_loss(trade.ticket, new_sl)
            elif self.mt5_bridge:
                result = await self.mt5_bridge.modify_position(trade.ticket, sl=new_sl)
                success = result.get('success', False)
            else:
                self.logger.error("No SL manager or MT5 bridge available")
                return False
                
            if success:
                trade.current_sl = new_sl
                self.logger.info(f"Updated SL for ticket {trade.ticket} to {new_sl}")
                return True
            else:
                self.logger.error(f"Failed to update SL for ticket {trade.ticket}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating SL for ticket {trade.ticket}: {e}")
            return False
            
    async def _process_tp_hits(self, trade: MultiTPTrade, hit_tps: List[TPLevel]):
        """Process all TP hits for a trade"""
        for tp_level in sorted(hit_tps, key=lambda x: x.level):
            try:
                # Get current price for execution
                price_data = self._get_current_price(trade.symbol)
                if not price_data:
                    continue
                    
                close_price = price_data.get('bid' if trade.direction == 'sell' else 'ask', 0)
                
                # Execute partial close
                success = await self._execute_partial_close(trade, tp_level, close_price)
                
                if success:
                    # Calculate and update new SL
                    new_sl = self._calculate_new_sl(trade, tp_level)
                    if new_sl and new_sl != trade.current_sl:
                        await self._update_stop_loss(trade, new_sl)
                    
                    # Log TP hit event
                    volume_closed = self._calculate_close_volume(trade, tp_level)
                    profit = ((close_price - trade.entry_price) if trade.direction == 'buy' 
                             else (trade.entry_price - close_price)) * volume_closed
                    
                    tp_hit_event = TPHitEvent(
                        ticket=trade.ticket,
                        tp_level=tp_level.level,
                        tp_price=tp_level.price,
                        actual_price=close_price,
                        closed_volume=volume_closed,
                        remaining_volume=trade.remaining_volume,
                        profit=profit,
                        new_sl=new_sl,
                        timestamp=datetime.now(),
                        success=True
                    )
                    self.tp_hit_history.append(tp_hit_event)
                    
                    # Check if trade should be deactivated
                    if trade.remaining_volume < trade.config.min_remaining_volume:
                        trade.is_active = False
                        self.logger.info(f"Trade {trade.ticket} deactivated - remaining volume below minimum")
                        
                else:
                    # Log failed TP hit
                    tp_hit_event = TPHitEvent(
                        ticket=trade.ticket,
                        tp_level=tp_level.level,
                        tp_price=tp_level.price,
                        actual_price=close_price,
                        closed_volume=0.0,
                        remaining_volume=trade.remaining_volume,
                        profit=0.0,
                        new_sl=trade.current_sl,
                        timestamp=datetime.now(),
                        success=False,
                        error_message="Partial close execution failed"
                    )
                    self.tp_hit_history.append(tp_hit_event)
                    
            except Exception as e:
                self.logger.error(f"Error processing TP hit for ticket {trade.ticket}, TP{tp_level.level}: {e}")
                
    async def _monitor_multi_tp_trades(self):
        """Background task to monitor multi-TP trades"""
        while self.is_monitoring:
            try:
                if not self.active_trades:
                    await asyncio.sleep(self.config.get('default_monitoring_interval', 1.0))
                    continue
                    
                # Check each active trade
                inactive_trades = []
                
                for ticket, trade in self.active_trades.items():
                    try:
                        if not trade.is_active:
                            inactive_trades.append(ticket)
                            continue
                            
                        # Get current price
                        price_data = self._get_current_price(trade.symbol)
                        if not price_data:
                            continue
                            
                        # Check for TP hits
                        hit_tps = self._check_tp_hits(trade, price_data)
                        
                        if hit_tps:
                            await self._process_tp_hits(trade, hit_tps)
                            
                        # Check if trade expired
                        if trade.config.expire_after_hours > 0:
                            expiry_time = trade.created_time + timedelta(hours=trade.config.expire_after_hours)
                            if datetime.now() > expiry_time:
                                trade.is_active = False
                                inactive_trades.append(ticket)
                                self.logger.info(f"Trade {ticket} expired after {trade.config.expire_after_hours} hours")
                                
                    except Exception as e:
                        self.logger.error(f"Error monitoring trade {ticket}: {e}")
                        
                # Remove inactive trades
                for ticket in inactive_trades:
                    self.active_trades.pop(ticket, None)
                    
                # Save trades after each monitoring cycle
                self._save_multi_tp_trades()
                
                await asyncio.sleep(self.config.get('default_monitoring_interval', 1.0))
                
            except Exception as e:
                self.logger.error(f"Error in multi-TP monitoring loop: {e}")
                await asyncio.sleep(5)  # Prevent tight error loop
                
    def start_monitoring(self):
        """Start background monitoring of multi-TP trades"""
        if not self.config.get('enabled', True):
            self.logger.info("Multi-TP manager is disabled")
            return
            
        if not self.is_monitoring:
            self.is_monitoring = True
            try:
                self.monitoring_task = asyncio.create_task(self._monitor_multi_tp_trades())
                self.logger.info("Multi-TP monitoring started")
            except RuntimeError:
                # No event loop running
                self.is_monitoring = False
                self.logger.warning("No event loop running, cannot start monitoring")
                
    def stop_monitoring(self):
        """Stop background monitoring"""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
            self.logger.info("Multi-TP monitoring stopped")
            
    def add_multi_tp_trade(self, ticket: int, symbol: str, direction: str, entry_price: float,
                          volume: float, tp_levels: List[Dict[str, Any]], 
                          sl_shift_mode: str = "break_even", sl_shift_buffer_pips: float = 2.0,
                          current_sl: Optional[float] = None) -> bool:
        """Add a new multi-TP trade for monitoring"""
        try:
            if ticket in self.active_trades:
                self.logger.warning(f"Trade {ticket} already exists in multi-TP manager")
                return False
                
            # Validate and create TP levels
            tp_level_objects = []
            total_percentage = 0.0
            
            for i, tp_data in enumerate(tp_levels):
                if len(tp_level_objects) >= self.config.get('max_tp_levels', 100):
                    self.logger.warning(f"Maximum TP levels ({self.config.get('max_tp_levels', 100)}) reached")
                    break
                    
                level = tp_data.get('level', i + 1)
                price = tp_data.get('price', 0.0)
                percentage = tp_data.get('percentage', 0.0)
                
                if price <= 0 or percentage <= 0:
                    self.logger.error(f"Invalid TP data: level={level}, price={price}, percentage={percentage}")
                    continue
                    
                total_percentage += percentage
                
                tp_level = TPLevel(
                    level=level,
                    price=price,
                    percentage=percentage
                )
                tp_level_objects.append(tp_level)
                
            if not tp_level_objects:
                self.logger.error("No valid TP levels provided")
                return False
                
            if total_percentage > 100.0:
                self.logger.warning(f"Total TP percentage {total_percentage}% exceeds 100%")
                
            # Get symbol-specific settings
            symbol_settings = self.config.get('symbol_specific_settings', {}).get(symbol, {})
            
            # Create config
            config = MultiTPConfig(
                tp_levels=tp_level_objects,
                sl_shift_mode=SLShiftMode(sl_shift_mode),
                sl_shift_buffer_pips=sl_shift_buffer_pips,
                min_remaining_volume=symbol_settings.get('min_remaining_volume', 
                                                       self.config.get('default_min_remaining_volume', 0.01)),
                max_slippage_pips=symbol_settings.get('max_slippage_pips', 
                                                    self.config.get('default_max_slippage_pips', 3.0)),
                enable_auto_monitoring=True,
                monitoring_interval=self.config.get('default_monitoring_interval', 1.0),
                expire_after_hours=self.config.get('default_expire_hours', 168)
            )
            
            # Create trade
            trade = MultiTPTrade(
                ticket=ticket,
                symbol=symbol,
                direction=direction.lower(),
                entry_price=entry_price,
                initial_volume=volume,
                remaining_volume=volume,
                current_sl=current_sl,
                config=config,
                created_time=datetime.now()
            )
            
            # Add to active trades
            self.active_trades[ticket] = trade
            
            # Start monitoring if not already running
            if not self.is_monitoring:
                self.start_monitoring()
                
            self.logger.info(f"Added multi-TP trade: Ticket {ticket}, {len(tp_level_objects)} TP levels")
            
            # Save trades
            self._save_multi_tp_trades()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding multi-TP trade {ticket}: {e}")
            return False
            
    def remove_multi_tp_trade(self, ticket: int, reason: str = "Manual removal") -> bool:
        """Remove a multi-TP trade from monitoring"""
        try:
            if ticket not in self.active_trades:
                self.logger.warning(f"Trade {ticket} not found in multi-TP manager")
                return False
                
            trade = self.active_trades.pop(ticket)
            trade.is_active = False
            
            self.logger.info(f"Removed multi-TP trade {ticket}: {reason}")
            
            # Save trades
            self._save_multi_tp_trades()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing multi-TP trade {ticket}: {e}")
            return False
            
    def get_trade_info(self, ticket: int) -> Optional[MultiTPTrade]:
        """Get information about a multi-TP trade"""
        return self.active_trades.get(ticket)
        
    def get_active_trades(self) -> Dict[int, MultiTPTrade]:
        """Get all active multi-TP trades"""
        return self.active_trades.copy()
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get multi-TP manager statistics"""
        total_trades = len(self.active_trades)
        total_tp_hits = len(self.tp_hit_history)
        successful_hits = len([h for h in self.tp_hit_history if h.success])
        
        total_profit = sum(trade.total_realized_profit for trade in self.active_trades.values())
        
        return {
            "active_trades": total_trades,
            "total_tp_hits": total_tp_hits,
            "successful_tp_hits": successful_hits,
            "tp_hit_success_rate": (successful_hits / total_tp_hits * 100) if total_tp_hits > 0 else 0.0,
            "total_realized_profit": total_profit,
            "monitoring_active": self.is_monitoring
        }
        
    def get_recent_tp_hits(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent TP hit events"""
        recent = sorted(self.tp_hit_history, key=lambda x: x.timestamp, reverse=True)[:limit]
        return [asdict(hit) for hit in recent]

# Global instance for easy access
multi_tp_manager = MultiTPManager()