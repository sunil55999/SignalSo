#!/usr/bin/env python3
"""
Model Update Pusher for SignalOS
Automatically checks for and downloads AI model updates
"""

import os
import json
import asyncio
import aiohttp
import tarfile
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
from datetime import datetime
import tempfile


class ModelUpdater:
    """AI Model Update Pusher - Downloads and manages AI model updates"""
    
    def __init__(self, config_path: str = "config/model_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.setup_logging()
        
        # Model configuration
        self.backend_url = self.config.get("backend_url", "https://api.signalojs.com")
        self.models_dir = Path(self.config.get("models_dir", "models"))
        self.current_model_dir = self.models_dir / "current_model"
        self.local_version_file = self.models_dir / "version.json"
        
        # Update settings
        self.check_interval_hours = self.config.get("check_interval_hours", 6)
        self.auto_download = self.config.get("auto_download", True)
        self.backup_old_models = self.config.get("backup_old_models", True)
        self.max_retries = self.config.get("max_retries", 3)
        
        # Ensure directories exist
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.current_model_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"ModelUpdater initialized - Backend: {self.backend_url}")
        
    def setup_logging(self):
        """Setup logging for model updater"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / "model_updater.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self) -> Dict[str, Any]:
        """Load model updater configuration"""
        default_config = {
            "backend_url": "https://api.signalojs.com",
            "models_dir": "models",
            "check_interval_hours": 6,
            "auto_download": True,
            "backup_old_models": True,
            "max_retries": 3,
            "notification_enabled": True,
            "verify_checksums": True
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    return {**default_config, **loaded_config}
        except Exception as e:
            print(f"Warning: Failed to load model config: {e}")
            
        return default_config
        
    def _save_config(self):
        """Save model updater configuration"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save model config: {e}")
            
    def get_local_version(self) -> Dict[str, Any]:
        """Get currently installed model version"""
        try:
            if self.local_version_file.exists():
                with open(self.local_version_file, 'r') as f:
                    version_data = json.load(f)
                    self.logger.info(f"Local model version: {version_data.get('version', 'unknown')}")
                    return version_data
        except Exception as e:
            self.logger.warning(f"Failed to read local version: {e}")
            
        # Return default version if file doesn't exist
        default_version = {
            "version": "1.0.0",
            "model_name": "signalojs_ai_model",
            "last_updated": None,
            "checksum": "",
            "size": 0
        }
        
        # Create the version file
        self._save_local_version(default_version)
        return default_version
        
    def _save_local_version(self, version_data: Dict[str, Any]):
        """Save local model version information"""
        try:
            with open(self.local_version_file, 'w') as f:
                json.dump(version_data, f, indent=2)
            self.logger.info(f"Saved local version: {version_data.get('version')}")
        except Exception as e:
            self.logger.error(f"Failed to save local version: {e}")
            
    async def fetch_remote_version(self) -> Optional[Dict[str, Any]]:
        """Fetch version information from remote backend"""
        try:
            url = f"{self.backend_url}/api/models/version.json"
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        remote_version = await response.json()
                        self.logger.info(f"Remote model version: {remote_version.get('version', 'unknown')}")
                        return remote_version
                    else:
                        self.logger.error(f"Failed to fetch remote version: HTTP {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Error fetching remote version: {e}")
            return None
            
    def compare_versions(self, local_version: str, remote_version: str) -> bool:
        """
        Compare version strings to determine if update is needed
        Returns True if remote version is newer
        """
        try:
            # Simple version comparison (can be enhanced for semantic versioning)
            local_parts = [int(x) for x in local_version.split('.')]
            remote_parts = [int(x) for x in remote_version.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(local_parts), len(remote_parts))
            local_parts.extend([0] * (max_len - len(local_parts)))
            remote_parts.extend([0] * (max_len - len(remote_parts)))
            
            for local, remote in zip(local_parts, remote_parts):
                if remote > local:
                    return True
                elif remote < local:
                    return False
                    
            return False  # Versions are equal
            
        except Exception as e:
            self.logger.error(f"Version comparison failed: {e}")
            return False
            
    async def check_for_updates(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if model update is available
        Returns (update_available, remote_version_data)
        """
        self.logger.info("Checking for model updates...")
        
        # Get local and remote versions
        local_version_data = self.get_local_version()
        remote_version_data = await self.fetch_remote_version()
        
        if not remote_version_data:
            return False, None
            
        local_version = local_version_data.get('version', '1.0.0')
        remote_version = remote_version_data.get('version', '1.0.0')
        
        # Compare versions
        update_available = self.compare_versions(local_version, remote_version)
        
        if update_available:
            self.logger.info(f"Model update available: {local_version} -> {remote_version}")
            return True, remote_version_data
        else:
            self.logger.info("Model is up to date")
            return False, None
            
    async def download_model(self, model_url: str, expected_checksum: str = None) -> Optional[Path]:
        """
        Download AI model from specified URL
        Returns path to downloaded file or None if failed
        """
        try:
            self.logger.info(f"Downloading model from: {model_url}")
            
            # Create temporary download directory
            temp_dir = Path(tempfile.mkdtemp(prefix="signalojs_model_"))
            temp_file = temp_dir / "model.tar.gz"
            
            timeout = aiohttp.ClientTimeout(total=3600)  # 1 hour timeout for large files
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(model_url) as response:
                    if response.status == 200:
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        
                        with open(temp_file, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Log progress every 10MB
                                if downloaded % (10 * 1024 * 1024) == 0 or downloaded == total_size:
                                    progress = (downloaded / total_size * 100) if total_size > 0 else 0
                                    self.logger.info(f"Download progress: {progress:.1f}% ({downloaded}/{total_size} bytes)")
                                    
                        # Verify checksum if provided
                        if expected_checksum and self.config.get("verify_checksums", True):
                            if not self._verify_checksum(temp_file, expected_checksum):
                                self.logger.error("Model checksum verification failed")
                                shutil.rmtree(temp_dir)
                                return None
                                
                        self.logger.info(f"Model downloaded successfully: {temp_file}")
                        return temp_file
                    else:
                        self.logger.error(f"Download failed: HTTP {response.status}")
                        shutil.rmtree(temp_dir)
                        return None
                        
        except Exception as e:
            self.logger.error(f"Model download failed: {e}")
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir, ignore_errors=True)
            return None
            
    def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
                    
            actual_checksum = sha256_hash.hexdigest()
            return actual_checksum.lower() == expected_checksum.lower()
            
        except Exception as e:
            self.logger.error(f"Checksum verification failed: {e}")
            return False
            
    def backup_current_model(self) -> bool:
        """Backup current model before update"""
        if not self.config.get("backup_old_models", True):
            return True
            
        try:
            if self.current_model_dir.exists() and any(self.current_model_dir.iterdir()):
                backup_dir = self.models_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                backup_dir.mkdir(parents=True, exist_ok=True)
                
                shutil.copytree(self.current_model_dir, backup_dir / "current_model")
                self.logger.info(f"Current model backed up to: {backup_dir}")
                
                # Clean old backups (keep last 5)
                self._cleanup_old_backups()
                return True
            else:
                self.logger.info("No current model to backup")
                return True
                
        except Exception as e:
            self.logger.error(f"Model backup failed: {e}")
            return False
            
    def _cleanup_old_backups(self, keep_count: int = 5):
        """Remove old model backups"""
        try:
            backup_dirs = [d for d in self.models_dir.iterdir() 
                          if d.is_dir() and d.name.startswith('backup_')]
            
            if len(backup_dirs) > keep_count:
                # Sort by creation time and remove oldest
                backup_dirs.sort(key=lambda x: x.stat().st_ctime)
                for old_backup in backup_dirs[:-keep_count]:
                    shutil.rmtree(old_backup)
                    self.logger.info(f"Removed old backup: {old_backup}")
                    
        except Exception as e:
            self.logger.warning(f"Backup cleanup failed: {e}")
            
    def extract_model(self, model_file: Path) -> bool:
        """
        Extract downloaded model to current_model directory
        Returns True if successful
        """
        try:
            self.logger.info(f"Extracting model: {model_file}")
            
            # Clear current model directory
            if self.current_model_dir.exists():
                shutil.rmtree(self.current_model_dir)
            self.current_model_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract tar.gz file
            with tarfile.open(model_file, 'r:gz') as tar:
                tar.extractall(path=self.current_model_dir)
                
            self.logger.info(f"Model extracted to: {self.current_model_dir}")
            
            # Clean up downloaded file
            temp_dir = model_file.parent
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Model extraction failed: {e}")
            return False
            
    async def perform_update(self, remote_version_data: Dict[str, Any]) -> bool:
        """
        Perform complete model update process
        Returns True if successful
        """
        try:
            model_url = remote_version_data.get('model_url')
            if not model_url:
                self.logger.error("No model URL provided in remote version data")
                return False
                
            expected_checksum = remote_version_data.get('checksum')
            
            # Backup current model
            if not self.backup_current_model():
                self.logger.error("Failed to backup current model")
                return False
                
            # Download new model
            downloaded_file = await self.download_model(model_url, expected_checksum)
            if not downloaded_file:
                self.logger.error("Failed to download new model")
                return False
                
            # Extract new model
            if not self.extract_model(downloaded_file):
                self.logger.error("Failed to extract new model")
                return False
                
            # Update local version info
            version_data = {
                "version": remote_version_data.get('version'),
                "model_name": remote_version_data.get('model_name', 'signalojs_ai_model'),
                "last_updated": datetime.now().isoformat(),
                "checksum": remote_version_data.get('checksum', ''),
                "size": remote_version_data.get('size', 0),
                "download_url": model_url
            }
            self._save_local_version(version_data)
            
            self.logger.info(f"Model update completed successfully: {version_data['version']}")
            
            # Trigger notification
            self.trigger_update_notification(version_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Model update failed: {e}")
            return False
            
    def trigger_update_notification(self, version_data: Dict[str, Any]):
        """Trigger user notification about model update"""
        try:
            if not self.config.get("notification_enabled", True):
                return
                
            notification_data = {
                "type": "model_update",
                "title": "AI Model Updated",
                "message": f"SignalOS AI model has been updated to version {version_data['version']}",
                "version": version_data['version'],
                "timestamp": datetime.now().isoformat()
            }
            
            # Save notification to file (can be picked up by main app)
            notifications_dir = Path("notifications")
            notifications_dir.mkdir(exist_ok=True)
            
            notification_file = notifications_dir / f"model_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(notification_file, 'w') as f:
                json.dump(notification_data, f, indent=2)
                
            self.logger.info(f"Update notification created: {notification_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to create update notification: {e}")
            
    async def auto_update_check(self) -> bool:
        """
        Automatic update check and download
        Returns True if update was performed
        """
        try:
            self.logger.info("Starting automatic model update check...")
            
            # Check for updates
            update_available, remote_version_data = await self.check_for_updates()
            
            if not update_available:
                return False
                
            if not self.config.get("auto_download", True):
                self.logger.info("Auto-download disabled, skipping update")
                return False
                
            # Perform update
            success = await self.perform_update(remote_version_data)
            
            if success:
                self.logger.info("Automatic model update completed successfully")
            else:
                self.logger.error("Automatic model update failed")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Auto update check failed: {e}")
            return False
            
    def get_update_status(self) -> Dict[str, Any]:
        """Get current update status information"""
        local_version = self.get_local_version()
        
        return {
            "current_version": local_version.get('version', 'unknown'),
            "last_updated": local_version.get('last_updated'),
            "last_check": self.config.get('last_check'),
            "auto_download_enabled": self.config.get('auto_download', True),
            "models_directory": str(self.models_dir),
            "backend_url": self.backend_url,
            "check_interval_hours": self.check_interval_hours
        }


# Helper functions for external use
async def check_model_updates() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Convenience function to check for model updates"""
    updater = ModelUpdater()
    return await updater.check_for_updates()


async def download_model_update(model_url: str, expected_checksum: str = None) -> bool:
    """Convenience function to download and install model update"""
    updater = ModelUpdater()
    
    # Create mock remote version data
    remote_version_data = {
        "model_url": model_url,
        "checksum": expected_checksum,
        "version": "auto_update",
        "model_name": "signalojs_ai_model"
    }
    
    return await updater.perform_update(remote_version_data)


def get_current_model_version() -> str:
    """Get current model version"""
    updater = ModelUpdater()
    version_data = updater.get_local_version()
    return version_data.get('version', 'unknown')


# Main function for testing
async def main():
    """Test the model updater"""
    print("🤖 Testing SignalOS Model Updater")
    print("=" * 50)
    
    updater = ModelUpdater()
    
    # Show current status
    status = updater.get_update_status()
    print("📊 Current Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Check for updates
    print(f"\n🔍 Checking for model updates...")
    update_available, remote_data = await updater.check_for_updates()
    
    if update_available:
        print(f"✅ Update available: {remote_data.get('version')}")
        print(f"📦 Model URL: {remote_data.get('model_url', 'N/A')}")
    else:
        print("✅ Model is up to date")
    
    print(f"\n📁 Models directory: {updater.models_dir}")
    print(f"📁 Current model: {updater.current_model_dir}")


if __name__ == "__main__":
    asyncio.run(main())