"""
Tests for onboarding functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from core.onboarding import OnboardingEngine, OnboardingStepType, OnboardingStatus


class TestOnboardingEngine:
    """Test onboarding engine functionality"""
    
    @pytest.fixture
    def engine(self):
        """Create onboarding engine instance"""
        return OnboardingEngine()
    
    @pytest.mark.asyncio
    async def test_initialization(self, engine):
        """Test engine initialization"""
        await engine.initialize()
        assert engine.step_configs is not None
        assert len(engine.step_configs) > 0
        assert "welcome" in engine.step_configs
        assert "profile_setup" in engine.step_configs
        assert "broker_connection" in engine.step_configs
    
    @pytest.mark.asyncio
    async def test_start_onboarding(self, engine):
        """Test starting onboarding process"""
        await engine.initialize()
        
        with patch.object(engine, '_create_onboarding_records') as mock_create:
            result = await engine.start_onboarding("user_123")
            
            assert result["success"] is True
            assert "current_step" in result
            assert "progress" in result
            assert "user_123" in engine.user_progress
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_current_step(self, engine):
        """Test getting current step"""
        await engine.initialize()
        
        # Start onboarding first
        await engine.start_onboarding("user_123")
        
        result = await engine.get_current_step("user_123")
        
        assert result["success"] is True
        assert "step" in result
        assert result["step"]["id"] == "welcome"
        assert result["step"]["title"] == "Welcome to SignalOS"
    
    @pytest.mark.asyncio
    async def test_get_current_step_not_started(self, engine):
        """Test getting current step when onboarding not started"""
        await engine.initialize()
        
        result = await engine.get_current_step("user_123")
        
        assert result["success"] is False
        assert "not started" in result["error"]
    
    @pytest.mark.asyncio
    async def test_complete_step(self, engine):
        """Test completing a step"""
        await engine.initialize()
        
        # Start onboarding
        await engine.start_onboarding("user_123")
        
        with patch.object(engine, '_validate_step') as mock_validate:
            mock_validate.return_value = {"valid": True}
            
            with patch.object(engine, '_update_step_status') as mock_update:
                step_data = {"first_name": "John", "last_name": "Doe"}
                result = await engine.complete_step("user_123", "welcome", step_data)
                
                assert result["success"] is True
                assert "welcome" in engine.user_progress["user_123"]["completed_steps"]
                mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_step_validation_failed(self, engine):
        """Test completing a step with validation failure"""
        await engine.initialize()
        
        # Start onboarding
        await engine.start_onboarding("user_123")
        
        with patch.object(engine, '_validate_step') as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "error": "Validation failed",
                "errors": ["Missing required field"]
            }
            
            step_data = {"incomplete": "data"}
            result = await engine.complete_step("user_123", "profile_setup", step_data)
            
            assert result["success"] is False
            assert "Validation failed" in result["error"]
            assert "validation_errors" in result
    
    @pytest.mark.asyncio
    async def test_skip_step(self, engine):
        """Test skipping an optional step"""
        await engine.initialize()
        
        # Start onboarding
        await engine.start_onboarding("user_123")
        
        with patch.object(engine, '_update_step_status') as mock_update:
            result = await engine.skip_step("user_123", "signal_provider_setup", "Not needed")
            
            assert result["success"] is True
            assert "signal_provider_setup" in engine.user_progress["user_123"]["completed_steps"]
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_skip_required_step(self, engine):
        """Test skipping a required step (should fail)"""
        await engine.initialize()
        
        # Start onboarding
        await engine.start_onboarding("user_123")
        
        result = await engine.skip_step("user_123", "profile_setup", "Not needed")
        
        assert result["success"] is False
        assert "Cannot skip required step" in result["error"]
    
    @pytest.mark.asyncio
    async def test_restart_step(self, engine):
        """Test restarting a step"""
        await engine.initialize()
        
        # Start onboarding and complete a step
        await engine.start_onboarding("user_123")
        engine.user_progress["user_123"]["completed_steps"].append("welcome")
        engine.user_progress["user_123"]["step_data"]["welcome"] = {"test": "data"}
        
        with patch.object(engine, '_update_step_status') as mock_update:
            result = await engine.restart_step("user_123", "welcome")
            
            assert result["success"] is True
            assert "welcome" not in engine.user_progress["user_123"]["completed_steps"]
            assert "welcome" not in engine.user_progress["user_123"]["step_data"]
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_progress(self, engine):
        """Test getting progress"""
        await engine.initialize()
        
        # Start onboarding
        await engine.start_onboarding("user_123")
        
        # Complete some steps
        engine.user_progress["user_123"]["completed_steps"] = ["welcome", "profile_setup"]
        
        result = await engine.get_progress("user_123")
        
        assert result["success"] is True
        assert "progress" in result
        
        progress = result["progress"]
        assert progress["completed_steps"] == 2
        assert progress["completion_percentage"] > 0
        assert "estimated_time_remaining" in progress
    
    @pytest.mark.asyncio
    async def test_get_onboarding_summary(self, engine):
        """Test getting onboarding summary"""
        await engine.initialize()
        
        # Start onboarding
        await engine.start_onboarding("user_123")
        
        result = await engine.get_onboarding_summary("user_123")
        
        assert result["success"] is True
        assert "summary" in result
        
        summary = result["summary"]
        assert summary["user_id"] == "user_123"
        assert "started_at" in summary
        assert "steps" in summary
        assert len(summary["steps"]) > 0
    
    @pytest.mark.asyncio
    async def test_validate_profile_setup(self, engine):
        """Test profile setup validation"""
        await engine.initialize()
        
        # Test valid data
        valid_data = {
            "first_name": "John",
            "last_name": "Doe",
            "timezone": "UTC",
            "experience_level": "intermediate"
        }
        
        result = await engine._validate_profile_setup(valid_data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        
        # Test invalid data
        invalid_data = {
            "first_name": "John"
            # Missing required fields
        }
        
        result = await engine._validate_profile_setup(invalid_data)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_validate_broker_connection(self, engine):
        """Test broker connection validation"""
        await engine.initialize()
        
        # Test valid data
        valid_data = {
            "broker_name": "Test Broker",
            "account_type": "demo",
            "server": "TestServer",
            "login": "12345",
            "password": "password"
        }
        
        result = await engine._validate_broker_connection(valid_data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        
        # Test invalid data
        invalid_data = {
            "broker_name": "Test Broker",
            "account_type": "invalid_type"
        }
        
        result = await engine._validate_broker_connection(invalid_data)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_validate_broker_verification(self, engine):
        """Test broker verification"""
        await engine.initialize()
        
        with patch.object(engine.mt5_bridge, 'test_connection') as mock_test:
            mock_test.return_value = {"success": True}
            
            with patch.object(engine.mt5_bridge, 'get_account_info') as mock_account:
                mock_account.return_value = {
                    "success": True,
                    "data": {"balance": 10000, "account": "12345"}
                }
                
                result = await engine._validate_broker_verification("user_123", {})
                
                assert result["valid"] is True
                assert "account_info" in result
                mock_test.assert_called_once()
                mock_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_system_test(self, engine):
        """Test system test execution"""
        await engine.initialize()
        
        with patch.object(engine.mt5_bridge, 'test_connection') as mock_test:
            mock_test.return_value = {"success": True, "message": "Connected"}
            
            with patch.object(engine.mt5_bridge, 'get_account_info') as mock_account:
                mock_account.return_value = {"success": True, "message": "Account OK"}
                
                with patch.object(engine, '_test_signal_parsing') as mock_parse:
                    mock_parse.return_value = {"success": True, "message": "Parsing OK"}
                    
                    with patch.object(engine, '_test_risk_management') as mock_risk:
                        mock_risk.return_value = {"success": True, "message": "Risk OK"}
                        
                        result = await engine._run_system_test("user_123")
                        
                        assert result["success"] is True
                        assert "results" in result
                        assert len(result["results"]) == 4
                        
                        # Check all tests passed
                        for test_result in result["results"]:
                            assert test_result["status"] == "passed"


class TestOnboardingAPI:
    """Test onboarding API endpoints"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return {"user_id": "test_user", "username": "test@example.com"}
    
    @pytest.mark.asyncio
    async def test_start_onboarding_endpoint(self, mock_user):
        """Test start onboarding endpoint"""
        from api.onboarding import start_onboarding
        
        with patch('core.onboarding.OnboardingEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.start_onboarding.return_value = {
                "success": True,
                "message": "Onboarding started",
                "current_step": {"id": "welcome", "title": "Welcome"},
                "progress": {"completion_percentage": 0}
            }
            mock_engine.return_value = mock_instance
            
            result = await start_onboarding(mock_user)
            
            assert result["success"] is True
            assert "current_step" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.start_onboarding.assert_called_once_with("test_user")
    
    @pytest.mark.asyncio
    async def test_get_current_step_endpoint(self, mock_user):
        """Test get current step endpoint"""
        from api.onboarding import get_current_step
        
        with patch('core.onboarding.OnboardingEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.get_current_step.return_value = {
                "success": True,
                "step": {
                    "id": "profile_setup",
                    "title": "Profile Setup",
                    "description": "Set up your profile",
                    "type": "profile",
                    "required": True
                }
            }
            mock_engine.return_value = mock_instance
            
            result = await get_current_step(mock_user)
            
            assert result["success"] is True
            assert "step" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.get_current_step.assert_called_once_with("test_user")
    
    @pytest.mark.asyncio
    async def test_complete_step_endpoint(self, mock_user):
        """Test complete step endpoint"""
        from api.onboarding import complete_step
        
        request = Mock()
        request.step_data = {"first_name": "John", "last_name": "Doe"}
        
        with patch('core.onboarding.OnboardingEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.complete_step.return_value = {
                "success": True,
                "message": "Step completed",
                "next_step": "broker_connection",
                "progress": {"completion_percentage": 20}
            }
            mock_engine.return_value = mock_instance
            
            result = await complete_step("profile_setup", request, mock_user)
            
            assert result["success"] is True
            assert "next_step" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.complete_step.assert_called_once_with(
                "test_user", "profile_setup", request.step_data
            )
    
    @pytest.mark.asyncio
    async def test_skip_step_endpoint(self, mock_user):
        """Test skip step endpoint"""
        from api.onboarding import skip_step
        
        request = Mock()
        request.reason = "Not needed"
        
        with patch('core.onboarding.OnboardingEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.skip_step.return_value = {
                "success": True,
                "message": "Step skipped",
                "next_step": "broker_connection",
                "progress": {"completion_percentage": 20}
            }
            mock_engine.return_value = mock_instance
            
            result = await skip_step("signal_provider_setup", request, mock_user)
            
            assert result["success"] is True
            assert "next_step" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.skip_step.assert_called_once_with(
                "test_user", "signal_provider_setup", "Not needed"
            )
    
    @pytest.mark.asyncio
    async def test_get_progress_endpoint(self, mock_user):
        """Test get progress endpoint"""
        from api.onboarding import get_progress
        
        with patch('core.onboarding.OnboardingEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.get_progress.return_value = {
                "success": True,
                "progress": {
                    "total_steps": 11,
                    "completed_steps": 3,
                    "completion_percentage": 27.3,
                    "estimated_time_remaining": 45
                }
            }
            mock_engine.return_value = mock_instance
            
            result = await get_progress(mock_user)
            
            assert result["success"] is True
            assert "progress" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.get_progress.assert_called_once_with("test_user")


if __name__ == "__main__":
    pytest.main([__file__])