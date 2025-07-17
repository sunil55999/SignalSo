#!/usr/bin/env python3
"""
Update Scheduler for SignalOS
Manages automatic update checks and scheduling
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import json

from .model_updater import ModelUpdater
from .notification_handler import NotificationHandler, NotificationType


class UpdateScheduler:
    """Manages automatic update checking and scheduling"""
    
    def __init__(self, config_path: str = "config/scheduler_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.setup_logging()
        
        # Initialize components
        self.model_updater = ModelUpdater()
        self.notification_handler = NotificationHandler()
        
        # Scheduling configuration
        self.check_interval_hours = self.config.get("check_interval_hours", 6)
        self.auto_update_enabled = self.config.get("auto_update_enabled", True)
        self.update_window_start = self.config.get("update_window_start", "02:00")  # 2 AM
        self.update_window_end = self.config.get("update_window_end", "06:00")    # 6 AM
        
        # State
        self.last_check = self.config.get("last_check")
        self.scheduler_task: Optional[asyncio.Task] = None
        self.running = False
        
    def setup_logging(self):
        """Setup logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / "update_scheduler.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self) -> Dict[str, Any]:
        """Load scheduler configuration"""
        default_config = {
            "check_interval_hours": 6,
            "auto_update_enabled": True,
            "update_window_start": "02:00",
            "update_window_end": "06:00",
            "retry_failed_updates": True,
            "max_retry_attempts": 3,
            "notify_on_check": False,
            "last_check": None
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    return {**default_config, **loaded_config}
        except Exception as e:
            print(f"Warning: Failed to load scheduler config: {e}")
            
        return default_config
        
    def _save_config(self):
        """Save scheduler configuration"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save scheduler config: {e}")
            
    def is_in_update_window(self) -> bool:
        """Check if current time is within the update window"""
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            
            start_time = self.update_window_start
            end_time = self.update_window_end
            
            if start_time <= end_time:
                # Same day window (e.g., 02:00 to 06:00)
                return start_time <= current_time <= end_time
            else:
                # Overnight window (e.g., 22:00 to 06:00)
                return current_time >= start_time or current_time <= end_time
                
        except Exception as e:
            self.logger.error(f"Failed to check update window: {e}")
            return True  # Default to allowing updates
            
    def should_check_for_updates(self) -> bool:
        """Check if it's time to check for updates"""
        if not self.last_check:
            return True
            
        try:
            last_check_time = datetime.fromisoformat(self.last_check)
            next_check_time = last_check_time + timedelta(hours=self.check_interval_hours)
            return datetime.now() >= next_check_time
            
        except Exception as e:
            self.logger.error(f"Failed to parse last check time: {e}")
            return True
            
    async def check_and_update_models(self) -> bool:
        """Check for and perform model updates if available"""
        try:
            self.logger.info("Starting scheduled model update check...")
            
            # Update last check time
            self.last_check = datetime.now().isoformat()
            self.config["last_check"] = self.last_check
            self._save_config()
            
            # Check for model updates
            update_available, remote_version_data = await self.model_updater.check_for_updates()
            
            if not update_available:
                self.logger.info("No model updates available")
                if self.config.get("notify_on_check", False):
                    self.notification_handler.create_system_notification(
                        "Update Check Complete",
                        "No model updates available. Current version is up to date."
                    )
                return False
                
            # Notify about available update
            self.notification_handler.notify_model_update_available(remote_version_data)
            
            # Perform update if auto-update is enabled and we're in the update window
            if self.auto_update_enabled and self.is_in_update_window():
                self.logger.info("Auto-update enabled and in update window, performing update...")
                
                success = await self.model_updater.perform_update(remote_version_data)
                
                if success:
                    self.notification_handler.notify_model_update_completed(remote_version_data)
                    self.logger.info("Scheduled model update completed successfully")
                else:
                    error_msg = "Failed to download or install model update"
                    self.notification_handler.notify_model_update_failed(remote_version_data, error_msg)
                    self.logger.error("Scheduled model update failed")
                    
                return success
            else:
                self.logger.info("Auto-update disabled or outside update window")
                return False
                
        except Exception as e:
            self.logger.error(f"Scheduled update check failed: {e}")
            return False
            
    async def start_scheduler(self):
        """Start the update scheduler"""
        if self.running:
            self.logger.warning("Scheduler already running")
            return
            
        self.running = True
        self.logger.info(f"Starting update scheduler (check interval: {self.check_interval_hours}h)")
        
        while self.running:
            try:
                # Check if it's time for an update check
                if self.should_check_for_updates():
                    await self.check_and_update_models()
                    
                # Wait before next check (check every 30 minutes, but only update based on interval)
                await asyncio.sleep(30 * 60)  # 30 minutes
                
            except asyncio.CancelledError:
                self.logger.info("Scheduler cancelled")
                break
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                
        self.running = False
        self.logger.info("Update scheduler stopped")
        
    def stop_scheduler(self):
        """Stop the update scheduler"""
        self.running = False
        if self.scheduler_task and not self.scheduler_task.done():
            self.scheduler_task.cancel()
            
        self.logger.info("Update scheduler stop requested")
        
    async def force_update_check(self) -> bool:
        """Force an immediate update check regardless of schedule"""
        self.logger.info("Forcing immediate update check...")
        return await self.check_and_update_models()
        
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        next_check = None
        if self.last_check:
            try:
                last_check_time = datetime.fromisoformat(self.last_check)
                next_check_time = last_check_time + timedelta(hours=self.check_interval_hours)
                next_check = next_check_time.isoformat()
            except:
                pass
                
        return {
            "running": self.running,
            "auto_update_enabled": self.auto_update_enabled,
            "check_interval_hours": self.check_interval_hours,
            "last_check": self.last_check,
            "next_check": next_check,
            "update_window": f"{self.update_window_start} - {self.update_window_end}",
            "in_update_window": self.is_in_update_window(),
            "should_check": self.should_check_for_updates()
        }
        
    def configure_scheduler(self, **kwargs):
        """Configure scheduler settings"""
        if "check_interval_hours" in kwargs:
            self.check_interval_hours = kwargs["check_interval_hours"]
            self.config["check_interval_hours"] = self.check_interval_hours
            
        if "auto_update_enabled" in kwargs:
            self.auto_update_enabled = kwargs["auto_update_enabled"]
            self.config["auto_update_enabled"] = self.auto_update_enabled
            
        if "update_window_start" in kwargs:
            self.update_window_start = kwargs["update_window_start"]
            self.config["update_window_start"] = self.update_window_start
            
        if "update_window_end" in kwargs:
            self.update_window_end = kwargs["update_window_end"]
            self.config["update_window_end"] = self.update_window_end
            
        self._save_config()
        self.logger.info("Scheduler configuration updated")


# Global scheduler instance
_global_scheduler: Optional[UpdateScheduler] = None


def get_scheduler() -> UpdateScheduler:
    """Get global scheduler instance"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = UpdateScheduler()
    return _global_scheduler


async def start_auto_updates():
    """Start automatic update checking"""
    scheduler = get_scheduler()
    await scheduler.start_scheduler()


def stop_auto_updates():
    """Stop automatic update checking"""
    scheduler = get_scheduler()
    scheduler.stop_scheduler()


async def force_update_check() -> bool:
    """Force an immediate update check"""
    scheduler = get_scheduler()
    return await scheduler.force_update_check()


def configure_auto_updates(**kwargs):
    """Configure automatic update settings"""
    scheduler = get_scheduler()
    scheduler.configure_scheduler(**kwargs)


def get_update_status() -> Dict[str, Any]:
    """Get current update system status"""
    scheduler = get_scheduler()
    return scheduler.get_scheduler_status()


# Main function for testing
async def main():
    """Test the update scheduler"""
    print("⏰ Testing SignalOS Update Scheduler")
    print("=" * 50)
    
    scheduler = UpdateScheduler()
    
    # Show current status
    status = scheduler.get_scheduler_status()
    print("📊 Scheduler Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Test update window checking
    print(f"\n🕐 Update Window Test:")
    print(f"   Current time in update window: {scheduler.is_in_update_window()}")
    print(f"   Should check for updates: {scheduler.should_check_for_updates()}")
    
    # Test forced update check
    print(f"\n🔍 Testing forced update check...")
    try:
        result = await scheduler.force_update_check()
        print(f"   Update check result: {'✅ Success' if result else '❌ No updates or failed'}")
    except Exception as e:
        print(f"   Update check error: {e}")
    
    # Test configuration
    print(f"\n⚙️ Testing configuration...")
    scheduler.configure_scheduler(
        check_interval_hours=12,
        auto_update_enabled=False,
        update_window_start="01:00",
        update_window_end="05:00"
    )
    
    new_status = scheduler.get_scheduler_status()
    print(f"   Updated check interval: {new_status['check_interval_hours']}h")
    print(f"   Auto-update enabled: {new_status['auto_update_enabled']}")
    
    print(f"\n✅ Update scheduler testing complete")


if __name__ == "__main__":
    asyncio.run(main())