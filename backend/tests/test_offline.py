"""
Tests for offline operations functionality
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from core.offline import OfflineOperationEngine, ConflictResolution


class TestOfflineOperationEngine:
    """Test offline operation engine functionality"""
    
    @pytest.fixture
    def engine(self):
        """Create offline operation engine instance"""
        return OfflineOperationEngine("test_user", "test_offline.db")
    
    @pytest.mark.asyncio
    async def test_initialization(self, engine):
        """Test engine initialization"""
        await engine.initialize()
        assert engine.user_id == "test_user"
        assert engine.offline_db_path == "test_offline.db"
    
    @pytest.mark.asyncio
    async def test_parse_signal_offline(self, engine):
        """Test offline signal parsing"""
        await engine.initialize()
        
        # Mock the parser service
        with patch.object(engine.parser_service, 'parse_offline') as mock_parse:
            mock_parse.return_value = {
                "id": "signal_123",
                "symbol": "EURUSD",
                "action": "BUY",
                "entry_price": 1.0850,
                "confidence": 0.95,
                "raw_text": "BUY EURUSD at 1.0850"
            }
            
            result = await engine.parse_signal_offline("BUY EURUSD at 1.0850")
            
            assert result["symbol"] == "EURUSD"
            assert result["action"] == "BUY"
            assert result["confidence"] == 0.95
            mock_parse.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_trade_offline(self, engine):
        """Test offline trade execution"""
        await engine.initialize()
        
        trade_params = {
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": 0.1,
            "price": 1.0850,
            "sl": 1.0800,
            "tp": 1.0900
        }
        
        result = await engine.execute_trade_offline(trade_params)
        
        assert result["success"] is True
        assert result["status"] == "queued_offline"
        assert "trade_id" in result
    
    @pytest.mark.asyncio
    async def test_get_offline_status(self, engine):
        """Test getting offline status"""
        await engine.initialize()
        
        status = await engine.get_offline_status()
        
        assert "is_online" in status
        assert "unsynced_actions" in status
        assert "unsynced_signals" in status
        assert "unsynced_trades" in status
        assert "offline_mode_active" in status
    
    @pytest.mark.asyncio
    async def test_set_online_status(self, engine):
        """Test setting online status"""
        await engine.initialize()
        
        # Test going online
        with patch.object(engine, 'sync_offline_actions') as mock_sync:
            mock_sync.return_value = {"successful": 0, "failed": 0}
            
            await engine.set_online_status(True)
            assert engine.is_online is True
            mock_sync.assert_called_once()
        
        # Test going offline
        await engine.set_online_status(False)
        assert engine.is_online is False
    
    @pytest.mark.asyncio
    async def test_sync_offline_actions(self, engine):
        """Test syncing offline actions"""
        await engine.initialize()
        
        # Mock unsynced actions
        with patch.object(engine, '_get_unsynced_actions') as mock_get:
            mock_get.return_value = [
                {
                    "id": "action_1",
                    "action_type": "SIGNAL_PARSE",
                    "payload": {"test": "data"},
                    "timestamp": datetime.now().isoformat(),
                    "sync_attempts": 0
                }
            ]
            
            with patch.object(engine, '_sync_single_action') as mock_sync:
                mock_sync.return_value = {"success": True}
                
                result = await engine.sync_offline_actions()
                
                assert result["total_actions"] == 1
                assert result["successful"] == 1
                assert result["failed"] == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_old_actions(self, engine):
        """Test cleaning up old actions"""
        await engine.initialize()
        
        deleted_count = await engine.cleanup_old_actions(30)
        
        assert isinstance(deleted_count, int)
        assert deleted_count >= 0


class TestOfflineAPI:
    """Test offline API endpoints"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return {"user_id": "test_user", "username": "test@example.com"}
    
    @pytest.mark.asyncio
    async def test_parse_signal_offline_endpoint(self, mock_user):
        """Test offline signal parsing endpoint"""
        from api.offline import parse_signal_offline
        
        request = Mock()
        request.text = "BUY EURUSD at 1.0850"
        request.image_data = None
        request.provider_id = None
        
        with patch('core.offline.OfflineOperationEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.parse_signal_offline.return_value = {
                "symbol": "EURUSD",
                "action": "BUY",
                "confidence": 0.95
            }
            mock_engine.return_value = mock_instance
            
            result = await parse_signal_offline(request, mock_user)
            
            assert result["success"] is True
            assert "signal" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.parse_signal_offline.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_trade_offline_endpoint(self, mock_user):
        """Test offline trade execution endpoint"""
        from api.offline import execute_trade_offline
        
        request = Mock()
        request.symbol = "EURUSD"
        request.type = "BUY"
        request.volume = 0.1
        request.price = 1.0850
        request.sl = 1.0800
        request.tp = 1.0900
        
        with patch('core.offline.OfflineOperationEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.execute_trade_offline.return_value = {
                "success": True,
                "trade_id": "trade_123",
                "status": "queued_offline"
            }
            mock_engine.return_value = mock_instance
            
            result = await execute_trade_offline(request, mock_user)
            
            assert result["success"] is True
            assert "trade" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.execute_trade_offline.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_offline_actions_endpoint(self, mock_user):
        """Test sync offline actions endpoint"""
        from api.offline import sync_offline_actions
        
        request = Mock()
        request.force_sync = True
        
        background_tasks = Mock()
        
        with patch('core.offline.OfflineOperationEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.sync_offline_actions.return_value = {
                "successful": 5,
                "failed": 0,
                "conflicts": 0
            }
            mock_engine.return_value = mock_instance
            
            result = await sync_offline_actions(request, background_tasks, mock_user)
            
            assert result["success"] is True
            assert "sync_result" in result
            mock_instance.set_online_status.assert_called_once_with(True)
            mock_instance.sync_offline_actions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_offline_status_endpoint(self, mock_user):
        """Test get offline status endpoint"""
        from api.offline import get_offline_status
        
        with patch('core.offline.OfflineOperationEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.get_offline_status.return_value = {
                "is_online": False,
                "unsynced_actions": 3,
                "unsynced_signals": 2,
                "unsynced_trades": 1
            }
            mock_engine.return_value = mock_instance
            
            result = await get_offline_status(mock_user)
            
            assert result["success"] is True
            assert "status" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.get_offline_status.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])