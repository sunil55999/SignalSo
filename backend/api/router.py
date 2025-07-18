"""
Main API router for SignalOS Backend
"""

from fastapi import APIRouter
from api.auth import auth_router
from api.signals import signals_router
from api.trading import trading_router
from api.admin import admin_router
from api.license import router as license_router
from api.parser import router as parser_router
from api.analytics import analytics_router
from api.trades import trades_router
from api.status import status_router

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(license_router, tags=["License Management"])
api_router.include_router(parser_router, tags=["Parser Management"])
api_router.include_router(signals_router, prefix="/signals", tags=["Signal Processing"])
api_router.include_router(trading_router, prefix="/trading", tags=["Trading"])
api_router.include_router(trades_router, prefix="/trades", tags=["Trade Execution"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(status_router, prefix="/status", tags=["Status & Health"])
api_router.include_router(admin_router, prefix="/admin", tags=["Administration"])