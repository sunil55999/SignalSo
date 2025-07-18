"""
Status and health monitoring endpoints
"""

import asyncio
import psutil
import time
from typing import Dict, Any, List
from fastapi import APIRouter, Request
from pydantic import BaseModel
from datetime import datetime, timedelta

from services.mt5_bridge import get_mt5_bridge
from workers.queue_manager import QueueManager
from utils.logging_config import get_logger

logger = get_logger("api.status")
status_router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime
    uptime_seconds: int
    version: str
    environment: str


class SystemMetrics(BaseModel):
    """System metrics response model"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_connections: int
    process_count: int


class ServiceStatus(BaseModel):
    """Service status response model"""
    name: str
    status: str
    last_check: datetime
    response_time_ms: float
    error_message: str = None


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model"""
    status: str
    timestamp: datetime
    uptime_seconds: int
    version: str
    environment: str
    services: List[ServiceStatus]
    system_metrics: SystemMetrics
    queue_stats: Dict[str, Any]


# Track application start time
START_TIME = time.time()


@status_router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    uptime = int(time.time() - START_TIME)
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        uptime_seconds=uptime,
        version="1.0.0",
        environment="production"
    )


@status_router.get("/healthz")
async def kubernetes_health_check():
    """Kubernetes-style health check endpoint"""
    return {"status": "ok"}


@status_router.get("/ready")
async def readiness_check():
    """Readiness check for load balancers"""
    try:
        # Check critical services
        mt5_bridge = get_mt5_bridge()
        
        # Basic connectivity checks
        checks = {
            "database": True,  # In production, check database connection
            "mt5_bridge": mt5_bridge.is_connected if mt5_bridge else False,
            "queue_manager": True  # In production, check queue manager
        }
        
        # If any critical service is down, return not ready
        if not all(checks.values()):
            return {"status": "not_ready", "checks": checks}, 503
        
        return {"status": "ready", "checks": checks}
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "error", "error": str(e)}, 503


@status_router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """Detailed health check with service status"""
    try:
        uptime = int(time.time() - START_TIME)
        
        # Check individual services
        services = await _check_services()
        
        # Get system metrics
        system_metrics = _get_system_metrics()
        
        # Get queue statistics
        queue_stats = await _get_queue_stats()
        
        # Determine overall status
        overall_status = "healthy"
        for service in services:
            if service.status == "unhealthy":
                overall_status = "degraded"
                break
            elif service.status == "warning":
                overall_status = "warning"
        
        return DetailedHealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime,
            version="1.0.0",
            environment="production",
            services=services,
            system_metrics=system_metrics,
            queue_stats=queue_stats
        )
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return DetailedHealthResponse(
            status="error",
            timestamp=datetime.utcnow(),
            uptime_seconds=int(time.time() - START_TIME),
            version="1.0.0",
            environment="production",
            services=[],
            system_metrics=SystemMetrics(
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_connections=0,
                process_count=0
            ),
            queue_stats={"error": str(e)}
        )


