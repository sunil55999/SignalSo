"""
Two-Factor Authentication API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from core.two_factor_auth import TwoFactorAuthEngine
from middleware.auth import verify_token
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/2fa", tags=["two-factor-auth"])
security = HTTPBearer()


class SetupTOTPRequest(BaseModel):
    issuer: str = "SignalOS"


class SetupSMSRequest(BaseModel):
    phone_number: str


class SetupEmailRequest(BaseModel):
    email: str


class VerifyCodeRequest(BaseModel):
    code: str


@router.post("/setup/totp")
async def setup_totp(
    request: SetupTOTPRequest,
    current_user: dict = Depends(verify_token)
):
    """Setup TOTP authentication"""
    try:
        user_id = current_user["user_id"]
        
        tfa_engine = TwoFactorAuthEngine()
        await tfa_engine.initialize()
        
        result = await tfa_engine.setup_totp(user_id, request.issuer)
        
        return result
        
    except Exception as e:
        logger.error(f"TOTP setup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup/sms")
async def setup_sms(
    request: SetupSMSRequest,
    current_user: dict = Depends(verify_token)
):
    """Setup SMS authentication"""
    try:
        user_id = current_user["user_id"]
        
        tfa_engine = TwoFactorAuthEngine()
        await tfa_engine.initialize()
        
        result = await tfa_engine.setup_sms(user_id, request.phone_number)
        
        return result
        
    except Exception as e:
        logger.error(f"SMS setup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup/email")
async def setup_email(
    request: SetupEmailRequest,
    current_user: dict = Depends(verify_token)
):
    """Setup email authentication"""
    try:
        user_id = current_user["user_id"]
        
        tfa_engine = TwoFactorAuthEngine()
        await tfa_engine.initialize()
        
        result = await tfa_engine.setup_email(user_id, request.email)
        
        return result
        
    except Exception as e:
        logger.error(f"Email setup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify/totp")
async def verify_totp_setup(
    request: VerifyCodeRequest,
    current_user: dict = Depends(verify_token)
):
    """Verify TOTP setup"""
    try:
        user_id = current_user["user_id"]
        
        tfa_engine = TwoFactorAuthEngine()
        await tfa_engine.initialize()
        
        result = await tfa_engine.verify_totp_setup(user_id, request.code)
        
        return result
        
    except Exception as e:
        logger.error(f"TOTP verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify/sms")
async def verify_sms_setup(
    request: VerifyCodeRequest,
    current_user: dict = Depends(verify_token)
):
    """Verify SMS setup"""
    try:
        user_id = current_user["user_id"]
        
        tfa_engine = TwoFactorAuthEngine()
        await tfa_engine.initialize()
        
        result = await tfa_engine.verify_sms_setup(user_id, request.code)
        
        return result
        
    except Exception as e:
        logger.error(f"SMS verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify/email")
async def verify_email_setup(
    request: VerifyCodeRequest,
    current_user: dict = Depends(verify_token)
):
    """Verify email setup"""
    try:
        user_id = current_user["user_id"]
        
        tfa_engine = TwoFactorAuthEngine()
        await tfa_engine.initialize()
        
        result = await tfa_engine.verify_email_setup(user_id, request.code)
        
        return result
        
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify")
async def verify_2fa_code(
    request: VerifyCodeRequest,
    current_user: dict = Depends(verify_token)
):
    """Verify 2FA code during authentication"""
    try:
        user_id = current_user["user_id"]
        
        tfa_engine = TwoFactorAuthEngine()
        await tfa_engine.initialize()
        
        result = await tfa_engine.verify_2fa_code(user_id, request.code)
        
        return result
        
    except Exception as e:
        logger.error(f"2FA verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/request-code")
async def request_2fa_code(
    current_user: dict = Depends(verify_token)
):
    """Request new 2FA code for SMS/Email methods"""
    try:
        user_id = current_user["user_id"]
        
        tfa_engine = TwoFactorAuthEngine()
        await tfa_engine.initialize()
        
        result = await tfa_engine.request_2fa_code(user_id)
        
        return result
        
    except Exception as e:
        logger.error(f"2FA code request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable")
async def disable_2fa(
    current_user: dict = Depends(verify_token)
):
    """Disable 2FA for user"""
    try:
        user_id = current_user["user_id"]
        
        tfa_engine = TwoFactorAuthEngine()
        await tfa_engine.initialize()
        
        result = await tfa_engine.disable_2fa(user_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to disable 2FA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/regenerate-backup-codes")
async def regenerate_backup_codes(
    current_user: dict = Depends(verify_token)
):
    """Regenerate backup codes"""
    try:
        user_id = current_user["user_id"]
        
        tfa_engine = TwoFactorAuthEngine()
        await tfa_engine.initialize()
        
        result = await tfa_engine.regenerate_backup_codes(user_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to regenerate backup codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_2fa_status(
    current_user: dict = Depends(verify_token)
):
    """Get 2FA status for user"""
    try:
        user_id = current_user["user_id"]
        
        tfa_engine = TwoFactorAuthEngine()
        await tfa_engine.initialize()
        
        status = await tfa_engine.get_2fa_status(user_id)
        
        return {
            "success": True,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Failed to get 2FA status: {e}")
        raise HTTPException(status_code=500, detail=str(e))