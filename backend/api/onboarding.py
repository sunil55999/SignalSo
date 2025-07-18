"""
Onboarding API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from core.onboarding import OnboardingEngine
from middleware.auth import verify_token
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/onboarding", tags=["onboarding"])
security = HTTPBearer()


class CompleteStepRequest(BaseModel):
    step_data: Dict[str, Any]


class SkipStepRequest(BaseModel):
    reason: str


@router.post("/start")
async def start_onboarding(
    current_user: dict = Depends(verify_token)
):
    """Start onboarding process"""
    try:
        user_id = current_user["user_id"]
        
        onboarding = OnboardingEngine()
        await onboarding.initialize()
        
        result = await onboarding.start_onboarding(user_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to start onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current-step")
async def get_current_step(
    current_user: dict = Depends(verify_token)
):
    """Get current onboarding step"""
    try:
        user_id = current_user["user_id"]
        
        onboarding = OnboardingEngine()
        await onboarding.initialize()
        
        result = await onboarding.get_current_step(user_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get current step: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/steps/{step_id}/complete")
async def complete_step(
    step_id: str,
    request: CompleteStepRequest,
    current_user: dict = Depends(verify_token)
):
    """Complete an onboarding step"""
    try:
        user_id = current_user["user_id"]
        
        onboarding = OnboardingEngine()
        await onboarding.initialize()
        
        result = await onboarding.complete_step(user_id, step_id, request.step_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to complete step: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/steps/{step_id}/skip")
async def skip_step(
    step_id: str,
    request: SkipStepRequest,
    current_user: dict = Depends(verify_token)
):
    """Skip an optional onboarding step"""
    try:
        user_id = current_user["user_id"]
        
        onboarding = OnboardingEngine()
        await onboarding.initialize()
        
        result = await onboarding.skip_step(user_id, step_id, request.reason)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to skip step: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/steps/{step_id}/restart")
async def restart_step(
    step_id: str,
    current_user: dict = Depends(verify_token)
):
    """Restart a failed or completed step"""
    try:
        user_id = current_user["user_id"]
        
        onboarding = OnboardingEngine()
        await onboarding.initialize()
        
        result = await onboarding.restart_step(user_id, step_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to restart step: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress")
async def get_progress(
    current_user: dict = Depends(verify_token)
):
    """Get onboarding progress"""
    try:
        user_id = current_user["user_id"]
        
        onboarding = OnboardingEngine()
        await onboarding.initialize()
        
        result = await onboarding.get_progress(user_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_onboarding_summary(
    current_user: dict = Depends(verify_token)
):
    """Get complete onboarding summary"""
    try:
        user_id = current_user["user_id"]
        
        onboarding = OnboardingEngine()
        await onboarding.initialize()
        
        result = await onboarding.get_onboarding_summary(user_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get onboarding summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))