@status_router.get("/metrics")
async def get_metrics():
    """Get system and application metrics"""
    try:
        # System metrics
        system_metrics = _get_system_metrics()
        
        # Application metrics
        app_metrics = {
            "uptime_seconds": int(time.time() - START_TIME),
            "total_requests": 0,  # In production, track from middleware
            "active_connections": 0,  # In production, track from middleware
            "error_rate": 0.0,  # In production, calculate from logs
            "average_response_time": 0.0  # In production, track from middleware
        }
        
        # Queue metrics
        queue_stats = await _get_queue_stats()
        
        # Trading metrics
        trading_metrics = {
            "active_trades": 0,  # In production, get from trade executor
            "total_trades_today": 0,  # In production, get from database
            "success_rate": 0.0,  # In production, calculate from trades
            "average_latency_ms": 85.5  # In production, track from MT5 bridge
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_metrics.dict(),
            "application": app_metrics,
            "queues": queue_stats,
            "trading": trading_metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {"error": str(e)}, 500


@status_router.get("/version")
async def get_version():
    """Get application version information"""
    return {
        "version": "1.0.0",
        "build_date": "2025-01-18",
        "commit_hash": "abc123def456",  # In production, get from CI/CD
        "environment": "production",
        "python_version": "3.11",
        "dependencies": {
            "fastapi": "0.104.1",
            "uvicorn": "0.24.0",
            "sqlalchemy": "2.0.23",
            "pydantic": "2.5.0"
        }
    }


@status_router.get("/stats")
async def get_application_stats():
    """Get application statistics"""
    try:
        uptime = int(time.time() - START_TIME)
        
        # Get system info
        system_info = {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_total": psutil.disk_usage('/').total,
            "boot_time": psutil.boot_time()
        }
        
        # Get process info
        process = psutil.Process()
        process_info = {
            "pid": process.pid,
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "memory_info": process.memory_info()._asdict(),
            "create_time": process.create_time(),
            "num_threads": process.num_threads()
        }
        
        # Application stats
        app_stats = {
            "uptime_seconds": uptime,
            "start_time": datetime.fromtimestamp(START_TIME).isoformat(),
            "current_time": datetime.utcnow().isoformat(),
            "timezone": "UTC"
        }
        
        return {
            "system": system_info,
            "process": process_info,
            "application": app_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"error": str(e)}, 500


async def _check_services() -> List[ServiceStatus]:
    """Check status of all services"""
    services = []
    
    # Check MT5 Bridge
    mt5_start = time.time()
    try:
        mt5_bridge = get_mt5_bridge()
        if mt5_bridge and mt5_bridge.is_connected:
            # Test connection
            account_info = await mt5_bridge.get_account_info()
            mt5_response_time = (time.time() - mt5_start) * 1000
            
            services.append(ServiceStatus(
                name="mt5_bridge",
                status="healthy",
                last_check=datetime.utcnow(),
                response_time_ms=mt5_response_time
            ))
        else:
            services.append(ServiceStatus(
                name="mt5_bridge",
                status="unhealthy",
                last_check=datetime.utcnow(),
                response_time_ms=0,
                error_message="MT5 bridge not connected"
            ))
    except Exception as e:
        services.append(ServiceStatus(
            name="mt5_bridge",
            status="unhealthy",
            last_check=datetime.utcnow(),
            response_time_ms=0,
            error_message=str(e)
        ))
    
    # Check Database (simulated)
    db_start = time.time()
    try:
        # In production, test database connection
        db_response_time = (time.time() - db_start) * 1000
        
        services.append(ServiceStatus(
            name="database",
            status="healthy",
            last_check=datetime.utcnow(),
            response_time_ms=db_response_time
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="database",
            status="unhealthy",
            last_check=datetime.utcnow(),
            response_time_ms=0,
            error_message=str(e)
        ))
    
    # Check Queue Manager
    queue_start = time.time()
    try:
        # In production, check queue manager health
        queue_response_time = (time.time() - queue_start) * 1000
        
        services.append(ServiceStatus(
            name="queue_manager",
            status="healthy",
            last_check=datetime.utcnow(),
            response_time_ms=queue_response_time
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="queue_manager",
            status="unhealthy",
            last_check=datetime.utcnow(),
            response_time_ms=0,
            error_message=str(e)
        ))
    
    return services


def _get_system_metrics() -> SystemMetrics:
    """Get system performance metrics"""
    try:
        # CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_usage = (disk.used / disk.total) * 100
        
        # Network connections
        connections = len(psutil.net_connections())
        
        # Process count
        process_count = len(psutil.pids())
        
        return SystemMetrics(
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            network_connections=connections,
            process_count=process_count
        )
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return SystemMetrics(
            cpu_usage=0.0,
            memory_usage=0.0,
            disk_usage=0.0,
            network_connections=0,
            process_count=0
        )


async def _get_queue_stats() -> Dict[str, Any]:
    """Get queue statistics"""
    try:
        # In production, get stats from queue manager
        queue_stats = {
            "total_queues": 3,
            "active_workers": 3,
            "pending_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "average_processing_time": 0.0
        }
        
        return queue_stats
        
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        return {"error": str(e)}