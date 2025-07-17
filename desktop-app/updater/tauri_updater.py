#!/usr/bin/env python3
"""
Tauri-Style Auto-Updater for SignalOS Desktop Application

Implements automatic updates with Tauri-style latest.json configuration.
Includes version checking, secure download/install, and rollback capabilities.
"""

import os
import sys
import json
import logging
import hashlib
import shutil
import zipfile
import tempfile
import subprocess
import threading
import asyncio
from typing import Dict, Optional, Any, Tuple, List
from pathlib import Path
from datetime import datetime
import requests
from dataclasses import dataclass
import platform

# Simple version comparison without semver
def compare_versions(v1: str, v2: str) -> bool:
    """Simple version comparison without semver dependency"""
    try:
        v1_parts = [int(x) for x in v1.lstrip('v').split('.')]
        v2_parts = [int(x) for x in v2.lstrip('v').split('.')]
        
        # Pad with zeros
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts += [0] * (max_len - len(v1_parts))
        v2_parts += [0] * (max_len - len(v2_parts))
        
        return v1_parts > v2_parts
    except:
        return False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class UpdateInfo:
    """Information about an available update (Tauri-style)"""
    version: str
    download_url: str
    changelog: str
    file_size: int
    checksum: str
    required: bool
    release_date: str
    signature: Optional[str] = None
    platform: Optional[str] = None
    arch: Optional[str] = None

@dataclass
class UpdateProgress:
    """Update progress tracking"""
    status: str
    current_version: str
    available_version: Optional[str]
    download_progress: float
    install_progress: float
    message: str
    error: Optional[str] = None

