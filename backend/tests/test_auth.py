"""
Tests for authentication module
"""

import pytest
from datetime import datetime, timedelta

from core.auth import AuthService, LicenseValidator, UserCredentials, TokenData, LicenseInfo


class TestAuthService:
    """Test authentication service"""
    
    def setup_method(self):
        """Setup test environment"""
        self.auth_service = AuthService()
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "test_password_123"
        
        # Hash password
        hashed = self.auth_service.hash_password(password)
        
        # Verify password
        assert self.auth_service.verify_password(password, hashed)
        assert not self.auth_service.verify_password("wrong_password", hashed)
    
    def test_device_fingerprint_generation(self):
        """Test device fingerprint generation"""
        device_info = {
            "platform": "Windows",
            "processor": "Intel i7",
            "memory": "16GB"
        }
        
        fingerprint1 = self.auth_service.generate_device_fingerprint(device_info)
        fingerprint2 = self.auth_service.generate_device_fingerprint(device_info)
        
        # Same device info should generate same fingerprint
        assert fingerprint1 == fingerprint2
        assert len(fingerprint1) == 16
    
    def test_license_key_creation(self):
        """Test license key creation"""
        user_id = "test_user"
        plan_type = "standard"
        
        license_key1 = self.auth_service.create_license_key(user_id, plan_type)
        license_key2 = self.auth_service.create_license_key(user_id, plan_type)
        
        # Each call should generate unique license key
        assert license_key1 != license_key2
        assert len(license_key1) == 32
        assert license_key1.isupper()  # Should be uppercase
    
    def test_token_creation_and_verification(self):
        """Test JWT token creation and verification"""
        token_data = TokenData(
            user_id="test_user",
            device_id="test_device_123",
            license_key="TEST_LICENSE_KEY",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        # Create token
        token = self.auth_service.create_access_token(token_data)
        
        # Verify token
        verified_data = self.auth_service.verify_token(token)
        
        assert verified_data is not None
        assert verified_data.user_id == token_data.user_id
        assert verified_data.device_id == token_data.device_id
        assert verified_data.license_key == token_data.license_key
    
    def test_expired_token_verification(self):
        """Test verification of expired token"""
        token_data = TokenData(
            user_id="test_user",
            device_id="test_device_123",
            license_key="TEST_LICENSE_KEY",
            expires_at=datetime.utcnow() - timedelta(hours=1)  # Expired
        )
        
        token = self.auth_service.create_access_token(token_data)
        verified_data = self.auth_service.verify_token(token)
        
        # Should return None for expired token
        assert verified_data is None
    
    def test_user_authentication(self):
        """Test user authentication"""
        credentials = UserCredentials(
            username="test_user",
            password="test_password",
            device_fingerprint="test_fingerprint_123"
        )
        
        token_data = self.auth_service.authenticate_user(credentials)
        
        assert token_data is not None
        assert token_data.user_id == credentials.username
        assert token_data.device_id == credentials.device_fingerprint[:16]
        assert len(token_data.license_key) == 32


class TestLicenseValidator:
    """Test license validation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.license_validator = LicenseValidator()
    
    def test_license_validation(self):
        """Test license validation"""
        # Valid license
        valid_license = LicenseInfo(
            license_key="VALID_LICENSE_KEY",
            user_id="test_user",
            device_id="test_device",
            expires_at=datetime.utcnow() + timedelta(days=30),
            features={"signal_parsing": True, "auto_trading": True},
            is_active=True
        )
        
        assert self.license_validator.auth_service.validate_license(valid_license)
        
        # Expired license
        expired_license = LicenseInfo(
            license_key="EXPIRED_LICENSE_KEY",
            user_id="test_user",
            device_id="test_device",
            expires_at=datetime.utcnow() - timedelta(days=1),
            features={"signal_parsing": True},
            is_active=True
        )
        
        assert not self.license_validator.auth_service.validate_license(expired_license)
        
        # Inactive license
        inactive_license = LicenseInfo(
            license_key="INACTIVE_LICENSE_KEY",
            user_id="test_user",
            device_id="test_device",
            expires_at=datetime.utcnow() + timedelta(days=30),
            features={"signal_parsing": True},
            is_active=False
        )
        
        assert not self.license_validator.auth_service.validate_license(inactive_license)
    
    def test_feature_access_check(self):
        """Test feature access checking"""
        license_info = LicenseInfo(
            license_key="TEST_LICENSE_KEY",
            user_id="test_user",
            device_id="test_device",
            expires_at=datetime.utcnow() + timedelta(days=30),
            features={
                "signal_parsing": True,
                "auto_trading": True,
                "advanced_strategies": False
            },
            is_active=True
        )
        
        # Should have access to enabled features
        assert self.license_validator.check_feature_access(license_info, "signal_parsing")
        assert self.license_validator.check_feature_access(license_info, "auto_trading")
        
        # Should not have access to disabled features
        assert not self.license_validator.check_feature_access(license_info, "advanced_strategies")
        
        # Should not have access to non-existent features
        assert not self.license_validator.check_feature_access(license_info, "non_existent_feature")
    
    def test_license_status_retrieval(self):
        """Test license status retrieval"""
        license_key = "TEST_LICENSE_KEY"
        
        status = self.license_validator.get_license_status(license_key)
        
        assert isinstance(status, dict)
        assert "valid" in status
        assert "expires_in_days" in status
        assert "features" in status
        assert isinstance(status["features"], dict)


@pytest.fixture
def sample_user_credentials():
    """Sample user credentials for testing"""
    return UserCredentials(
        username="test_trader",
        password="secure_password_123",
        device_fingerprint="unique_device_fingerprint_hash",
        telegram_id="123456789"
    )


@pytest.fixture
def sample_license_info():
    """Sample license info for testing"""
    return LicenseInfo(
        license_key="SAMPLE_LICENSE_KEY_12345",
        user_id="test_trader",
        device_id="device_123",
        expires_at=datetime.utcnow() + timedelta(days=30),
        features={
            "signal_parsing": True,
            "auto_trading": True,
            "telegram_integration": True,
            "advanced_strategies": False
        },
        is_active=True
    )


def test_auth_integration(sample_user_credentials, sample_license_info):
    """Integration test for authentication flow"""
    auth_service = AuthService()
    
    # Authenticate user
    token_data = auth_service.authenticate_user(sample_user_credentials)
    
    assert token_data is not None
    
    # Create and verify token
    access_token = auth_service.create_access_token(token_data)
    verified_token_data = auth_service.verify_token(access_token)
    
    assert verified_token_data is not None
    assert verified_token_data.user_id == sample_user_credentials.username