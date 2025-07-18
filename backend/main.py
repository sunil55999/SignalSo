#!/usr/bin/env python3
"""
SignalOS Backend - Main Application Entry Point

A production-grade trading signal processing and execution backend service.
Designed for professional traders with intelligent signal processing, 
real-time market monitoring, and advanced trading automation.
"""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add backend to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.router import api_router
from config.settings import get_settings
from middleware.auth import AuthMiddleware
from middleware.error_handler import ErrorHandlerMiddleware
from utils.logging_config import setup_logging
from workers.queue_manager import QueueManager

# Initialize settings
settings = get_settings()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 SignalOS Backend starting up...")
    
    # Start background workers
    from workers.queue_manager import QueueManager
    from workers.parse_worker import get_parse_worker
    from workers.trade_retry import get_retry_worker
    from workers.cleaner_worker import get_cleaner_worker
    
    # Start queue manager
    queue_manager = QueueManager()
    await queue_manager.start()
    app.state.queue_manager = queue_manager
    
    # Start Part 2 workers
    parse_worker = get_parse_worker()
    await parse_worker.start()
    app.state.parse_worker = parse_worker
    
    retry_worker = get_retry_worker()
    await retry_worker.start()
    app.state.retry_worker = retry_worker
    
    cleaner_worker = get_cleaner_worker()
    await cleaner_worker.start()
    app.state.cleaner_worker = cleaner_worker
    
    logger.info("✅ SignalOS Backend startup complete")
    
    yield
    
    # Cleanup
    logger.info("🔄 SignalOS Backend shutting down...")
    await cleaner_worker.stop()
    await retry_worker.stop()
    await parse_worker.stop()
    await queue_manager.stop()
    logger.info("✅ SignalOS Backend shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="SignalOS Backend API",
    description="Professional trading signal processing and execution backend",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
from middleware.rate_limit import RateLimitMiddleware, RateLimitRule
app.add_middleware(RateLimitMiddleware, default_rule=RateLimitRule(requests=1000, window=60))
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(AuthMiddleware)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SignalOS Backend",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs" if settings.ENVIRONMENT == "development" else "disabled"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": int(asyncio.get_event_loop().time()),
        "environment": settings.ENVIRONMENT
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting SignalOS Backend on {settings.HOST}:{settings.PORT}")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
        workers=1 if settings.ENVIRONMENT == "development" else settings.WORKERS
    )