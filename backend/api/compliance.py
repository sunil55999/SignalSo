"""
Compliance API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from core.compliance import ComplianceEngine
from middleware.auth import verify_token
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/compliance", tags=["compliance"])
security = HTTPBearer()


class ActivateComplianceRequest(BaseModel):
    profile_name: str
    custom_restrictions: Optional[Dict[str, Any]] = None


class CreateCustomProfileRequest(BaseModel):
    name: str
    description: str
    restrictions: Dict[str, Any]


class ValidateTradeRequest(BaseModel):
    symbol: str
    type: str
    volume: float
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None


@router.get("/profiles")
async def get_available_profiles(
    current_user: dict = Depends(verify_token)
):
    """Get available compliance profiles"""
    try:
        compliance = ComplianceEngine()
        await compliance.initialize()
        
        result = await compliance.get_available_profiles()
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get compliance profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/{profile_id}")
async def get_profile_details(
    profile_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get detailed profile information"""
    try:
        compliance = ComplianceEngine()
        await compliance.initialize()
        
        result = await compliance.get_profile_details(profile_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get profile details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate")
async def activate_compliance_mode(
    request: ActivateComplianceRequest,
    current_user: dict = Depends(verify_token)
):
    """Activate compliance mode for user"""
    try:
        user_id = current_user["user_id"]
        
        compliance = ComplianceEngine()
        await compliance.initialize()
        
        result = await compliance.activate_compliance_mode(
            user_id, request.profile_name, request.custom_restrictions
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to activate compliance mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deactivate")
async def deactivate_compliance_mode(
    current_user: dict = Depends(verify_token)
):
    """Deactivate compliance mode for user"""
    try:
        user_id = current_user["user_id"]
        
        compliance = ComplianceEngine()
        await compliance.initialize()
        
        result = await compliance.deactivate_compliance_mode(user_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to deactivate compliance mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-trade")
async def validate_trade(
    request: ValidateTradeRequest,
    current_user: dict = Depends(verify_token)
):
    """Validate trade against compliance rules"""
    try:
        user_id = current_user["user_id"]
        
        compliance = ComplianceEngine()
        await compliance.initialize()
        
        trade_params = {
            "symbol": request.symbol,
            "type": request.type,
            "volume": request.volume,
            "price": request.price,
            "sl": request.sl,
            "tp": request.tp
        }
        
        result = await compliance.validate_trade(user_id, trade_params)
        
        return {
            "success": True,
            "validation": result
        }
        
    except Exception as e:
        logger.error(f"Trade validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_compliance_status(
    current_user: dict = Depends(verify_token)
):
    """Get compliance status for user"""
    try:
        user_id = current_user["user_id"]
        
        compliance = ComplianceEngine()
        await compliance.initialize()
        
        status = await compliance.get_compliance_status(user_id)
        
        return {
            "success": True,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Failed to get compliance status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom-profile")
async def create_custom_profile(
    request: CreateCustomProfileRequest,
    current_user: dict = Depends(verify_token)
):
    """Create custom compliance profile"""
    try:
        user_id = current_user["user_id"]
        
        compliance = ComplianceEngine()
        await compliance.initialize()
        
        profile_data = {
            "name": request.name,
            "description": request.description,
            "restrictions": request.restrictions
        }
        
        result = await compliance.create_custom_profile(user_id, profile_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create custom profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def generate_compliance_report(
    days: int = 30,
    current_user: dict = Depends(verify_token)
):
    """Generate compliance report for user"""
    try:
        user_id = current_user["user_id"]
        
        compliance = ComplianceEngine()
        await compliance.initialize()
        
        result = await compliance.generate_compliance_report(user_id, days)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))