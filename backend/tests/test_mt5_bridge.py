"""
Tests for MT5 bridge service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import socket
import json

from services.mt5_bridge import (
    MT5Bridge, MT5BridgeSocket, MT5BridgeFile, 
    MT5TradeRequest, MT5TradeResult, MT5OrderType, MT5TradeAction
)


class TestMT5TradeRequest:
    """Test cases for MT5 trade request"""
    
    def test_trade_request_creation(self):
        """Test creating MT5 trade request"""
        request = MT5TradeRequest(
            action=MT5TradeAction.TRADE_ACTION_DEAL,
            symbol="XAUUSD",
            volume=0.1,
            type=MT5OrderType.ORDER_TYPE_BUY,
            price=1950.0,
            sl=1940.0,
            tp=1960.0
        )
        
        assert request.action == MT5TradeAction.TRADE_ACTION_DEAL
        assert request.symbol == "XAUUSD"
        assert request.volume == 0.1
        assert request.type == MT5OrderType.ORDER_TYPE_BUY
        assert request.price == 1950.0
        assert request.sl == 1940.0
        assert request.tp == 1960.0


class TestMT5TradeResult:
    """Test cases for MT5 trade result"""
    
    def test_trade_result_creation(self):
        """Test creating MT5 trade result"""
        result = MT5TradeResult(
            retcode=10009,
            deal=12345,
            order=67890,
            volume=0.1,
            price=1950.0,
            bid=1949.5,
            ask=1950.5
        )
        
        assert result.retcode == 10009
        assert result.deal == 12345
        assert result.order == 67890
        assert result.volume == 0.1
        assert result.price == 1950.0
        assert result.bid == 1949.5
        assert result.ask == 1950.5


class TestMT5BridgeSocket:
    """Test cases for MT5 socket bridge"""
    
    @pytest.fixture
    def socket_bridge(self):
        """Create socket bridge instance"""
        return MT5BridgeSocket("127.0.0.1", 9999)
    
    @pytest.mark.asyncio
    async def test_connect_success(self, socket_bridge):
        """Test successful connection"""
        mock_socket = Mock()
        mock_socket.connect = Mock()
        
        with patch('socket.socket', return_value=mock_socket):
            with patch.object(socket_bridge, '_send_command', return_value={"status": "ok"}):
                result = await socket_bridge.connect()
                
                assert result is True
                assert socket_bridge.is_connected is True
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, socket_bridge):
        """Test connection failure"""
        with patch('socket.socket', side_effect=ConnectionError("Connection failed")):
            result = await socket_bridge.connect()
            
            assert result is False
            assert socket_bridge.is_connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect(self, socket_bridge):
        """Test disconnection"""
        mock_socket = Mock()
        socket_bridge.socket = mock_socket
        socket_bridge.is_connected = True
        
        await socket_bridge.disconnect()
        
        assert socket_bridge.is_connected is False
        assert socket_bridge.socket is None
        mock_socket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_trade_request(self, socket_bridge):
        """Test sending trade request"""
        socket_bridge.is_connected = True
        
        request = MT5TradeRequest(
            action=MT5TradeAction.TRADE_ACTION_DEAL,
            symbol="XAUUSD",
            volume=0.1,
            type=MT5OrderType.ORDER_TYPE_BUY
        )
        
        mock_response = {
            "result": {
                "retcode": 10009,
                "order": 12345,
                "deal": 67890,
                "volume": 0.1,
                "price": 1950.0
            }
        }
        
        with patch.object(socket_bridge, '_send_command', return_value=mock_response):
            result = await socket_bridge.send_trade_request(request)
            
            assert isinstance(result, MT5TradeResult)
            assert result.retcode == 10009
            assert result.order == 12345
            assert result.deal == 67890
    
    @pytest.mark.asyncio
    async def test_get_account_info(self, socket_bridge):
        """Test getting account info"""
        socket_bridge.is_connected = True
        
        mock_response = {
            "data": {
                "login": 12345,
                "balance": 10000.0,
                "equity": 10500.0,
                "margin": 500.0
            }
        }
        
        with patch.object(socket_bridge, '_send_command', return_value=mock_response):
            result = await socket_bridge.get_account_info()
            
            assert result["login"] == 12345
            assert result["balance"] == 10000.0
            assert result["equity"] == 10500.0
    
    @pytest.mark.asyncio
    async def test_get_symbol_info(self, socket_bridge):
        """Test getting symbol info"""
        socket_bridge.is_connected = True
        
        mock_response = {
            "data": {
                "symbol": "XAUUSD",
                "bid": 1949.5,
                "ask": 1950.5,
                "spread": 1.0,
                "digits": 2
            }
        }
        
        with patch.object(socket_bridge, '_send_command', return_value=mock_response):
            result = await socket_bridge.get_symbol_info("XAUUSD")
            
            assert result["symbol"] == "XAUUSD"
            assert result["bid"] == 1949.5
            assert result["ask"] == 1950.5
    
    @pytest.mark.asyncio
    async def test_get_positions(self, socket_bridge):
        """Test getting positions"""
        socket_bridge.is_connected = True
        
        mock_response = {
            "data": [
                {
                    "ticket": 12345,
                    "symbol": "XAUUSD",
                    "volume": 0.1,
                    "type": "BUY",
                    "profit": 150.0
                }
            ]
        }
        
        with patch.object(socket_bridge, '_send_command', return_value=mock_response):
            result = await socket_bridge.get_positions()
            
            assert len(result) == 1
            assert result[0]["ticket"] == 12345
            assert result[0]["symbol"] == "XAUUSD"
    
    @pytest.mark.asyncio
    async def test_command_not_connected(self, socket_bridge):
        """Test command when not connected"""
        socket_bridge.is_connected = False
        
        with pytest.raises(ConnectionError):
            await socket_bridge._send_command({"action": "test"})


class TestMT5BridgeFile:
    """Test cases for MT5 file bridge"""
    
    @pytest.fixture
    def file_bridge(self, tmp_path):
        """Create file bridge instance"""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        return MT5BridgeFile(str(input_dir), str(output_dir))
    
    @pytest.mark.asyncio
    async def test_connect_success(self, file_bridge):
        """Test successful connection via file"""
        # Create mock response file
        response_data = {"status": "ok"}
        
        async def mock_file_command(command):
            return response_data
        
        with patch.object(file_bridge, '_send_file_command', side_effect=mock_file_command):
            result = await file_bridge.connect()
            
            assert result is True
            assert file_bridge.is_connected is True
    
    @pytest.mark.asyncio
    async def test_connect_timeout(self, file_bridge):
        """Test connection timeout"""
        async def mock_timeout_command(command):
            raise TimeoutError("Connection timeout")
        
        with patch.object(file_bridge, '_send_file_command', side_effect=mock_timeout_command):
            result = await file_bridge.connect()
            
            assert result is False
            assert file_bridge.is_connected is False
    
    @pytest.mark.asyncio
    async def test_send_trade_request(self, file_bridge):
        """Test sending trade request via file"""
        file_bridge.is_connected = True
        
        request = MT5TradeRequest(
            action=MT5TradeAction.TRADE_ACTION_DEAL,
            symbol="XAUUSD",
            volume=0.1,
            type=MT5OrderType.ORDER_TYPE_BUY
        )
        
        mock_response = {
            "result": {
                "retcode": 10009,
                "order": 12345,
                "deal": 67890,
                "volume": 0.1,
                "price": 1950.0
            }
        }
        
        with patch.object(file_bridge, '_send_file_command', return_value=mock_response):
            result = await file_bridge.send_trade_request(request)
            
            assert isinstance(result, MT5TradeResult)
            assert result.retcode == 10009
            assert result.order == 12345
    
    def test_get_next_request_id(self, file_bridge):
        """Test request ID generation"""
        id1 = file_bridge._get_next_request_id()
        id2 = file_bridge._get_next_request_id()
        
        assert id2 == id1 + 1
    
    @pytest.mark.asyncio
    async def test_disconnect(self, file_bridge):
        """Test disconnection"""
        file_bridge.is_connected = True
        
        await file_bridge.disconnect()
        
        assert file_bridge.is_connected is False


class TestMT5Bridge:
    """Test cases for main MT5 bridge"""
    
    @pytest.fixture
    def mt5_bridge(self):
        """Create MT5 bridge instance"""
        return MT5Bridge(prefer_socket=True)
    
    @pytest.mark.asyncio
    async def test_connect_socket_success(self, mt5_bridge):
        """Test successful socket connection"""
        with patch.object(mt5_bridge.socket_bridge, 'connect', return_value=True):
            result = await mt5_bridge.connect()
            
            assert result is True
            assert mt5_bridge.is_connected is True
            assert mt5_bridge.active_bridge == mt5_bridge.socket_bridge
    
    @pytest.mark.asyncio
    async def test_connect_socket_fallback_to_file(self, mt5_bridge):
        """Test fallback from socket to file"""
        with patch.object(mt5_bridge.socket_bridge, 'connect', return_value=False):
            with patch.object(mt5_bridge.file_bridge, 'connect', return_value=True):
                result = await mt5_bridge.connect()
                
                assert result is True
                assert mt5_bridge.is_connected is True
                assert mt5_bridge.active_bridge == mt5_bridge.file_bridge
    
    @pytest.mark.asyncio
    async def test_connect_all_methods_fail(self, mt5_bridge):
        """Test when all connection methods fail"""
        with patch.object(mt5_bridge.socket_bridge, 'connect', return_value=False):
            with patch.object(mt5_bridge.file_bridge, 'connect', return_value=False):
                result = await mt5_bridge.connect()
                
                assert result is False
                assert mt5_bridge.is_connected is False
                assert mt5_bridge.active_bridge is None
    
    @pytest.mark.asyncio
    async def test_connect_file_first(self, mt5_bridge):
        """Test file connection first when preferred"""
        mt5_bridge.prefer_socket = False
        
        with patch.object(mt5_bridge.file_bridge, 'connect', return_value=True):
            result = await mt5_bridge.connect()
            
            assert result is True
            assert mt5_bridge.active_bridge == mt5_bridge.file_bridge
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mt5_bridge):
        """Test disconnection"""
        mock_bridge = Mock()
        mock_bridge.disconnect = AsyncMock()
        
        mt5_bridge.active_bridge = mock_bridge
        mt5_bridge.is_connected = True
        
        await mt5_bridge.disconnect()
        
        assert mt5_bridge.is_connected is False
        assert mt5_bridge.active_bridge is None
        mock_bridge.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_trade_request(self, mt5_bridge):
        """Test sending trade request"""
        mock_bridge = Mock()
        mock_bridge.send_trade_request = AsyncMock(return_value=MT5TradeResult(retcode=10009))
        
        mt5_bridge.active_bridge = mock_bridge
        mt5_bridge.is_connected = True
        
        request = MT5TradeRequest(
            action=MT5TradeAction.TRADE_ACTION_DEAL,
            symbol="XAUUSD",
            volume=0.1,
            type=MT5OrderType.ORDER_TYPE_BUY
        )
        
        result = await mt5_bridge.send_trade_request(request)
        
        assert isinstance(result, MT5TradeResult)
        assert result.retcode == 10009
        mock_bridge.send_trade_request.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_get_account_info(self, mt5_bridge):
        """Test getting account info"""
        mock_bridge = Mock()
        mock_bridge.get_account_info = AsyncMock(return_value={"login": 12345})
        
        mt5_bridge.active_bridge = mock_bridge
        mt5_bridge.is_connected = True
        
        result = await mt5_bridge.get_account_info()
        
        assert result["login"] == 12345
        mock_bridge.get_account_info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_not_connected_error(self, mt5_bridge):
        """Test error when not connected"""
        mt5_bridge.is_connected = False
        
        request = MT5TradeRequest(
            action=MT5TradeAction.TRADE_ACTION_DEAL,
            symbol="XAUUSD",
            volume=0.1,
            type=MT5OrderType.ORDER_TYPE_BUY
        )
        
        with pytest.raises(ConnectionError):
            await mt5_bridge.send_trade_request(request)
    
    @pytest.mark.asyncio
    async def test_get_symbol_info(self, mt5_bridge):
        """Test getting symbol info"""
        mock_bridge = Mock()
        mock_bridge.get_symbol_info = AsyncMock(return_value={"symbol": "XAUUSD"})
        
        mt5_bridge.active_bridge = mock_bridge
        mt5_bridge.is_connected = True
        
        result = await mt5_bridge.get_symbol_info("XAUUSD")
        
        assert result["symbol"] == "XAUUSD"
        mock_bridge.get_symbol_info.assert_called_once_with("XAUUSD")
    
    @pytest.mark.asyncio
    async def test_get_positions(self, mt5_bridge):
        """Test getting positions"""
        mock_bridge = Mock()
        mock_bridge.get_positions = AsyncMock(return_value=[{"ticket": 12345}])
        
        mt5_bridge.active_bridge = mock_bridge
        mt5_bridge.is_connected = True
        
        result = await mt5_bridge.get_positions()
        
        assert len(result) == 1
        assert result[0]["ticket"] == 12345
        mock_bridge.get_positions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_orders(self, mt5_bridge):
        """Test getting orders"""
        mock_bridge = Mock()
        mock_bridge.get_orders = AsyncMock(return_value=[{"ticket": 12345}])
        
        mt5_bridge.active_bridge = mock_bridge
        mt5_bridge.is_connected = True
        
        result = await mt5_bridge.get_orders()
        
        assert len(result) == 1
        assert result[0]["ticket"] == 12345
        mock_bridge.get_orders.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])