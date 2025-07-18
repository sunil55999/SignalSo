"""
Marketplace API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.security import HTTPBearer
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging

from core.marketplace import MarketplaceEngine
from middleware.auth import verify_token
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/marketplace", tags=["marketplace"])
security = HTTPBearer()


class PluginConfigRequest(BaseModel):
    config: Dict[str, Any]


@router.get("/plugins")
async def get_marketplace_plugins(
    category: Optional[str] = None,
    current_user: dict = Depends(verify_token)
):
    """Get available marketplace plugins"""
    try:
        marketplace = MarketplaceEngine()
        await marketplace.initialize()
        
        result = await marketplace.get_marketplace_plugins(category)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get marketplace plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/{plugin_id}/install")
async def install_plugin(
    plugin_id: str,
    plugin_file: UploadFile = File(...),
    current_user: dict = Depends(verify_token)
):
    """Install a plugin from marketplace"""
    try:
        user_id = current_user["user_id"]
        
        # Read plugin file
        plugin_data = await plugin_file.read()
        
        # Initialize marketplace
        marketplace = MarketplaceEngine()
        await marketplace.initialize()
        
        # Install plugin
        result = await marketplace.install_plugin(plugin_id, user_id, plugin_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Plugin installation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/{plugin_id}/activate")
async def activate_plugin(
    plugin_id: str,
    current_user: dict = Depends(verify_token)
):
    """Activate a plugin"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize marketplace
        marketplace = MarketplaceEngine()
        await marketplace.initialize()
        
        # Activate plugin
        result = await marketplace.activate_plugin(user_id, plugin_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Plugin activation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/{plugin_id}/deactivate")
async def deactivate_plugin(
    plugin_id: str,
    current_user: dict = Depends(verify_token)
):
    """Deactivate a plugin"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize marketplace
        marketplace = MarketplaceEngine()
        await marketplace.initialize()
        
        # Deactivate plugin
        result = await marketplace.deactivate_plugin(user_id, plugin_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Plugin deactivation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/plugins/{plugin_id}")
async def uninstall_plugin(
    plugin_id: str,
    current_user: dict = Depends(verify_token)
):
    """Uninstall a plugin"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize marketplace
        marketplace = MarketplaceEngine()
        await marketplace.initialize()
        
        # Uninstall plugin
        result = await marketplace.uninstall_plugin(user_id, plugin_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Plugin uninstallation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plugins/{plugin_id}/update")
async def update_plugin(
    plugin_id: str,
    plugin_file: UploadFile = File(...),
    current_user: dict = Depends(verify_token)
):
    """Update a plugin"""
    try:
        user_id = current_user["user_id"]
        
        # Read plugin file
        plugin_data = await plugin_file.read()
        
        # Initialize marketplace
        marketplace = MarketplaceEngine()
        await marketplace.initialize()
        
        # Update plugin
        result = await marketplace.update_plugin(user_id, plugin_id, plugin_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Plugin update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plugins/{plugin_id}/config")
async def get_plugin_config_schema(
    plugin_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get plugin configuration schema"""
    try:
        # Initialize marketplace
        marketplace = MarketplaceEngine()
        await marketplace.initialize()
        
        # Get config schema
        result = await marketplace.get_plugin_config_schema(plugin_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get plugin config schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plugins/{plugin_id}/config")
async def update_plugin_config(
    plugin_id: str,
    request: PluginConfigRequest,
    current_user: dict = Depends(verify_token)
):
    """Update plugin configuration"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize marketplace
        marketplace = MarketplaceEngine()
        await marketplace.initialize()
        
        # Update config
        result = await marketplace.update_plugin_config(user_id, plugin_id, request.config)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to update plugin config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/{plugin_id}/execute/{method_name}")
async def execute_plugin_method(
    plugin_id: str,
    method_name: str,
    parameters: Dict[str, Any] = {},
    current_user: dict = Depends(verify_token)
):
    """Execute a plugin method"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize marketplace
        marketplace = MarketplaceEngine()
        await marketplace.initialize()
        
        # Execute method
        result = await marketplace.execute_plugin_method(
            user_id, plugin_id, method_name, **parameters
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Plugin method execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-plugins")
async def get_user_plugins(
    current_user: dict = Depends(verify_token)
):
    """Get user's installed plugins"""
    try:
        user_id = current_user["user_id"]
        
        # Initialize marketplace
        marketplace = MarketplaceEngine()
        await marketplace.initialize()
        
        # Get user plugins
        result = await marketplace.get_user_plugins(user_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get user plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_marketplace_stats(
    current_user: dict = Depends(verify_token)
):
    """Get marketplace statistics"""
    try:
        # Initialize marketplace
        marketplace = MarketplaceEngine()
        await marketplace.initialize()
        
        # Get stats
        stats = await marketplace.get_plugin_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get marketplace stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))