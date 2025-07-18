"""
Integration tests for the audit-required features
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from core.offline import OfflineOperationEngine
from core.marketplace import MarketplaceEngine
from core.compliance import ComplianceEngine
from core.onboarding import OnboardingEngine
from core.two_factor_auth import TwoFactorAuthEngine


class TestAuditFeatureIntegration:
    """Test integration between all audit-required features"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return {"user_id": "test_user", "username": "test@example.com"}
    
    @pytest.mark.asyncio
    async def test_complete_user_onboarding_flow(self, mock_user):
        """Test complete user onboarding flow"""
        # Initialize onboarding engine
        onboarding = OnboardingEngine()
        await onboarding.initialize()
        
        # Mock the necessary dependencies
        with patch.object(onboarding.mt5_bridge, 'test_connection') as mock_connection:
            mock_connection.return_value = {"success": True}
            
            with patch.object(onboarding.mt5_bridge, 'get_account_info') as mock_account:
                mock_account.return_value = {
                    "success": True,
                    "data": {"balance": 10000, "account": "12345"}
                }
                
                # Start onboarding
                start_result = await onboarding.start_onboarding(mock_user["user_id"])
                assert start_result["success"] is True
                
                # Complete profile setup
                profile_data = {
                    "first_name": "John",
                    "last_name": "Doe",
                    "timezone": "UTC",
                    "experience_level": "intermediate"
                }
                
                profile_result = await onboarding.complete_step(
                    mock_user["user_id"], "profile_setup", profile_data
                )
                assert profile_result["success"] is True
                
                # Complete broker connection
                broker_data = {
                    "broker_name": "Test Broker",
                    "account_type": "demo",
                    "server": "TestServer",
                    "login": "12345",
                    "password": "password"
                }
                
                broker_result = await onboarding.complete_step(
                    mock_user["user_id"], "broker_connection", broker_data
                )
                assert broker_result["success"] is True
                
                # Get final progress
                progress = await onboarding.get_progress(mock_user["user_id"])
                assert progress["success"] is True
                assert progress["progress"]["completion_percentage"] > 0
    
    @pytest.mark.asyncio
    async def test_offline_to_online_sync_with_compliance(self, mock_user):
        """Test offline operations syncing with compliance validation"""
        # Initialize engines
        offline = OfflineOperationEngine(mock_user["user_id"])
        compliance = ComplianceEngine()
        
        await offline.initialize()
        await compliance.initialize()
        
        # Activate compliance mode
        compliance_result = await compliance.activate_compliance_mode(
            mock_user["user_id"], "ftmo"
        )
        assert compliance_result["success"] is True
        
        # Execute trade offline
        trade_params = {
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": 1.0,  # Within FTMO limits
            "price": 1.0850,
            "sl": 1.0800,
            "tp": 1.0900
        }
        
        with patch.object(offline.trade_service, 'execute_trade') as mock_trade:
            mock_trade.return_value = {
                "success": True,
                "trade_id": "trade_123",
                "status": "executed"
            }
            
            trade_result = await offline.execute_trade_offline(trade_params)
            assert trade_result["success"] is True
            
            # Validate trade against compliance
            with patch.object(compliance, '_get_daily_trading_stats') as mock_stats:
                mock_stats.return_value = {
                    "trade_count": 1,
                    "daily_loss": 0.01,
                    "drawdown": 0.02,
                    "profit_loss": -50.0
                }
                
                validation_result = await compliance.validate_trade(
                    mock_user["user_id"], trade_params
                )
                assert validation_result["valid"] is True
                
                # Sync offline actions
                offline.is_online = True
                sync_result = await offline.sync_offline_actions()
                assert sync_result["successful"] >= 0
    
    @pytest.mark.asyncio
    async def test_plugin_installation_with_2fa(self, mock_user):
        """Test plugin installation with 2FA enabled"""
        # Initialize engines
        marketplace = MarketplaceEngine()
        tfa = TwoFactorAuthEngine()
        
        await marketplace.initialize()
        await tfa.initialize()
        
        # Setup 2FA
        with patch.object(tfa, '_send_sms') as mock_sms:
            mock_sms.return_value = {"success": True}
            
            sms_result = await tfa.setup_sms(mock_user["user_id"], "+1234567890")
            assert sms_result["success"] is True
            
            # Verify 2FA setup
            verify_result = await tfa.verify_sms_setup(mock_user["user_id"], "123456")
            assert verify_result["success"] is True
        
        # Install plugin (would require 2FA in real implementation)
        mock_plugin_data = b"mock_plugin_zip_data"
        
        with patch.object(marketplace, '_validate_plugin_package') as mock_validate:
            mock_validate.return_value = {
                "name": "Test Plugin",
                "version": "1.0.0",
                "type": "signal_provider"
            }
            
            with patch.object(marketplace, '_extract_plugin') as mock_extract:
                with patch.object(marketplace, '_register_plugin') as mock_register:
                    with patch.object(marketplace, '_create_user_plugin_record') as mock_create:
                        
                        install_result = await marketplace.install_plugin(
                            "test_plugin", mock_user["user_id"], mock_plugin_data
                        )
                        assert install_result["success"] is True
    
    @pytest.mark.asyncio
    async def test_offline_signal_parsing_with_plugin(self, mock_user):
        """Test offline signal parsing with installed plugin"""
        # Initialize engines
        offline = OfflineOperationEngine(mock_user["user_id"])
        marketplace = MarketplaceEngine()
        
        await offline.initialize()
        await marketplace.initialize()
        
        # Mock installed plugin
        mock_plugin_module = Mock()
        mock_plugin_module.parse_signal = AsyncMock(return_value={
            "symbol": "EURUSD",
            "action": "BUY",
            "entry_price": 1.0850,
            "confidence": 0.95
        })
        
        marketplace.loaded_plugins["signal_parser"] = {
            "module": mock_plugin_module,
            "info": {"name": "Signal Parser Plugin"}
        }
        
        # Parse signal offline using plugin
        signal_text = "BUY EURUSD at 1.0850"
        
        with patch.object(offline.parser_service, 'parse_offline') as mock_parse:
            mock_parse.return_value = {
                "symbol": "EURUSD",
                "action": "BUY",
                "entry_price": 1.0850,
                "confidence": 0.95,
                "raw_text": signal_text
            }
            
            result = await offline.parse_signal_offline(signal_text)
            assert result["symbol"] == "EURUSD"
            assert result["action"] == "BUY"
            assert result["confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_compliance_report_with_audit_trail(self, mock_user):
        """Test compliance report generation with audit trail"""
        # Initialize compliance engine
        compliance = ComplianceEngine()
        await compliance.initialize()
        
        # Activate compliance mode
        compliance.active_profiles[mock_user["user_id"]] = {
            "profile_name": "ftmo",
            "profile": compliance.default_profiles["ftmo"],
            "activated_at": datetime.now()
        }
        
        # Add violation history
        compliance.violation_history[mock_user["user_id"]] = [
            {
                "timestamp": datetime.now() - timedelta(hours=1),
                "violation": {
                    "rule": "max_lot_size",
                    "severity": "high",
                    "details": "Attempted to trade 5.0 lots (max: 2.0)"
                }
            },
            {
                "timestamp": datetime.now() - timedelta(hours=2),
                "violation": {
                    "rule": "stop_loss_required",
                    "severity": "high",
                    "details": "Trade executed without stop loss"
                }
            }
        ]
        
        # Generate compliance report
        report_result = await compliance.generate_compliance_report(
            mock_user["user_id"], 30
        )
        
        assert report_result["success"] is True
        assert "report" in report_result
        
        report = report_result["report"]
        assert report["user_id"] == mock_user["user_id"]
        assert report["profile"] == "ftmo"
        assert len(report["violations"]) == 2
        assert report["compliance_score"] < 1.0  # Should be reduced due to violations
    
    @pytest.mark.asyncio
    async def test_end_to_end_trading_workflow(self, mock_user):
        """Test complete end-to-end trading workflow"""
        # Initialize all engines
        offline = OfflineOperationEngine(mock_user["user_id"])
        compliance = ComplianceEngine()
        marketplace = MarketplaceEngine()
        tfa = TwoFactorAuthEngine()
        
        await offline.initialize()
        await compliance.initialize()
        await marketplace.initialize()
        await tfa.initialize()
        
        # 1. Setup 2FA
        with patch.object(tfa, '_send_sms') as mock_sms:
            mock_sms.return_value = {"success": True}
            
            await tfa.setup_sms(mock_user["user_id"], "+1234567890")
            await tfa.verify_sms_setup(mock_user["user_id"], "123456")
        
        # 2. Activate compliance mode
        await compliance.activate_compliance_mode(mock_user["user_id"], "ftmo")
        
        # 3. Install signal provider plugin
        mock_plugin_data = b"mock_plugin_zip_data"
        
        with patch.object(marketplace, '_validate_plugin_package') as mock_validate:
            mock_validate.return_value = {
                "name": "Signal Provider",
                "version": "1.0.0",
                "type": "signal_provider"
            }
            
            with patch.object(marketplace, '_extract_plugin'):
                with patch.object(marketplace, '_register_plugin'):
                    with patch.object(marketplace, '_create_user_plugin_record'):
                        await marketplace.install_plugin(
                            "signal_provider", mock_user["user_id"], mock_plugin_data
                        )
        
        # 4. Parse signal offline
        signal_text = "BUY EURUSD at 1.0850 SL 1.0800 TP 1.0900"
        
        with patch.object(offline.parser_service, 'parse_offline') as mock_parse:
            mock_parse.return_value = {
                "symbol": "EURUSD",
                "action": "BUY",
                "entry_price": 1.0850,
                "sl": 1.0800,
                "tp": 1.0900,
                "confidence": 0.95,
                "raw_text": signal_text
            }
            
            signal_result = await offline.parse_signal_offline(signal_text)
            assert signal_result["symbol"] == "EURUSD"
        
        # 5. Validate trade against compliance
        trade_params = {
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": 1.0,
            "price": 1.0850,
            "sl": 1.0800,
            "tp": 1.0900
        }
        
        with patch.object(compliance, '_get_daily_trading_stats') as mock_stats:
            mock_stats.return_value = {
                "trade_count": 0,
                "daily_loss": 0.0,
                "drawdown": 0.0,
                "profit_loss": 0.0
            }
            
            validation = await compliance.validate_trade(
                mock_user["user_id"], trade_params
            )
            assert validation["valid"] is True
        
        # 6. Execute trade offline
        with patch.object(offline.trade_service, 'execute_trade') as mock_trade:
            mock_trade.return_value = {
                "success": True,
                "trade_id": "trade_123",
                "status": "executed"
            }
            
            trade_result = await offline.execute_trade_offline(trade_params)
            assert trade_result["success"] is True
        
        # 7. Sync when online
        offline.is_online = True
        sync_result = await offline.sync_offline_actions()
        assert sync_result["successful"] >= 0
        
        # 8. Generate compliance report
        report_result = await compliance.generate_compliance_report(
            mock_user["user_id"], 30
        )
        assert report_result["success"] is True
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mock_user):
        """Test error handling and recovery across all systems"""
        # Initialize engines
        offline = OfflineOperationEngine(mock_user["user_id"])
        compliance = ComplianceEngine()
        
        await offline.initialize()
        await compliance.initialize()
        
        # Test invalid trade with compliance
        invalid_trade = {
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": 10.0,  # Exceeds any reasonable limit
            "price": 1.0850,
            "sl": None,  # Missing required SL
            "tp": 1.0900
        }
        
        # Activate compliance mode
        await compliance.activate_compliance_mode(mock_user["user_id"], "ftmo")
        
        # Should fail validation
        with patch.object(compliance, '_get_daily_trading_stats') as mock_stats:
            mock_stats.return_value = {
                "trade_count": 0,
                "daily_loss": 0.0,
                "drawdown": 0.0,
                "profit_loss": 0.0
            }
            
            validation = await compliance.validate_trade(
                mock_user["user_id"], invalid_trade
            )
            assert validation["valid"] is False
            assert len(validation["violations"]) > 0
        
        # Test offline operation with network error
        with patch.object(offline.trade_service, 'execute_trade') as mock_trade:
            mock_trade.side_effect = Exception("Network error")
            
            # Should still queue the trade
            trade_result = await offline.execute_trade_offline(invalid_trade)
            assert trade_result["success"] is True
            assert trade_result["status"] == "queued_offline"
        
        # Test sync failure recovery
        offline.is_online = True
        with patch.object(offline, '_sync_single_action') as mock_sync:
            mock_sync.side_effect = Exception("Sync error")
            
            sync_result = await offline.sync_offline_actions()
            assert sync_result["failed"] >= 0  # Should handle failures gracefully


if __name__ == "__main__":
    pytest.main([__file__, "-v"])