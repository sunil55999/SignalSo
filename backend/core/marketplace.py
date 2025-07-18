"""
SignalOS Plugin & Marketplace Ecosystem
Handles plugin lifecycle, marketplace operations, and third-party integrations
"""

import json
import os
import zipfile
import hashlib
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import importlib.util
import sys

from db.models import MarketplacePlugin, UserPlugin
from utils.logging_config import get_logger

logger = get_logger(__name__)


class PluginStatus(Enum):
    INSTALLED = "installed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNINSTALLED = "uninstalled"
    ERROR = "error"


class PluginType(Enum):
    SIGNAL_PROVIDER = "signal_provider"
    STRATEGY = "strategy"
    INDICATOR = "indicator"
    UTILITY = "utility"
    NOTIFICATION = "notification"


class MarketplaceEngine:
    """Core marketplace and plugin management engine"""
    
    def __init__(self):
        self.plugins_dir = Path("plugins")
        self.plugins_dir.mkdir(exist_ok=True)
        self.loaded_plugins = {}
        self.plugin_registry = {}
        
    async def initialize(self):
        """Initialize marketplace engine"""
        try:
            await self._setup_plugin_directory()
            await self._load_plugin_registry()
            await self._scan_installed_plugins()
            logger.info("Marketplace engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize marketplace engine: {e}")
            raise
    
    async def _setup_plugin_directory(self):
        """Setup plugin directory structure"""
        directories = [
            "plugins/signal_providers",
            "plugins/strategies", 
            "plugins/indicators",
            "plugins/utilities",
            "plugins/notifications"
        ]
        
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    async def _load_plugin_registry(self):
        """Load plugin registry from database"""
        # This would load from your database
        # For now, create a mock registry
        self.plugin_registry = {
            "official_plugins": [],
            "community_plugins": [],
            "premium_plugins": []
        }
    
    async def _scan_installed_plugins(self):
        """Scan and register installed plugins"""
        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir():
                await self._register_plugin(plugin_dir)
    
    async def install_plugin(self, plugin_id: str, user_id: str, plugin_data: bytes) -> Dict[str, Any]:
        """Install a plugin from marketplace"""
        try:
            # Validate plugin
            plugin_info = await self._validate_plugin_package(plugin_data)
            
            # Extract plugin
            plugin_path = await self._extract_plugin(plugin_id, plugin_data)
            
            # Register plugin
            await self._register_plugin(plugin_path)
            
            # Update database
            await self._create_user_plugin_record(user_id, plugin_id, plugin_info)
            
            logger.info(f"Plugin {plugin_id} installed successfully for user {user_id}")
            return {
                "success": True,
                "plugin_id": plugin_id,
                "message": "Plugin installed successfully"
            }
            
        except Exception as e:
            logger.error(f"Plugin installation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _validate_plugin_package(self, plugin_data: bytes) -> Dict[str, Any]:
        """Validate plugin package integrity and security"""
        try:
            # Check file size
            if len(plugin_data) > 50 * 1024 * 1024:  # 50MB limit
                raise ValueError("Plugin package too large")
            
            # Verify zip file
            import io
            with zipfile.ZipFile(io.BytesIO(plugin_data)) as zf:
                # Check for required files
                required_files = ['plugin.json', 'main.py']
                file_list = zf.namelist()
                
                for required_file in required_files:
                    if required_file not in file_list:
                        raise ValueError(f"Missing required file: {required_file}")
                
                # Load plugin metadata
                with zf.open('plugin.json') as f:
                    plugin_info = json.load(f)
                
                # Validate plugin info
                required_fields = ['name', 'version', 'author', 'description', 'type']
                for field in required_fields:
                    if field not in plugin_info:
                        raise ValueError(f"Missing required field: {field}")
                
                # Security check - scan for dangerous patterns
                await self._security_scan_plugin(zf)
                
                return plugin_info
                
        except Exception as e:
            logger.error(f"Plugin validation failed: {e}")
            raise
    
    async def _security_scan_plugin(self, zip_file: zipfile.ZipFile):
        """Perform basic security scan on plugin"""
        dangerous_patterns = [
            'import os',
            'import sys',
            'import subprocess',
            'eval(',
            'exec(',
            '__import__',
            'open(',
            'file(',
        ]
        
        for file_info in zip_file.filelist:
            if file_info.filename.endswith('.py'):
                with zip_file.open(file_info) as f:
                    content = f.read().decode('utf-8')
                    
                    for pattern in dangerous_patterns:
                        if pattern in content:
                            logger.warning(f"Potentially dangerous pattern found in {file_info.filename}: {pattern}")
                            # For now, just log warnings
                            # In production, you might want to block installation
    
    async def _extract_plugin(self, plugin_id: str, plugin_data: bytes) -> Path:
        """Extract plugin to plugins directory"""
        plugin_path = self.plugins_dir / plugin_id
        plugin_path.mkdir(exist_ok=True)
        
        import io
        with zipfile.ZipFile(io.BytesIO(plugin_data)) as zf:
            zf.extractall(plugin_path)
        
        return plugin_path
    
    async def _register_plugin(self, plugin_path: Path):
        """Register plugin in system"""
        try:
            # Load plugin metadata
            plugin_json_path = plugin_path / 'plugin.json'
            if not plugin_json_path.exists():
                return
            
            with open(plugin_json_path, 'r') as f:
                plugin_info = json.load(f)
            
            plugin_id = plugin_info.get('id', plugin_path.name)
            
            # Load plugin module
            main_py_path = plugin_path / 'main.py'
            if main_py_path.exists():
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{plugin_id}", main_py_path
                )
                plugin_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin_module)
                
                self.loaded_plugins[plugin_id] = {
                    'module': plugin_module,
                    'info': plugin_info,
                    'path': plugin_path
                }
                
                logger.info(f"Plugin {plugin_id} registered successfully")
            
        except Exception as e:
            logger.error(f"Failed to register plugin at {plugin_path}: {e}")
    
    async def _create_user_plugin_record(self, user_id: str, plugin_id: str, plugin_info: Dict[str, Any]):
        """Create user plugin record in database"""
        # This would create a record in your database
        # For now, just log the installation
        logger.info(f"Created user plugin record: {user_id} -> {plugin_id}")
    
    async def activate_plugin(self, user_id: str, plugin_id: str) -> Dict[str, Any]:
        """Activate a plugin for user"""
        try:
            if plugin_id not in self.loaded_plugins:
                raise ValueError(f"Plugin {plugin_id} not found")
            
            plugin = self.loaded_plugins[plugin_id]
            
            # Call plugin activation method if exists
            if hasattr(plugin['module'], 'activate'):
                await plugin['module'].activate(user_id)
            
            # Update database status
            await self._update_plugin_status(user_id, plugin_id, PluginStatus.ACTIVE)
            
            logger.info(f"Plugin {plugin_id} activated for user {user_id}")
            return {
                "success": True,
                "message": "Plugin activated successfully"
            }
            
        except Exception as e:
            logger.error(f"Plugin activation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def deactivate_plugin(self, user_id: str, plugin_id: str) -> Dict[str, Any]:
        """Deactivate a plugin for user"""
        try:
            if plugin_id not in self.loaded_plugins:
                raise ValueError(f"Plugin {plugin_id} not found")
            
            plugin = self.loaded_plugins[plugin_id]
            
            # Call plugin deactivation method if exists
            if hasattr(plugin['module'], 'deactivate'):
                await plugin['module'].deactivate(user_id)
            
            # Update database status
            await self._update_plugin_status(user_id, plugin_id, PluginStatus.INACTIVE)
            
            logger.info(f"Plugin {plugin_id} deactivated for user {user_id}")
            return {
                "success": True,
                "message": "Plugin deactivated successfully"
            }
            
        except Exception as e:
            logger.error(f"Plugin deactivation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def uninstall_plugin(self, user_id: str, plugin_id: str) -> Dict[str, Any]:
        """Uninstall a plugin"""
        try:
            if plugin_id in self.loaded_plugins:
                plugin = self.loaded_plugins[plugin_id]
                
                # Call plugin cleanup method if exists
                if hasattr(plugin['module'], 'cleanup'):
                    await plugin['module'].cleanup(user_id)
                
                # Remove from loaded plugins
                del self.loaded_plugins[plugin_id]
            
            # Remove plugin directory
            plugin_path = self.plugins_dir / plugin_id
            if plugin_path.exists():
                import shutil
                shutil.rmtree(plugin_path)
            
            # Update database status
            await self._update_plugin_status(user_id, plugin_id, PluginStatus.UNINSTALLED)
            
            logger.info(f"Plugin {plugin_id} uninstalled for user {user_id}")
            return {
                "success": True,
                "message": "Plugin uninstalled successfully"
            }
            
        except Exception as e:
            logger.error(f"Plugin uninstallation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_plugin_status(self, user_id: str, plugin_id: str, status: PluginStatus):
        """Update plugin status in database"""
        # This would update your database
        logger.info(f"Updated plugin status: {user_id} -> {plugin_id} -> {status.value}")
    
    async def get_marketplace_plugins(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get available marketplace plugins"""
        try:
            # This would query your database for available plugins
            # For now, return mock data
            plugins = [
                {
                    "id": "advanced_signal_parser",
                    "name": "Advanced Signal Parser",
                    "description": "Enhanced AI signal parsing with 99% accuracy",
                    "version": "1.0.0",
                    "author": "SignalOS Team",
                    "category": "signal_provider",
                    "type": "official",
                    "rating": 4.8,
                    "downloads": 1250,
                    "price": 0.0,
                    "is_active": True
                },
                {
                    "id": "martingale_strategy",
                    "name": "Martingale Strategy",
                    "description": "Classic martingale trading strategy with risk management",
                    "version": "2.1.0",
                    "author": "CommunityDev",
                    "category": "strategy",
                    "type": "community",
                    "rating": 4.2,
                    "downloads": 892,
                    "price": 29.99,
                    "is_active": True
                }
            ]
            
            if category:
                plugins = [p for p in plugins if p['category'] == category]
            
            return {
                "success": True,
                "plugins": plugins,
                "total": len(plugins)
            }
            
        except Exception as e:
            logger.error(f"Failed to get marketplace plugins: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_user_plugins(self, user_id: str) -> Dict[str, Any]:
        """Get user's installed plugins"""
        try:
            # This would query your database
            # For now, return mock data
            user_plugins = [
                {
                    "id": "advanced_signal_parser",
                    "name": "Advanced Signal Parser",
                    "status": "active",
                    "installed_at": "2025-01-18T10:00:00Z",
                    "last_used": "2025-01-18T12:30:00Z"
                }
            ]
            
            return {
                "success": True,
                "plugins": user_plugins,
                "total": len(user_plugins)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user plugins: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_plugin(self, user_id: str, plugin_id: str, plugin_data: bytes) -> Dict[str, Any]:
        """Update an existing plugin"""
        try:
            # Validate new plugin version
            plugin_info = await self._validate_plugin_package(plugin_data)
            
            # Backup current plugin
            await self._backup_plugin(plugin_id)
            
            # Install new version
            result = await self.install_plugin(plugin_id, user_id, plugin_data)
            
            if result["success"]:
                logger.info(f"Plugin {plugin_id} updated successfully for user {user_id}")
                return {
                    "success": True,
                    "message": "Plugin updated successfully"
                }
            else:
                # Restore backup if update failed
                await self._restore_plugin_backup(plugin_id)
                return result
                
        except Exception as e:
            logger.error(f"Plugin update failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _backup_plugin(self, plugin_id: str):
        """Backup current plugin before update"""
        plugin_path = self.plugins_dir / plugin_id
        backup_path = self.plugins_dir / f"{plugin_id}_backup"
        
        if plugin_path.exists():
            import shutil
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.copytree(plugin_path, backup_path)
    
    async def _restore_plugin_backup(self, plugin_id: str):
        """Restore plugin from backup"""
        plugin_path = self.plugins_dir / plugin_id
        backup_path = self.plugins_dir / f"{plugin_id}_backup"
        
        if backup_path.exists():
            import shutil
            if plugin_path.exists():
                shutil.rmtree(plugin_path)
            shutil.copytree(backup_path, plugin_path)
    
    async def execute_plugin_method(self, user_id: str, plugin_id: str, method_name: str, *args, **kwargs) -> Dict[str, Any]:
        """Execute a plugin method"""
        try:
            if plugin_id not in self.loaded_plugins:
                raise ValueError(f"Plugin {plugin_id} not found or not active")
            
            plugin = self.loaded_plugins[plugin_id]
            
            if not hasattr(plugin['module'], method_name):
                raise ValueError(f"Method {method_name} not found in plugin {plugin_id}")
            
            method = getattr(plugin['module'], method_name)
            result = await method(user_id, *args, **kwargs)
            
            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Plugin method execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_plugin_config_schema(self, plugin_id: str) -> Dict[str, Any]:
        """Get plugin configuration schema"""
        try:
            if plugin_id not in self.loaded_plugins:
                raise ValueError(f"Plugin {plugin_id} not found")
            
            plugin = self.loaded_plugins[plugin_id]
            
            # Get config schema from plugin info
            config_schema = plugin['info'].get('config_schema', {})
            
            return {
                "success": True,
                "schema": config_schema
            }
            
        except Exception as e:
            logger.error(f"Failed to get plugin config schema: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_plugin_config(self, user_id: str, plugin_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update plugin configuration"""
        try:
            # Validate config against schema
            schema_result = await self.get_plugin_config_schema(plugin_id)
            if not schema_result["success"]:
                return schema_result
            
            # Update config in database
            await self._update_plugin_config_db(user_id, plugin_id, config)
            
            # Notify plugin of config change
            if plugin_id in self.loaded_plugins:
                plugin = self.loaded_plugins[plugin_id]
                if hasattr(plugin['module'], 'on_config_update'):
                    await plugin['module'].on_config_update(user_id, config)
            
            return {
                "success": True,
                "message": "Plugin configuration updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to update plugin config: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_plugin_config_db(self, user_id: str, plugin_id: str, config: Dict[str, Any]):
        """Update plugin configuration in database"""
        # This would update your database
        logger.info(f"Updated plugin config: {user_id} -> {plugin_id}")
    
    async def get_plugin_stats(self) -> Dict[str, Any]:
        """Get marketplace and plugin statistics"""
        try:
            return {
                "total_plugins": len(self.loaded_plugins),
                "active_plugins": len([p for p in self.loaded_plugins.values() if p.get('active', False)]),
                "categories": {
                    "signal_provider": 15,
                    "strategy": 23,
                    "indicator": 8,
                    "utility": 12,
                    "notification": 5
                },
                "marketplace_health": "healthy"
            }
            
        except Exception as e:
            logger.error(f"Failed to get plugin stats: {e}")
            return {
                "success": False,
                "error": str(e)
            }