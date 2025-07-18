"""
Authentication API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional

from core.auth import AuthService, UserCredentials, TokenData, LicenseValidator, DeviceBinding
from utils.logging_config import get_logger

logger = get_logger("api.auth")
auth_router = APIRouter()
auth_service = AuthService()
license_validator = LicenseValidator()


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str
    device_info: Dict[str, Any]


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    license_key: str


class RegisterRequest(BaseModel):
    """Registration request model"""
    username: str
    password: str
    email: str
    device_info: Dict[str, Any]
    telegram_id: Optional[str] = None


class LicenseStatusResponse(BaseModel):
    """License status response model"""
    valid: bool
    expires_in_days: int
    features: Dict[str, bool]


@auth_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """User login endpoint"""
    try:
        # Create credentials
        device_fingerprint = auth_service.generate_device_fingerprint(request.device_info)
        
        credentials = UserCredentials(
            username=request.username,
            password=request.password,
            device_fingerprint=device_fingerprint
        )
        
        # Authenticate user
        token_data = auth_service.authenticate_user(credentials)
        
        if not token_data:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # Create access token
        access_token = auth_service.create_access_token(token_data)
        
        logger.info(f"User {request.username} logged in successfully")
        
        return LoginResponse(
            access_token=access_token,
            expires_in=auth_service.expiration_hours * 3600,
            user_id=token_data.user_id,
            license_key=token_data.license_key
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@auth_router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest):
    """User registration endpoint"""
    try:
        # In production, this would create user in database
        # For now, we'll simulate registration
        
        device_fingerprint = auth_service.generate_device_fingerprint(request.device_info)
        
        # Hash password
        hashed_password = auth_service.hash_password(request.password)
        
        # Create credentials for login
        credentials = UserCredentials(
            username=request.username,
            password=request.password,  # Use plain password for authentication
            device_fingerprint=device_fingerprint,
            telegram_id=request.telegram_id
        )
        
        # Authenticate (simulate successful registration)
        token_data = auth_service.authenticate_user(credentials)
        
        if not token_data:
            raise HTTPException(
                status_code=400,
                detail="Registration failed"
            )
        
        # Create access token
        access_token = auth_service.create_access_token(token_data)
        
        logger.info(f"User {request.username} registered successfully")
        
        return LoginResponse(
            access_token=access_token,
            expires_in=auth_service.expiration_hours * 3600,
            user_id=token_data.user_id,
            license_key=token_data.license_key
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@auth_router.get("/license-status", response_model=LicenseStatusResponse)
async def get_license_status(request: Request):
    """Get license status for authenticated user"""
    try:
        # Get license key from request state (set by auth middleware)
        license_key = getattr(request.state, 'license_key', None)
        
        if not license_key:
            raise HTTPException(status_code=401, detail="License key not found")
        
        # Get license status
        license_status = license_validator.get_license_status(license_key)
        
        return LicenseStatusResponse(**license_status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"License status error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@auth_router.post("/refresh-token")
async def refresh_token(request: Request):
    """Refresh access token"""
    try:
        # Get current token data from request state
        user_id = getattr(request.state, 'user_id', None)
        device_id = getattr(request.state, 'device_id', None)
        license_key = getattr(request.state, 'license_key', None)
        
        if not all([user_id, device_id, license_key]):
            raise HTTPException(status_code=401, detail="Invalid token data")
        
        # Create new token data
        from datetime import datetime, timedelta
        new_token_data = TokenData(
            user_id=user_id,
            device_id=device_id,
            license_key=license_key,
            expires_at=datetime.utcnow() + timedelta(hours=auth_service.expiration_hours)
        )
        
        # Create new access token
        new_access_token = auth_service.create_access_token(new_token_data)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": auth_service.expiration_hours * 3600
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@auth_router.post("/logout")
async def logout(request: Request):
    """User logout endpoint"""
    try:
        user_id = getattr(request.state, 'user_id', None)
        
        # In production, would invalidate token in database/cache
        logger.info(f"User {user_id} logged out")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Part 2 Guide - Enhanced Auth Endpoints

class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class DeviceBindingRequest(BaseModel):
    """Device binding request"""
    device_uuid: str
    device_fingerprint: str
    ip_address: str
    user_agent: str


class TokenVerifyRequest(BaseModel):
    """Token verification request"""
    token: str


def get_current_user(request: Request):
    """Get current user from request state"""
    user_id = getattr(request.state, 'user_id', None)
    device_id = getattr(request.state, 'device_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"user_id": user_id, "device_id": device_id}


@auth_router.post("/verify")
async def verify_token(request: TokenVerifyRequest):
    """Validate token endpoint - Part 2 guide"""
    try:
        token_data = auth_service.verify_token(request.token)
        
        if not token_data:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Verify device binding
        device_valid = auth_service.verify_device_binding(token_data.user_id, token_data.device_id)
        
        if not device_valid:
            raise HTTPException(status_code=401, detail="Device not authorized")
        
        return {
            "valid": True,
            "user_id": token_data.user_id,
            "device_id": token_data.device_id,
            "expires_at": token_data.expires_at.isoformat(),
            "message": "Token verified successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=500, detail="Token verification failed")


@auth_router.post("/bind-device")
async def bind_device(request: DeviceBindingRequest, current_user: dict = Depends(get_current_user)):
    """Save UUID/IP for hardware lock - Part 2 guide"""
    try:
        user_id = current_user["user_id"]
        
        device_binding = auth_service.bind_device(
            user_id=user_id,
            device_uuid=request.device_uuid,
            ip_address=request.ip_address,
            user_agent=request.user_agent
        )
        
        logger.info(f"Device bound for user {user_id}")
        return {
            "success": True,
            "device_id": device_binding.device_id,
            "device_uuid": device_binding.device_uuid,
            "bound_at": device_binding.created_at.isoformat(),
            "message": "Device bound successfully"
        }
        
    except Exception as e:
        logger.error(f"Device binding error: {e}")
        raise HTTPException(status_code=500, detail="Device binding failed")