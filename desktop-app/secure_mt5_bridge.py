"""
Secure MT5 Bridge for SignalOS Desktop App
Fixes Issue #11: Unsafe MT5 API integration with proper error handling and validation
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import json

# Fix #11: Secure MT5 API integration
class MT5OperationResult(Enum):
    """MT5 operation result codes"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    INVALID_PARAMS = "invalid_params"
    CONNECTION_ERROR = "connection_error"
    INSUFFICIENT_MARGIN = "insufficient_margin"
    INVALID_SYMBOL = "invalid_symbol"
    MARKET_CLOSED = "market_closed"

@dataclass
class MT5TradeRequest:
    """Validated MT5 trade request"""
    action: str
    symbol: str
    volume: float
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    deviation: int = 20
    magic: int = 0
    comment: str = "SignalOS"
    type_time: int = 0  # GTC
    type_filling: int = 0  # FOK

@dataclass
class MT5TradeResult:
    """MT5 trade operation result"""
    result: MT5OperationResult
    ticket: Optional[int] = None
    volume: Optional[float] = None
    price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    comment: Optional[str] = None
    error_code: Optional[int] = None
    error_description: Optional[str] = None

class SecureMT5Bridge:
    """
    Secure MT5 bridge with comprehensive error handling and validation
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize secure MT5 bridge
        
        Args:
            config: MT5 connection configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._validate_config(config)
        self.mt5 = None
        self.is_connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.last_error = None
        
        # Trading limits for safety
        self.max_volume = 10.0
        self.min_volume = 0.01
        self.max_sl_distance = 1000  # pips
        self.max_tp_distance = 1000  # pips
        
        # Valid symbols (should be loaded from broker)
        self.valid_symbols = set()
        
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate MT5 configuration parameters"""
        required_fields = ['server', 'login', 'password', 'path']
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required MT5 config field: {field}")
        
        # Sanitize and validate values
        validated_config = {
            'server': str(config['server']).strip(),
            'login': int(config['login']),
            'password': str(config['password']),
            'path': str(config['path']).strip(),
            'timeout': config.get('timeout', 30),
            'enable_real_trading': config.get('enable_real_trading', False)
        }
        
        # Validate login number
        if validated_config['login'] <= 0:
            raise ValueError("Invalid MT5 login number")
        
        # Validate server name
        if not validated_config['server'] or len(validated_config['server']) < 3:
            raise ValueError("Invalid MT5 server name")
        
        return validated_config
    
    def connect(self) -> bool:
        """
        Safely connect to MT5 terminal
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Import MT5 library safely
            try:
                import MetaTrader5 as mt5
                self.mt5 = mt5
            except ImportError:
                self.logger.error("MetaTrader5 library not installed")
                return False
            
            # Initialize MT5 connection
            if not self.mt5.initialize(
                path=self.config['path'],
                login=self.config['login'],
                password=self.config['password'],
                server=self.config['server'],
                timeout=self.config['timeout']
            ):
                error = self.mt5.last_error()
                self.last_error = f"MT5 initialization failed: {error}"
                self.logger.error(self.last_error)
                return False
            
            # Verify connection
            account_info = self.mt5.account_info()
            if account_info is None:
                self.last_error = "Failed to get account information"
                self.logger.error(self.last_error)
                self.disconnect()
                return False
            
            # Load valid symbols
            self._load_valid_symbols()
            
            self.is_connected = True
            self.connection_attempts = 0
            self.logger.info(f"Successfully connected to MT5: {account_info.login}")
            
            return True
            
        except Exception as e:
            self.connection_attempts += 1
            self.last_error = f"Connection error: {str(e)}"
            self.logger.error(self.last_error)
            return False
    
    def disconnect(self) -> None:
        """Safely disconnect from MT5"""
        try:
            if self.mt5 and self.is_connected:
                self.mt5.shutdown()
                self.logger.info("Disconnected from MT5")
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
        finally:
            self.is_connected = False
            self.mt5 = None
    
    def _load_valid_symbols(self) -> None:
        """Load valid trading symbols from broker"""
        try:
            symbols = self.mt5.symbols_get()
            if symbols:
                self.valid_symbols = {symbol.name for symbol in symbols if symbol.visible}
                self.logger.debug(f"Loaded {len(self.valid_symbols)} valid symbols")
            else:
                self.logger.warning("No symbols loaded from broker")
        except Exception as e:
            self.logger.error(f"Failed to load symbols: {e}")
    
    def _validate_trade_request(self, request: MT5TradeRequest) -> bool:
        """
        Validate trade request parameters
        
        Args:
            request: Trade request to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate action
            valid_actions = ['BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP']
            if request.action not in valid_actions:
                self.logger.error(f"Invalid trade action: {request.action}")
                return False
            
            # Validate symbol
            if request.symbol not in self.valid_symbols:
                self.logger.error(f"Invalid symbol: {request.symbol}")
                return False
            
            # Validate volume
            if not (self.min_volume <= request.volume <= self.max_volume):
                self.logger.error(f"Invalid volume: {request.volume}")
                return False
            
            # Validate prices
            if request.price is not None and request.price <= 0:
                self.logger.error(f"Invalid price: {request.price}")
                return False
            
            # Validate stop loss and take profit distances
            if request.price and request.sl:
                sl_distance = abs(request.price - request.sl)
                if sl_distance > self.max_sl_distance * self._get_point_value(request.symbol):
                    self.logger.error(f"Stop loss too far: {sl_distance}")
                    return False
            
            if request.price and request.tp:
                tp_distance = abs(request.price - request.tp)
                if tp_distance > self.max_tp_distance * self._get_point_value(request.symbol):
                    self.logger.error(f"Take profit too far: {tp_distance}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Trade validation error: {e}")
            return False
    
    def _get_point_value(self, symbol: str) -> float:
        """Get point value for symbol"""
        try:
            symbol_info = self.mt5.symbol_info(symbol)
            return symbol_info.point if symbol_info else 0.0001
        except:
            return 0.0001  # Default pip value
    
    def _check_trading_conditions(self, symbol: str) -> bool:
        """Check if trading conditions are suitable"""
        try:
            # Check if market is open
            symbol_info = self.mt5.symbol_info(symbol)
            if not symbol_info or not symbol_info.visible:
                self.logger.warning(f"Symbol not available: {symbol}")
                return False
            
            # Check trading session
            if symbol_info.trade_mode == 0:  # Trade disabled
                self.logger.warning(f"Trading disabled for symbol: {symbol}")
                return False
            
            # Check spread
            spread = symbol_info.spread
            if spread > 50:  # More than 5 pips spread
                self.logger.warning(f"High spread for {symbol}: {spread}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking trading conditions: {e}")
            return False
    
    def place_order(self, request: MT5TradeRequest) -> MT5TradeResult:
        """
        Safely place trading order
        
        Args:
            request: Validated trade request
            
        Returns:
            Trade operation result
        """
        if not self.is_connected:
            return MT5TradeResult(MT5OperationResult.CONNECTION_ERROR, 
                                error_description="Not connected to MT5")
        
        # Check if real trading is enabled
        if self.config.get('enable_real_trading') != True:
            return MT5TradeResult(MT5OperationResult.FAILED,
                                error_description="Real trading disabled in configuration")
        
        # Validate request
        if not self._validate_trade_request(request):
            return MT5TradeResult(MT5OperationResult.INVALID_PARAMS,
                                error_description="Invalid trade parameters")
        
        # Check trading conditions
        if not self._check_trading_conditions(request.symbol):
            return MT5TradeResult(MT5OperationResult.MARKET_CLOSED,
                                error_description="Unfavorable trading conditions")
        
        try:
            # Prepare order request
            order_request = {
                "action": getattr(self.mt5, f"TRADE_ACTION_{request.action}", None),
                "symbol": request.symbol,
                "volume": request.volume,
                "type": getattr(self.mt5, f"ORDER_TYPE_{request.action}", None),
                "price": request.price or self._get_current_price(request.symbol, request.action),
                "sl": request.sl,
                "tp": request.tp,
                "deviation": request.deviation,
                "magic": request.magic,
                "comment": request.comment[:31],  # MT5 comment limit
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_FOK,
            }
            
            # Remove None values
            order_request = {k: v for k, v in order_request.items() if v is not None}
            
            # Send order
            result = self.mt5.order_send(order_request)
            
            if result is None:
                error = self.mt5.last_error()
                return MT5TradeResult(MT5OperationResult.FAILED,
                                    error_code=error[0] if error else None,
                                    error_description=str(error[1]) if error else "Unknown error")
            
            if result.retcode == self.mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"Order placed successfully: {result.order}")
                return MT5TradeResult(
                    result=MT5OperationResult.SUCCESS,
                    ticket=result.order,
                    volume=result.volume,
                    price=result.price,
                    bid=result.bid,
                    ask=result.ask,
                    comment=result.comment
                )
            else:
                self.logger.error(f"Order failed: {result.retcode} - {result.comment}")
                return MT5TradeResult(
                    result=MT5OperationResult.FAILED,
                    error_code=result.retcode,
                    error_description=result.comment
                )
                
        except Exception as e:
            self.logger.error(f"Order placement error: {e}")
            return MT5TradeResult(MT5OperationResult.FAILED,
                                error_description=str(e))
    
    def _get_current_price(self, symbol: str, action: str) -> float:
        """Get current price for symbol and action"""
        try:
            tick = self.mt5.symbol_info_tick(symbol)
            if tick:
                return tick.ask if action.startswith('BUY') else tick.bid
            return 0.0
        except:
            return 0.0
    
    def close_position(self, ticket: int) -> MT5TradeResult:
        """
        Safely close position
        
        Args:
            ticket: Position ticket to close
            
        Returns:
            Close operation result
        """
        if not self.is_connected:
            return MT5TradeResult(MT5OperationResult.CONNECTION_ERROR)
        
        try:
            # Get position info
            position = self.mt5.positions_get(ticket=ticket)
            if not position:
                return MT5TradeResult(MT5OperationResult.FAILED,
                                    error_description="Position not found")
            
            position = position[0]
            
            # Prepare close request
            close_request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": self.mt5.ORDER_TYPE_SELL if position.type == 0 else self.mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "price": self._get_current_price(position.symbol, 
                                               "SELL" if position.type == 0 else "BUY"),
                "deviation": 20,
                "magic": position.magic,
                "comment": "SignalOS Close",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            
            # Send close request
            result = self.mt5.order_send(close_request)
            
            if result and result.retcode == self.mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"Position closed successfully: {ticket}")
                return MT5TradeResult(MT5OperationResult.SUCCESS, ticket=ticket)
            else:
                error_desc = result.comment if result else "Unknown error"
                return MT5TradeResult(MT5OperationResult.FAILED,
                                    error_description=error_desc)
                
        except Exception as e:
            self.logger.error(f"Position close error: {e}")
            return MT5TradeResult(MT5OperationResult.FAILED, error_description=str(e))
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information safely
        
        Returns:
            Account information or empty dict on error
        """
        if not self.is_connected:
            return {}
        
        try:
            account_info = self.mt5.account_info()
            if account_info:
                return {
                    'login': account_info.login,
                    'balance': account_info.balance,
                    'equity': account_info.equity,
                    'margin': account_info.margin,
                    'free_margin': account_info.margin_free,
                    'margin_level': account_info.margin_level,
                    'currency': account_info.currency,
                    'server': account_info.server,
                    'leverage': account_info.leverage,
                }
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return {}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get open positions safely
        
        Returns:
            List of position information
        """
        if not self.is_connected:
            return []
        
        try:
            positions = self.mt5.positions_get()
            if positions:
                return [
                    {
                        'ticket': pos.ticket,
                        'symbol': pos.symbol,
                        'type': 'BUY' if pos.type == 0 else 'SELL',
                        'volume': pos.volume,
                        'price_open': pos.price_open,
                        'price_current': pos.price_current,
                        'sl': pos.sl,
                        'tp': pos.tp,
                        'profit': pos.profit,
                        'swap': pos.swap,
                        'comment': pos.comment,
                        'time': pos.time,
                    }
                    for pos in positions
                ]
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on MT5 connection
        
        Returns:
            Health status information
        """
        health_status = {
            'connected': self.is_connected,
            'last_error': self.last_error,
            'connection_attempts': self.connection_attempts,
            'valid_symbols_count': len(self.valid_symbols),
        }
        
        if self.is_connected:
            try:
                # Test basic operations
                account_info = self.mt5.account_info()
                terminal_info = self.mt5.terminal_info()
                
                health_status.update({
                    'account_available': account_info is not None,
                    'terminal_available': terminal_info is not None,
                    'trading_allowed': terminal_info.trade_allowed if terminal_info else False,
                    'connection_quality': 'good' if account_info and terminal_info else 'degraded'
                })
                
            except Exception as e:
                health_status.update({
                    'connection_quality': 'poor',
                    'health_error': str(e)
                })
        
        return health_status

# Global secure MT5 bridge instance
secure_mt5_bridge = None

def initialize_secure_mt5(config: Dict[str, Any]) -> bool:
    """
    Initialize global secure MT5 bridge
    
    Args:
        config: MT5 configuration
        
    Returns:
        True if initialization successful
    """
    global secure_mt5_bridge
    try:
        secure_mt5_bridge = SecureMT5Bridge(config)
        return secure_mt5_bridge.connect()
    except Exception as e:
        logging.error(f"Failed to initialize secure MT5 bridge: {e}")
        return False

def get_secure_mt5_bridge() -> Optional[SecureMT5Bridge]:
    """Get global secure MT5 bridge instance"""
    return secure_mt5_bridge