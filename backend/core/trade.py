"""
Trading execution engine with MT5 integration
"""

import asyncio
import socket
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

from services.parser_ai import ParsedSignal, SignalType
from utils.logging_config import get_logger

logger = get_logger("trade")


class OrderType(Enum):
    """MT5 Order types"""
    BUY = 0
    SELL = 1
    BUY_LIMIT = 2
    SELL_LIMIT = 3
    BUY_STOP = 4
    SELL_STOP = 5


class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


@dataclass
class TradeOrder:
    """Trade order data structure"""
    id: str
    symbol: str
    order_type: OrderType
    volume: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    deviation: int = 10
    magic_number: int = 12345
    comment: str = "SignalOS"
    status: OrderStatus = OrderStatus.PENDING
    ticket: Optional[int] = None
    executed_price: Optional[float] = None
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['order_type'] = self.order_type.value
        data['status'] = self.status.value
        data['executed_at'] = self.executed_at.isoformat() if self.executed_at else None
        return data


class MT5Bridge:
    """MT5 communication bridge via socket"""
    
    def __init__(self, host: str = "localhost", port: int = 9999, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Connect to MT5 bridge"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            
            # Use asyncio to make it non-blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.socket.connect, (self.host, self.port))
            
            self.is_connected = True
            logger.info(f"Connected to MT5 bridge at {self.host}:{self.port}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MT5 bridge: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from MT5 bridge"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            finally:
                self.socket = None
                self.is_connected = False
                logger.info("Disconnected from MT5 bridge")
    
    async def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to MT5 and get response"""
        if not self.is_connected:
            raise ConnectionError("Not connected to MT5 bridge")
        
        try:
            # Serialize command
            command_str = json.dumps(command) + "\n"
            command_bytes = command_str.encode('utf-8')
            
            # Send command
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.socket.sendall, command_bytes)
            
            # Receive response
            response_bytes = await loop.run_in_executor(None, self._receive_response)
            response_str = response_bytes.decode('utf-8')
            
            # Parse response
            response = json.loads(response_str)
            
            logger.debug(f"MT5 command: {command['action']} -> {response.get('status', 'unknown')}")
            
            return response
            
        except Exception as e:
            logger.error(f"MT5 command error: {e}")
            raise
    
    def _receive_response(self) -> bytes:
        """Receive response from socket"""
        response = b""
        while True:
            chunk = self.socket.recv(1024)
            if not chunk:
                break
            response += chunk
            if b"\n" in response:
                break
        return response.rstrip(b"\n")
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information"""
        command = {
            "action": "symbol_info",
            "symbol": symbol
        }
        return await self.send_command(command)
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        command = {
            "action": "account_info"
        }
        return await self.send_command(command)
    
    async def open_position(self, order: TradeOrder) -> Dict[str, Any]:
        """Open trading position"""
        command = {
            "action": "open_position",
            "symbol": order.symbol,
            "order_type": order.order_type.value,
            "volume": order.volume,
            "price": order.price,
            "stop_loss": order.stop_loss,
            "take_profit": order.take_profit,
            "deviation": order.deviation,
            "magic": order.magic_number,
            "comment": order.comment
        }
        return await self.send_command(command)
    
    async def close_position(self, ticket: int) -> Dict[str, Any]:
        """Close trading position"""
        command = {
            "action": "close_position",
            "ticket": ticket
        }
        return await self.send_command(command)
    
    async def modify_position(self, ticket: int, stop_loss: float = None, 
                             take_profit: float = None) -> Dict[str, Any]:
        """Modify trading position"""
        command = {
            "action": "modify_position",
            "ticket": ticket,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
        return await self.send_command(command)


class RiskManager:
    """Risk management for trading operations"""
    
    def __init__(self):
        self.max_daily_trades = 50
        self.max_risk_per_trade = 0.02  # 2%
        self.max_total_risk = 0.10  # 10%
        self.min_lot_size = 0.01
        self.max_lot_size = 10.0
        
        self.daily_trade_count = 0
        self.daily_reset_date = datetime.now().date()
    
    def check_daily_limit(self) -> bool:
        """Check if daily trade limit is exceeded"""
        current_date = datetime.now().date()
        
        # Reset counter if new day
        if current_date > self.daily_reset_date:
            self.daily_trade_count = 0
            self.daily_reset_date = current_date
        
        return self.daily_trade_count < self.max_daily_trades
    
    def calculate_position_size(self, account_balance: float, entry_price: float, 
                               stop_loss: float, risk_percentage: float = None) -> float:
        """Calculate appropriate position size based on risk"""
        if risk_percentage is None:
            risk_percentage = self.max_risk_per_trade
        
        # Calculate risk amount
        risk_amount = account_balance * risk_percentage
        
        # Calculate pip value (simplified for major pairs)
        pip_risk = abs(entry_price - stop_loss)
        if pip_risk == 0:
            return self.min_lot_size
        
        # Calculate lot size
        lot_size = risk_amount / (pip_risk * 10)  # Simplified calculation
        
        # Apply limits
        lot_size = max(self.min_lot_size, min(lot_size, self.max_lot_size))
        
        return round(lot_size, 2)
    
    def validate_trade(self, order: TradeOrder, account_info: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate trade before execution"""
        
        # Check daily limit
        if not self.check_daily_limit():
            return False, "Daily trade limit exceeded"
        
        # Check lot size
        if order.volume < self.min_lot_size or order.volume > self.max_lot_size:
            return False, f"Invalid lot size: {order.volume}"
        
        # Check account balance
        balance = account_info.get("balance", 0)
        if balance <= 0:
            return False, "Insufficient account balance"
        
        # Check margin requirements (simplified)
        required_margin = order.volume * 1000  # Simplified calculation
        free_margin = account_info.get("margin_free", 0)
        
        if required_margin > free_margin:
            return False, "Insufficient margin"
        
        return True, "Trade validated successfully"


class TradeExecutor:
    """Main trade execution engine"""
    
    def __init__(self):
        self.mt5_bridge = MT5Bridge()
        self.risk_manager = RiskManager()
        self.active_orders: Dict[str, TradeOrder] = {}
        self.execution_stats = {
            "total_orders": 0,
            "successful_orders": 0,
            "failed_orders": 0,
            "total_volume": 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize the trade executor"""
        try:
            # Connect to MT5 bridge
            connected = await self.mt5_bridge.connect()
            if not connected:
                logger.error("Failed to connect to MT5 bridge")
                return False
            
            # Test connection with account info
            account_info = await self.mt5_bridge.get_account_info()
            logger.info(f"Connected to MT5 account: {account_info.get('login', 'unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Trade executor initialization failed: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the trade executor"""
        await self.mt5_bridge.disconnect()
        logger.info("Trade executor shutdown complete")
    
    async def execute_signal(self, signal: ParsedSignal) -> TradeOrder:
        """Execute trading signal"""
        try:
            # Create order from signal
            order = await self._create_order_from_signal(signal)
            
            # Validate trade
            account_info = await self.mt5_bridge.get_account_info()
            is_valid, validation_message = self.risk_manager.validate_trade(order, account_info)
            
            if not is_valid:
                order.status = OrderStatus.FAILED
                order.error_message = validation_message
                logger.warning(f"Trade validation failed: {validation_message}")
                return order
            
            # Execute the order
            order.status = OrderStatus.EXECUTING
            self.active_orders[order.id] = order
            
            # Send to MT5
            result = await self.mt5_bridge.open_position(order)
            
            if result.get("status") == "success":
                order.status = OrderStatus.EXECUTED
                order.ticket = result.get("ticket")
                order.executed_price = result.get("price")
                order.executed_at = datetime.utcnow()
                
                # Update stats
                self.execution_stats["successful_orders"] += 1
                self.execution_stats["total_volume"] += order.volume
                self.risk_manager.daily_trade_count += 1
                
                logger.info(f"Order executed successfully: {order.symbol} {order.order_type.name}")
            else:
                order.status = OrderStatus.FAILED
                order.error_message = result.get("error", "Unknown error")
                self.execution_stats["failed_orders"] += 1
                
                logger.error(f"Order execution failed: {order.error_message}")
            
            self.execution_stats["total_orders"] += 1
            
            return order
            
        except Exception as e:
            logger.error(f"Signal execution error: {e}")
            
            # Create failed order
            order = TradeOrder(
                id=f"FAILED_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                symbol=signal.symbol,
                order_type=OrderType.BUY if signal.signal_type == SignalType.BUY else OrderType.SELL,
                volume=0.01,
                status=OrderStatus.FAILED,
                error_message=str(e)
            )
            
            return order
    
    async def _create_order_from_signal(self, signal: ParsedSignal) -> TradeOrder:
        """Create trade order from parsed signal"""
        
        # Determine order type
        if signal.signal_type == SignalType.BUY:
            order_type = OrderType.BUY
        elif signal.signal_type == SignalType.SELL:
            order_type = OrderType.SELL
        else:
            raise ValueError(f"Invalid signal type: {signal.signal_type}")
        
        # Get account info for position sizing
        account_info = await self.mt5_bridge.get_account_info()
        account_balance = account_info.get("balance", 10000)  # Default fallback
        
        # Calculate position size
        if signal.entry_price and signal.stop_loss:
            volume = self.risk_manager.calculate_position_size(
                account_balance, signal.entry_price, signal.stop_loss
            )
        else:
            volume = 0.01  # Default minimum
        
        # Create order
        order_id = f"SIG_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        order = TradeOrder(
            id=order_id,
            symbol=signal.symbol,
            order_type=order_type,
            volume=volume,
            price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit[0] if signal.take_profit else None,
            comment=f"SignalOS {signal.parsing_method}"
        )
        
        return order
    
    async def close_order(self, order_id: str) -> bool:
        """Close an active order"""
        try:
            order = self.active_orders.get(order_id)
            if not order or not order.ticket:
                logger.warning(f"Order {order_id} not found or not executed")
                return False
            
            result = await self.mt5_bridge.close_position(order.ticket)
            
            if result.get("status") == "success":
                order.status = OrderStatus.CANCELLED
                logger.info(f"Order {order_id} closed successfully")
                return True
            else:
                logger.error(f"Failed to close order {order_id}: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error closing order {order_id}: {e}")
            return False
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        stats = self.execution_stats.copy()
        
        if stats["total_orders"] > 0:
            stats["success_rate"] = stats["successful_orders"] / stats["total_orders"]
        else:
            stats["success_rate"] = 0.0
        
        stats["active_orders_count"] = len(self.active_orders)
        stats["daily_trades_remaining"] = self.risk_manager.max_daily_trades - self.risk_manager.daily_trade_count
        
        return stats
    
    def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get list of active orders"""
        return [order.to_dict() for order in self.active_orders.values()]