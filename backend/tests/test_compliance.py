"""
Tests for compliance functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from core.compliance import ComplianceEngine, ComplianceMode, RiskLevel, TradingRestriction, ComplianceRule


class TestComplianceEngine:
    """Test compliance engine functionality"""
    
    @pytest.fixture
    def engine(self):
        """Create compliance engine instance"""
        return ComplianceEngine()
    
    @pytest.mark.asyncio
    async def test_initialization(self, engine):
        """Test engine initialization"""
        await engine.initialize()
        assert engine.default_profiles is not None
        assert len(engine.default_profiles) > 0
        assert "ftmo" in engine.default_profiles
        assert "eu_mifid_ii" in engine.default_profiles
    
    @pytest.mark.asyncio
    async def test_activate_compliance_mode(self, engine):
        """Test compliance mode activation"""
        await engine.initialize()
        
        with patch.object(engine, '_update_user_compliance_db') as mock_update:
            result = await engine.activate_compliance_mode("user_123", "ftmo")
            
            assert result["success"] is True
            assert result["profile"] == "ftmo"
            assert "user_123" in engine.active_profiles
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_activate_compliance_mode_unknown_profile(self, engine):
        """Test compliance mode activation with unknown profile"""
        await engine.initialize()
        
        result = await engine.activate_compliance_mode("user_123", "unknown_profile")
        
        assert result["success"] is False
        assert "Unknown compliance profile" in result["error"]
    
    @pytest.mark.asyncio
    async def test_deactivate_compliance_mode(self, engine):
        """Test compliance mode deactivation"""
        await engine.initialize()
        
        # First activate a profile
        engine.active_profiles["user_123"] = {
            "profile_name": "ftmo",
            "profile": engine.default_profiles["ftmo"]
        }
        
        with patch.object(engine, '_deactivate_user_compliance_db') as mock_deactivate:
            result = await engine.deactivate_compliance_mode("user_123")
            
            assert result["success"] is True
            assert "user_123" not in engine.active_profiles
            mock_deactivate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_trade_no_compliance(self, engine):
        """Test trade validation with no compliance mode"""
        await engine.initialize()
        
        trade_params = {
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": 1.0,
            "sl": 1.0800,
            "tp": 1.0900
        }
        
        result = await engine.validate_trade("user_123", trade_params)
        
        assert result["valid"] is True
        assert result["message"] == "No compliance mode active"
    
    @pytest.mark.asyncio
    async def test_validate_trade_with_compliance(self, engine):
        """Test trade validation with compliance mode"""
        await engine.initialize()
        
        # Activate FTMO profile
        engine.active_profiles["user_123"] = {
            "profile_name": "ftmo",
            "profile": engine.default_profiles["ftmo"],
            "activated_at": datetime.now()
        }
        
        with patch.object(engine, '_get_daily_trading_stats') as mock_stats:
            mock_stats.return_value = {
                "trade_count": 2,
                "daily_loss": 0.01,
                "drawdown": 0.02,
                "profit_loss": -100.0
            }
            
            # Test valid trade
            trade_params = {
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 1.0,  # Within FTMO limit (2.0)
                "sl": 1.0800,
                "tp": 1.0900
            }
            
            result = await engine.validate_trade("user_123", trade_params)
            
            assert result["valid"] is True
            assert result["profile"] == "ftmo"
            assert len(result["violations"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_trade_violations(self, engine):
        """Test trade validation with violations"""
        await engine.initialize()
        
        # Activate FTMO profile
        engine.active_profiles["user_123"] = {
            "profile_name": "ftmo",
            "profile": engine.default_profiles["ftmo"],
            "activated_at": datetime.now()
        }
        
        with patch.object(engine, '_get_daily_trading_stats') as mock_stats:
            mock_stats.return_value = {
                "trade_count": 2,
                "daily_loss": 0.01,
                "drawdown": 0.02,
                "profit_loss": -100.0
            }
            
            # Test invalid trade (volume too large)
            trade_params = {
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 5.0,  # Exceeds FTMO limit (2.0)
                "sl": None,     # Missing required SL
                "tp": 1.0900
            }
            
            result = await engine.validate_trade("user_123", trade_params)
            
            assert result["valid"] is False
            assert len(result["violations"]) > 0
            assert result["profile"] == "ftmo"
    
    @pytest.mark.asyncio
    async def test_get_compliance_status(self, engine):
        """Test getting compliance status"""
        await engine.initialize()
        
        # Test without active compliance
        result = await engine.get_compliance_status("user_123")
        
        assert result["active"] is False
        assert result["profile"] is None
        
        # Test with active compliance
        engine.active_profiles["user_123"] = {
            "profile_name": "ftmo",
            "profile": engine.default_profiles["ftmo"],
            "activated_at": datetime.now()
        }
        
        result = await engine.get_compliance_status("user_123")
        
        assert result["active"] is True
        assert result["profile"] == "ftmo"
        assert "profile_name" in result
        assert "activated_at" in result
    
    @pytest.mark.asyncio
    async def test_get_available_profiles(self, engine):
        """Test getting available profiles"""
        await engine.initialize()
        
        result = await engine.get_available_profiles()
        
        assert result["success"] is True
        assert "profiles" in result
        assert "total" in result
        assert len(result["profiles"]) > 0
        
        # Check profile structure
        profile = result["profiles"][0]
        assert "id" in profile
        assert "name" in profile
        assert "description" in profile
        assert "category" in profile
    
    @pytest.mark.asyncio
    async def test_get_profile_details(self, engine):
        """Test getting profile details"""
        await engine.initialize()
        
        result = await engine.get_profile_details("ftmo")
        
        assert result["success"] is True
        assert "profile" in result
        
        profile = result["profile"]
        assert profile["id"] == "ftmo"
        assert profile["name"] == "FTMO Prop Firm"
        assert "restrictions" in profile
        assert "rules" in profile
    
    @pytest.mark.asyncio
    async def test_get_profile_details_invalid(self, engine):
        """Test getting profile details for invalid profile"""
        await engine.initialize()
        
        result = await engine.get_profile_details("invalid_profile")
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_create_custom_profile(self, engine):
        """Test creating custom compliance profile"""
        await engine.initialize()
        
        profile_data = {
            "name": "Custom Profile",
            "description": "Custom compliance profile",
            "restrictions": {
                "max_lot_size": 1.0,
                "max_daily_loss": 0.03,
                "stop_loss_required": True
            }
        }
        
        with patch.object(engine, '_save_custom_profile_db') as mock_save:
            result = await engine.create_custom_profile("user_123", profile_data)
            
            assert result["success"] is True
            assert "profile_id" in result
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_custom_profile_invalid(self, engine):
        """Test creating custom profile with invalid data"""
        await engine.initialize()
        
        profile_data = {
            "name": "Custom Profile"
            # Missing required fields
        }
        
        result = await engine.create_custom_profile("user_123", profile_data)
        
        assert result["success"] is False
        assert "Missing required field" in result["error"]
    
    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, engine):
        """Test generating compliance report"""
        await engine.initialize()
        
        # Activate compliance mode
        engine.active_profiles["user_123"] = {
            "profile_name": "ftmo",
            "profile": engine.default_profiles["ftmo"],
            "activated_at": datetime.now()
        }
        
        # Add some mock violations
        engine.violation_history["user_123"] = [
            {
                "timestamp": datetime.now() - timedelta(hours=1),
                "violation": {
                    "rule": "max_lot_size",
                    "severity": "high"
                }
            },
            {
                "timestamp": datetime.now() - timedelta(hours=2),
                "violation": {
                    "rule": "stop_loss_required",
                    "severity": "high"
                }
            }
        ]
        
        result = await engine.generate_compliance_report("user_123", 30)
        
        assert result["success"] is True
        assert "report" in result
        
        report = result["report"]
        assert report["user_id"] == "user_123"
        assert report["profile"] == "ftmo"
        assert "summary" in report
        assert "violation_breakdown" in report
        assert "compliance_score" in report
        assert "recommendations" in report
    
    @pytest.mark.asyncio
    async def test_generate_compliance_report_no_profile(self, engine):
        """Test generating compliance report with no active profile"""
        await engine.initialize()
        
        result = await engine.generate_compliance_report("user_123", 30)
        
        assert result["success"] is False
        assert "No active compliance profile" in result["error"]


class TestComplianceAPI:
    """Test compliance API endpoints"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return {"user_id": "test_user", "username": "test@example.com"}
    
    @pytest.mark.asyncio
    async def test_get_available_profiles_endpoint(self, mock_user):
        """Test get available profiles endpoint"""
        from api.compliance import get_available_profiles
        
        with patch('core.compliance.ComplianceEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.get_available_profiles.return_value = {
                "success": True,
                "profiles": [
                    {
                        "id": "ftmo",
                        "name": "FTMO Prop Firm",
                        "category": "prop_firm"
                    }
                ],
                "total": 1
            }
            mock_engine.return_value = mock_instance
            
            result = await get_available_profiles(mock_user)
            
            assert result["success"] is True
            assert "profiles" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.get_available_profiles.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_activate_compliance_mode_endpoint(self, mock_user):
        """Test activate compliance mode endpoint"""
        from api.compliance import activate_compliance_mode
        
        request = Mock()
        request.profile_name = "ftmo"
        request.custom_restrictions = None
        
        with patch('core.compliance.ComplianceEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.activate_compliance_mode.return_value = {
                "success": True,
                "profile": "ftmo",
                "message": "Compliance mode activated"
            }
            mock_engine.return_value = mock_instance
            
            result = await activate_compliance_mode(request, mock_user)
            
            assert result["success"] is True
            assert result["profile"] == "ftmo"
            mock_instance.initialize.assert_called_once()
            mock_instance.activate_compliance_mode.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_trade_endpoint(self, mock_user):
        """Test validate trade endpoint"""
        from api.compliance import validate_trade
        
        request = Mock()
        request.symbol = "EURUSD"
        request.type = "BUY"
        request.volume = 1.0
        request.price = 1.0850
        request.sl = 1.0800
        request.tp = 1.0900
        
        with patch('core.compliance.ComplianceEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.validate_trade.return_value = {
                "valid": True,
                "violations": [],
                "profile": "ftmo"
            }
            mock_engine.return_value = mock_instance
            
            result = await validate_trade(request, mock_user)
            
            assert result["success"] is True
            assert "validation" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.validate_trade.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])