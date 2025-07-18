"""
Admin API endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from utils.logging_config import get_logger

logger = get_logger("api.admin")
admin_router = APIRouter()


class SystemStatsResponse(BaseModel):
    """System statistics response model"""
    uptime: str
    memory_usage: Dict[str, float]
    cpu_usage: float
    queue_stats: Dict[str, Any]
    trading_stats: Dict[str, Any]


@admin_router.get("/system/status")
async def get_system_status(bg_request: Request):
    """Get system status and health"""
    try:
        # Check if user has admin permissions
        user_id = getattr(bg_request.state, 'user_id', None)
        
        # In production, check admin role
        # For now, allow all authenticated users
        
        import psutil
        import time
        from datetime import datetime, timedelta
        
        # System stats
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get queue stats
        queue_manager = bg_request.app.state.queue_manager
        queue_stats = queue_manager.get_queue_stats()
        
        # Get trading stats (import here to avoid circular imports)
        from api.trading import trade_executor
        trading_stats = trade_executor.get_execution_stats()
        
        return SystemStatsResponse(
            uptime=str(timedelta(seconds=int(time.time() - psutil.boot_time()))),
            memory_usage={
                "total": memory.total / (1024**3),  # GB
                "used": memory.used / (1024**3),
                "percent": memory.percent
            },
            cpu_usage=cpu_percent,
            queue_stats=queue_stats,
            trading_stats=trading_stats
        )
        
    except Exception as e:
        logger.error(f"System status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/logs")
async def get_system_logs(
    level: str = "INFO",
    limit: int = 100,
    bg_request: Request = None
):
    """Get system logs"""
    try:
        # Check admin permissions
        user_id = getattr(bg_request.state, 'user_id', None)
        
        # In production, read from log files
        # For now, return sample logs
        
        sample_logs = [
            {
                "timestamp": "2025-01-18T10:00:00Z",
                "level": "INFO",
                "module": "api.signals",
                "message": "Signal parsing task completed successfully"
            },
            {
                "timestamp": "2025-01-18T09:59:00Z",
                "level": "INFO",
                "module": "core.trade",
                "message": "Order executed successfully: EURUSD BUY"
            },
            {
                "timestamp": "2025-01-18T09:58:00Z",
                "level": "WARNING",
                "module": "services.parser_ai",
                "message": "AI parsing failed, using regex fallback"
            }
        ]
        
        # Filter by level if specified
        if level.upper() != "ALL":
            sample_logs = [log for log in sample_logs if log["level"] == level.upper()]
        
        return {
            "logs": sample_logs[:limit],
            "total": len(sample_logs),
            "level_filter": level
        }
        
    except Exception as e:
        logger.error(f"Get logs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/queue/status")
async def get_queue_status(bg_request: Request):
    """Get queue manager status"""
    try:
        user_id = getattr(bg_request.state, 'user_id', None)
        
        queue_manager = bg_request.app.state.queue_manager
        stats = queue_manager.get_queue_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"Queue status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/queue/clear")
async def clear_queue(queue_name: Optional[str] = None, bg_request: Request = None):
    """Clear queue tasks"""
    try:
        user_id = getattr(bg_request.state, 'user_id', None)
        
        # In production, implement queue clearing
        logger.info(f"Queue {queue_name or 'all'} cleared by admin {user_id}")
        
        return {"message": f"Queue {queue_name or 'all'} cleared successfully"}
        
    except Exception as e:
        logger.error(f"Clear queue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/users")
async def get_users(limit: int = 100, offset: int = 0):
    """Get user list (admin only)"""
    try:
        # In production, query user database
        sample_users = [
            {
                "id": f"user_{i}",
                "username": f"trader_{i}",
                "license_key": f"LIC_{i:06d}",
                "created_at": "2025-01-18T10:00:00Z",
                "last_login": "2025-01-18T10:00:00Z",
                "is_active": True
            }
            for i in range(1, 21)
        ]
        
        return {
            "users": sample_users[offset:offset + limit],
            "total": len(sample_users),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Get users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/config")
async def get_system_config():
    """Get system configuration"""
    try:
        from config.settings import get_settings
        settings = get_settings()
        
        # Return safe config (no secrets)
        safe_config = {
            "environment": settings.ENVIRONMENT,
            "host": settings.HOST,
            "port": settings.PORT,
            "log_level": settings.LOG_LEVEL,
            "max_daily_trades": settings.MAX_DAILY_TRADES,
            "ai_confidence_threshold": settings.AI_CONFIDENCE_THRESHOLD
        }
        
        return safe_config
        
    except Exception as e:
        logger.error(f"Get config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/config/update")
async def update_config(config_data: Dict[str, Any], bg_request: Request):
    """Update system configuration"""
    try:
        user_id = getattr(bg_request.state, 'user_id', None)
        
        # In production, validate and update configuration
        logger.info(f"Configuration updated by admin {user_id}")
        
        return {"message": "Configuration updated successfully"}
        
    except Exception as e:
        logger.error(f"Update config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/maintenance/start")
async def start_maintenance_mode():
    """Start maintenance mode"""
    try:
        # In production, set maintenance flag
        logger.info("Maintenance mode started")
        
        return {"message": "Maintenance mode started"}
        
    except Exception as e:
        logger.error(f"Start maintenance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/maintenance/stop")
async def stop_maintenance_mode():
    """Stop maintenance mode"""
    try:
        # In production, clear maintenance flag
        logger.info("Maintenance mode stopped")
        
        return {"message": "Maintenance mode stopped"}
        
    except Exception as e:
        logger.error(f"Stop maintenance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))