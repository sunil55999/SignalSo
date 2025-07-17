#!/usr/bin/env python3
"""
Cloud Config Sync Module
Synchronizes local configuration with cloud storage
"""

import json
import asyncio
import aiohttp
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from pathlib import Path


class CloudConfigSync:
    """Sync local user_config.json with cloud copy via REST API"""
    
    def __init__(self, config_path: str = "config/user_config.json", api_base: str = "https://api.signalojs.com"):
        self.config_path = Path(config_path)
        self.api_base = api_base.rstrip('/')
        self.sync_config_path = Path("config/sync_settings.json")
        self.sync_settings = self._load_sync_settings()
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for cloud sync"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / "cloud_sync.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _load_sync_settings(self) -> Dict[str, Any]:
        """Load sync configuration settings"""
        default_settings = {
            "auto_sync_enabled": True,
            "sync_interval_minutes": 30,
            "last_sync_timestamp": None,
            "last_sync_hash": None,
            "api_key": None,
            "user_id": None,
            "sync_conflicts_resolution": "cloud_wins",  # cloud_wins, local_wins, manual
            "backup_before_sync": True,
            "retry_attempts": 3,
            "timeout_seconds": 30
        }
        
        try:
            if self.sync_config_path.exists():
                with open(self.sync_config_path, 'r') as f:
                    loaded_settings = json.load(f)
                    return {**default_settings, **loaded_settings}
        except Exception as e:
            self.logger.warning(f"Failed to load sync settings: {e}")
            
        return default_settings
        
    def _save_sync_settings(self):
        """Save sync settings to file"""
        try:
            self.sync_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.sync_config_path, 'w') as f:
                json.dump(self.sync_settings, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save sync settings: {e}")
            
    def _calculate_config_hash(self, config_data: Dict[str, Any]) -> str:
        """Calculate hash of configuration data for change detection"""
        config_str = json.dumps(config_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(config_str.encode()).hexdigest()
        
    def _load_local_config(self) -> Tuple[Dict[str, Any], str]:
        """Load local configuration and calculate hash"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    config_hash = self._calculate_config_hash(config_data)
                    return config_data, config_hash
            else:
                # Create default config if it doesn't exist
                default_config = {
                    "user_preferences": {
                        "language": "en",
                        "theme": "dark",
                        "notifications": True
                    },
                    "trading_settings": {
                        "default_lot_size": 0.01,
                        "max_risk_percent": 2.0,
                        "auto_sl_enabled": True
                    },
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0.0"
                }
                self._save_local_config(default_config)
                config_hash = self._calculate_config_hash(default_config)
                return default_config, config_hash
                
        except Exception as e:
            self.logger.error(f"Failed to load local config: {e}")
            return {}, ""
            
    def _save_local_config(self, config_data: Dict[str, Any]):
        """Save configuration to local file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Backup existing config if enabled
            if self.sync_settings.get("backup_before_sync", True) and self.config_path.exists():
                backup_path = self.config_path.with_suffix('.backup.json')
                with open(self.config_path, 'r') as src, open(backup_path, 'w') as dst:
                    dst.write(src.read())
                    
            # Save new config
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
                
            self.logger.info("Local config saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save local config: {e}")
            raise
            
    async def _make_api_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Tuple[bool, Dict[str, Any]]:
        """Make authenticated API request"""
        if not self.sync_settings.get("api_key"):
            return False, {"error": "No API key configured"}
            
        url = f"{self.api_base}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.sync_settings['api_key']}",
            "Content-Type": "application/json"
        }
        
        timeout = aiohttp.ClientTimeout(total=self.sync_settings.get("timeout_seconds", 30))
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if method.upper() == "GET":
                    async with session.get(url, headers=headers) as response:
                        result = await response.json()
                        return response.status == 200, result
                        
                elif method.upper() == "POST":
                    async with session.post(url, headers=headers, json=data) as response:
                        result = await response.json()
                        return response.status == 200, result
                        
                elif method.upper() == "PUT":
                    async with session.put(url, headers=headers, json=data) as response:
                        result = await response.json()
                        return response.status == 200, result
                        
        except Exception as e:
            self.logger.error(f"API request failed: {e}")
            return False, {"error": str(e)}
            
    async def fetch_cloud_config(self) -> Tuple[bool, Dict[str, Any]]:
        """Fetch configuration from cloud"""
        user_id = self.sync_settings.get("user_id")
        if not user_id:
            return False, {"error": "No user ID configured"}
            
        endpoint = f"/config/{user_id}"
        success, result = await self._make_api_request("GET", endpoint)
        
        if success:
            self.logger.info("Successfully fetched cloud config")
            return True, result.get("config", {})
        else:
            self.logger.error(f"Failed to fetch cloud config: {result}")
            return False, result
            
    async def upload_local_config(self, force: bool = False) -> Tuple[bool, str]:
        """Upload local configuration to cloud"""
        local_config, local_hash = self._load_local_config()
        
        if not local_config:
            return False, "No local config to upload"
            
        # Check if upload is needed
        if not force and local_hash == self.sync_settings.get("last_sync_hash"):
            return True, "Config already up to date"
            
        user_id = self.sync_settings.get("user_id")
        if not user_id:
            return False, "No user ID configured"
            
        upload_data = {
            "config": local_config,
            "hash": local_hash,
            "timestamp": datetime.now().isoformat(),
            "version": local_config.get("version", "1.0.0")
        }
        
        endpoint = f"/config/{user_id}"
        success, result = await self._make_api_request("PUT", endpoint, upload_data)
        
        if success:
            # Update sync tracking
            self.sync_settings["last_sync_timestamp"] = datetime.now().isoformat()
            self.sync_settings["last_sync_hash"] = local_hash
            self._save_sync_settings()
            
            self.logger.info("Successfully uploaded config to cloud")
            return True, "Config uploaded successfully"
        else:
            self.logger.error(f"Failed to upload config: {result}")
            return False, result.get("error", "Upload failed")
            
    async def download_cloud_config(self, force: bool = False) -> Tuple[bool, str]:
        """Download configuration from cloud and apply locally"""
        success, cloud_config = await self.fetch_cloud_config()
        
        if not success:
            return False, cloud_config.get("error", "Failed to fetch cloud config")
            
        if not cloud_config:
            return False, "No cloud config available"
            
        local_config, local_hash = self._load_local_config()
        cloud_hash = self._calculate_config_hash(cloud_config)
        
        # Check if download is needed
        if not force and cloud_hash == local_hash:
            return True, "Config already synchronized"
            
        # Handle conflicts based on resolution strategy
        conflict_resolution = self.sync_settings.get("sync_conflicts_resolution", "cloud_wins")
        
        if conflict_resolution == "cloud_wins" or force:
            # Apply cloud config
            self._save_local_config(cloud_config)
            
            # Update sync tracking
            self.sync_settings["last_sync_timestamp"] = datetime.now().isoformat()
            self.sync_settings["last_sync_hash"] = cloud_hash
            self._save_sync_settings()
            
            self.logger.info("Successfully downloaded and applied cloud config")
            return True, "Cloud config applied successfully"
            
        elif conflict_resolution == "local_wins":
            # Keep local config, but update sync hash to prevent future conflicts
            self.sync_settings["last_sync_hash"] = local_hash
            self._save_sync_settings()
            return True, "Local config preserved"
            
        else:  # manual resolution
            return False, "Manual conflict resolution required"
            
    async def auto_sync(self) -> Tuple[bool, str]:
        """Perform automatic bidirectional sync"""
        if not self.sync_settings.get("auto_sync_enabled", True):
            return True, "Auto-sync disabled"
            
        # Check sync interval
        last_sync = self.sync_settings.get("last_sync_timestamp")
        if last_sync:
            last_sync_dt = datetime.fromisoformat(last_sync)
            sync_interval = self.sync_settings.get("sync_interval_minutes", 30)
            if (datetime.now() - last_sync_dt).total_seconds() < sync_interval * 60:
                return True, "Sync interval not reached"
                
        # Fetch cloud config to compare
        cloud_success, cloud_config = await self.fetch_cloud_config()
        if not cloud_success:
            return False, f"Failed to fetch cloud config: {cloud_config}"
            
        local_config, local_hash = self._load_local_config()
        cloud_hash = self._calculate_config_hash(cloud_config) if cloud_config else ""
        
        # Determine sync direction
        if not cloud_config:
            # No cloud config, upload local
            return await self.upload_local_config()
        elif not local_config:
            # No local config, download cloud
            return await self.download_cloud_config()
        elif cloud_hash != local_hash:
            # Configs differ, use resolution strategy
            conflict_resolution = self.sync_settings.get("sync_conflicts_resolution", "cloud_wins")
            if conflict_resolution == "cloud_wins":
                return await self.download_cloud_config()
            else:
                return await self.upload_local_config()
        else:
            # Configs are identical
            return True, "Configs already synchronized"
            
    def force_push_config(self) -> Tuple[bool, str]:
        """Force push local config to cloud (synchronous wrapper)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.upload_local_config(force=True))
        finally:
            loop.close()
            
    def force_pull_config(self) -> Tuple[bool, str]:
        """Force pull cloud config to local (synchronous wrapper)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.download_cloud_config(force=True))
        finally:
            loop.close()
            
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status"""
        local_config, local_hash = self._load_local_config()
        
        return {
            "auto_sync_enabled": self.sync_settings.get("auto_sync_enabled", True),
            "last_sync": self.sync_settings.get("last_sync_timestamp"),
            "local_config_hash": local_hash,
            "last_sync_hash": self.sync_settings.get("last_sync_hash"),
            "config_modified": local_hash != self.sync_settings.get("last_sync_hash"),
            "api_configured": bool(self.sync_settings.get("api_key")),
            "user_configured": bool(self.sync_settings.get("user_id")),
            "sync_interval_minutes": self.sync_settings.get("sync_interval_minutes", 30)
        }
        
    def configure_sync(self, api_key: str, user_id: str, auto_sync: bool = True):
        """Configure cloud sync settings"""
        self.sync_settings.update({
            "api_key": api_key,
            "user_id": user_id,
            "auto_sync_enabled": auto_sync
        })
        self._save_sync_settings()
        self.logger.info("Sync configuration updated")


async def main():
    """Test cloud config sync"""
    print("☁️ Testing Cloud Config Sync")
    print("=" * 50)
    
    # Initialize sync manager
    sync_manager = CloudConfigSync()
    
    # Show current status
    status = sync_manager.get_sync_status()
    print("📊 Current Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
        
    # Test configuration
    if not status["api_configured"]:
        print("\n⚙️ Configuring test credentials...")
        sync_manager.configure_sync("test_api_key", "test_user_123")
        
    # Test local config operations
    print("\n📁 Testing local config operations...")
    local_config, local_hash = sync_manager._load_local_config()
    print(f"   Local config loaded: {bool(local_config)}")
    print(f"   Config hash: {local_hash[:16]}...")
    
    # Test sync operations (will fail without real API, but tests the flow)
    print("\n🔄 Testing sync operations...")
    try:
        success, message = await sync_manager.auto_sync()
        print(f"   Auto sync: {'✅' if success else '❌'} {message}")
    except Exception as e:
        print(f"   Auto sync: ❌ {e}")
        
    print("\n✅ Cloud sync system initialized")


if __name__ == "__main__":
    asyncio.run(main())