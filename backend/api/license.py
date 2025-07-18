"""
License API endpoints for SignalOS Backend
Implements Part 2 guide licensing endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from core.license import (
    LicenseEngine, License, LicenseActivation, LicenseRenewal, 
    LicenseStatus, get_license_engine
)
from api.auth import get_current_user
from utils.logging_config import get_logger

logger = get_logger(__name__)
security = HTTPBearer()
router = APIRouter(prefix="/api/v1/license", tags=["License Management"])


class LicenseCreateRequest(BaseModel):
    """Create license request"""
    user_id: str
    plan_type: str = "standard"
    duration_days: int = 30


class LicenseResponse(BaseModel):
    """License response"""
    success: bool
    license: Optional[License] = None
    status: Optional[LicenseStatus] = None
    message: str


@router.get("/status")
async def get_license_status(
    license_key: str,
    current_user = Depends(get_current_user),
    license_engine: LicenseEngine = Depends(get_license_engine)
) -> LicenseResponse:
    """Get license status - Part 2 guide endpoint"""
    try:
        status = license_engine.get_license_status(license_key)
        
        if not status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License not found"
            )
        
        # Verify user owns this license
        license_obj = license_engine.licenses.get(license_key)
        if license_obj and license_obj.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        logger.info(f"License status retrieved: {license_key}")
        return LicenseResponse(
            success=True,
            status=status,
            message="License status retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"License status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/activate")
async def activate_license(
    activation: LicenseActivation,
    current_user = Depends(get_current_user),
    license_engine: LicenseEngine = Depends(get_license_engine)
) -> LicenseResponse:
    """Activate license for device - Part 2 guide endpoint"""
    try:
        # Verify user matches current user
        if activation.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User ID mismatch"
            )
        
        success = license_engine.activate_license(activation)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License activation failed"
            )
        
        # Get updated license status
        license_status = license_engine.get_license_status(activation.license_key)
        
        logger.info(f"License activated: {activation.license_key}")
        return LicenseResponse(
            success=True,
            status=license_status,
            message="License activated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"License activation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="License activation failed"
        )


@router.post("/renew")
async def renew_license(
    renewal: LicenseRenewal,
    current_user = Depends(get_current_user),
    license_engine: LicenseEngine = Depends(get_license_engine)
) -> LicenseResponse:
    """Renew license - Part 2 guide endpoint"""
    try:
        # Verify user owns this license
        license_obj = license_engine.licenses.get(renewal.license_key)
        if not license_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License not found"
            )
        
        if license_obj.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        success = license_engine.renew_license(renewal)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License renewal failed"
            )
        
        # Get updated license status
        license_status = license_engine.get_license_status(renewal.license_key)
        
        logger.info(f"License renewed: {renewal.license_key}")
        return LicenseResponse(
            success=True,
            status=license_status,
            message="License renewed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"License renewal error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="License renewal failed"
        )


@router.post("/create")
async def create_license(
    request: LicenseCreateRequest,
    current_user = Depends(get_current_user),
    license_engine: LicenseEngine = Depends(get_license_engine)
) -> LicenseResponse:
    """Create new license (admin only)"""
    try:
        # In production, add admin role check
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        license_obj = license_engine.create_license(
            user_id=request.user_id,
            plan_type=request.plan_type,
            duration_days=request.duration_days
        )
        
        logger.info(f"License created: {license_obj.key}")
        return LicenseResponse(
            success=True,
            license=license_obj,
            message="License created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"License creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="License creation failed"
        )


@router.delete("/deactivate/{license_key}")
async def deactivate_license(
    license_key: str,
    current_user = Depends(get_current_user),
    license_engine: LicenseEngine = Depends(get_license_engine)
) -> LicenseResponse:
    """Deactivate license"""
    try:
        # Verify user owns this license or is admin
        license_obj = license_engine.licenses.get(license_key)
        if not license_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License not found"
            )
        
        user_is_owner = license_obj.user_id == current_user["user_id"]
        user_is_admin = current_user.get("role") == "admin"
        
        if not (user_is_owner or user_is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        success = license_engine.deactivate_license(license_key, "user_request")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License deactivation failed"
            )
        
        logger.info(f"License deactivated: {license_key}")
        return LicenseResponse(
            success=True,
            message="License deactivated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"License deactivation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="License deactivation failed"
        )


@router.get("/user/{user_id}")
async def get_user_licenses(
    user_id: str,
    current_user = Depends(get_current_user),
    license_engine: LicenseEngine = Depends(get_license_engine)
) -> dict:
    """Get all licenses for user"""
    try:
        # Users can only see their own licenses, admins can see any
        if user_id != current_user["user_id"] and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        licenses = license_engine.get_user_licenses(user_id)
        
        return {
            "success": True,
            "licenses": licenses,
            "count": len(licenses),
            "message": "User licenses retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user licenses error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user licenses"
        )


@router.post("/unbind-device")
async def unbind_device(
    license_key: str,
    device_id: str,
    current_user = Depends(get_current_user),
    license_engine: LicenseEngine = Depends(get_license_engine)
) -> LicenseResponse:
    """Unbind device from license"""
    try:
        # Verify user owns this license
        license_obj = license_engine.licenses.get(license_key)
        if not license_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License not found"
            )
        
        if license_obj.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        success = license_engine.unbind_device(license_key, device_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Device unbinding failed"
            )
        
        logger.info(f"Device {device_id} unbound from license {license_key}")
        return LicenseResponse(
            success=True,
            message="Device unbound successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device unbinding error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Device unbinding failed"
        )


@router.post("/cleanup")
async def cleanup_expired_licenses(
    current_user = Depends(get_current_user),
    license_engine: LicenseEngine = Depends(get_license_engine)
) -> dict:
    """Cleanup expired licenses (admin only)"""
    try:
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        expired_count = license_engine.cleanup_expired_licenses()
        
        return {
            "success": True,
            "expired_count": expired_count,
            "message": f"Cleaned up {expired_count} expired licenses"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"License cleanup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="License cleanup failed"
        )