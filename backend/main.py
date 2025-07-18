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
    
    # Initialize queue manager
    queue_manager = QueueManager()
    await queue_manager.start()
    app.state.queue_manager = queue_manager
    
    logger.info("✅ SignalOS Backend startup complete")
    
    yield
    
    # Cleanup
    logger.info("🔄 SignalOS Backend shutting down...")
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