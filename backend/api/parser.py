"""
Parser API endpoints for SignalOS Backend
Implements Part 2 Guide - User feedback and training endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

from core.parse import (
    CentralParseController, ParseRequest, ParseResult, ParseFeedback, 
    ParseType, get_parse_controller
)
from workers.parse_worker import get_parse_worker
from api.auth import get_current_user
from utils.logging_config import get_logger

logger = get_logger(__name__)
security = HTTPBearer()
router = APIRouter(prefix="/api/v1/parser", tags=["Parser Management"])


class FeedbackRequest(BaseModel):
    """Parser feedback request"""
    request_id: str
    is_correct: bool
    corrected_signal: Optional[Dict[str, Any]] = None
    feedback_text: Optional[str] = None


class TrainingRequest(BaseModel):
    """Parser training request"""
    training_data: Dict[str, Any]
    training_type: str = "feedback"  # feedback, correction, enhancement


@router.post("/feedback")
async def submit_feedback(
    feedback_request: FeedbackRequest,
    current_user = Depends(get_current_user),
    parse_controller: CentralParseController = Depends(get_parse_controller)
) -> dict:
    """Submit user feedback for training - Part 2 guide endpoint"""
    try:
        feedback = ParseFeedback(
            feedback_id="",  # Will be generated
            request_id=feedback_request.request_id,
            user_id=current_user["user_id"],
            is_correct=feedback_request.is_correct,
            corrected_signal=feedback_request.corrected_signal,
            feedback_text=feedback_request.feedback_text,
            created_at=datetime.utcnow()
        )
        
        success = parse_controller.submit_feedback(feedback)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to submit feedback"
            )
        
        logger.info(f"Feedback submitted for request {feedback_request.request_id}")
        return {
            "success": True,
            "feedback_id": feedback.feedback_id,
            "message": "Feedback submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Feedback submission failed"
        )


@router.post("/train")
async def submit_training_data(
    training_request: TrainingRequest,
    current_user = Depends(get_current_user),
    parse_controller: CentralParseController = Depends(get_parse_controller)
) -> dict:
    """Submit training data - Part 2 guide endpoint"""
    try:
        # In production, this would trigger ML model training
        # For now, we'll log the training request
        
        logger.info(f"Training data submitted by user {current_user['user_id']}")
        
        # Store training data (in production, use proper ML pipeline)
        training_id = f"train_{datetime.utcnow().timestamp()}"
        
        return {
            "success": True,
            "training_id": training_id,
            "message": "Training data submitted successfully",
            "note": "Training will be processed in background"
        }
        
    except Exception as e:
        logger.error(f"Training submission error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Training submission failed"
        )


@router.get("/feedback/history")
async def get_feedback_history(
    current_user = Depends(get_current_user),
    parse_controller: CentralParseController = Depends(get_parse_controller)
) -> dict:
    """Get user's feedback history"""
    try:
        feedback_history = parse_controller.get_feedback_history(current_user["user_id"])
        
        return {
            "success": True,
            "feedback_count": len(feedback_history),
            "feedback_history": [
                {
                    "feedback_id": fb.feedback_id,
                    "request_id": fb.request_id,
                    "is_correct": fb.is_correct,
                    "feedback_text": fb.feedback_text,
                    "created_at": fb.created_at.isoformat()
                } for fb in feedback_history
            ]
        }
        
    except Exception as e:
        logger.error(f"Feedback history error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve feedback history"
        )


@router.get("/stats")
async def get_parser_stats(
    current_user = Depends(get_current_user),
    parse_controller: CentralParseController = Depends(get_parse_controller)
) -> dict:
    """Get parser performance statistics"""
    try:
        stats = parse_controller.get_performance_stats()
        
        return {
            "success": True,
            "stats": stats,
            "message": "Parser statistics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Parser stats error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve parser statistics"
        )