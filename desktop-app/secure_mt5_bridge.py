"""
Secure MT5 Bridge for SignalOS
Comprehensive validation, error handling, and trading limits for MT5 integration
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from decimal import Decimal, ROUND_HALF_UP

class MT5Error(Exception):
    """Custom exception for MT5-related errors"""
    pass

class TradeType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"

class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"

@dataclass
class TradingLimits:
    max_lot_size: float = 10.0
    min_lot_size: float = 0.01
    max_orders_per_minute: int = 10
    max_open_positions: int = 50
    max_daily_volume: float = 100.0
    max_risk_per_trade: float = 5.0  # Percentage
    allowed_symbols: List[str] = None
    
    def __post_init__(self):
        if self.allowed_symbols is None:
            self.allowed_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']

@dataclass
class TradeRequest:
    symbol: str
    trade_type: TradeType
    volume: float
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: str = ""
    magic_number: int = 0
    deviation: int = 10
    
    def validate(self, limits: TradingLimits) -> bool:
        """Validate trade request against limits"""
        if self.symbol not in limits.allowed_symbols:
            raise MT5Error(f"Symbol not allowed: {self.symbol}")
            
        if not (limits.min_lot_size <= self.volume <= limits.max_lot_size):
            raise MT5Error(f"Invalid lot size: {self.volume}")
            
        if self.price is not None and self.price <= 0:
            raise MT5Error(f"Invalid price: {self.price}")
            
        return True

@dataclass
class TradeResult:
    success: bool
    ticket: Optional[int] = None
    error_code: Optional[int] = None
    error_message: str = ""
    execution_time: float = 0.0
    request_id: str = ""

class SecureMT5Bridge:
    """Secure MT5 bridge with comprehensive validation and error handling"""
    
    def __init__(self, config_file: str = "config.json", limits_file: str = "trading_limits.json"):
        self.config_file = config_file
        self.limits_file = limits_file
        self.logger = logging.getLogger(__name__)
        self.mt5 = None
        self.is_connected = False
        self.connection_lock = threading.Lock()
        self.order_history = []
        self.daily_volume = 0.0
        self.last_reset = datetime.now().date()
        
        # Load configuration and limits
        self._load_config()
        self._load_trading_limits()
        
        # Rate limiting
        self.order_timestamps = []
        
    def _load_config(self):
        """Load MT5 configuration safely"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.warning(f"Config load failed: {e}, using defaults")
            self.config = {
                "mt5_path": "",
                "server": "",
                "login": 0,
                "password": "",
                "timeout": 30,
                "retry_attempts": 3
            }
            
    def _load_trading_limits(self):
        """Load trading limits configuration"""
        try:
            with open(self.limits_file, 'r') as f:
                limits_data = json.load(f)
                self.trading_limits = TradingLimits(**limits_data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.warning(f"Limits load failed: {e}, using defaults")
            self.trading_limits = TradingLimits()
            
    def _check_rate_limit(self) -> bool:
        """Check if rate limit is exceeded"""
        now = time.time()
        # Remove timestamps older than 1 minute
        self.order_timestamps = [ts for ts in self.order_timestamps if now - ts < 60]
        
        if len(self.order_timestamps) >= self.trading_limits.max_orders_per_minute:
            return False
            
        self.order_timestamps.append(now)
        return True
        
    def _reset_daily_volume(self):
        """Reset daily volume if new day"""
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_volume = 0.0
            self.last_reset = today
            
    def _validate_symbol(self, symbol: str) -> bool:
        """Validate symbol format and availability"""
        if not symbol or not isinstance(symbol, str):
            return False
            
        # Basic symbol format validation
        if len(symbol) < 6 or len(symbol) > 8:
            return False
            
        # Check against allowed symbols
        return symbol.upper() in self.trading_limits.allowed_symbols
        
    def _validate_price(self, symbol: str, price: float) -> bool:
        """Validate price against symbol specifications"""
        try:
            if not self.mt5:
                return True  # Skip validation if not connected
                
            # Get symbol info
            symbol_info = self.mt5.symbol_info(symbol)
            if not symbol_info:
                return False
                
            # Check price is within reasonable bounds
            tick = self.mt5.symbol_info_tick(symbol)
            if not tick:
                return False
                
            # Price should be within 10% of current market price
            bid, ask = tick.bid, tick.ask
            spread_pct = abs(price - (bid + ask) / 2) / ((bid + ask) / 2) * 100
            
            return spread_pct <= 10.0
            
        except Exception as e:
            self.logger.error(f"Price validation failed: {e}")
            return False
            
    def _calculate_pip_value(self, symbol: str, volume: float) -> float:
        """Calculate pip value for risk management"""
        try:
            if not self.mt5:
                return 1.0
                
            symbol_info = self.mt5.symbol_info(symbol)
            if not symbol_info:
                return 1.0
                
            # Basic pip value calculation
            if symbol.endswith('JPY'):
                pip_value = 0.01 * volume * 100
            else:
                pip_value = 0.0001 * volume * 100000
                
            return pip_value
            
        except Exception as e:
            self.logger.error(f"Pip value calculation failed: {e}")
            return 1.0
            
    def connect(self) -> bool:
        """Establish secure connection to MT5"""
        with self.connection_lock:
            try:
                if self.is_connected:
                    return True
                    
                # Import MT5 library
                try:
                    import MetaTrader5 as mt5
                    self.mt5 = mt5
                except ImportError:
                    raise MT5Error("MetaTrader5 library not installed")
                    
                # Initialize MT5
                if not self.mt5.initialize(
                    path=self.config.get('mt5_path', ''),
                    login=self.config.get('login', 0),
                    server=self.config.get('server', ''),
                    password=self.config.get('password', ''),
                    timeout=self.config.get('timeout', 30000)
                ):
                    error = self.mt5.last_error()
                    raise MT5Error(f"MT5 initialization failed: {error}")
                    
                # Verify connection
                account_info = self.mt5.account_info()
                if not account_info:
                    raise MT5Error("Failed to get account info")
                    
                self.is_connected = True
                self.logger.info(f"Connected to MT5 account: {account_info.login}")
                return True
                
            except Exception as e:
                self.logger.error(f"MT5 connection failed: {e}")
                self.is_connected = False
                return False
                
    def disconnect(self):
        """Safely disconnect from MT5"""
        with self.connection_lock:
            try:
                if self.mt5 and self.is_connected:
                    self.mt5.shutdown()
                self.is_connected = False
                self.logger.info("Disconnected from MT5")
            except Exception as e:
                self.logger.error(f"Disconnect error: {e}")
                
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information safely"""
        if not self.is_connected:
            return None
            
        try:
            account_info = self.mt5.account_info()
            if not account_info:
                return None
                
            return {
                'login': account_info.login,
                'server': account_info.server,
                'balance': float(account_info.balance),
                'equity': float(account_info.equity),
                'margin': float(account_info.margin),
                'free_margin': float(account_info.margin_free),
                'margin_level': float(account_info.margin_level) if account_info.margin_level else 0.0,
                'currency': account_info.currency,
                'profit': float(account_info.profit)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return None
            
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions safely"""
        if not self.is_connected:
            return []
            
        try:
            positions = self.mt5.positions_get()
            if not positions:
                return []
                
            result = []
            for pos in positions:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == 0 else 'SELL',
                    'volume': float(pos.volume),
                    'price_open': float(pos.price_open),
                    'price_current': float(pos.price_current),
                    'sl': float(pos.sl) if pos.sl else None,
                    'tp': float(pos.tp) if pos.tp else None,
                    'profit': float(pos.profit),
                    'swap': float(pos.swap),
                    'comment': pos.comment,
                    'magic': pos.magic,
                    'time': datetime.fromtimestamp(pos.time)
                })
                
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            return []
            
    def send_order(self, request: TradeRequest) -> TradeResult:
        """Send order with comprehensive validation"""
        start_time = time.time()
        request_id = f"req_{int(start_time)}_{id(request)}"
        
        try:
            # Basic validations
            if not self.is_connected:
                raise MT5Error("Not connected to MT5")
                
            if not self._check_rate_limit():
                raise MT5Error("Rate limit exceeded")
                
            self._reset_daily_volume()
            
            # Validate request
            request.validate(self.trading_limits)
            
            # Symbol validation
            if not self._validate_symbol(request.symbol):
                raise MT5Error(f"Invalid symbol: {request.symbol}")
                
            # Price validation for pending orders
            if request.price and not self._validate_price(request.symbol, request.price):
                raise MT5Error("Invalid price")
                
            # Volume validation
            if self.daily_volume + request.volume > self.trading_limits.max_daily_volume:
                raise MT5Error("Daily volume limit exceeded")
                
            # Position count validation
            if len(self.get_positions()) >= self.trading_limits.max_open_positions:
                raise MT5Error("Maximum positions limit reached")
                
            # Prepare MT5 request
            mt5_request = {
                "action": self.mt5.TRADE_ACTION_DEAL if request.trade_type in [TradeType.BUY, TradeType.SELL] else self.mt5.TRADE_ACTION_PENDING,
                "symbol": request.symbol,
                "volume": request.volume,
                "type": self._get_mt5_order_type(request.trade_type),
                "deviation": request.deviation,
                "magic": request.magic_number,
                "comment": request.comment[:31],  # MT5 comment limit
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            
            # Add price for pending orders
            if request.price:
                mt5_request["price"] = request.price
                
            # Add stop loss and take profit
            if request.sl:
                mt5_request["sl"] = request.sl
            if request.tp:
                mt5_request["tp"] = request.tp
                
            # Send order
            result = self.mt5.order_send(mt5_request)
            
            if not result:
                raise MT5Error("Order send failed - no result")
                
            execution_time = time.time() - start_time
            
            if result.retcode == self.mt5.TRADE_RETCODE_DONE:
                # Update daily volume
                self.daily_volume += request.volume
                
                # Log successful order
                self.order_history.append({
                    'request_id': request_id,
                    'ticket': result.order,
                    'symbol': request.symbol,
                    'volume': request.volume,
                    'type': request.trade_type.value,
                    'timestamp': datetime.now(),
                    'success': True
                })
                
                return TradeResult(
                    success=True,
                    ticket=result.order,
                    execution_time=execution_time,
                    request_id=request_id
                )
            else:
                error_msg = f"Order failed: {result.retcode} - {result.comment}"
                raise MT5Error(error_msg)
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(f"Order failed [{request_id}]: {error_msg}")
            
            # Log failed order
            self.order_history.append({
                'request_id': request_id,
                'symbol': request.symbol,
                'volume': request.volume,
                'type': request.trade_type.value,
                'timestamp': datetime.now(),
                'success': False,
                'error': error_msg
            })
            
            return TradeResult(
                success=False,
                error_message=error_msg,
                execution_time=execution_time,
                request_id=request_id
            )
            
    def _get_mt5_order_type(self, trade_type: TradeType) -> int:
        """Convert TradeType to MT5 order type"""
        mapping = {
            TradeType.BUY: self.mt5.ORDER_TYPE_BUY,
            TradeType.SELL: self.mt5.ORDER_TYPE_SELL,
            TradeType.BUY_LIMIT: self.mt5.ORDER_TYPE_BUY_LIMIT,
            TradeType.SELL_LIMIT: self.mt5.ORDER_TYPE_SELL_LIMIT,
            TradeType.BUY_STOP: self.mt5.ORDER_TYPE_BUY_STOP,
            TradeType.SELL_STOP: self.mt5.ORDER_TYPE_SELL_STOP
        }
        return mapping.get(trade_type, self.mt5.ORDER_TYPE_BUY)
        
    def close_position(self, ticket: int) -> TradeResult:
        """Close position safely"""
        try:
            if not self.is_connected:
                raise MT5Error("Not connected to MT5")
                
            # Get position info
            position = self.mt5.positions_get(ticket=ticket)
            if not position:
                raise MT5Error(f"Position not found: {ticket}")
                
            pos = position[0]
            
            # Prepare close request
            close_request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": self.mt5.ORDER_TYPE_SELL if pos.type == 0 else self.mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "deviation": 10,
                "magic": pos.magic,
                "comment": f"Close #{ticket}",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            
            result = self.mt5.order_send(close_request)
            
            if result and result.retcode == self.mt5.TRADE_RETCODE_DONE:
                return TradeResult(success=True, ticket=result.order)
            else:
                error_msg = f"Close failed: {result.retcode if result else 'No result'}"
                return TradeResult(success=False, error_message=error_msg)
                
        except Exception as e:
            return TradeResult(success=False, error_message=str(e))
            
    def modify_position(self, ticket: int, sl: Optional[float] = None, 
                       tp: Optional[float] = None) -> TradeResult:
        """Modify position SL/TP safely"""
        try:
            if not self.is_connected:
                raise MT5Error("Not connected to MT5")
                
            # Get position info
            position = self.mt5.positions_get(ticket=ticket)
            if not position:
                raise MT5Error(f"Position not found: {ticket}")
                
            pos = position[0]
            
            # Prepare modification request
            modify_request = {
                "action": self.mt5.TRADE_ACTION_SLTP,
                "symbol": pos.symbol,
                "position": ticket,
                "sl": sl if sl is not None else pos.sl,
                "tp": tp if tp is not None else pos.tp,
            }
            
            result = self.mt5.order_send(modify_request)
            
            if result and result.retcode == self.mt5.TRADE_RETCODE_DONE:
                return TradeResult(success=True, ticket=ticket)
            else:
                error_msg = f"Modify failed: {result.retcode if result else 'No result'}"
                return TradeResult(success=False, error_message=error_msg)
                
        except Exception as e:
            return TradeResult(success=False, error_message=str(e))
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get trading statistics"""
        return {
            'is_connected': self.is_connected,
            'daily_volume': self.daily_volume,
            'orders_today': len([o for o in self.order_history 
                               if o['timestamp'].date() == datetime.now().date()]),
            'success_rate': self._calculate_success_rate(),
            'position_count': len(self.get_positions()),
            'last_reset': self.last_reset.isoformat(),
            'rate_limit_remaining': self.trading_limits.max_orders_per_minute - len(self.order_timestamps)
        }
        
    def _calculate_success_rate(self) -> float:
        """Calculate order success rate"""
        if not self.order_history:
            return 0.0
            
        successful = sum(1 for order in self.order_history if order['success'])
        return (successful / len(self.order_history)) * 100

# Global secure MT5 bridge instance
secure_mt5_bridge = SecureMT5Bridge()

def send_secure_order(symbol: str, trade_type: str, volume: float, 
                     price: float = None, sl: float = None, tp: float = None) -> Dict[str, Any]:
    """Global function for secure order sending"""
    try:
        trade_type_enum = TradeType(trade_type.upper())
        request = TradeRequest(
            symbol=symbol.upper(),
            trade_type=trade_type_enum,
            volume=volume,
            price=price,
            sl=sl,
            tp=tp
        )
        
        result = secure_mt5_bridge.send_order(request)
        return asdict(result)
        
    except Exception as e:
        return {'success': False, 'error_message': str(e)}

def get_secure_positions() -> List[Dict[str, Any]]:
    """Global function for getting positions securely"""
    return secure_mt5_bridge.get_positions()

def close_secure_position(ticket: int) -> Dict[str, Any]:
    """Global function for closing positions securely"""
    result = secure_mt5_bridge.close_position(ticket)
    return asdict(result)