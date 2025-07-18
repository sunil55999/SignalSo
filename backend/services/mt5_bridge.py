"""
MT5 Bridge Service - Socket/File-based MT5 connector
"""

import asyncio
import json
import socket
import struct
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import tempfile
import os
from datetime import datetime

from utils.logging_config import get_logger

logger = get_logger("mt5_bridge")


class MT5OrderType(Enum):
    """MT5 Order types"""
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TYPE_BUY_STOP_LIMIT = 6
    ORDER_TYPE_SELL_STOP_LIMIT = 7


class MT5TradeAction(Enum):
    """MT5 Trade actions"""
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_SLTP = 6
    TRADE_ACTION_MODIFY = 7
    TRADE_ACTION_REMOVE = 8
    TRADE_ACTION_CLOSE_BY = 10


@dataclass
class MT5TradeRequest:
    """MT5 trade request structure"""
    action: MT5TradeAction
    symbol: str
    volume: float
    type: MT5OrderType
    price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    deviation: int = 10
    magic: int = 12345
    comment: str = "SignalOS"
    type_filling: int = 0  # ORDER_FILLING_FOK
    type_time: int = 0     # ORDER_TIME_GTC
    expiration: int = 0


@dataclass
class MT5TradeResult:
    """MT5 trade result structure"""
    retcode: int
    deal: int = 0
    order: int = 0
    volume: float = 0.0
    price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    comment: str = ""
    request_id: int = 0
    retcode_external: int = 0


