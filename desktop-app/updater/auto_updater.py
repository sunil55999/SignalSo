#!/usr/bin/env python3
"""
Auto Updater for SignalOS Desktop Application

Implements automatic application updates with version checking,
download management, and safe update installation.
"""

import os
import sys
import json
import hashlib
import logging
import asyncio
import aiohttp
import zipfile
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import platform
import tempfile

class UpdateStatus(Enum):
    """Update status enumeration"""
    CHECKING = "checking"
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"
    UP_TO_DATE = "up_to_date"
    DISABLED = "disabled"

@dataclass
class VersionInfo:
    """Version information structure"""
    version: str
    build_number: int
    release_date: datetime
    channel: str  # stable, beta, alpha
    download_url: str
    checksum: str
    size_bytes: int
    changelog: List[str]
    required_restart: bool

@dataclass
class UpdateProgress:
    """Update progress information"""
    status: UpdateStatus
    current_version: str
    available_version: Optional[str]
    download_progress: float  # 0.0 to 100.0
    install_progress: float   # 0.0 to 100.0
    message: str
    error: Optional[str]

class AutoUpdater:
    """Automatic application updater"""
    
    def __init__(self, config_file: str = "config.json", update_dir: str = "updates"):
        self.config_file = config_file
        self.update_dir = Path(update_dir)
        self.config = self._load_config()
        self._setup_logging()
        
        # Application information
        self.app_name = self.config.get("app_name", "SignalOS")
        self.current_version = self.config.get("current_version", "1.0.0")
        self.build_number = self.config.get("build_number", 1)
        self.update_channel = self.config.get("update_channel", "stable")
        
        # Update server configuration
        self.update_server_url = self.config.get("update_server_url", "https://updates.signalos.com")
        self.check_interval_hours = self.config.get("check_interval_hours", 24)
        self.auto_download = self.config.get("auto_download", True)
        self.auto_install = self.config.get("auto_install", False)
        
        # Update state
        self.update_progress = UpdateProgress(
            status=UpdateStatus.UP_TO_DATE,
            current_version=self.current_version,
            available_version=None,
            download_progress=0.0,
            install_progress=0.0,
            message="No updates available",
            error=None
        )
        
        # Create update directory
        self.update_dir.mkdir(exist_ok=True)
        
        # Background task
        self.update_task: Optional[asyncio.Task] = None
        self.is_running = False
        
    def _load_config(self) -> Dict[str, Any]:
        """Load updater configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('auto_updater', self._get_default_config())
        except FileNotFoundError:
            return self._create_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default updater configuration"""
        return {
            "enabled": True,
            "app_name": "SignalOS",
            "current_version": "1.0.0",
            "build_number": 1,
            "update_channel": "stable",  # stable, beta, alpha
            "update_server_url": "https://updates.signalos.com",
            "check_interval_hours": 24,
            "auto_download": True,
            "auto_install": False,
            "backup_before_update": True,
            "rollback_on_failure": True,
            "verify_signatures": True,
            "download_timeout": 300,
            "retry_attempts": 3,
            "update_channels": {
                "stable": {"priority": 1, "auto_install": False},
                "beta": {"priority": 2, "auto_install": False},
                "alpha": {"priority": 3, "auto_install": False}
            }
        }
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration and save to file"""
        default_config = {
            "auto_updater": self._get_default_config()
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
            
        return default_config["auto_updater"]
    
    def _setup_logging(self):
        """Setup logging for auto updater"""
        self.logger = logging.getLogger('AutoUpdater')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # File handler
            log_file = self.update_dir / "updater.log"
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
    
    def _get_system_info(self) -> Dict[str, str]:
        """Get system information for update compatibility"""
        return {
            "platform": platform.system(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "platform_release": platform.release()
        }
    
    async def check_for_updates(self) -> Optional[VersionInfo]:
        """Check for available updates"""
        if not self.config.get("enabled", True):
            self.update_progress.status = UpdateStatus.DISABLED
            return None
        
        try:
            self.update_progress.status = UpdateStatus.CHECKING
            self.update_progress.message = "Checking for updates..."
            
            # Prepare request data
            request_data = {
                "app_name": self.app_name,
                "current_version": self.current_version,
                "build_number": self.build_number,
                "channel": self.update_channel,
                "system_info": self._get_system_info()
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.update_server_url}/api/updates/check"
                timeout = aiohttp.ClientTimeout(total=30)
                
                async with session.post(url, json=request_data, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("update_available"):
                            version_info = VersionInfo(
                                version=data["version"],
                                build_number=data["build_number"],
                                release_date=datetime.fromisoformat(data["release_date"]),
                                channel=data["channel"],
                                download_url=data["download_url"],
                                checksum=data["checksum"],
                                size_bytes=data["size_bytes"],
                                changelog=data.get("changelog", []),
                                required_restart=data.get("required_restart", True)
                            )
                            
                            self.update_progress.status = UpdateStatus.AVAILABLE
                            self.update_progress.available_version = version_info.version
                            self.update_progress.message = f"Update available: {version_info.version}"
                            
                            self.logger.info(f"Update available: {version_info.version}")
                            return version_info
                        else:
                            self.update_progress.status = UpdateStatus.UP_TO_DATE
                            self.update_progress.message = "Application is up to date"
                            return None
                    else:
                        error_msg = f"Update check failed: {response.status}"
                        self.logger.error(error_msg)
                        self.update_progress.status = UpdateStatus.FAILED
                        self.update_progress.error = error_msg
                        return None
                        
        except asyncio.TimeoutError:
            error_msg = "Update check timed out"
            self.logger.error(error_msg)
            self.update_progress.status = UpdateStatus.FAILED
            self.update_progress.error = error_msg
            return None
        except Exception as e:
            error_msg = f"Update check error: {e}"
            self.logger.error(error_msg)
            self.update_progress.status = UpdateStatus.FAILED
            self.update_progress.error = error_msg
            return None
    
    async def download_update(self, version_info: VersionInfo) -> Optional[Path]:
        """Download update package"""
        try:
            self.update_progress.status = UpdateStatus.DOWNLOADING
            self.update_progress.message = f"Downloading update {version_info.version}..."
            
            download_path = self.update_dir / f"{self.app_name}_{version_info.version}.zip"
            
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=self.config.get("download_timeout", 300))
                
                async with session.get(version_info.download_url, timeout=timeout) as response:
                    if response.status == 200:
                        total_size = int(response.headers.get('Content-Length', 0))
                        downloaded_size = 0
                        
                        with open(download_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                
                                if total_size > 0:
                                    progress = (downloaded_size / total_size) * 100
                                    self.update_progress.download_progress = progress
                                    
                                    if downloaded_size % (1024 * 1024) == 0:  # Log every MB
                                        self.logger.info(f"Downloaded {downloaded_size // (1024 * 1024)}MB of {total_size // (1024 * 1024)}MB")
                        
                        # Verify checksum
                        if await self._verify_checksum(download_path, version_info.checksum):
                            self.update_progress.download_progress = 100.0
                            self.update_progress.message = f"Download completed: {version_info.version}"
                            self.logger.info(f"Update downloaded successfully: {download_path}")
                            return download_path
                        else:
                            download_path.unlink()  # Remove corrupted file
                            error_msg = "Downloaded file checksum verification failed"
                            self.logger.error(error_msg)
                            self.update_progress.status = UpdateStatus.FAILED
                            self.update_progress.error = error_msg
                            return None
                    else:
                        error_msg = f"Download failed: {response.status}"
                        self.logger.error(error_msg)
                        self.update_progress.status = UpdateStatus.FAILED
                        self.update_progress.error = error_msg
                        return None
                        
        except Exception as e:
            error_msg = f"Download error: {e}"
            self.logger.error(error_msg)
            self.update_progress.status = UpdateStatus.FAILED
            self.update_progress.error = error_msg
            return None
    
    async def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            actual_checksum = hasher.hexdigest()
            return actual_checksum.lower() == expected_checksum.lower()
            
        except Exception as e:
            self.logger.error(f"Checksum verification error: {e}")
            return False
    
    async def install_update(self, update_file: Path, version_info: VersionInfo) -> bool:
        """Install update package"""
        try:
            self.update_progress.status = UpdateStatus.INSTALLING
            self.update_progress.message = f"Installing update {version_info.version}..."
            
            # Create backup if enabled
            backup_path = None
            if self.config.get("backup_before_update", True):
                backup_path = await self._create_backup()
                if not backup_path:
                    error_msg = "Failed to create backup"
                    self.logger.error(error_msg)
                    self.update_progress.status = UpdateStatus.FAILED
                    self.update_progress.error = error_msg
                    return False
            
            # Extract update
            extract_path = self.update_dir / f"extract_{version_info.version}"
            extract_path.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(update_file, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            self.update_progress.install_progress = 30.0
            
            # Run update script if exists
            update_script = extract_path / "update.py"
            if update_script.exists():
                result = await self._run_update_script(update_script, extract_path)
                if not result:
                    if backup_path:
                        await self._restore_backup(backup_path)
                    return False
            else:
                # Default update process: replace files
                await self._replace_application_files(extract_path)
            
            self.update_progress.install_progress = 80.0
            
            # Update version info
            await self._update_version_info(version_info)
            
            self.update_progress.install_progress = 100.0
            self.update_progress.status = UpdateStatus.COMPLETED
            self.update_progress.message = f"Update {version_info.version} installed successfully"
            
            # Cleanup
            shutil.rmtree(extract_path, ignore_errors=True)
            update_file.unlink(missing_ok=True)
            
            self.logger.info(f"Update {version_info.version} installed successfully")
            return True
            
        except Exception as e:
            error_msg = f"Installation error: {e}"
            self.logger.error(error_msg)
            self.update_progress.status = UpdateStatus.FAILED
            self.update_progress.error = error_msg
            return False
    
    async def _create_backup(self) -> Optional[Path]:
        """Create backup of current application"""
        try:
            backup_dir = self.update_dir / "backup"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"backup_{self.current_version}_{timestamp}.zip"
            
            app_dir = Path(__file__).parent.parent  # Go up to desktop-app directory
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in app_dir.rglob('*'):
                    if file_path.is_file() and not str(file_path).startswith(str(self.update_dir)):
                        archive_name = file_path.relative_to(app_dir)
                        zip_file.write(file_path, archive_name)
            
            self.logger.info(f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            return None
    
    async def _restore_backup(self, backup_path: Path) -> bool:
        """Restore from backup"""
        try:
            app_dir = Path(__file__).parent.parent
            
            with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                zip_ref.extractall(app_dir)
            
            self.logger.info(f"Backup restored: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup restoration failed: {e}")
            return False
    
    async def _run_update_script(self, script_path: Path, extract_path: Path) -> bool:
        """Run custom update script"""
        try:
            # Prepare environment for update script
            env = os.environ.copy()
            env['UPDATE_SOURCE_DIR'] = str(extract_path)
            env['UPDATE_TARGET_DIR'] = str(Path(__file__).parent.parent)
            env['UPDATE_VERSION'] = self.update_progress.available_version or "unknown"
            
            # Run update script
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(script_path),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.logger.info(f"Update script completed successfully")
                return True
            else:
                error_msg = f"Update script failed: {stderr.decode()}"
                self.logger.error(error_msg)
                return False
                
        except Exception as e:
            self.logger.error(f"Update script execution failed: {e}")
            return False
    
    async def _replace_application_files(self, source_dir: Path):
        """Replace application files with updated versions"""
        app_dir = Path(__file__).parent.parent
        
        for source_file in source_dir.rglob('*'):
            if source_file.is_file():
                relative_path = source_file.relative_to(source_dir)
                target_file = app_dir / relative_path
                
                # Create target directory if needed
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(source_file, target_file)
                self.logger.debug(f"Updated file: {relative_path}")
    
    async def _update_version_info(self, version_info: VersionInfo):
        """Update version information in config"""
        try:
            # Update config file
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            if "auto_updater" not in config_data:
                config_data["auto_updater"] = {}
            
            config_data["auto_updater"]["current_version"] = version_info.version
            config_data["auto_updater"]["build_number"] = version_info.build_number
            config_data["auto_updater"]["last_update"] = datetime.now().isoformat()
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            # Update instance variables
            self.current_version = version_info.version
            self.build_number = version_info.build_number
            self.update_progress.current_version = version_info.version
            
        except Exception as e:
            self.logger.error(f"Failed to update version info: {e}")
    
    async def perform_update(self, version_info: VersionInfo) -> bool:
        """Perform complete update process"""
        try:
            # Download update
            download_path = await self.download_update(version_info)
            if not download_path:
                return False
            
            # Install update
            success = await self.install_update(download_path, version_info)
            
            if success and version_info.required_restart:
                self.update_progress.message = "Update completed. Restart required."
                self.logger.info("Update completed successfully. Application restart required.")
            
            return success
            
        except Exception as e:
            error_msg = f"Update process failed: {e}"
            self.logger.error(error_msg)
            self.update_progress.status = UpdateStatus.FAILED
            self.update_progress.error = error_msg
            return False
    
    async def start_update_checker(self):
        """Start background update checker"""
        if self.is_running:
            self.logger.warning("Update checker is already running")
            return
        
        self.is_running = True
        self.update_task = asyncio.create_task(self._update_checker_loop())
        self.logger.info("Update checker started")
    
    async def stop_update_checker(self):
        """Stop background update checker"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Update checker stopped")
    
    async def _update_checker_loop(self):
        """Background update checker loop"""
        try:
            while self.is_running:
                # Check for updates
                version_info = await self.check_for_updates()
                
                if version_info and self.auto_download:
                    # Auto-download update
                    download_path = await self.download_update(version_info)
                    
                    if download_path and self.auto_install:
                        # Auto-install update
                        await self.install_update(download_path, version_info)
                
                # Wait for next check
                await asyncio.sleep(self.check_interval_hours * 3600)
                
        except asyncio.CancelledError:
            self.logger.info("Update checker loop cancelled")
        except Exception as e:
            self.logger.error(f"Update checker loop error: {e}")
    
    def get_update_progress(self) -> Dict[str, Any]:
        """Get current update progress"""
        return {
            "status": self.update_progress.status.value,
            "current_version": self.update_progress.current_version,
            "available_version": self.update_progress.available_version,
            "download_progress": self.update_progress.download_progress,
            "install_progress": self.update_progress.install_progress,
            "message": self.update_progress.message,
            "error": self.update_progress.error
        }


# Example usage and testing
async def main():
    """Example usage of auto updater"""
    updater = AutoUpdater()
    
    # Start update checker
    await updater.start_update_checker()
    
    # Manual update check
    version_info = await updater.check_for_updates()
    if version_info:
        print(f"Update available: {version_info.version}")
        print(f"Changelog: {version_info.changelog}")
        
        # Perform update
        success = await updater.perform_update(version_info)
        print(f"Update successful: {success}")
    else:
        print("No updates available")
    
    # Show progress
    progress = updater.get_update_progress()
    print(f"Update progress: {json.dumps(progress, indent=2)}")
    
    # Stop update checker
    await updater.stop_update_checker()


if __name__ == "__main__":
    asyncio.run(main())