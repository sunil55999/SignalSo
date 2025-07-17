#!/usr/bin/env python3
"""
MT5 Socket Bridge for SignalOS Desktop Application

Implements MT4/MT5 trade execution via socket communication and Python API.
Provides reliable connection management and trade execution capabilities.
"""

import asyncio
import json
import logging
import socket
import struct
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logging.warning("MetaTrader5 library not available")

class TradeOperation(Enum):
    """Trade operation types"""
    BUY = "buy"
    SELL = "sell"
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"
    BUY_STOP = "buy_stop"
    SELL_STOP = "sell_stop"
    CLOSE = "close"
    MODIFY = "modify"

class OrderType(Enum):
    """MT5 order types"""
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5

@dataclass
class TradeRequest:
    """Trade request structure"""
    action: str
    symbol: str
    volume: float
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    deviation: int = 10
    magic: int = 0
    comment: str = "SignalOS"
    type_time: int = 0  # Good till cancelled
    expiration: Optional[datetime] = None

@dataclass
class TradeResult:
    """Trade execution result"""
    success: bool
    order_id: Optional[int] = None
    deal_id: Optional[int] = None
    position_id: Optional[int] = None
    volume: float = 0.0
    price: float = 0.0
    error_code: int = 0
    error_message: str = ""
    execution_time: Optional[datetime] = None

@dataclass
class AccountInfo:
    """MT5 account information"""
    login: int
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    profit: float
    currency: str
    server: str
    company: str