class MT5BridgeSocket:
    """Socket-based MT5 bridge connector"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9999, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.is_connected = False
        self._lock = asyncio.Lock()
    
    async def connect(self) -> bool:
        """Connect to MT5 bridge socket"""
        try:
            async with self._lock:
                if self.is_connected:
                    return True
                
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.timeout)
                
                # Connect asynchronously
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.socket.connect, (self.host, self.port))
                
                # Send handshake
                handshake = {"action": "handshake", "client": "SignalOS", "version": "1.0.0"}
                response = await self._send_command(handshake)
                
                if response.get("status") == "ok":
                    self.is_connected = True
                    logger.info(f"Connected to MT5 bridge at {self.host}:{self.port}")
                    return True
                else:
                    logger.error(f"MT5 bridge handshake failed: {response}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to connect to MT5 bridge: {e}")
            await self.disconnect()
            return False
    
    async def disconnect(self):
        """Disconnect from MT5 bridge"""
        async with self._lock:
            self.is_connected = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                finally:
                    self.socket = None
                    logger.info("Disconnected from MT5 bridge")
    
    async def _send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to MT5 bridge via socket"""
        try:
            # Serialize command
            command_json = json.dumps(command)
            command_bytes = command_json.encode('utf-8')
            
            # Send length first (4 bytes)
            length = len(command_bytes)
            length_bytes = struct.pack('<I', length)
            
            # Send command
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.socket.sendall, length_bytes + command_bytes)
            
            # Receive response length
            response_length_bytes = await loop.run_in_executor(None, self._recv_exact, 4)
            response_length = struct.unpack('<I', response_length_bytes)[0]
            
            # Receive response data
            response_bytes = await loop.run_in_executor(None, self._recv_exact, response_length)
            response_json = response_bytes.decode('utf-8')
            
            # Parse response
            response = json.loads(response_json)
            
            logger.debug(f"MT5 command: {command.get('action')} -> {response.get('retcode', 'unknown')}")
            
            return response
            
        except Exception as e:
            logger.error(f"MT5 command error: {e}")
            raise
    
    def _recv_exact(self, size: int) -> bytes:
        """Receive exact number of bytes"""
        data = b""
        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                raise ConnectionError("Socket connection lost")
            data += chunk
        return data
    
    async def send_trade_request(self, request: MT5TradeRequest) -> MT5TradeResult:
        """Send trade request to MT5"""
        if not self.is_connected:
            raise ConnectionError("Not connected to MT5 bridge")
        
        command = {
            "action": "trade_request",
            "request": {
                "action": request.action.value,
                "symbol": request.symbol,
                "volume": request.volume,
                "type": request.type.value,
                "price": request.price,
                "sl": request.sl,
                "tp": request.tp,
                "deviation": request.deviation,
                "magic": request.magic,
                "comment": request.comment,
                "type_filling": request.type_filling,
                "type_time": request.type_time,
                "expiration": request.expiration
            }
        }
        
        response = await self._send_command(command)
        
        # Convert response to MT5TradeResult
        result_data = response.get("result", {})
        return MT5TradeResult(
            retcode=result_data.get("retcode", 10000),
            deal=result_data.get("deal", 0),
            order=result_data.get("order", 0),
            volume=result_data.get("volume", 0.0),
            price=result_data.get("price", 0.0),
            bid=result_data.get("bid", 0.0),
            ask=result_data.get("ask", 0.0),
            comment=result_data.get("comment", ""),
            request_id=result_data.get("request_id", 0),
            retcode_external=result_data.get("retcode_external", 0)
        )
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get MT5 account information"""
        command = {"action": "account_info"}
        response = await self._send_command(command)
        return response.get("data", {})
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get MT5 symbol information"""
        command = {"action": "symbol_info", "symbol": symbol}
        response = await self._send_command(command)
        return response.get("data", {})
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        command = {"action": "positions_get"}
        response = await self._send_command(command)
        return response.get("data", [])
    
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get all pending orders"""
        command = {"action": "orders_get"}
        response = await self._send_command(command)
        return response.get("data", [])


class MT5BridgeFile:
    """File-based MT5 bridge connector"""
    
    def __init__(self, input_dir: str = None, output_dir: str = None):
        self.input_dir = Path(input_dir) if input_dir else Path(tempfile.gettempdir()) / "mt5_input"
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "mt5_output"
        
        # Create directories
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        self.is_connected = False
        self._request_counter = 0
    
    async def connect(self) -> bool:
        """Test file bridge connection"""
        try:
            # Create test file
            test_file = self.input_dir / "test_connection.json"
            test_data = {
                "action": "test_connection",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": self._get_next_request_id()
            }
            
            with open(test_file, 'w') as f:
                json.dump(test_data, f)
            
            # Wait for response (with timeout)
            response_file = self.output_dir / f"response_{test_data['request_id']}.json"
            
            for _ in range(30):  # 30 second timeout
                if response_file.exists():
                    with open(response_file, 'r') as f:
                        response = json.load(f)
                    
                    # Clean up files
                    test_file.unlink(missing_ok=True)
                    response_file.unlink(missing_ok=True)
                    
                    if response.get("status") == "ok":
                        self.is_connected = True
                        logger.info(f"Connected to MT5 bridge via file system")
                        return True
                
                await asyncio.sleep(1)
            
            logger.error("MT5 bridge file connection timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to MT5 bridge via files: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect file bridge"""
        self.is_connected = False
        logger.info("Disconnected from MT5 bridge file system")
    
    def _get_next_request_id(self) -> int:
        """Get next request ID"""
        self._request_counter += 1
        return self._request_counter
    
    async def _send_file_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command via file system"""
        try:
            request_id = self._get_next_request_id()
            command["request_id"] = request_id
            command["timestamp"] = datetime.utcnow().isoformat()
            
            # Write request file
            request_file = self.input_dir / f"request_{request_id}.json"
            with open(request_file, 'w') as f:
                json.dump(command, f)
            
            # Wait for response
            response_file = self.output_dir / f"response_{request_id}.json"
            
            for _ in range(30):  # 30 second timeout
                if response_file.exists():
                    with open(response_file, 'r') as f:
                        response = json.load(f)
                    
                    # Clean up files
                    request_file.unlink(missing_ok=True)
                    response_file.unlink(missing_ok=True)
                    
                    return response
                
                await asyncio.sleep(1)
            
            raise TimeoutError(f"File command timeout for request {request_id}")
            
        except Exception as e:
            logger.error(f"File command error: {e}")
            raise
    
    async def send_trade_request(self, request: MT5TradeRequest) -> MT5TradeResult:
        """Send trade request via file system"""
        if not self.is_connected:
            raise ConnectionError("Not connected to MT5 bridge")
        
        command = {
            "action": "trade_request",
            "request": {
                "action": request.action.value,
                "symbol": request.symbol,
                "volume": request.volume,
                "type": request.type.value,
                "price": request.price,
                "sl": request.sl,
                "tp": request.tp,
                "deviation": request.deviation,
                "magic": request.magic,
                "comment": request.comment,
                "type_filling": request.type_filling,
                "type_time": request.type_time,
                "expiration": request.expiration
            }
        }
        
        response = await self._send_file_command(command)
        
        # Convert response to MT5TradeResult
        result_data = response.get("result", {})
        return MT5TradeResult(
            retcode=result_data.get("retcode", 10000),
            deal=result_data.get("deal", 0),
            order=result_data.get("order", 0),
            volume=result_data.get("volume", 0.0),
            price=result_data.get("price", 0.0),
            bid=result_data.get("bid", 0.0),
            ask=result_data.get("ask", 0.0),
            comment=result_data.get("comment", ""),
            request_id=result_data.get("request_id", 0),
            retcode_external=result_data.get("retcode_external", 0)
        )
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get MT5 account information"""
        command = {"action": "account_info"}
        response = await self._send_file_command(command)
        return response.get("data", {})
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get MT5 symbol information"""
        command = {"action": "symbol_info", "symbol": symbol}
        response = await self._send_file_command(command)
        return response.get("data", {})
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        command = {"action": "positions_get"}
        response = await self._send_file_command(command)
        return response.get("data", [])
    
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get all pending orders"""
        command = {"action": "orders_get"}
        response = await self._send_file_command(command)
        return response.get("data", [])


