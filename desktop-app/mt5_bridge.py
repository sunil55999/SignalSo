"""
MT5 Bridge for SignalOS
Handles MetaTrader 5 connection and trade execution with comprehensive error handling
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import asyncio

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"

class TradeResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    PARTIAL = "partial"

@dataclass
class MT5Config:
    terminal_path: str = ""
    login: int = 0
    password: str = ""
    server: str = ""
    timeout: int = 60000
    portable: bool = False
    enable_logging: bool = True
    log_file: str = "logs/mt5_bridge.log"
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class TradeRequest:
    symbol: str
    action: OrderType
    volume: float
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: str = ""
    magic: int = 0
    deviation: int = 20
    type_time: int = None  # Order expiration type
    type_filling: int = None  # Order filling type

@dataclass
class TradeResult:
    success: bool
    ticket: Optional[int] = None
    price: Optional[float] = None
    volume: Optional[float] = None
    error_code: Optional[int] = None
    error_description: str = ""
    retcode: Optional[int] = None
    request_id: Optional[int] = None
    raw_result: Optional[Dict] = None

class MT5Bridge:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/mt5_bridge.log"):
        self.config_file = config_file
        self.config = self._load_config()
        self.is_connected = False
        self.last_error = None
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        
        # Setup logging
        self._setup_logging(log_file)
        
        # Symbol mapping for broker-specific symbols
        self.symbol_mapping = self._load_symbol_mapping()
        
        # Connection status tracking
        self.last_ping = None
        self.account_info = {}
        
        if not MT5_AVAILABLE:
            self.logger.warning("MetaTrader5 library not available. Running in simulation mode.")

    def _load_config(self) -> MT5Config:
        """Load MT5 configuration from JSON file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    mt5_config = config_data.get('mt5', {})
                    return MT5Config(**mt5_config)
            else:
                return self._create_default_config()
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return MT5Config()

    def _create_default_config(self) -> MT5Config:
        """Create default configuration and save to file"""
        default_config = MT5Config()
        
        try:
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['mt5'] = asdict(default_config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Failed to save default config: {e}")
        
        return default_config

    def _setup_logging(self, log_file: str):
        """Setup logging for MT5 operations"""
        # Create logs directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger('MT5Bridge')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # File handler
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

    def _load_symbol_mapping(self) -> Dict[str, str]:
        """Load symbol mapping for broker-specific symbol names"""
        default_mapping = {
            "EURUSD": "EURUSD",
            "GBPUSD": "GBPUSD", 
            "USDJPY": "USDJPY",
            "USDCHF": "USDCHF",
            "AUDUSD": "AUDUSD",
            "USDCAD": "USDCAD",
            "NZDUSD": "NZDUSD",
            "XAUUSD": "XAUUSD",
            "XAGUSD": "XAGUSD",
            "US30": "US30",
            "NAS100": "NAS100",
            "SPX500": "SPX500",
            "GER30": "GER30"
        }
        
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    return config_data.get('symbol_mapping', default_mapping)
        except Exception:
            pass
        
        return default_mapping

    def initialize(self) -> bool:
        """Initialize MT5 terminal connection"""
        if not MT5_AVAILABLE:
            self.logger.warning("MT5 library not available. Simulating connection.")
            self.is_connected = True
            return True

        try:
            self.logger.info("Initializing MT5 connection...")
            
            # Initialize MT5
            if self.config.terminal_path:
                if not mt5.initialize(path=self.config.terminal_path, 
                                    login=self.config.login,
                                    password=self.config.password,
                                    server=self.config.server,
                                    timeout=self.config.timeout,
                                    portable=self.config.portable):
                    error = mt5.last_error()
                    self.logger.error(f"MT5 initialization failed: {error}")
                    self.last_error = error
                    return False
            else:
                if not mt5.initialize():
                    error = mt5.last_error()
                    self.logger.error(f"MT5 initialization failed: {error}")
                    self.last_error = error
                    return False

            # Verify connection by getting account info
            account_info = mt5.account_info()
            if account_info is None:
                error = mt5.last_error()
                self.logger.error(f"Failed to get account info: {error}")
                self.last_error = error
                return False

            self.account_info = account_info._asdict()
            self.is_connected = True
            self.connection_attempts = 0
            self.last_ping = datetime.now()
            
            self.logger.info(f"MT5 connected successfully. Account: {self.account_info.get('login', 'Unknown')}")
            return True

        except Exception as e:
            self.logger.error(f"Exception during MT5 initialization: {e}")
            self.last_error = str(e)
            return False

    def disconnect(self):
        """Disconnect from MT5 terminal"""
        if MT5_AVAILABLE and self.is_connected:
            mt5.shutdown()
            self.logger.info("MT5 disconnected")
        
        self.is_connected = False
        self.account_info = {}

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and account information"""
        if not self.is_connected:
            return {
                "connected": False,
                "error": self.last_error,
                "account_info": {},
                "last_ping": None
            }

        # Update account info if connected
        if MT5_AVAILABLE:
            try:
                account_info = mt5.account_info()
                if account_info:
                    self.account_info = account_info._asdict()
                    self.last_ping = datetime.now()
                else:
                    self.logger.warning("Failed to get account info - connection may be lost")
                    self.is_connected = False
            except Exception as e:
                self.logger.error(f"Error checking connection status: {e}")
                self.is_connected = False

        return {
            "connected": self.is_connected,
            "account_info": self.account_info,
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
            "error": self.last_error
        }

    def _map_symbol(self, symbol: str) -> str:
        """Map symbol to broker-specific symbol name"""
        return self.symbol_mapping.get(symbol, symbol)

    def _validate_trade_request(self, request: TradeRequest) -> Tuple[bool, str]:
        """Validate trade request parameters"""
        if not self.is_connected:
            return False, "MT5 not connected"

        if request.volume <= 0:
            return False, "Invalid volume"

        if not request.symbol:
            return False, "Symbol not specified"

        # Map symbol
        mapped_symbol = self._map_symbol(request.symbol)
        request.symbol = mapped_symbol

        # Get symbol info if MT5 is available
        if MT5_AVAILABLE:
            try:
                symbol_info = mt5.symbol_info(mapped_symbol)
                if symbol_info is None:
                    return False, f"Symbol {mapped_symbol} not found"

                # Check if symbol is enabled for trading
                if not symbol_info.select:
                    if not mt5.symbol_select(mapped_symbol, True):
                        return False, f"Failed to select symbol {mapped_symbol}"

                # Validate volume
                if request.volume < symbol_info.volume_min:
                    return False, f"Volume below minimum ({symbol_info.volume_min})"
                
                if request.volume > symbol_info.volume_max:
                    return False, f"Volume above maximum ({symbol_info.volume_max})"

            except Exception as e:
                return False, f"Symbol validation error: {e}"

        return True, "Valid"

    async def send_market_order(self, request: TradeRequest) -> TradeResult:
        """Send market order to MT5"""
        # Validate request
        is_valid, validation_msg = self._validate_trade_request(request)
        if not is_valid:
            self.logger.error(f"Invalid trade request: {validation_msg}")
            return TradeResult(
                success=False,
                error_description=validation_msg,
                raw_result={"validation_error": validation_msg}
            )

        if not MT5_AVAILABLE:
            # Simulation mode
            self.logger.info(f"SIMULATION: Market order {request.action.value} {request.volume} {request.symbol}")
            return TradeResult(
                success=True,
                ticket=int(time.time()),
                price=1.0,  # Simulated price
                volume=request.volume,
                error_description="Simulated execution"
            )

        try:
            # Get current prices
            symbol_info = mt5.symbol_info_tick(request.symbol)
            if symbol_info is None:
                return TradeResult(
                    success=False,
                    error_description=f"No tick data for {request.symbol}"
                )

            # Determine order type and price
            if request.action == OrderType.BUY:
                order_type = mt5.ORDER_TYPE_BUY
                price = symbol_info.ask
            elif request.action == OrderType.SELL:
                order_type = mt5.ORDER_TYPE_SELL
                price = symbol_info.bid
            else:
                return TradeResult(
                    success=False,
                    error_description=f"Invalid market order type: {request.action}"
                )

            # Create order request
            mt5_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": request.symbol,
                "volume": request.volume,
                "type": order_type,
                "price": price,
                "deviation": request.deviation,
                "magic": request.magic,
                "comment": request.comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Add SL/TP if specified
            if request.sl:
                mt5_request["sl"] = request.sl
            if request.tp:
                mt5_request["tp"] = request.tp

            self.logger.info(f"Sending market order: {request.action.value} {request.volume} {request.symbol} @ {price}")

            # Send order
            result = mt5.order_send(mt5_request)
            
            if result is None:
                error = mt5.last_error()
                self.logger.error(f"Order send failed: {error}")
                return TradeResult(
                    success=False,
                    error_code=error[0] if error else None,
                    error_description=error[1] if error else "Unknown error"
                )

            result_dict = result._asdict()
            self.logger.info(f"Order result: {result_dict}")

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return TradeResult(
                    success=True,
                    ticket=result.order,
                    price=result.price,
                    volume=result.volume,
                    retcode=result.retcode,
                    raw_result=result_dict
                )
            else:
                return TradeResult(
                    success=False,
                    retcode=result.retcode,
                    error_description=f"Order failed with retcode: {result.retcode}",
                    raw_result=result_dict
                )

        except Exception as e:
            self.logger.error(f"Exception in send_market_order: {e}")
            return TradeResult(
                success=False,
                error_description=str(e)
            )

    async def send_pending_order(self, request: TradeRequest) -> TradeResult:
        """Send pending order to MT5"""
        # Validate request
        is_valid, validation_msg = self._validate_trade_request(request)
        if not is_valid:
            self.logger.error(f"Invalid pending order request: {validation_msg}")
            return TradeResult(
                success=False,
                error_description=validation_msg
            )

        if request.price is None:
            return TradeResult(
                success=False,
                error_description="Price required for pending orders"
            )

        if not MT5_AVAILABLE:
            # Simulation mode
            self.logger.info(f"SIMULATION: Pending order {request.action.value} {request.volume} {request.symbol} @ {request.price}")
            return TradeResult(
                success=True,
                ticket=int(time.time()),
                price=request.price,
                volume=request.volume,
                error_description="Simulated pending order"
            )

        try:
            # Map order types
            order_type_map = {
                OrderType.BUY_LIMIT: mt5.ORDER_TYPE_BUY_LIMIT,
                OrderType.SELL_LIMIT: mt5.ORDER_TYPE_SELL_LIMIT,
                OrderType.BUY_STOP: mt5.ORDER_TYPE_BUY_STOP,
                OrderType.SELL_STOP: mt5.ORDER_TYPE_SELL_STOP
            }

            if request.action not in order_type_map:
                return TradeResult(
                    success=False,
                    error_description=f"Invalid pending order type: {request.action}"
                )

            # Create order request
            mt5_request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": request.symbol,
                "volume": request.volume,
                "type": order_type_map[request.action],
                "price": request.price,
                "magic": request.magic,
                "comment": request.comment,
                "type_time": request.type_time or mt5.ORDER_TIME_GTC,
            }

            # Add SL/TP if specified
            if request.sl:
                mt5_request["sl"] = request.sl
            if request.tp:
                mt5_request["tp"] = request.tp

            self.logger.info(f"Sending pending order: {request.action.value} {request.volume} {request.symbol} @ {request.price}")

            # Send order
            result = mt5.order_send(mt5_request)
            
            if result is None:
                error = mt5.last_error()
                self.logger.error(f"Pending order send failed: {error}")
                return TradeResult(
                    success=False,
                    error_code=error[0] if error else None,
                    error_description=error[1] if error else "Unknown error"
                )

            result_dict = result._asdict()
            self.logger.info(f"Pending order result: {result_dict}")

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return TradeResult(
                    success=True,
                    ticket=result.order,
                    price=result.price,
                    volume=result.volume,
                    retcode=result.retcode,
                    raw_result=result_dict
                )
            else:
                return TradeResult(
                    success=False,
                    retcode=result.retcode,
                    error_description=f"Pending order failed with retcode: {result.retcode}",
                    raw_result=result_dict
                )

        except Exception as e:
            self.logger.error(f"Exception in send_pending_order: {e}")
            return TradeResult(
                success=False,
                error_description=str(e)
            )

    async def close_position(self, ticket: int, volume: Optional[float] = None) -> TradeResult:
        """Close position by ticket"""
        if not self.is_connected:
            return TradeResult(
                success=False,
                error_description="MT5 not connected"
            )

        if not MT5_AVAILABLE:
            # Simulation mode
            self.logger.info(f"SIMULATION: Closing position {ticket}")
            return TradeResult(
                success=True,
                ticket=ticket,
                error_description="Simulated position close"
            )

        try:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return TradeResult(
                    success=False,
                    error_description=f"Position {ticket} not found"
                )

            position = position[0]
            
            # Determine close volume
            close_volume = volume if volume else position.volume
            
            # Determine opposite order type
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(position.symbol).bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(position.symbol).ask

            # Create close request
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": close_volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "magic": position.magic,
                "comment": f"Close {ticket}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            self.logger.info(f"Closing position {ticket}: {close_volume} lots")

            # Send close order
            result = mt5.order_send(close_request)
            
            if result is None:
                error = mt5.last_error()
                self.logger.error(f"Position close failed: {error}")
                return TradeResult(
                    success=False,
                    error_code=error[0] if error else None,
                    error_description=error[1] if error else "Unknown error"
                )

            result_dict = result._asdict()
            self.logger.info(f"Position close result: {result_dict}")

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return TradeResult(
                    success=True,
                    ticket=result.order,
                    price=result.price,
                    volume=result.volume,
                    retcode=result.retcode,
                    raw_result=result_dict
                )
            else:
                return TradeResult(
                    success=False,
                    retcode=result.retcode,
                    error_description=f"Position close failed with retcode: {result.retcode}",
                    raw_result=result_dict
                )

        except Exception as e:
            self.logger.error(f"Exception in close_position: {e}")
            return TradeResult(
                success=False,
                error_description=str(e)
            )

    async def delete_pending_order(self, ticket: int) -> TradeResult:
        """Delete pending order by ticket"""
        if not self.is_connected:
            return TradeResult(
                success=False,
                error_description="MT5 not connected"
            )

        if not MT5_AVAILABLE:
            # Simulation mode
            self.logger.info(f"SIMULATION: Deleting pending order {ticket}")
            return TradeResult(
                success=True,
                ticket=ticket,
                error_description="Simulated order deletion"
            )

        try:
            # Create delete request
            delete_request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket,
            }

            self.logger.info(f"Deleting pending order {ticket}")

            # Send delete order
            result = mt5.order_send(delete_request)
            
            if result is None:
                error = mt5.last_error()
                self.logger.error(f"Order deletion failed: {error}")
                return TradeResult(
                    success=False,
                    error_code=error[0] if error else None,
                    error_description=error[1] if error else "Unknown error"
                )

            result_dict = result._asdict()
            self.logger.info(f"Order deletion result: {result_dict}")

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return TradeResult(
                    success=True,
                    ticket=ticket,
                    retcode=result.retcode,
                    raw_result=result_dict
                )
            else:
                return TradeResult(
                    success=False,
                    retcode=result.retcode,
                    error_description=f"Order deletion failed with retcode: {result.retcode}",
                    raw_result=result_dict
                )

        except Exception as e:
            self.logger.error(f"Exception in delete_pending_order: {e}")
            return TradeResult(
                success=False,
                error_description=str(e)
            )

    def modify_position(self, ticket: int, sl: Optional[float] = None, tp: Optional[float] = None) -> TradeResult:
        """Modify position SL/TP"""
        if not self.is_connected:
            return TradeResult(
                success=False,
                error_description="MT5 not connected"
            )

        if not MT5_AVAILABLE:
            # Simulation mode
            self.logger.info(f"SIMULATION: Modifying position {ticket} SL: {sl} TP: {tp}")
            return TradeResult(
                success=True,
                ticket=ticket,
                error_description="Simulated position modification"
            )

        try:
            # Create modify request
            modify_request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
            }

            if sl is not None:
                modify_request["sl"] = sl
            if tp is not None:
                modify_request["tp"] = tp

            self.logger.info(f"Modifying position {ticket}: SL={sl}, TP={tp}")

            # Send modify order
            result = mt5.order_send(modify_request)
            
            if result is None:
                error = mt5.last_error()
                self.logger.error(f"Position modification failed: {error}")
                return TradeResult(
                    success=False,
                    error_code=error[0] if error else None,
                    error_description=error[1] if error else "Unknown error"
                )

            result_dict = result._asdict()
            self.logger.info(f"Position modification result: {result_dict}")

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return TradeResult(
                    success=True,
                    ticket=ticket,
                    retcode=result.retcode,
                    raw_result=result_dict
                )
            else:
                return TradeResult(
                    success=False,
                    retcode=result.retcode,
                    error_description=f"Position modification failed with retcode: {result.retcode}",
                    raw_result=result_dict
                )

        except Exception as e:
            self.logger.error(f"Exception in modify_position: {e}")
            return TradeResult(
                success=False,
                error_description=str(e)
            )

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information"""
        mapped_symbol = self._map_symbol(symbol)
        
        if not MT5_AVAILABLE:
            # Return simulated symbol info
            return {
                "symbol": mapped_symbol,
                "digits": 5,
                "point": 0.00001,
                "spread": 10,
                "volume_min": 0.01,
                "volume_max": 100.0,
                "pip_value": 10.0,
                "tick_value": 1.0,
                "contract_size": 100000
            }

        try:
            symbol_info = mt5.symbol_info(mapped_symbol)
            if symbol_info is None:
                return None

            return {
                "symbol": symbol_info.name,
                "digits": symbol_info.digits,
                "point": symbol_info.point,
                "spread": symbol_info.spread,
                "volume_min": symbol_info.volume_min,
                "volume_max": symbol_info.volume_max,
                "pip_value": symbol_info.trade_tick_value,
                "tick_value": symbol_info.trade_tick_value,
                "contract_size": symbol_info.trade_contract_size
            }

        except Exception as e:
            self.logger.error(f"Error getting symbol info for {mapped_symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get current bid/ask prices for symbol"""
        mapped_symbol = self._map_symbol(symbol)
        
        if not MT5_AVAILABLE:
            # Return simulated prices
            return {
                "bid": 1.0,
                "ask": 1.00001,
                "time": time.time()
            }

        try:
            tick = mt5.symbol_info_tick(mapped_symbol)
            if tick is None:
                return None

            return {
                "bid": tick.bid,
                "ask": tick.ask,
                "time": tick.time
            }

        except Exception as e:
            self.logger.error(f"Error getting current price for {mapped_symbol}: {e}")
            return None

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open positions"""
        if not MT5_AVAILABLE:
            return []

        try:
            if symbol:
                mapped_symbol = self._map_symbol(symbol)
                positions = mt5.positions_get(symbol=mapped_symbol)
            else:
                positions = mt5.positions_get()

            if positions is None:
                return []

            return [pos._asdict() for pos in positions]

        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []

    def get_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get pending orders"""
        if not MT5_AVAILABLE:
            return []

        try:
            if symbol:
                mapped_symbol = self._map_symbol(symbol)
                orders = mt5.orders_get(symbol=mapped_symbol)
            else:
                orders = mt5.orders_get()

            if orders is None:
                return []

            return [order._asdict() for order in orders]

        except Exception as e:
            self.logger.error(f"Error getting orders: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get MT5 bridge statistics"""
        return {
            "connected": self.is_connected,
            "connection_attempts": self.connection_attempts,
            "last_error": self.last_error,
            "account_info": self.account_info,
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
            "mt5_available": MT5_AVAILABLE,
            "symbol_mappings": len(self.symbol_mapping)
        }


# Global instance for easy access
_mt5_bridge_instance = None

def get_mt5_bridge() -> MT5Bridge:
    """Get global MT5 bridge instance"""
    global _mt5_bridge_instance
    if _mt5_bridge_instance is None:
        _mt5_bridge_instance = MT5Bridge()
    return _mt5_bridge_instance


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_mt5_bridge():
        """Test MT5 bridge functionality"""
        bridge = MT5Bridge()
        
        # Initialize connection
        if bridge.initialize():
            print("MT5 connected successfully")
            
            # Get connection status
            status = bridge.get_connection_status()
            print(f"Connection status: {status}")
            
            # Test market order
            request = TradeRequest(
                symbol="EURUSD",
                action=OrderType.BUY,
                volume=0.01,
                comment="Test order",
                magic=12345
            )
            
            result = await bridge.send_market_order(request)
            print(f"Market order result: {result}")
            
        else:
            print("Failed to connect to MT5")
        
        # Cleanup
        bridge.disconnect()
    
    # Run test
    asyncio.run(test_mt5_bridge())