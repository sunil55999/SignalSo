"""
Tests for trade API endpoints
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from api.trades import trades_router, OpenTradeRequest, CloseTradeRequest, ModifyTradeRequest, TradeType
from services.mt5_bridge import MT5TradeResult, MT5OrderType, MT5TradeAction


class TestTradesAPI:
    """Test cases for trades API endpoints"""
    
    @pytest.fixture
    def mock_mt5_bridge(self):
        """Create mock MT5 bridge"""
        bridge = Mock()
        bridge.is_connected = True
        bridge.connect = AsyncMock(return_value=True)
        bridge.send_trade_request = AsyncMock()
        bridge.get_positions = AsyncMock(return_value=[])
        bridge.get_account_info = AsyncMock(return_value={})
        bridge.get_symbol_info = AsyncMock(return_value={})
        return bridge
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = Mock()
        request.state = Mock()
        request.state.user_id = "test_user"
        return request
    
    @pytest.mark.asyncio
    async def test_open_trade_success(self, mock_mt5_bridge, mock_request):
        """Test successful trade opening"""
        # Mock successful MT5 response
        mock_result = MT5TradeResult(
            retcode=10009,  # TRADE_RETCODE_DONE
            order=12345,
            deal=67890,
            volume=0.1,
            price=1950.0
        )
        mock_mt5_bridge.send_trade_request.return_value = mock_result
        
        request = OpenTradeRequest(
            symbol="XAUUSD",
            type=TradeType.BUY,
            volume=0.1,
            price=1950.0,
            sl=1940.0,
            tp=[1960.0]
        )
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import open_trade
            response = await open_trade(request, mock_request)
            
            assert response.success is True
            assert response.ticket == 12345
            assert "XAUUSD" in response.message
    
    @pytest.mark.asyncio
    async def test_open_trade_failure(self, mock_mt5_bridge, mock_request):
        """Test failed trade opening"""
        # Mock failed MT5 response
        mock_result = MT5TradeResult(
            retcode=10013,  # TRADE_RETCODE_INVALID_PRICE
            order=0,
            deal=0,
            volume=0.0,
            price=0.0
        )
        mock_mt5_bridge.send_trade_request.return_value = mock_result
        
        request = OpenTradeRequest(
            symbol="XAUUSD",
            type=TradeType.BUY,
            volume=0.1,
            price=1950.0
        )
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import open_trade
            response = await open_trade(request, mock_request)
            
            assert response.success is False
            assert response.error is not None
            assert "10013" in response.error
    
    @pytest.mark.asyncio
    async def test_close_trade_success(self, mock_mt5_bridge, mock_request):
        """Test successful trade closing"""
        # Mock position exists
        mock_positions = [
            {"ticket": 12345, "symbol": "XAUUSD", "volume": 0.1}
        ]
        mock_mt5_bridge.get_positions.return_value = mock_positions
        
        # Mock successful close response
        mock_result = MT5TradeResult(
            retcode=10009,  # TRADE_RETCODE_DONE
            order=12345,
            deal=67890,
            volume=0.1,
            price=1955.0
        )
        mock_mt5_bridge.send_trade_request.return_value = mock_result
        
        request = CloseTradeRequest(
            ticket=12345,
            reason="Test close"
        )
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import close_trade
            response = await close_trade(request, mock_request)
            
            assert response.success is True
            assert response.ticket == 12345
            assert "Test close" in response.message
    
    @pytest.mark.asyncio
    async def test_close_trade_not_found(self, mock_mt5_bridge, mock_request):
        """Test closing non-existent trade"""
        # Mock no positions
        mock_mt5_bridge.get_positions.return_value = []
        
        request = CloseTradeRequest(
            ticket=99999,
            reason="Test close"
        )
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import close_trade
            
            with pytest.raises(Exception):  # Should raise HTTPException
                await close_trade(request, mock_request)
    
    @pytest.mark.asyncio
    async def test_modify_trade_success(self, mock_mt5_bridge, mock_request):
        """Test successful trade modification"""
        # Mock successful modify response
        mock_result = MT5TradeResult(
            retcode=10009,  # TRADE_RETCODE_DONE
            order=12345,
            deal=0,
            volume=0.0,
            price=0.0
        )
        mock_mt5_bridge.send_trade_request.return_value = mock_result
        
        request = ModifyTradeRequest(
            ticket=12345,
            sl=1935.0,
            tp=1965.0
        )
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import modify_trade
            response = await modify_trade(request, mock_request)
            
            assert response.success is True
            assert response.ticket == 12345
            assert "modified successfully" in response.message
    
    @pytest.mark.asyncio
    async def test_get_trade_status(self, mock_mt5_bridge, mock_request):
        """Test getting trade status"""
        # Mock positions
        mock_positions = [
            {
                "ticket": 12345,
                "symbol": "XAUUSD",
                "type": "BUY",
                "volume": 0.1,
                "profit": 150.0,
                "price_open": 1950.0,
                "price_current": 1965.0,
                "sl": 1940.0,
                "tp": 1970.0,
                "time": datetime.utcnow().isoformat()
            }
        ]
        mock_mt5_bridge.get_positions.return_value = mock_positions
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import get_trade_status
            response = await get_trade_status(mock_request)
            
            assert len(response) == 1
            assert response[0].ticket == 12345
            assert response[0].symbol == "XAUUSD"
            assert response[0].profit_loss == 150.0
    
    @pytest.mark.asyncio
    async def test_get_trade_history(self, mock_request):
        """Test getting trade history"""
        with patch('api.trades.mt5_bridge'):
            from api.trades import get_trade_history
            response = await get_trade_history(mock_request)
            
            assert "trades" in response
            assert "total" in response
            assert "limit" in response
            assert "offset" in response
            assert "has_more" in response
    
    @pytest.mark.asyncio
    async def test_get_account_info(self, mock_mt5_bridge, mock_request):
        """Test getting account information"""
        # Mock account info
        mock_account = {
            "login": 12345,
            "balance": 10000.0,
            "equity": 10500.0,
            "margin": 500.0,
            "profit": 500.0,
            "margin_free": 9500.0
        }
        mock_mt5_bridge.get_account_info.return_value = mock_account
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import get_account_info
            response = await get_account_info(mock_request)
            
            assert response["login"] == 12345
            assert response["balance"] == 10000.0
            assert response["equity"] == 10500.0
            assert "margin_level" in response
    
    @pytest.mark.asyncio
    async def test_get_symbol_info(self, mock_mt5_bridge, mock_request):
        """Test getting symbol information"""
        # Mock symbol info
        mock_symbol = {
            "symbol": "XAUUSD",
            "bid": 1949.5,
            "ask": 1950.5,
            "spread": 1.0,
            "digits": 2,
            "contract_size": 100.0
        }
        mock_mt5_bridge.get_symbol_info.return_value = mock_symbol
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import get_symbol_info
            response = await get_symbol_info("XAUUSD", mock_request)
            
            assert response["symbol"] == "XAUUSD"
            assert response["bid"] == 1949.5
            assert response["ask"] == 1950.5
    
    @pytest.mark.asyncio
    async def test_bulk_close_trades(self, mock_mt5_bridge, mock_request):
        """Test bulk closing trades"""
        # Mock positions
        mock_positions = [
            {
                "ticket": 12345,
                "symbol": "XAUUSD",
                "type": "BUY",
                "profit": 150.0
            },
            {
                "ticket": 12346,
                "symbol": "EURUSD",
                "type": "BUY",
                "profit": 50.0
            }
        ]
        mock_mt5_bridge.get_positions.return_value = mock_positions
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import bulk_close_trades
            response = await bulk_close_trades(mock_request, symbol="XAUUSD")
            
            assert response["success"] is True
            assert response["closed_count"] == 1  # Only XAUUSD position
            assert response["failed_count"] == 0
            assert "closed_trades" in response
            assert "total_profit" in response
    
    @pytest.mark.asyncio
    async def test_bulk_close_with_profit_threshold(self, mock_mt5_bridge, mock_request):
        """Test bulk closing trades with profit threshold"""
        # Mock positions
        mock_positions = [
            {
                "ticket": 12345,
                "symbol": "XAUUSD",
                "type": "BUY",
                "profit": 150.0
            },
            {
                "ticket": 12346,
                "symbol": "EURUSD",
                "type": "BUY",
                "profit": 25.0
            }
        ]
        mock_mt5_bridge.get_positions.return_value = mock_positions
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import bulk_close_trades
            response = await bulk_close_trades(mock_request, profit_threshold=100.0)
            
            assert response["success"] is True
            assert response["closed_count"] == 1  # Only position with profit >= 100
            assert response["failed_count"] == 0
    
    def test_convert_to_mt5_order_type(self):
        """Test conversion of API trade types to MT5 order types"""
        from api.trades import _convert_to_mt5_order_type
        
        assert _convert_to_mt5_order_type(TradeType.BUY) == MT5OrderType.ORDER_TYPE_BUY
        assert _convert_to_mt5_order_type(TradeType.SELL) == MT5OrderType.ORDER_TYPE_SELL
        assert _convert_to_mt5_order_type(TradeType.BUY_LIMIT) == MT5OrderType.ORDER_TYPE_BUY_LIMIT
        assert _convert_to_mt5_order_type(TradeType.SELL_LIMIT) == MT5OrderType.ORDER_TYPE_SELL_LIMIT
        assert _convert_to_mt5_order_type(TradeType.BUY_STOP) == MT5OrderType.ORDER_TYPE_BUY_STOP
        assert _convert_to_mt5_order_type(TradeType.SELL_STOP) == MT5OrderType.ORDER_TYPE_SELL_STOP
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, mock_mt5_bridge, mock_request):
        """Test handling of connection errors"""
        # Mock connection failure
        mock_mt5_bridge.is_connected = False
        mock_mt5_bridge.connect.return_value = False
        
        request = OpenTradeRequest(
            symbol="XAUUSD",
            type=TradeType.BUY,
            volume=0.1
        )
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import open_trade
            
            # Should still attempt to connect
            await open_trade(request, mock_request)
            mock_mt5_bridge.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invalid_ticket_handling(self, mock_request):
        """Test handling of invalid ticket numbers"""
        request = CloseTradeRequest(
            ticket=None,
            order_id=None
        )
        
        with patch('api.trades.mt5_bridge'):
            from api.trades import close_trade
            
            with pytest.raises(Exception):  # Should raise HTTPException
                await close_trade(request, mock_request)
    
    @pytest.mark.asyncio
    async def test_symbol_filtering(self, mock_mt5_bridge, mock_request):
        """Test filtering trades by symbol"""
        # Mock positions with different symbols
        mock_positions = [
            {
                "ticket": 12345,
                "symbol": "XAUUSD",
                "type": "BUY",
                "volume": 0.1,
                "profit": 150.0,
                "price_open": 1950.0,
                "price_current": 1965.0,
                "sl": 1940.0,
                "tp": 1970.0,
                "time": datetime.utcnow().isoformat()
            },
            {
                "ticket": 12346,
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 0.2,
                "profit": 50.0,
                "price_open": 1.0850,
                "price_current": 1.0875,
                "sl": 1.0800,
                "tp": 1.0900,
                "time": datetime.utcnow().isoformat()
            }
        ]
        mock_mt5_bridge.get_positions.return_value = mock_positions
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import get_trade_status
            response = await get_trade_status(mock_request, symbol="XAUUSD")
            
            assert len(response) == 1
            assert response[0].symbol == "XAUUSD"
    
    @pytest.mark.asyncio
    async def test_ticket_filtering(self, mock_mt5_bridge, mock_request):
        """Test filtering trades by ticket"""
        # Mock positions
        mock_positions = [
            {
                "ticket": 12345,
                "symbol": "XAUUSD",
                "type": "BUY",
                "volume": 0.1,
                "profit": 150.0,
                "price_open": 1950.0,
                "price_current": 1965.0,
                "sl": 1940.0,
                "tp": 1970.0,
                "time": datetime.utcnow().isoformat()
            }
        ]
        mock_mt5_bridge.get_positions.return_value = mock_positions
        
        with patch('api.trades.mt5_bridge', mock_mt5_bridge):
            from api.trades import get_trade_status
            response = await get_trade_status(mock_request, ticket=12345)
            
            assert len(response) == 1
            assert response[0].ticket == 12345


if __name__ == "__main__":
    pytest.main([__file__])