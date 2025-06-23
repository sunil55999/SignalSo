"""
Trigger Pending Order Engine for SignalOS
Monitors market conditions and triggers pending orders when prices reach specified levels
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

class OrderType(Enum):
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"
    BUY_STOP = "buy_stop"
    SELL_STOP = "sell_stop"

class OrderStatus(Enum):
    PENDING = "pending"
    TRIGGERED = "triggered"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"

class TriggerMode(Enum):
    AUTO = "auto"
    MANUAL = "manual"
    DISABLED = "disabled"

@dataclass
class PendingOrder:
    order_id: str
    signal_id: str
    symbol: str
    order_type: OrderType
    trigger_price: float
    volume: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    slippage_pips: float
    expiry_time: Optional[datetime]
    status: OrderStatus
    created_time: datetime
    provider_id: Optional[str] = None
    provider_name: Optional[str] = None
    comment: Optional[str] = None
    triggered_time: Optional[datetime] = None
    triggered_price: Optional[float] = None
    mt5_ticket: Optional[int] = None
    attempts: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "order_type": self.order_type.value,
            "trigger_price": self.trigger_price,
            "volume": self.volume,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "slippage_pips": self.slippage_pips,
            "expiry_time": self.expiry_time.isoformat() if self.expiry_time else None,
            "status": self.status.value,
            "created_time": self.created_time.isoformat(),
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "comment": self.comment,
            "triggered_time": self.triggered_time.isoformat() if self.triggered_time else None,
            "triggered_price": self.triggered_price,
            "mt5_ticket": self.mt5_ticket,
            "attempts": self.attempts,
            "last_error": self.last_error
        }

@dataclass
class TriggerEvent:
    order_id: str
    signal_id: str
    symbol: str
    trigger_price: float
    market_price: float
    slippage_pips: float
    execution_time: datetime
    success: bool
    mt5_ticket: Optional[int] = None
    error_message: Optional[str] = None

class TriggerPendingOrder:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/pending_orders.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Pending orders storage
        self.pending_orders: Dict[str, PendingOrder] = {}
        self.trigger_history: List[TriggerEvent] = []
        
        # Module dependencies
        self.mt5_bridge = None
        self.spread_checker = None
        self.ticket_tracker = None
        self.retry_engine = None
        
        # Price monitoring
        self.price_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = 1  # seconds
        
        # Background monitoring
        self.monitoring_task = None
        self.is_monitoring = False
        
        # Load existing orders
        self._load_pending_orders()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load trigger pending order configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "trigger_pending_order" not in config:
                config["trigger_pending_order"] = {
                    "enabled": True,
                    "default_mode": "auto",
                    "price_check_interval": 1.0,
                    "max_slippage_pips": 3.0,
                    "max_trigger_attempts": 3,
                    "order_expiry_hours": 168,  # 7 days
                    "cleanup_expired_hours": 24,
                    "enable_notifications": True,
                    "symbol_specific_settings": {
                        "EURUSD": {
                            "max_slippage_pips": 2.0,
                            "price_check_interval": 0.5
                        },
                        "GBPUSD": {
                            "max_slippage_pips": 2.5,
                            "price_check_interval": 0.5
                        },
                        "XAUUSD": {
                            "max_slippage_pips": 10.0,
                            "price_check_interval": 1.0
                        }
                    }
                }
                self._save_config(config)
                
            return config.get("trigger_pending_order", {})
            
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
            "default_mode": "auto",
            "price_check_interval": 1.0,
            "max_slippage_pips": 3.0,
            "max_trigger_attempts": 3,
            "order_expiry_hours": 168,
            "cleanup_expired_hours": 24,
            "enable_notifications": True,
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
        """Setup dedicated logger for pending orders"""
        logger = logging.getLogger("trigger_pending_order")
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
        
    def _load_pending_orders(self):
        """Load existing pending orders from storage"""
        orders_file = self.log_path.replace('.log', '_orders.json')
        try:
            if os.path.exists(orders_file):
                with open(orders_file, 'r') as f:
                    orders_data = json.load(f)
                    
                for order_data in orders_data.get('pending_orders', []):
                    order = PendingOrder(
                        order_id=order_data['order_id'],
                        signal_id=order_data['signal_id'],
                        symbol=order_data['symbol'],
                        order_type=OrderType(order_data['order_type']),
                        trigger_price=order_data['trigger_price'],
                        volume=order_data['volume'],
                        stop_loss=order_data.get('stop_loss'),
                        take_profit=order_data.get('take_profit'),
                        slippage_pips=order_data['slippage_pips'],
                        expiry_time=datetime.fromisoformat(order_data['expiry_time']) if order_data.get('expiry_time') else None,
                        status=OrderStatus(order_data['status']),
                        created_time=datetime.fromisoformat(order_data['created_time']),
                        provider_id=order_data.get('provider_id'),
                        provider_name=order_data.get('provider_name'),
                        comment=order_data.get('comment'),
                        triggered_time=datetime.fromisoformat(order_data['triggered_time']) if order_data.get('triggered_time') else None,
                        triggered_price=order_data.get('triggered_price'),
                        mt5_ticket=order_data.get('mt5_ticket'),
                        attempts=order_data.get('attempts', 0),
                        last_error=order_data.get('last_error')
                    )
                    self.pending_orders[order.order_id] = order
                    
                self.logger.info(f"Loaded {len(self.pending_orders)} pending orders from storage")
                
        except Exception as e:
            self.logger.error(f"Error loading pending orders: {e}")
            
    def _save_pending_orders(self):
        """Save pending orders to storage"""
        orders_file = self.log_path.replace('.log', '_orders.json')
        try:
            orders_data = {
                'pending_orders': [order.to_dict() for order in self.pending_orders.values()],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(orders_file, 'w') as f:
                json.dump(orders_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error saving pending orders: {e}")
            
    def set_dependencies(self, mt5_bridge=None, spread_checker=None, ticket_tracker=None, retry_engine=None):
        """Set module dependencies"""
        self.mt5_bridge = mt5_bridge
        self.spread_checker = spread_checker
        self.ticket_tracker = ticket_tracker
        self.retry_engine = retry_engine
        
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
            
    def _should_trigger_order(self, order: PendingOrder, current_price_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if order should be triggered based on current price"""
        if not current_price_data:
            return False, "No price data available"
            
        # Check if order is expired
        if order.expiry_time and datetime.now() > order.expiry_time:
            return False, "Order expired"
            
        # Get appropriate price for comparison
        current_price = 0
        if order.order_type in [OrderType.BUY_LIMIT, OrderType.BUY_STOP]:
            current_price = current_price_data.get('ask', 0)
        else:  # SELL_LIMIT, SELL_STOP
            current_price = current_price_data.get('bid', 0)
            
        if current_price == 0:
            return False, "Invalid price data"
            
        # Check trigger conditions based on order type
        pip_value = self._get_pip_value(order.symbol)
        slippage_tolerance = order.slippage_pips * pip_value
        
        trigger_met = False
        reason = ""
        
        if order.order_type == OrderType.BUY_LIMIT:
            # BUY LIMIT triggers when price drops to or below trigger price
            if current_price <= (order.trigger_price + slippage_tolerance):
                trigger_met = True
                reason = f"BUY LIMIT triggered: price {current_price} <= {order.trigger_price} + slippage"
                
        elif order.order_type == OrderType.SELL_LIMIT:
            # SELL LIMIT triggers when price rises to or above trigger price
            if current_price >= (order.trigger_price - slippage_tolerance):
                trigger_met = True
                reason = f"SELL LIMIT triggered: price {current_price} >= {order.trigger_price} - slippage"
                
        elif order.order_type == OrderType.BUY_STOP:
            # BUY STOP triggers when price rises to or above trigger price
            if current_price >= (order.trigger_price - slippage_tolerance):
                trigger_met = True
                reason = f"BUY STOP triggered: price {current_price} >= {order.trigger_price} - slippage"
                
        elif order.order_type == OrderType.SELL_STOP:
            # SELL STOP triggers when price drops to or below trigger price
            if current_price <= (order.trigger_price + slippage_tolerance):
                trigger_met = True
                reason = f"SELL STOP triggered: price {current_price} <= {order.trigger_price} + slippage"
                
        return trigger_met, reason
        
    async def _execute_pending_order(self, order: PendingOrder, trigger_price: float, reason: str) -> bool:
        """Execute a triggered pending order"""
        try:
            if not self.mt5_bridge:
                self.logger.error("MT5 bridge not available for order execution")
                return False
                
            # Determine order action
            action = "BUY" if order.order_type in [OrderType.BUY_LIMIT, OrderType.BUY_STOP] else "SELL"
            
            # Prepare trade request
            trade_request = {
                'symbol': order.symbol,
                'action': action,
                'volume': order.volume,
                'price': trigger_price,
                'sl': order.stop_loss,
                'tp': order.take_profit,
                'type': 'market',
                'comment': f"Triggered: {order.comment or order.signal_id}",
                'deviation': int(order.slippage_pips)
            }
            
            # Execute trade through MT5 bridge
            result = await self.mt5_bridge.execute_trade(trade_request)
            
            if result.get('success', False):
                # Update order status
                order.status = OrderStatus.TRIGGERED
                order.triggered_time = datetime.now()
                order.triggered_price = trigger_price
                order.mt5_ticket = result.get('ticket')
                
                # Register with ticket tracker if available
                if self.ticket_tracker and order.mt5_ticket:
                    self.ticket_tracker.register_trade_ticket(
                        ticket=order.mt5_ticket,
                        symbol=order.symbol,
                        direction=action.lower(),
                        entry_price=trigger_price,
                        lot_size=order.volume,
                        stop_loss=order.stop_loss,
                        take_profit=order.take_profit,
                        provider_id=order.provider_id or "pending_order",
                        provider_name=order.provider_name or "Pending Order System",
                        signal_content=f"Triggered pending order: {order.signal_id}"
                    )
                
                # Log trigger event
                trigger_event = TriggerEvent(
                    order_id=order.order_id,
                    signal_id=order.signal_id,
                    symbol=order.symbol,
                    trigger_price=order.trigger_price,
                    market_price=trigger_price,
                    slippage_pips=order.slippage_pips,
                    execution_time=datetime.now(),
                    success=True,
                    mt5_ticket=order.mt5_ticket
                )
                self.trigger_history.append(trigger_event)
                
                self.logger.info(f"Pending order executed: {order.order_id} -> ticket {order.mt5_ticket} ({reason})")
                return True
                
            else:
                error_msg = result.get('error', 'Unknown error')
                order.last_error = error_msg
                order.attempts += 1
                
                # Log failed trigger event
                trigger_event = TriggerEvent(
                    order_id=order.order_id,
                    signal_id=order.signal_id,
                    symbol=order.symbol,
                    trigger_price=order.trigger_price,
                    market_price=trigger_price,
                    slippage_pips=order.slippage_pips,
                    execution_time=datetime.now(),
                    success=False,
                    error_message=error_msg
                )
                self.trigger_history.append(trigger_event)
                
                self.logger.error(f"Failed to execute pending order {order.order_id}: {error_msg}")
                
                # Mark as failed if max attempts reached
                if order.attempts >= self.config.get('max_trigger_attempts', 3):
                    order.status = OrderStatus.FAILED
                    self.logger.warning(f"Pending order {order.order_id} marked as failed after {order.attempts} attempts")
                    
                return False
                
        except Exception as e:
            order.last_error = str(e)
            order.attempts += 1
            self.logger.error(f"Error executing pending order {order.order_id}: {e}")
            return False
            
    async def _monitor_pending_orders(self):
        """Background task to monitor pending orders"""
        while self.is_monitoring:
            try:
                if not self.pending_orders:
                    await asyncio.sleep(self.config.get('price_check_interval', 1.0))
                    continue
                    
                # Get unique symbols for price checking
                symbols = set(order.symbol for order in self.pending_orders.values() 
                            if order.status == OrderStatus.PENDING)
                
                # Check each symbol's price
                for symbol in symbols:
                    try:
                        price_data = self._get_current_price(symbol)
                        if not price_data:
                            continue
                            
                        # Check all pending orders for this symbol
                        symbol_orders = [order for order in self.pending_orders.values() 
                                       if order.symbol == symbol and order.status == OrderStatus.PENDING]
                        
                        for order in symbol_orders:
                            should_trigger, reason = self._should_trigger_order(order, price_data)
                            
                            if should_trigger:
                                # Check spread if spread checker is available
                                if self.spread_checker:
                                    spread_result, _ = self.spread_checker.check_spread_before_trade(symbol)
                                    if spread_result.value in ["blocked_high_spread", "blocked_no_quotes", "blocked_stale_quotes"]:
                                        self.logger.warning(f"Pending order {order.order_id} trigger delayed due to spread: {spread_result.value}")
                                        continue
                                
                                # Execute the order
                                trigger_price = price_data.get('ask' if order.order_type in [OrderType.BUY_LIMIT, OrderType.BUY_STOP] else 'bid', 0)
                                success = await self._execute_pending_order(order, trigger_price, reason)
                                
                                if success:
                                    # Remove from pending orders
                                    self.pending_orders.pop(order.order_id, None)
                                    
                    except Exception as e:
                        self.logger.error(f"Error monitoring symbol {symbol}: {e}")
                        
                # Cleanup expired orders
                self._cleanup_expired_orders()
                
                # Save orders after each monitoring cycle
                self._save_pending_orders()
                
                await asyncio.sleep(self.config.get('price_check_interval', 1.0))
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(1)  # Prevent tight error loop
                
    def _cleanup_expired_orders(self):
        """Clean up expired orders"""
        now = datetime.now()
        expired_orders = []
        
        for order_id, order in self.pending_orders.items():
            if order.expiry_time and now > order.expiry_time:
                order.status = OrderStatus.EXPIRED
                expired_orders.append(order_id)
                
        for order_id in expired_orders:
            order = self.pending_orders.pop(order_id, None)
            if order:
                self.logger.info(f"Expired pending order removed: {order_id}")
                
    def start_monitoring(self):
        """Start background monitoring of pending orders"""
        if not self.config.get('enabled', True):
            self.logger.info("Pending order monitoring is disabled")
            return
            
        if not self.is_monitoring:
            self.is_monitoring = True
            try:
                self.monitoring_task = asyncio.create_task(self._monitor_pending_orders())
                self.logger.info("Pending order monitoring started")
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
            self.logger.info("Pending order monitoring stopped")
            
    def add_pending_order(self, signal_id: str, symbol: str, order_type: OrderType,
                         trigger_price: float, volume: float, stop_loss: Optional[float] = None,
                         take_profit: Optional[float] = None, slippage_pips: float = None,
                         expiry_hours: int = None, provider_id: str = None,
                         provider_name: str = None, comment: str = None) -> str:
        """Add a new pending order"""
        try:
            # Generate unique order ID
            order_id = f"PO_{symbol}_{int(time.time())}_{len(self.pending_orders)}"
            
            # Set defaults
            if slippage_pips is None:
                symbol_settings = self.config.get('symbol_specific_settings', {}).get(symbol, {})
                slippage_pips = symbol_settings.get('max_slippage_pips', self.config.get('max_slippage_pips', 3.0))
                
            if expiry_hours is None:
                expiry_hours = self.config.get('order_expiry_hours', 168)
                
            expiry_time = datetime.now() + timedelta(hours=expiry_hours) if expiry_hours > 0 else None
            
            # Create pending order
            order = PendingOrder(
                order_id=order_id,
                signal_id=signal_id,
                symbol=symbol,
                order_type=order_type,
                trigger_price=trigger_price,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                slippage_pips=slippage_pips,
                expiry_time=expiry_time,
                status=OrderStatus.PENDING,
                created_time=datetime.now(),
                provider_id=provider_id,
                provider_name=provider_name,
                comment=comment
            )
            
            # Add to pending orders
            self.pending_orders[order_id] = order
            
            # Start monitoring if not already running
            if not self.is_monitoring:
                self.start_monitoring()
                
            self.logger.info(f"Added pending order: {order_id} for {symbol} {order_type.value} @ {trigger_price}")
            
            # Save orders
            self._save_pending_orders()
            
            return order_id
            
        except Exception as e:
            self.logger.error(f"Error adding pending order: {e}")
            return ""
            
    def cancel_pending_order(self, order_id: str, reason: str = "Manual cancellation") -> bool:
        """Cancel a pending order"""
        try:
            if order_id not in self.pending_orders:
                self.logger.warning(f"Pending order not found: {order_id}")
                return False
                
            order = self.pending_orders[order_id]
            if order.status != OrderStatus.PENDING:
                self.logger.warning(f"Cannot cancel order {order_id} with status {order.status.value}")
                return False
                
            order.status = OrderStatus.CANCELLED
            order.last_error = reason
            
            # Remove from active monitoring
            self.pending_orders.pop(order_id, None)
            
            self.logger.info(f"Cancelled pending order: {order_id} - {reason}")
            
            # Save orders
            self._save_pending_orders()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling pending order {order_id}: {e}")
            return False
            
    def manual_trigger_order(self, order_id: str, reason: str = "Manual trigger") -> bool:
        """Manually trigger a pending order"""
        try:
            if order_id not in self.pending_orders:
                self.logger.warning(f"Pending order not found: {order_id}")
                return False
                
            order = self.pending_orders[order_id]
            if order.status != OrderStatus.PENDING:
                self.logger.warning(f"Cannot trigger order {order_id} with status {order.status.value}")
                return False
                
            # Get current price
            price_data = self._get_current_price(order.symbol)
            if not price_data:
                self.logger.error(f"Cannot get price data for manual trigger: {order_id}")
                return False
                
            trigger_price = price_data.get('ask' if order.order_type in [OrderType.BUY_LIMIT, OrderType.BUY_STOP] else 'bid', 0)
            
            # Execute the order
            async def execute():
                return await self._execute_pending_order(order, trigger_price, reason)
                
            # Run in event loop or create one
            try:
                success = asyncio.run(execute())
            except RuntimeError:
                # Event loop already running
                success = False
                self.logger.error("Cannot execute manual trigger in running event loop")
                
            if success:
                self.pending_orders.pop(order_id, None)
                self._save_pending_orders()
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error manually triggering order {order_id}: {e}")
            return False
            
    def get_pending_orders(self, symbol: str = None, status: OrderStatus = None) -> List[PendingOrder]:
        """Get pending orders with optional filtering"""
        orders = list(self.pending_orders.values())
        
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
            
        if status:
            orders = [order for order in orders if order.status == status]
            
        return orders
        
    def get_order_info(self, order_id: str) -> Optional[PendingOrder]:
        """Get information about a specific order"""
        return self.pending_orders.get(order_id)
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get pending order statistics"""
        total_orders = len(self.pending_orders)
        pending_count = len([o for o in self.pending_orders.values() if o.status == OrderStatus.PENDING])
        triggered_count = len(self.trigger_history)
        successful_triggers = len([e for e in self.trigger_history if e.success])
        
        return {
            "total_pending_orders": total_orders,
            "active_pending": pending_count,
            "total_triggered": triggered_count,
            "successful_triggers": successful_triggers,
            "trigger_success_rate": (successful_triggers / triggered_count * 100) if triggered_count > 0 else 0.0,
            "monitoring_active": self.is_monitoring
        }

# Global instance for easy access
trigger_pending_order = TriggerPendingOrder()