class TauriUpdater:
    """
    Tauri-style automatic updater for SignalOS
    """
    
    def __init__(self, config_file: str = "config.json", update_server: str = None):
        self.config_file = config_file
        self.config = self._load_config()
        self.update_server = update_server or self.config.get("update_server", "https://updates.signalos.com")
        self.current_version = self.config.get("version", "1.0.0")
        self.app_name = self.config.get("app_name", "SignalOS")
        self.update_dir = Path("updates")
        self.backup_dir = Path("backups")
        
        # Create directories
        self.update_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Update state
        self.update_in_progress = False
        self.progress_callback = None
        self.auto_update_enabled = self.config.get("auto_update", True)
        self.check_interval = self.config.get("update_check_interval", 3600)  # 1 hour
        
        # Platform info
        self.platform = platform.system().lower()
        self.arch = platform.machine().lower()
        
        logger.info(f"TauriUpdater initialized for {self.app_name} v{self.current_version}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    async def check_for_updates(self) -> Optional[UpdateInfo]:
        """
        Check for available updates using Tauri-style latest.json
        """
        try:
            # Construct latest.json URL
            latest_url = f"{self.update_server}/latest.json"
            
            logger.info(f"Checking for updates at: {latest_url}")
            
            # Download latest.json
            response = requests.get(latest_url, timeout=30)
            response.raise_for_status()
            
            latest_data = response.json()
            
            # Extract version info
            available_version = latest_data.get("version", "0.0.0")
            
            # Compare versions
            if self._is_newer_version(available_version, self.current_version):
                # Find platform-specific download
                platforms = latest_data.get("platforms", {})
                platform_key = f"{self.platform}-{self.arch}"
                
                if platform_key in platforms:
                    platform_data = platforms[platform_key]
                    
                    update_info = UpdateInfo(
                        version=available_version,
                        download_url=platform_data.get("url", ""),
                        changelog=latest_data.get("changelog", ""),
                        file_size=platform_data.get("size", 0),
                        checksum=platform_data.get("checksum", ""),
                        required=latest_data.get("required", False),
                        release_date=latest_data.get("release_date", ""),
                        signature=platform_data.get("signature"),
                        platform=self.platform,
                        arch=self.arch
                    )
                    
                    logger.info(f"Update available: {self.current_version} -> {available_version}")
                    return update_info
                else:
                    logger.warning(f"No update available for platform: {platform_key}")
                    return None
            else:
                logger.info("Application is up to date")
                return None
                
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            return None
    
    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """Compare version strings"""
        return compare_versions(version1, version2)
    
    async def download_update(self, update_info: UpdateInfo, progress_callback=None) -> Optional[str]:
        """
        Download update package
        """
        try:
            if not update_info.download_url:
                raise ValueError("No download URL provided")
            
            # Create download filename
            filename = f"{self.app_name}-{update_info.version}-{self.platform}-{self.arch}.zip"
            download_path = self.update_dir / filename
            
            logger.info(f"Downloading update from: {update_info.download_url}")
            
            # Download with progress tracking
            response = requests.get(update_info.download_url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress, "Downloading update...")
            
            # Verify checksum
            if update_info.checksum:
                if not self._verify_checksum(download_path, update_info.checksum):
                    raise ValueError("Checksum verification failed")
            
            logger.info(f"Update downloaded successfully: {download_path}")
            return str(download_path)
            
        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            return None
    
    def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            actual_checksum = hasher.hexdigest()
            return actual_checksum == expected_checksum
            
        except Exception as e:
            logger.error(f"Checksum verification error: {e}")
            return False
    
    async def install_update(self, update_package: str, progress_callback=None) -> bool:
        """
        Install downloaded update
        """
        try:
            if not os.path.exists(update_package):
                raise FileNotFoundError(f"Update package not found: {update_package}")
            
            # Create backup of current version
            backup_path = self._create_backup()
            if not backup_path:
                logger.error("Failed to create backup")
                return False
            
            # Extract update package
            extract_path = self.update_dir / "extracted"
            if extract_path.exists():
                shutil.rmtree(extract_path)
            extract_path.mkdir(parents=True)
            
            logger.info(f"Extracting update package: {update_package}")
            
            with zipfile.ZipFile(update_package, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
                
                if progress_callback:
                    progress_callback(50, "Extracting update...")
            
            # Install update files
            self._install_files(extract_path, progress_callback)
            
            # Update version in config
            self._update_version_info(update_package)
            
            # Cleanup
            shutil.rmtree(extract_path)
            os.remove(update_package)
            
            logger.info("Update installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install update: {e}")
            return False
    
    def _create_backup(self) -> Optional[str]:
        """Create backup of current version"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{self.app_name}_backup_{self.current_version}_{timestamp}"
            backup_path = self.backup_dir / backup_name
            
            # Create backup directory
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Copy current application files
            app_files = [
                "main.py",
                "config.json",
                "requirements.txt",
                "parser/",
                "strategy/",
                "auth/",
                "updater/"
            ]
            
            for file_item in app_files:
                src = Path(file_item)
                if src.exists():
                    if src.is_file():
                        shutil.copy2(src, backup_path / src.name)
                    else:
                        shutil.copytree(src, backup_path / src.name, dirs_exist_ok=True)
            
            logger.info(f"Backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def _install_files(self, extract_path: Path, progress_callback=None):
        """Install extracted files"""
        try:
            # Get list of files to install
            files_to_install = []
            for root, dirs, files in os.walk(extract_path):
                for file in files:
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(extract_path)
                    files_to_install.append((file_path, rel_path))
            
            # Install files
            for i, (src_path, rel_path) in enumerate(files_to_install):
                dest_path = Path(rel_path)
                
                # Create destination directory
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(src_path, dest_path)
                
                # Update progress
                if progress_callback:
                    progress = 50 + (i / len(files_to_install)) * 50
                    progress_callback(progress, f"Installing: {rel_path}")
            
            logger.info(f"Installed {len(files_to_install)} files")
            
        except Exception as e:
            logger.error(f"Failed to install files: {e}")
            raise
    
    def _update_version_info(self, update_package: str):
        """Update version information in config"""
        try:
            # Extract version from package name
            package_name = Path(update_package).stem
            version_match = None
            
            # Try to extract version from filename
            import re
            match = re.search(r'-(\d+\.\d+\.\d+)-', package_name)
            if match:
                new_version = match.group(1)
                
                # Update config
                self.config["version"] = new_version
                self.config["last_update"] = datetime.now().isoformat()
                self._save_config()
                
                # Update current version
                self.current_version = new_version
                
                logger.info(f"Version updated to: {new_version}")
            
        except Exception as e:
            logger.error(f"Failed to update version info: {e}")
    
    async def auto_update_loop(self):
        """
        Automatic update checking loop
        """
        while self.auto_update_enabled:
            try:
                # Check for updates
                update_info = await self.check_for_updates()
                
                if update_info:
                    logger.info(f"Auto-update available: {update_info.version}")
                    
                    # Download and install if required or configured
                    if update_info.required or self.config.get("auto_install", False):
                        await self.perform_update(update_info)
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Auto-update loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def perform_update(self, update_info: UpdateInfo) -> bool:
        """
        Perform complete update process
        """
        try:
            if self.update_in_progress:
                logger.warning("Update already in progress")
                return False
            
            self.update_in_progress = True
            
            # Create progress tracker
            progress = UpdateProgress(
                status="downloading",
                current_version=self.current_version,
                available_version=update_info.version,
                download_progress=0.0,
                install_progress=0.0,
                message="Starting update..."
            )
            
            def update_progress(percent: float, message: str):
                progress.download_progress = percent
                progress.message = message
                if self.progress_callback:
                    self.progress_callback(progress)
            
            # Download update
            update_package = await self.download_update(update_info, update_progress)
            
            if not update_package:
                progress.status = "failed"
                progress.error = "Failed to download update"
                if self.progress_callback:
                    self.progress_callback(progress)
                return False
            
            # Install update
            progress.status = "installing"
            progress.download_progress = 100.0
            
            def install_progress(percent: float, message: str):
                progress.install_progress = percent
                progress.message = message
                if self.progress_callback:
                    self.progress_callback(progress)
            
            success = await self.install_update(update_package, install_progress)
            
            if success:
                progress.status = "completed"
                progress.install_progress = 100.0
                progress.message = "Update completed successfully"
                logger.info("Update completed successfully")
            else:
                progress.status = "failed"
                progress.error = "Failed to install update"
                logger.error("Update installation failed")
            
            if self.progress_callback:
                self.progress_callback(progress)
            
            return success
            
        except Exception as e:
            logger.error(f"Update process failed: {e}")
            return False
        finally:
            self.update_in_progress = False
    
    def rollback_update(self, backup_name: str = None) -> bool:
        """
        Rollback to previous version
        """
        try:
            if not backup_name:
                # Find latest backup
                backups = list(self.backup_dir.glob(f"{self.app_name}_backup_*"))
                if not backups:
                    logger.error("No backups found")
                    return False
                
                # Sort by modification time
                backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                backup_path = backups[0]
            else:
                backup_path = self.backup_dir / backup_name
            
            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_path}")
                return False
            
            logger.info(f"Rolling back to backup: {backup_path}")
            
            # Restore files from backup
            for item in backup_path.iterdir():
                if item.is_file():
                    shutil.copy2(item, Path(item.name))
                else:
                    if Path(item.name).exists():
                        shutil.rmtree(Path(item.name))
                    shutil.copytree(item, Path(item.name))
            
            # Reload config
            self.config = self._load_config()
            self.current_version = self.config.get("version", "1.0.0")
            
            logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def get_update_status(self) -> Dict[str, Any]:
        """Get current update status"""
        return {
            "current_version": self.current_version,
            "update_in_progress": self.update_in_progress,
            "auto_update_enabled": self.auto_update_enabled,
            "last_check": self.config.get("last_update_check"),
            "last_update": self.config.get("last_update"),
            "platform": self.platform,
            "arch": self.arch
        }
    
    def set_progress_callback(self, callback):
        """Set progress callback function"""
        self.progress_callback = callback
    
    def enable_auto_update(self, enabled: bool):
        """Enable/disable auto-update"""
        self.auto_update_enabled = enabled
        self.config["auto_update"] = enabled
        self._save_config()


# Example usage and testing
async def test_updater():
    """Test the updater functionality"""
    
    updater = TauriUpdater()
    
    def progress_callback(progress: UpdateProgress):
        print(f"Status: {progress.status}")
        print(f"Download: {progress.download_progress:.1f}%")
        print(f"Install: {progress.install_progress:.1f}%")
        print(f"Message: {progress.message}")
        if progress.error:
            print(f"Error: {progress.error}")
        print("-" * 50)
    
    updater.set_progress_callback(progress_callback)
    
    # Check for updates
    print("Checking for updates...")
    update_info = await updater.check_for_updates()
    
    if update_info:
        print(f"Update available: {update_info.version}")
        print(f"Size: {update_info.file_size} bytes")
        print(f"Changelog: {update_info.changelog}")
        
        # Perform update
        success = await updater.perform_update(update_info)
        print(f"Update result: {'Success' if success else 'Failed'}")
    else:
        print("No updates available")
    
    # Show status
    status = updater.get_update_status()
    print(f"Update Status: {status}")


if __name__ == "__main__":
    asyncio.run(test_updater())