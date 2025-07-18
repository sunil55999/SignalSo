"""
Signal processing API endpoints
"""

from fastapi import APIRouter, HTTPException, Request, File, UploadFile, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import base64

from services.parser_ai import SignalProcessor, ParsedSignal
from workers.queue_manager import TaskPriority
from utils.logging_config import get_logger

logger = get_logger("api.signals")
signals_router = APIRouter()


class SignalParseRequest(BaseModel):
    """Signal parsing request model"""
    text: str
    image_data: Optional[str] = None  # Base64 encoded image
    priority: str = "normal"
    auto_execute: bool = False


class SignalParseResponse(BaseModel):
    """Signal parsing response model"""
    success: bool
    task_id: Optional[str] = None
    parsed_signal: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SignalValidateRequest(BaseModel):
    """Signal validation request model"""
    signal_data: Dict[str, Any]


class SignalStatsResponse(BaseModel):
    """Signal processing statistics response"""
    total_processed: int
    successful_parses: int
    failed_parses: int
    success_rate: float
    ai_success_rate: float


@signals_router.post("/parse", response_model=SignalParseResponse)
async def parse_signal(request: SignalParseRequest, bg_request: Request, background_tasks: BackgroundTasks):
    """Parse trading signal from text/image"""
    try:
        # Get queue manager from app state
        queue_manager = bg_request.app.state.queue_manager
        
        # Decode image data if provided
        image_bytes = None
        if request.image_data:
            try:
                image_bytes = base64.b64decode(request.image_data)
            except Exception as e:
                logger.warning(f"Failed to decode image data: {e}")
        
        # Determine priority
        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL
        }
        priority = priority_map.get(request.priority.lower(), TaskPriority.NORMAL)
        
        # Prepare task data
        task_data = {
            "text": request.text,
            "image_data": image_bytes,
            "auto_execute": request.auto_execute,
            "user_id": getattr(bg_request.state, 'user_id', 'unknown')
        }
        
        # Add to queue
        task_id = await queue_manager.add_task("parse_signal", task_data, priority)
        
        logger.info(f"Signal parsing task {task_id} added to queue")
        
        return SignalParseResponse(
            success=True,
            task_id=task_id
        )
        
    except Exception as e:
        logger.error(f"Signal parsing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@signals_router.post("/parse-sync", response_model=SignalParseResponse)
async def parse_signal_sync(request: SignalParseRequest):
    """Parse trading signal synchronously (for testing)"""
    try:
        # Create signal processor
        processor = SignalProcessor()
        
        # Decode image data if provided
        image_bytes = None
        if request.image_data:
            try:
                image_bytes = base64.b64decode(request.image_data)
            except Exception as e:
                logger.warning(f"Failed to decode image data: {e}")
        
        # Process signal
        parsed_signal = await processor.process_signal(request.text, image_bytes)
        
        if parsed_signal:
            return SignalParseResponse(
                success=True,
                parsed_signal=parsed_signal.to_dict()
            )
        else:
            return SignalParseResponse(
                success=False,
                error="Failed to parse signal"
            )
            
    except Exception as e:
        logger.error(f"Sync signal parsing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@signals_router.post("/upload", response_model=SignalParseResponse)
async def upload_signal_image(
    file: UploadFile = File(...),
    auto_execute: bool = False,
    priority: str = "normal",
    bg_request: Request = None
):
    """Upload and parse signal from image file"""
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file data
        image_data = await file.read()
        
        # Get queue manager
        queue_manager = bg_request.app.state.queue_manager
        
        # Determine priority
        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL
        }
        task_priority = priority_map.get(priority.lower(), TaskPriority.NORMAL)
        
        # Prepare task data
        task_data = {
            "text": "",  # No text for image-only
            "image_data": image_data,
            "auto_execute": auto_execute,
            "user_id": getattr(bg_request.state, 'user_id', 'unknown'),
            "filename": file.filename
        }
        
        # Add to queue
        task_id = await queue_manager.add_task("parse_signal", task_data, task_priority)
        
        logger.info(f"Image signal parsing task {task_id} added to queue")
        
        return SignalParseResponse(
            success=True,
            task_id=task_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@signals_router.post("/validate", response_model=Dict[str, Any])
async def validate_signal(request: SignalValidateRequest):
    """Validate parsed signal data"""
    try:
        signal_data = request.signal_data
        
        # Basic validation
        required_fields = ["symbol", "signal_type"]
        missing_fields = [field for field in required_fields if field not in signal_data]
        
        if missing_fields:
            return {
                "valid": False,
                "errors": f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        # Validate signal type
        valid_types = ["BUY", "SELL", "CLOSE", "MODIFY"]
        if signal_data.get("signal_type") not in valid_types:
            return {
                "valid": False,
                "errors": f"Invalid signal type. Must be one of: {', '.join(valid_types)}"
            }
        
        # Validate symbol format
        symbol = signal_data.get("symbol", "")
        if len(symbol) < 3:
            return {
                "valid": False,
                "errors": "Symbol must be at least 3 characters"
            }
        
        # Additional validations
        warnings = []
        
        # Check for entry price
        if not signal_data.get("entry_price"):
            warnings.append("No entry price specified")
        
        # Check for stop loss
        if not signal_data.get("stop_loss"):
            warnings.append("No stop loss specified")
        
        # Check for take profit
        if not signal_data.get("take_profit"):
            warnings.append("No take profit levels specified")
        
        return {
            "valid": True,
            "warnings": warnings,
            "confidence": signal_data.get("confidence", "UNCERTAIN")
        }
        
    except Exception as e:
        logger.error(f"Signal validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@signals_router.get("/task/{task_id}")
async def get_task_status(task_id: str, bg_request: Request):
    """Get status of signal processing task"""
    try:
        # In production, this would query task status from database/cache
        # For now, return basic status
        
        return {
            "task_id": task_id,
            "status": "completed",  # Simulated
            "progress": 100,
            "result": {
                "success": True,
                "message": "Signal processed successfully"
            }
        }
        
    except Exception as e:
        logger.error(f"Task status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@signals_router.get("/stats", response_model=SignalStatsResponse)
async def get_signal_stats():
    """Get signal processing statistics"""
    try:
        # Create processor to get stats
        processor = SignalProcessor()
        stats = processor.get_processing_stats()
        
        return SignalStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@signals_router.get("/history")
async def get_signal_history(
    limit: int = 100,
    offset: int = 0,
    bg_request: Request = None
):
    """Get signal processing history"""
    try:
        user_id = getattr(bg_request.state, 'user_id', None)
        
        # In production, this would query database
        # For now, return sample data
        
        sample_signals = [
            {
                "id": f"signal_{i}",
                "symbol": "EURUSD",
                "signal_type": "BUY",
                "confidence": "HIGH",
                "processed_at": "2025-01-18T10:00:00Z",
                "executed": i % 2 == 0
            }
            for i in range(1, min(limit + 1, 11))
        ]
        
        return {
            "signals": sample_signals[offset:offset + limit],
            "total": len(sample_signals),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@signals_router.delete("/history/{signal_id}")
async def delete_signal(signal_id: str, bg_request: Request):
    """Delete a signal from history"""
    try:
        user_id = getattr(bg_request.state, 'user_id', None)
        
        # In production, would delete from database
        logger.info(f"Signal {signal_id} deleted by user {user_id}")
        
        return {"message": f"Signal {signal_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Delete signal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))