class MT5SocketBridge:
    """MT5 trade execution bridge with socket and API support"""
    
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/mt5_bridge.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Connection settings
        self.mt5_path = self.config.get("mt5_path", "")
        self.login = self.config.get("login", 0)
        self.password = self.config.get("password", "")
        self.server = self.config.get("server", "")
        
        # Socket server settings
        self.socket_enabled = self.config.get("socket_enabled", True)
        self.socket_host = self.config.get("socket_host", "localhost")
        self.socket_port = self.config.get("socket_port", 9090)
        
        # Connection state
        self.is_connected = False
        self.last_connection_check = None
        self.connection_retry_count = 0
        self.max_retry_attempts = self.config.get("max_retry_attempts", 5)
        
        # Socket server
        self.socket_server = None
        self.socket_clients = []
        self.server_task = None
        
        # Statistics
        self.stats = {
            "total_trades": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "connection_attempts": 0,
            "last_trade_time": None,
            "trades_by_symbol": {},
            "trades_by_type": {}
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Load MT5 bridge configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('mt5_bridge', self._get_default_config())
        except FileNotFoundError:
            return self._create_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default MT5 configuration"""
        return {
            "enabled": True,
            "mt5_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
            "login": 0,
            "password": "",
            "server": "",
            "timeout": 10000,
            "socket_enabled": True,
            "socket_host": "localhost",
            "socket_port": 9090,
            "max_retry_attempts": 5,
            "retry_delay": 5,
            "connection_check_interval": 30,
            "default_deviation": 10,
            "default_magic": 12345,
            "max_slippage": 3,
            "enable_logging": True
        }
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration and save to file"""
        default_config = {
            "mt5_bridge": self._get_default_config()
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
            
        return default_config["mt5_bridge"]
    
    def _setup_logging(self):
        """Setup logging for MT5 bridge"""
        self.logger = logging.getLogger('MT5SocketBridge')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # Ensure log directory exists
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            # File handler
            file_handler = logging.FileHandler(self.log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
    
    def connect(self) -> bool:
        """Connect to MT5 terminal"""
        if not MT5_AVAILABLE:
            self.logger.error("MetaTrader5 library not available")
            return False
        
        try:
            self.stats["connection_attempts"] += 1
            
            # Initialize MT5 connection
            if self.mt5_path:
                if not mt5.initialize(path=self.mt5_path):
                    self.logger.error(f"MT5 initialize failed: {mt5.last_error()}")
                    return False
            else:
                if not mt5.initialize():
                    self.logger.error(f"MT5 initialize failed: {mt5.last_error()}")
                    return False
            
            # Login if credentials provided
            if self.login and self.password and self.server:
                authorized = mt5.login(self.login, password=self.password, server=self.server)
                if not authorized:
                    self.logger.error(f"MT5 login failed: {mt5.last_error()}")
                    mt5.shutdown()
                    return False
            
            # Test connection
            account_info = mt5.account_info()
            if account_info is None:
                self.logger.error("Failed to get account info")
                mt5.shutdown()
                return False
            
            self.is_connected = True
            self.last_connection_check = datetime.now()
            self.connection_retry_count = 0
            
            self.logger.info(f"Connected to MT5: {account_info.login}@{account_info.server}")
            return True
            
        except Exception as e:
            self.logger.error(f"MT5 connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MT5 terminal"""
        try:
            if MT5_AVAILABLE and self.is_connected:
                mt5.shutdown()
                self.is_connected = False
                self.logger.info("Disconnected from MT5")
        except Exception as e:
            self.logger.error(f"MT5 disconnect error: {e}")
    
    def check_connection(self) -> bool:
        """Check if MT5 connection is still active"""
        if not MT5_AVAILABLE:
            return False
        
        try:
            if not self.is_connected:
                return False
            
            # Check if we can get account info
            account_info = mt5.account_info()
            if account_info is None:
                self.is_connected = False
                return False
            
            self.last_connection_check = datetime.now()
            return True
            
        except Exception as e:
            self.logger.error(f"Connection check error: {e}")
            self.is_connected = False
            return False
    
    def get_account_info(self) -> Optional[AccountInfo]:
        """Get MT5 account information"""
        if not self.check_connection():
            return None
        
        try:
            info = mt5.account_info()
            if info is None:
                return None
            
            return AccountInfo(
                login=info.login,
                balance=info.balance,
                equity=info.equity,
                margin=info.margin,
                free_margin=info.margin_free,
                margin_level=info.margin_level,
                profit=info.profit,
                currency=info.currency,
                server=info.server,
                company=info.company
            )
            
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return None
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information"""
        if not self.check_connection():
            return None
        
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return None
            
            return {
                "symbol": info.name,
                "bid": info.bid,
                "ask": info.ask,
                "spread": info.spread,
                "point": info.point,
                "digits": info.digits,
                "volume_min": info.volume_min,
                "volume_max": info.volume_max,
                "volume_step": info.volume_step,
                "trade_allowed": info.trade_mode != 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    def send_trade_request(self, request: TradeRequest) -> TradeResult:
        """Send trade request to MT5"""
        if not self.check_connection():
            return TradeResult(
                success=False,
                error_code=-1,
                error_message="Not connected to MT5"
            )
        
        try:
            # Build MT5 trade request
            mt5_request = {
                "symbol": request.symbol,
                "volume": request.volume,
                "deviation": request.deviation,
                "magic": request.magic,
                "comment": request.comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Set action and type
            if request.action == "buy":
                mt5_request["action"] = mt5.TRADE_ACTION_DEAL
                mt5_request["type"] = mt5.ORDER_TYPE_BUY
                if request.price:
                    mt5_request["price"] = request.price
            elif request.action == "sell":
                mt5_request["action"] = mt5.TRADE_ACTION_DEAL
                mt5_request["type"] = mt5.ORDER_TYPE_SELL
                if request.price:
                    mt5_request["price"] = request.price
            elif request.action == "buy_limit":
                mt5_request["action"] = mt5.TRADE_ACTION_PENDING
                mt5_request["type"] = mt5.ORDER_TYPE_BUY_LIMIT
                mt5_request["price"] = request.price
            elif request.action == "sell_limit":
                mt5_request["action"] = mt5.TRADE_ACTION_PENDING
                mt5_request["type"] = mt5.ORDER_TYPE_SELL_LIMIT
                mt5_request["price"] = request.price
            elif request.action == "buy_stop":
                mt5_request["action"] = mt5.TRADE_ACTION_PENDING
                mt5_request["type"] = mt5.ORDER_TYPE_BUY_STOP
                mt5_request["price"] = request.price
            elif request.action == "sell_stop":
                mt5_request["action"] = mt5.TRADE_ACTION_PENDING
                mt5_request["type"] = mt5.ORDER_TYPE_SELL_STOP
                mt5_request["price"] = request.price
            
            # Add stop loss and take profit
            if request.sl:
                mt5_request["sl"] = request.sl
            if request.tp:
                mt5_request["tp"] = request.tp
            
            # Send request
            result = mt5.order_send(mt5_request)
            
            # Update statistics
            self.stats["total_trades"] += 1
            self.stats["last_trade_time"] = datetime.now().isoformat()
            
            if request.symbol not in self.stats["trades_by_symbol"]:
                self.stats["trades_by_symbol"][request.symbol] = 0
            self.stats["trades_by_symbol"][request.symbol] += 1
            
            if request.action not in self.stats["trades_by_type"]:
                self.stats["trades_by_type"][request.action] = 0
            self.stats["trades_by_type"][request.action] += 1
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                self.stats["successful_trades"] += 1
                trade_result = TradeResult(
                    success=True,
                    order_id=result.order,
                    deal_id=result.deal,
                    volume=result.volume,
                    price=result.price,
                    execution_time=datetime.now()
                )
                self.logger.info(f"Trade executed: {request.action} {request.volume} {request.symbol} at {result.price}")
            else:
                self.stats["failed_trades"] += 1
                trade_result = TradeResult(
                    success=False,
                    error_code=result.retcode,
                    error_message=f"Trade failed: {result.comment}",
                    execution_time=datetime.now()
                )
                self.logger.error(f"Trade failed: {result.retcode} - {result.comment}")
            
            return trade_result
            
        except Exception as e:
            self.stats["failed_trades"] += 1
            error_msg = f"Trade execution error: {e}"
            self.logger.error(error_msg)
            return TradeResult(
                success=False,
                error_code=-1,
                error_message=error_msg,
                execution_time=datetime.now()
            )
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions"""
        if not self.check_connection():
            return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                result.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "buy" if pos.type == 0 else "sell",
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "price_current": pos.price_current,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                    "swap": pos.swap,
                    "comment": pos.comment,
                    "magic": pos.magic,
                    "time": datetime.fromtimestamp(pos.time)
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get pending orders"""
        if not self.check_connection():
            return []
        
        try:
            orders = mt5.orders_get()
            if orders is None:
                return []
            
            result = []
            for order in orders:
                order_types = {
                    0: "buy", 1: "sell", 2: "buy_limit", 3: "sell_limit",
                    4: "buy_stop", 5: "sell_stop"
                }
                
                result.append({
                    "ticket": order.ticket,
                    "symbol": order.symbol,
                    "type": order_types.get(order.type, "unknown"),
                    "volume": order.volume_initial,
                    "price_open": order.price_open,
                    "sl": order.sl,
                    "tp": order.tp,
                    "comment": order.comment,
                    "magic": order.magic,
                    "time_setup": datetime.fromtimestamp(order.time_setup),
                    "time_expiration": datetime.fromtimestamp(order.time_expiration) if order.time_expiration > 0 else None
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting orders: {e}")
            return []
    
    async def start_socket_server(self):
        """Start socket server for external connections"""
        if not self.socket_enabled:
            return
        
        try:
            self.socket_server = await asyncio.start_server(
                self._handle_socket_client,
                self.socket_host,
                self.socket_port
            )
            
            self.logger.info(f"Socket server started on {self.socket_host}:{self.socket_port}")
            
            async with self.socket_server:
                await self.socket_server.serve_forever()
                
        except Exception as e:
            self.logger.error(f"Socket server error: {e}")
    
    async def _handle_socket_client(self, reader, writer):
        """Handle socket client connection"""
        client_address = writer.get_extra_info('peername')
        self.logger.info(f"Socket client connected: {client_address}")
        
        try:
            while True:
                # Read message length
                length_data = await reader.read(4)
                if not length_data:
                    break
                
                message_length = struct.unpack('!I', length_data)[0]
                
                # Read message data
                message_data = await reader.read(message_length)
                if not message_data:
                    break
                
                # Process message
                try:
                    message = json.loads(message_data.decode('utf-8'))
                    response = await self._process_socket_message(message)
                    
                    # Send response
                    response_data = json.dumps(response).encode('utf-8')
                    response_length = struct.pack('!I', len(response_data))
                    writer.write(response_length + response_data)
                    await writer.drain()
                    
                except json.JSONDecodeError:
                    error_response = {"error": "Invalid JSON message"}
                    response_data = json.dumps(error_response).encode('utf-8')
                    response_length = struct.pack('!I', len(response_data))
                    writer.write(response_length + response_data)
                    await writer.drain()
                    
        except Exception as e:
            self.logger.error(f"Socket client error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            self.logger.info(f"Socket client disconnected: {client_address}")
    
    async def _process_socket_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process socket message and return response"""
        try:
            command = message.get("command")
            
            if command == "trade":
                # Execute trade
                request = TradeRequest(
                    action=message["action"],
                    symbol=message["symbol"],
                    volume=message["volume"],
                    price=message.get("price"),
                    sl=message.get("sl"),
                    tp=message.get("tp"),
                    deviation=message.get("deviation", 10),
                    magic=message.get("magic", 0),
                    comment=message.get("comment", "Socket Trade")
                )
                
                result = self.send_trade_request(request)
                return {
                    "success": result.success,
                    "order_id": result.order_id,
                    "price": result.price,
                    "error": result.error_message
                }
                
            elif command == "account_info":
                # Get account information
                account = self.get_account_info()
                if account:
                    return {"success": True, "account": asdict(account)}
                else:
                    return {"success": False, "error": "Failed to get account info"}
                    
            elif command == "positions":
                # Get positions
                positions = self.get_positions()
                return {"success": True, "positions": positions}
                
            elif command == "orders":
                # Get orders
                orders = self.get_orders()
                return {"success": True, "orders": orders}
                
            elif command == "symbol_info":
                # Get symbol info
                symbol = message.get("symbol")
                if symbol:
                    info = self.get_symbol_info(symbol)
                    if info:
                        return {"success": True, "symbol_info": info}
                    else:
                        return {"success": False, "error": f"Symbol {symbol} not found"}
                else:
                    return {"success": False, "error": "Symbol not specified"}
                    
            else:
                return {"success": False, "error": f"Unknown command: {command}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get bridge statistics"""
        return {
            **self.stats,
            "connection_status": {
                "connected": self.is_connected,
                "last_check": self.last_connection_check.isoformat() if self.last_connection_check else None,
                "retry_count": self.connection_retry_count
            },
            "configuration": {
                "socket_enabled": self.socket_enabled,
                "socket_host": self.socket_host,
                "socket_port": self.socket_port,
                "mt5_available": MT5_AVAILABLE
            }
        }


# Example usage and testing
async def main():
    """Example usage of MT5 socket bridge"""
    bridge = MT5SocketBridge()
    
    # Connect to MT5
    if bridge.connect():
        print("Connected to MT5")
        
        # Get account info
        account = bridge.get_account_info()
        if account:
            print(f"Account: {account.login}, Balance: {account.balance}")
        
        # Get positions
        positions = bridge.get_positions()
        print(f"Open positions: {len(positions)}")
        
        # Example trade
        trade_request = TradeRequest(
            action="buy",
            symbol="EURUSD",
            volume=0.01,
            sl=1.1000,
            tp=1.1100
        )
        
        result = bridge.send_trade_request(trade_request)
        print(f"Trade result: {result.success}")
        
        # Start socket server
        await bridge.start_socket_server()
        
    else:
        print("Failed to connect to MT5")


if __name__ == "__main__":
    asyncio.run(main())