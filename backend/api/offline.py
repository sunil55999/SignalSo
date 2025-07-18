"""
Offline Operations API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import HTTPBearer
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from core.offline import OfflineOperationEngine
from middleware.auth import verify_token
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/offline", tags=["offline"])
security = HTTPBearer()


class OfflineSignalRequest(BaseModel):
    text: str
    image_data: Optional[str] = None
    provider_id: Optional[str] = None


class OfflineTradeRequest(BaseModel):
    symbol: str
    type: str
    volume: float
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None


class SyncRequest(BaseModel):
    force_sync: bool = False


@router.post("/parse-signal")
async def parse_signal_offline(
    request: OfflineSignalRequest,
    current_user: dict = Depends(verify_token)
):
    """Parse signal while offline"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize offline engine
        offline_engine = OfflineOperationEngine(user_id)
        await offline_engine.initialize()
        
        # Parse signal offline
        result = await offline_engine.parse_signal_offline(
            signal_text=request.text,
            image_data=request.image_data
        )
        
        return {
            "success": True,
            "signal": result,
            "message": "Signal parsed offline successfully"
        }
        
    except Exception as e:
        logger.error(f"Offline signal parsing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-trade")
async def execute_trade_offline(
    request: OfflineTradeRequest,
    current_user: dict = Depends(verify_token)
):
    """Queue trade for offline execution"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize offline engine
        offline_engine = OfflineOperationEngine(user_id)
        await offline_engine.initialize()
        
        # Queue trade for offline execution
        trade_params = {
            "symbol": request.symbol,
            "type": request.type,
            "volume": request.volume,
            "price": request.price,
            "sl": request.sl,
            "tp": request.tp
        }
        
        result = await offline_engine.execute_trade_offline(trade_params)
        
        return {
            "success": True,
            "trade": result,
            "message": "Trade queued for offline execution"
        }
        
    except Exception as e:
        logger.error(f"Offline trade execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_offline_actions(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(verify_token)
):
    """Sync offline actions with server"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize offline engine
        offline_engine = OfflineOperationEngine(user_id)
        await offline_engine.initialize()
        
        # Set online status
        await offline_engine.set_online_status(True)
        
        # Sync in background if not force sync
        if not request.force_sync:
            background_tasks.add_task(offline_engine.sync_offline_actions)
            return {
                "success": True,
                "message": "Sync started in background"
            }
        
        # Sync immediately
        sync_result = await offline_engine.sync_offline_actions()
        
        return {
            "success": True,
            "sync_result": sync_result,
            "message": "Offline actions synced successfully"
        }
        
    except Exception as e:
        logger.error(f"Offline sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_offline_status(
    current_user: dict = Depends(verify_token)
):
    """Get offline operation status"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize offline engine
        offline_engine = OfflineOperationEngine(user_id)
        await offline_engine.initialize()
        
        # Get status
        status = await offline_engine.get_offline_status()
        
        return {
            "success": True,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Failed to get offline status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set-online-status")
async def set_online_status(
    is_online: bool,
    current_user: dict = Depends(verify_token)
):
    """Set online/offline status"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize offline engine
        offline_engine = OfflineOperationEngine(user_id)
        await offline_engine.initialize()
        
        # Set online status
        await offline_engine.set_online_status(is_online)
        
        return {
            "success": True,
            "message": f"Status set to {'online' if is_online else 'offline'}"
        }
        
    except Exception as e:
        logger.error(f"Failed to set online status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup")
async def cleanup_old_actions(
    days_old: int = 30,
    current_user: dict = Depends(verify_token)
):
    """Clean up old offline actions"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize offline engine
        offline_engine = OfflineOperationEngine(user_id)
        await offline_engine.initialize()
        
        # Cleanup old actions
        deleted_count = await offline_engine.cleanup_old_actions(days_old)
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} old actions"
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))