class MT5Bridge:
    """Main MT5 bridge service with fallback support"""
    
    def __init__(self, prefer_socket: bool = True, socket_host: str = "127.0.0.1", 
                 socket_port: int = 9999, file_input_dir: str = None, 
                 file_output_dir: str = None):
        self.prefer_socket = prefer_socket
        self.socket_bridge = MT5BridgeSocket(socket_host, socket_port)
        self.file_bridge = MT5BridgeFile(file_input_dir, file_output_dir)
        self.active_bridge = None
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Connect using preferred method with fallback"""
        try:
            if self.prefer_socket:
                # Try socket first
                if await self.socket_bridge.connect():
                    self.active_bridge = self.socket_bridge
                    self.is_connected = True
                    logger.info("Using socket bridge for MT5 connection")
                    return True
                
                # Fallback to file bridge
                logger.warning("Socket bridge failed, trying file bridge")
                if await self.file_bridge.connect():
                    self.active_bridge = self.file_bridge
                    self.is_connected = True
                    logger.info("Using file bridge for MT5 connection")
                    return True
            else:
                # Try file first
                if await self.file_bridge.connect():
                    self.active_bridge = self.file_bridge
                    self.is_connected = True
                    logger.info("Using file bridge for MT5 connection")
                    return True
                
                # Fallback to socket bridge
                logger.warning("File bridge failed, trying socket bridge")
                if await self.socket_bridge.connect():
                    self.active_bridge = self.socket_bridge
                    self.is_connected = True
                    logger.info("Using socket bridge for MT5 connection")
                    return True
            
            logger.error("All MT5 bridge connection methods failed")
            return False
            
        except Exception as e:
            logger.error(f"MT5 bridge connection error: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MT5 bridge"""
        if self.active_bridge:
            await self.active_bridge.disconnect()
            self.active_bridge = None
        
        self.is_connected = False
        logger.info("MT5 bridge disconnected")
    
    async def send_trade_request(self, request: MT5TradeRequest) -> MT5TradeResult:
        """Send trade request to MT5"""
        if not self.is_connected or not self.active_bridge:
            raise ConnectionError("Not connected to MT5 bridge")
        
        return await self.active_bridge.send_trade_request(request)
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get MT5 account information"""
        if not self.is_connected or not self.active_bridge:
            raise ConnectionError("Not connected to MT5 bridge")
        
        return await self.active_bridge.get_account_info()
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get MT5 symbol information"""
        if not self.is_connected or not self.active_bridge:
            raise ConnectionError("Not connected to MT5 bridge")
        
        return await self.active_bridge.get_symbol_info(symbol)
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        if not self.is_connected or not self.active_bridge:
            raise ConnectionError("Not connected to MT5 bridge")
        
        return await self.active_bridge.get_positions()
    
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get all pending orders"""
        if not self.is_connected or not self.active_bridge:
            raise ConnectionError("Not connected to MT5 bridge")
        
        return await self.active_bridge.get_orders()


# Global bridge instance
_mt5_bridge = None


def get_mt5_bridge() -> MT5Bridge:
    """Get global MT5 bridge instance"""
    global _mt5_bridge
    if _mt5_bridge is None:
        _mt5_bridge = MT5Bridge()
    return _mt5_bridge