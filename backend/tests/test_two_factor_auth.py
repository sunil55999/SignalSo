"""
Tests for two-factor authentication functionality
"""

import pytest
import asyncio
import base64
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from core.two_factor_auth import TwoFactorAuthEngine


class TestTwoFactorAuthEngine:
    """Test 2FA engine functionality"""
    
    @pytest.fixture
    def engine(self):
        """Create 2FA engine instance"""
        return TwoFactorAuthEngine()
    
    @pytest.mark.asyncio
    async def test_initialization(self, engine):
        """Test engine initialization"""
        await engine.initialize()
        assert engine.otp_codes == {}
        assert engine.backup_codes == {}
    
    @pytest.mark.asyncio
    async def test_setup_totp(self, engine):
        """Test TOTP setup"""
        await engine.initialize()
        
        with patch.object(engine, '_store_2fa_setup') as mock_store:
            result = await engine.setup_totp("user_123", "SignalOS")
            
            assert result["success"] is True
            assert "setup_data" in result
            assert "secret" in result["setup_data"]
            assert "qr_code" in result["setup_data"]
            assert "backup_codes" in result["setup_data"]
            assert "provisioning_uri" in result["setup_data"]
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_setup_sms(self, engine):
        """Test SMS setup"""
        await engine.initialize()
        
        with patch.object(engine, '_validate_phone_number') as mock_validate:
            mock_validate.return_value = True
            
            with patch.object(engine, '_send_sms') as mock_send:
                mock_send.return_value = {"success": True}
                
                result = await engine.setup_sms("user_123", "+1234567890")
                
                assert result["success"] is True
                assert "expires_in" in result
                assert "user_123" in engine.otp_codes
                mock_validate.assert_called_once()
                mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_setup_sms_invalid_phone(self, engine):
        """Test SMS setup with invalid phone number"""
        await engine.initialize()
        
        with patch.object(engine, '_validate_phone_number') as mock_validate:
            mock_validate.return_value = False
            
            result = await engine.setup_sms("user_123", "invalid_phone")
            
            assert result["success"] is False
            assert "Invalid phone number" in result["error"]
    
    @pytest.mark.asyncio
    async def test_setup_email(self, engine):
        """Test email setup"""
        await engine.initialize()
        
        with patch.object(engine, '_validate_email') as mock_validate:
            mock_validate.return_value = True
            
            with patch.object(engine, '_send_email') as mock_send:
                mock_send.return_value = {"success": True}
                
                result = await engine.setup_email("user_123", "test@example.com")
                
                assert result["success"] is True
                assert "expires_in" in result
                assert "user_123" in engine.otp_codes
                mock_validate.assert_called_once()
                mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_setup_email_invalid_email(self, engine):
        """Test email setup with invalid email"""
        await engine.initialize()
        
        with patch.object(engine, '_validate_email') as mock_validate:
            mock_validate.return_value = False
            
            result = await engine.setup_email("user_123", "invalid_email")
            
            assert result["success"] is False
            assert "Invalid email" in result["error"]
    
    @pytest.mark.asyncio
    async def test_verify_totp_setup(self, engine):
        """Test TOTP setup verification"""
        await engine.initialize()
        
        with patch.object(engine, '_get_pending_2fa_setup') as mock_get:
            mock_get.return_value = {
                "secret": "JBSWY3DPEHPK3PXP",
                "backup_codes": ["12345678", "87654321"]
            }
            
            with patch('pyotp.TOTP') as mock_totp:
                mock_totp_instance = Mock()
                mock_totp_instance.verify.return_value = True
                mock_totp.return_value = mock_totp_instance
                
                with patch.object(engine, '_activate_2fa') as mock_activate:
                    result = await engine.verify_totp_setup("user_123", "123456")
                    
                    assert result["success"] is True
                    assert "backup_codes" in result
                    mock_activate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_totp_setup_invalid_code(self, engine):
        """Test TOTP setup verification with invalid code"""
        await engine.initialize()
        
        with patch.object(engine, '_get_pending_2fa_setup') as mock_get:
            mock_get.return_value = {
                "secret": "JBSWY3DPEHPK3PXP",
                "backup_codes": ["12345678", "87654321"]
            }
            
            with patch('pyotp.TOTP') as mock_totp:
                mock_totp_instance = Mock()
                mock_totp_instance.verify.return_value = False
                mock_totp.return_value = mock_totp_instance
                
                result = await engine.verify_totp_setup("user_123", "invalid")
                
                assert result["success"] is False
                assert "Invalid verification code" in result["error"]
    
    @pytest.mark.asyncio
    async def test_verify_sms_setup(self, engine):
        """Test SMS setup verification"""
        await engine.initialize()
        
        # Set up OTP code
        engine.otp_codes["user_123"] = {
            "code": "123456",
            "expires": datetime.now() + timedelta(minutes=5),
            "phone_number": "+1234567890"
        }
        
        with patch.object(engine, '_activate_2fa') as mock_activate:
            result = await engine.verify_sms_setup("user_123", "123456")
            
            assert result["success"] is True
            assert "backup_codes" in result
            assert "user_123" not in engine.otp_codes
            mock_activate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_sms_setup_expired(self, engine):
        """Test SMS setup verification with expired code"""
        await engine.initialize()
        
        # Set up expired OTP code
        engine.otp_codes["user_123"] = {
            "code": "123456",
            "expires": datetime.now() - timedelta(minutes=1),
            "phone_number": "+1234567890"
        }
        
        result = await engine.verify_sms_setup("user_123", "123456")
        
        assert result["success"] is False
        assert "expired" in result["error"]
        assert "user_123" not in engine.otp_codes
    
    @pytest.mark.asyncio
    async def test_verify_email_setup(self, engine):
        """Test email setup verification"""
        await engine.initialize()
        
        # Set up OTP code
        engine.otp_codes["user_123"] = {
            "code": "123456",
            "expires": datetime.now() + timedelta(minutes=10),
            "email": "test@example.com"
        }
        
        with patch.object(engine, '_activate_2fa') as mock_activate:
            result = await engine.verify_email_setup("user_123", "123456")
            
            assert result["success"] is True
            assert "backup_codes" in result
            assert "user_123" not in engine.otp_codes
            mock_activate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_2fa_code_totp(self, engine):
        """Test 2FA code verification for TOTP"""
        await engine.initialize()
        
        with patch.object(engine, '_get_user_2fa_method') as mock_get:
            mock_get.return_value = {
                "method": "TOTP",
                "secret": "JBSWY3DPEHPK3PXP"
            }
            
            with patch.object(engine, '_verify_totp_code') as mock_verify:
                mock_verify.return_value = {
                    "success": True,
                    "message": "TOTP verified"
                }
                
                result = await engine.verify_2fa_code("user_123", "123456")
                
                assert result["success"] is True
                mock_verify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_2fa_code_no_method(self, engine):
        """Test 2FA code verification with no method enabled"""
        await engine.initialize()
        
        with patch.object(engine, '_get_user_2fa_method') as mock_get:
            mock_get.return_value = None
            
            result = await engine.verify_2fa_code("user_123", "123456")
            
            assert result["success"] is False
            assert "not enabled" in result["error"]
    
    @pytest.mark.asyncio
    async def test_request_2fa_code_sms(self, engine):
        """Test requesting 2FA code for SMS"""
        await engine.initialize()
        
        with patch.object(engine, '_get_user_2fa_method') as mock_get:
            mock_get.return_value = {
                "method": "SMS",
                "phone_number": "+1234567890"
            }
            
            with patch.object(engine, '_send_sms_code') as mock_send:
                mock_send.return_value = {
                    "success": True,
                    "message": "SMS sent"
                }
                
                result = await engine.request_2fa_code("user_123")
                
                assert result["success"] is True
                mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_request_2fa_code_email(self, engine):
        """Test requesting 2FA code for email"""
        await engine.initialize()
        
        with patch.object(engine, '_get_user_2fa_method') as mock_get:
            mock_get.return_value = {
                "method": "EMAIL",
                "email": "test@example.com"
            }
            
            with patch.object(engine, '_send_email_code') as mock_send:
                mock_send.return_value = {
                    "success": True,
                    "message": "Email sent"
                }
                
                result = await engine.request_2fa_code("user_123")
                
                assert result["success"] is True
                mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disable_2fa(self, engine):
        """Test disabling 2FA"""
        await engine.initialize()
        
        # Set up some test data
        engine.otp_codes["user_123"] = {"test": "data"}
        engine.backup_codes["user_123"] = ["codes"]
        
        with patch.object(engine, '_remove_2fa_from_db') as mock_remove:
            result = await engine.disable_2fa("user_123")
            
            assert result["success"] is True
            assert "user_123" not in engine.otp_codes
            assert "user_123" not in engine.backup_codes
            mock_remove.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_regenerate_backup_codes(self, engine):
        """Test regenerating backup codes"""
        await engine.initialize()
        
        with patch.object(engine, '_update_backup_codes') as mock_update:
            result = await engine.regenerate_backup_codes("user_123")
            
            assert result["success"] is True
            assert "backup_codes" in result
            assert len(result["backup_codes"]) == 10
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_2fa_status(self, engine):
        """Test getting 2FA status"""
        await engine.initialize()
        
        with patch.object(engine, '_get_user_2fa_method') as mock_get:
            mock_get.return_value = {
                "method": "TOTP",
                "last_used": datetime.now().isoformat()
            }
            
            with patch.object(engine, '_count_remaining_backup_codes') as mock_count:
                mock_count.return_value = 8
                
                result = await engine.get_2fa_status("user_123")
                
                assert result["enabled"] is True
                assert result["method"] == "TOTP"
                assert result["backup_codes_remaining"] == 8
    
    @pytest.mark.asyncio
    async def test_get_2fa_status_disabled(self, engine):
        """Test getting 2FA status when disabled"""
        await engine.initialize()
        
        with patch.object(engine, '_get_user_2fa_method') as mock_get:
            mock_get.return_value = None
            
            result = await engine.get_2fa_status("user_123")
            
            assert result["enabled"] is False
            assert result["method"] is None
    
    @pytest.mark.asyncio
    async def test_generate_qr_code(self, engine):
        """Test QR code generation"""
        await engine.initialize()
        
        with patch('qrcode.QRCode') as mock_qr:
            mock_qr_instance = Mock()
            mock_img = Mock()
            mock_qr_instance.make_image.return_value = mock_img
            mock_qr.return_value = mock_qr_instance
            
            # Mock the save method
            mock_img.save = Mock()
            
            provisioning_uri = "otpauth://totp/SignalOS:user_123?secret=JBSWY3DPEHPK3PXP&issuer=SignalOS"
            result = await engine._generate_qr_code(provisioning_uri)
            
            assert isinstance(result, str)
            mock_qr.assert_called_once()
            mock_qr_instance.add_data.assert_called_once_with(provisioning_uri)
    
    @pytest.mark.asyncio
    async def test_generate_backup_codes(self, engine):
        """Test backup code generation"""
        await engine.initialize()
        
        codes = await engine._generate_backup_codes()
        
        assert len(codes) == 10
        for code in codes:
            assert isinstance(code, str)
            assert len(code) == 8
    
    @pytest.mark.asyncio
    async def test_generate_verification_code(self, engine):
        """Test verification code generation"""
        await engine.initialize()
        
        code = await engine._generate_verification_code()
        
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()
    
    @pytest.mark.asyncio
    async def test_validate_phone_number(self, engine):
        """Test phone number validation"""
        await engine.initialize()
        
        # Test valid numbers
        assert await engine._validate_phone_number("+1234567890") is True
        assert await engine._validate_phone_number("1234567890") is True
        assert await engine._validate_phone_number("+44 1234 567890") is True
        
        # Test invalid numbers
        assert await engine._validate_phone_number("invalid") is False
        assert await engine._validate_phone_number("123") is False
        assert await engine._validate_phone_number("") is False
    
    @pytest.mark.asyncio
    async def test_validate_email(self, engine):
        """Test email validation"""
        await engine.initialize()
        
        # Test valid emails
        assert await engine._validate_email("test@example.com") is True
        assert await engine._validate_email("user+tag@domain.co.uk") is True
        
        # Test invalid emails
        assert await engine._validate_email("invalid-email") is False
        assert await engine._validate_email("@example.com") is False
        assert await engine._validate_email("test@") is False
        assert await engine._validate_email("") is False


