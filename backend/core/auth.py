"""
Authentication and licensing core module
"""

import jwt
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from pydantic import BaseModel, validator

from config.settings import get_settings
from utils.logging_config import get_logger

settings = get_settings()
logger = get_logger("auth")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LicenseInfo(BaseModel):
    """License information model"""
    license_key: str
    user_id: str
    device_id: str
    expires_at: datetime
    features: Dict[str, bool] = {}
    is_active: bool = True
    
    @validator("expires_at")
    def validate_expiry(cls, v):
        if v < datetime.utcnow():
            raise ValueError("License has expired")
        return v


class UserCredentials(BaseModel):
    """User credentials model"""
    username: str
    password: str
    telegram_id: Optional[str] = None
    device_fingerprint: str


class TokenData(BaseModel):
    """JWT token data"""
    user_id: str
    device_id: str
    license_key: str
    expires_at: datetime
    token_type: str = "access"  # access or refresh


class RefreshTokenData(BaseModel):
    """Refresh token data"""
    user_id: str
    device_id: str
    token_id: str
    expires_at: datetime


class DeviceBinding(BaseModel):
    """Device binding data"""
    device_id: str
    user_id: str
    device_uuid: str
    ip_address: str
    user_agent: str
    created_at: datetime
    last_seen: datetime
    is_active: bool = True


class AuthService:
    """Authentication service"""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration_hours = settings.JWT_EXPIRATION_HOURS
        self.refresh_expiration_days = 30
        self.device_bindings: Dict[str, DeviceBinding] = {}  # In production, use database
        self.refresh_tokens: Dict[str, RefreshTokenData] = {}  # In production, use database
    
    def hash_password(self, password: str) -> str:
        """Hash password"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def generate_device_fingerprint(self, device_info: Dict[str, Any]) -> str:
        """Generate device fingerprint"""
        fingerprint_data = f"{device_info.get('platform', '')}-{device_info.get('processor', '')}-{device_info.get('memory', '')}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    def create_license_key(self, user_id: str, plan_type: str = "standard") -> str:
        """Create license key"""
        license_data = f"{user_id}-{plan_type}-{uuid.uuid4().hex[:8]}"
        return hashlib.sha256(license_data.encode()).hexdigest()[:32].upper()
    
    def create_access_token(self, token_data: TokenData) -> str:
        """Create JWT access token"""
        payload = {
            "user_id": token_data.user_id,
            "device_id": token_data.device_id,
            "license_key": token_data.license_key,
            "exp": token_data.expires_at,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Access token created for user {token_data.user_id}")
        
        return token
    
    def create_refresh_token(self, user_id: str, device_id: str) -> str:
        """Create JWT refresh token"""
        token_id = uuid.uuid4().hex
        expires_at = datetime.utcnow() + timedelta(days=self.refresh_expiration_days)
        
        refresh_data = RefreshTokenData(
            user_id=user_id,
            device_id=device_id,
            token_id=token_id,
            expires_at=expires_at
        )
        
        payload = {
            "user_id": user_id,
            "device_id": device_id,
            "token_id": token_id,
            "exp": expires_at,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Store refresh token (in production, use database)
        self.refresh_tokens[token_id] = refresh_data
        
        logger.info(f"Refresh token created for user {user_id}")
        return token
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            token_data = TokenData(
                user_id=payload["user_id"],
                device_id=payload["device_id"],
                license_key=payload["license_key"],
                expires_at=datetime.fromtimestamp(payload["exp"])
            )
            
            return token_data
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def bind_device(self, user_id: str, device_uuid: str, ip_address: str, user_agent: str) -> DeviceBinding:
        """Bind device to user account"""
        device_id = f"{user_id}_{hashlib.sha256(device_uuid.encode()).hexdigest()[:8]}"
        
        device_binding = DeviceBinding(
            device_id=device_id,
            user_id=user_id,
            device_uuid=device_uuid,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            is_active=True
        )
        
        # Store device binding (in production, use database)
        self.device_bindings[device_id] = device_binding
        
        logger.info(f"Device {device_uuid} bound to user {user_id}")
        return device_binding
    
    def verify_device_binding(self, user_id: str, device_id: str) -> bool:
        """Verify device is bound to user"""
        device_binding = self.device_bindings.get(device_id)
        if not device_binding:
            logger.warning(f"Device {device_id} not found for user {user_id}")
            return False
        
        if device_binding.user_id != user_id or not device_binding.is_active:
            logger.warning(f"Device {device_id} not authorized for user {user_id}")
            return False
        
        # Update last seen
        device_binding.last_seen = datetime.utcnow()
        return True
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != "refresh":
                logger.warning("Invalid token type for refresh")
                return None
            
            token_id = payload.get("token_id")
            stored_token = self.refresh_tokens.get(token_id)
            
            if not stored_token or stored_token.expires_at < datetime.utcnow():
                logger.warning("Refresh token expired or not found")
                return None
            
            # Create new access token
            expires_at = datetime.utcnow() + timedelta(hours=self.expiration_hours)
            token_data = TokenData(
                user_id=stored_token.user_id,
                device_id=stored_token.device_id,
                license_key="",  # Will be filled by license validator
                expires_at=expires_at
            )
            
            return self.create_access_token(token_data)
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None
    
    def revoke_refresh_token(self, token_id: str) -> bool:
        """Revoke refresh token"""
        if token_id in self.refresh_tokens:
            del self.refresh_tokens[token_id]
            logger.info(f"Refresh token {token_id} revoked")
            return True
        return False
    
    def validate_license(self, license_info: LicenseInfo) -> bool:
        """Validate license"""
        try:
            # Check if license is active
            if not license_info.is_active:
                logger.warning(f"License {license_info.license_key} is not active")
                return False
            
            # Check expiration
            if license_info.expires_at < datetime.utcnow():
                logger.warning(f"License {license_info.license_key} has expired")
                return False
            
            # Additional license validation logic
            return True
            
        except Exception as e:
            logger.error(f"License validation error: {e}")
            return False
    
    def authenticate_user(self, credentials: UserCredentials) -> Optional[TokenData]:
        """Authenticate user and return token data"""
        try:
            # In production, this would validate against a database
            # For now, we'll use a basic validation
            
            if not credentials.username or not credentials.password:
                logger.warning("Invalid credentials provided")
                return None
            
            # Generate device ID from fingerprint
            device_id = credentials.device_fingerprint[:16]
            
            # Create token data
            expires_at = datetime.utcnow() + timedelta(hours=self.expiration_hours)
            
            token_data = TokenData(
                user_id=credentials.username,
                device_id=device_id,
                license_key=self.create_license_key(credentials.username),
                expires_at=expires_at
            )
            
            logger.info(f"User {credentials.username} authenticated successfully")
            return token_data
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None


class LicenseValidator:
    """License validation service"""
    
    def __init__(self):
        self.auth_service = AuthService()
    
    def check_feature_access(self, license_info: LicenseInfo, feature: str) -> bool:
        """Check if license allows access to specific feature"""
        if not self.auth_service.validate_license(license_info):
            return False
        
        return license_info.features.get(feature, False)
    
    def get_license_status(self, license_key: str) -> Dict[str, Any]:
        """Get license status information"""
        # In production, this would query a database
        return {
            "valid": True,
            "expires_in_days": 30,
            "features": {
                "signal_parsing": True,
                "auto_trading": True,
                "advanced_strategies": True,
                "telegram_integration": True
            }
        }