class TestTwoFactorAuthAPI:
    """Test 2FA API endpoints"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return {"user_id": "test_user", "username": "test@example.com"}
    
    @pytest.mark.asyncio
    async def test_setup_totp_endpoint(self, mock_user):
        """Test TOTP setup endpoint"""
        from api.two_factor import setup_totp
        
        request = Mock()
        request.issuer = "SignalOS"
        
        with patch('core.two_factor_auth.TwoFactorAuthEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.setup_totp.return_value = {
                "success": True,
                "setup_data": {
                    "secret": "JBSWY3DPEHPK3PXP",
                    "qr_code": "base64_qr_code",
                    "backup_codes": ["12345678", "87654321"]
                }
            }
            mock_engine.return_value = mock_instance
            
            result = await setup_totp(request, mock_user)
            
            assert result["success"] is True
            assert "setup_data" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.setup_totp.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_totp_setup_endpoint(self, mock_user):
        """Test TOTP verification endpoint"""
        from api.two_factor import verify_totp_setup
        
        request = Mock()
        request.code = "123456"
        
        with patch('core.two_factor_auth.TwoFactorAuthEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.verify_totp_setup.return_value = {
                "success": True,
                "message": "TOTP activated",
                "backup_codes": ["12345678", "87654321"]
            }
            mock_engine.return_value = mock_instance
            
            result = await verify_totp_setup(request, mock_user)
            
            assert result["success"] is True
            assert "backup_codes" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.verify_totp_setup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_2fa_status_endpoint(self, mock_user):
        """Test 2FA status endpoint"""
        from api.two_factor import get_2fa_status
        
        with patch('core.two_factor_auth.TwoFactorAuthEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.get_2fa_status.return_value = {
                "enabled": True,
                "method": "TOTP",
                "backup_codes_remaining": 8
            }
            mock_engine.return_value = mock_instance
            
            result = await get_2fa_status(mock_user)
            
            assert result["success"] is True
            assert "status" in result
            assert result["status"]["enabled"] is True
            mock_instance.initialize.assert_called_once()
            mock_instance.get_2fa_status.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])