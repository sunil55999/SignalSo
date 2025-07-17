#!/usr/bin/env python3
"""
Notification Handler for SignalOS Updates
Manages user notifications for model and application updates
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class NotificationType(Enum):
    """Types of notifications"""
    MODEL_UPDATE = "model_update"
    APP_UPDATE = "app_update" 
    UPDATE_FAILED = "update_failed"
    UPDATE_AVAILABLE = "update_available"
    SYSTEM_INFO = "system_info"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationHandler:
    """Handles all update-related notifications"""
    
    def __init__(self, notifications_dir: str = "notifications"):
        self.notifications_dir = Path(notifications_dir)
        self.notifications_dir.mkdir(exist_ok=True)
        self.setup_logging()
        
        # Configuration
        self.max_notifications = 50  # Keep last 50 notifications
        self.enabled = True
        
    def setup_logging(self):
        """Setup logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / "notifications.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def create_notification(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new notification
        Returns notification ID
        """
        if not self.enabled:
            return ""
            
        try:
            notification_id = f"{notification_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            notification = {
                "id": notification_id,
                "type": notification_type.value,
                "title": title,
                "message": message,
                "priority": priority.value,
                "timestamp": datetime.now().isoformat(),
                "read": False,
                "data": data or {}
            }
            
            # Save notification to file
            notification_file = self.notifications_dir / f"{notification_id}.json"
            with open(notification_file, 'w') as f:
                json.dump(notification, f, indent=2)
                
            self.logger.info(f"Created notification: {notification_id} - {title}")
            
            # Cleanup old notifications
            self._cleanup_old_notifications()
            
            return notification_id
            
        except Exception as e:
            self.logger.error(f"Failed to create notification: {e}")
            return ""
            
    def notify_model_update_available(self, version_data: Dict[str, Any]) -> str:
        """Notify about available model update"""
        version = version_data.get('version', 'unknown')
        size_mb = round(version_data.get('size', 0) / (1024 * 1024), 1)
        
        title = "AI Model Update Available"
        message = f"New AI model version {version} is available ({size_mb} MB). The update will improve signal processing accuracy."
        
        return self.create_notification(
            NotificationType.UPDATE_AVAILABLE,
            title,
            message,
            NotificationPriority.MEDIUM,
            {"version_data": version_data, "update_type": "model"}
        )
        
    def notify_model_update_completed(self, version_data: Dict[str, Any]) -> str:
        """Notify about completed model update"""
        version = version_data.get('version', 'unknown')
        
        title = "AI Model Updated"
        message = f"AI model successfully updated to version {version}. Enhanced signal processing is now active."
        
        return self.create_notification(
            NotificationType.MODEL_UPDATE,
            title,
            message,
            NotificationPriority.HIGH,
            {"version_data": version_data, "update_type": "model", "status": "completed"}
        )
        
    def notify_model_update_failed(self, version_data: Dict[str, Any], error: str) -> str:
        """Notify about failed model update"""
        version = version_data.get('version', 'unknown')
        
        title = "Model Update Failed"
        message = f"Failed to update AI model to version {version}. Using previous version. Error: {error[:100]}"
        
        return self.create_notification(
            NotificationType.UPDATE_FAILED,
            title,
            message,
            NotificationPriority.HIGH,
            {"version_data": version_data, "error": error, "update_type": "model"}
        )
        
    def notify_app_update_available(self, version_data: Dict[str, Any]) -> str:
        """Notify about available application update"""
        version = version_data.get('version', 'unknown')
        
        title = "Application Update Available"
        message = f"SignalOS version {version} is available with new features and improvements."
        
        return self.create_notification(
            NotificationType.UPDATE_AVAILABLE,
            title,
            message,
            NotificationPriority.MEDIUM,
            {"version_data": version_data, "update_type": "application"}
        )
        
    def notify_download_progress(self, version: str, progress: float) -> str:
        """Notify about download progress"""
        title = "Downloading Update"
        message = f"Downloading version {version}: {progress:.1f}% complete"
        
        return self.create_notification(
            NotificationType.SYSTEM_INFO,
            title,
            message,
            NotificationPriority.LOW,
            {"version": version, "progress": progress, "action": "download"}
        )
        
    def notify_system_restart_required(self, version: str) -> str:
        """Notify that system restart is required"""
        title = "Restart Required"
        message = f"Please restart SignalOS to complete the update to version {version}."
        
        return self.create_notification(
            NotificationType.SYSTEM_INFO,
            title,
            message,
            NotificationPriority.CRITICAL,
            {"version": version, "action": "restart_required"}
        )
        
    def get_notifications(self, unread_only: bool = False, limit: int = 20) -> List[Dict[str, Any]]:
        """Get notifications, optionally filtered by read status"""
        try:
            notifications = []
            
            # Get all notification files
            notification_files = sorted(
                self.notifications_dir.glob("*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            for notification_file in notification_files[:limit]:
                try:
                    with open(notification_file, 'r') as f:
                        notification = json.load(f)
                        
                    if unread_only and notification.get('read', False):
                        continue
                        
                    notifications.append(notification)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load notification {notification_file}: {e}")
                    
            return notifications
            
        except Exception as e:
            self.logger.error(f"Failed to get notifications: {e}")
            return []
            
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        try:
            notification_file = self.notifications_dir / f"{notification_id}.json"
            
            if not notification_file.exists():
                return False
                
            with open(notification_file, 'r') as f:
                notification = json.load(f)
                
            notification['read'] = True
            notification['read_at'] = datetime.now().isoformat()
            
            with open(notification_file, 'w') as f:
                json.dump(notification, f, indent=2)
                
            self.logger.info(f"Marked notification as read: {notification_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to mark notification as read: {e}")
            return False
            
    def clear_notifications(self, notification_type: Optional[NotificationType] = None) -> int:
        """Clear notifications, optionally filtered by type"""
        try:
            cleared_count = 0
            
            for notification_file in self.notifications_dir.glob("*.json"):
                if notification_type:
                    # Check if notification matches type
                    try:
                        with open(notification_file, 'r') as f:
                            notification = json.load(f)
                        if notification.get('type') != notification_type.value:
                            continue
                    except:
                        continue
                        
                notification_file.unlink()
                cleared_count += 1
                
            self.logger.info(f"Cleared {cleared_count} notifications")
            return cleared_count
            
        except Exception as e:
            self.logger.error(f"Failed to clear notifications: {e}")
            return 0
            
    def _cleanup_old_notifications(self):
        """Remove old notifications to keep within limit"""
        try:
            notification_files = sorted(
                self.notifications_dir.glob("*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if len(notification_files) > self.max_notifications:
                # Remove oldest notifications
                for old_file in notification_files[self.max_notifications:]:
                    old_file.unlink()
                    
                removed_count = len(notification_files) - self.max_notifications
                self.logger.info(f"Cleaned up {removed_count} old notifications")
                
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old notifications: {e}")
            
    def get_notification_summary(self) -> Dict[str, Any]:
        """Get summary of notification status"""
        try:
            all_notifications = self.get_notifications(limit=self.max_notifications)
            unread_notifications = [n for n in all_notifications if not n.get('read', False)]
            
            # Count by type
            type_counts = {}
            priority_counts = {}
            
            for notification in all_notifications:
                ntype = notification.get('type', 'unknown')
                priority = notification.get('priority', 'medium')
                
                type_counts[ntype] = type_counts.get(ntype, 0) + 1
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
                
            return {
                "total_notifications": len(all_notifications),
                "unread_notifications": len(unread_notifications),
                "notifications_by_type": type_counts,
                "notifications_by_priority": priority_counts,
                "latest_notification": all_notifications[0] if all_notifications else None,
                "enabled": self.enabled
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get notification summary: {e}")
            return {
                "total_notifications": 0,
                "unread_notifications": 0,
                "notifications_by_type": {},
                "notifications_by_priority": {},
                "latest_notification": None,
                "enabled": self.enabled
            }
            
    def enable_notifications(self, enabled: bool = True):
        """Enable or disable notifications"""
        self.enabled = enabled
        self.logger.info(f"Notifications {'enabled' if enabled else 'disabled'}")
        
    def create_system_notification(self, title: str, message: str, data: Dict[str, Any] = None) -> str:
        """Create a system information notification"""
        return self.create_notification(
            NotificationType.SYSTEM_INFO,
            title,
            message,
            NotificationPriority.LOW,
            data
        )


# Convenience functions for external use
def notify_update_available(version_data: Dict[str, Any], update_type: str = "model") -> str:
    """Quick function to notify about available update"""
    handler = NotificationHandler()
    
    if update_type == "model":
        return handler.notify_model_update_available(version_data)
    else:
        return handler.notify_app_update_available(version_data)


def notify_update_completed(version_data: Dict[str, Any], update_type: str = "model") -> str:
    """Quick function to notify about completed update"""
    handler = NotificationHandler()
    
    if update_type == "model":
        return handler.notify_model_update_completed(version_data)
    else:
        return handler.create_notification(
            NotificationType.APP_UPDATE,
            "Application Updated",
            f"SignalOS updated to version {version_data.get('version', 'unknown')}",
            NotificationPriority.HIGH,
            {"version_data": version_data, "update_type": "application"}
        )


def get_unread_notifications() -> List[Dict[str, Any]]:
    """Get all unread notifications"""
    handler = NotificationHandler()
    return handler.get_notifications(unread_only=True)


# Main function for testing
def main():
    """Test the notification handler"""
    print("🔔 Testing SignalOS Notification Handler")
    print("=" * 50)
    
    handler = NotificationHandler()
    
    # Create test notifications
    print("📝 Creating test notifications...")
    
    # Model update available
    mock_version_data = {
        "version": "2.1.0",
        "size": 157286400,
        "model_url": "https://api.signalojs.com/models/test.tar.gz"
    }
    
    n1 = handler.notify_model_update_available(mock_version_data)
    print(f"   ✅ Model update available: {n1}")
    
    # Model update completed
    n2 = handler.notify_model_update_completed(mock_version_data)
    print(f"   ✅ Model update completed: {n2}")
    
    # System notification
    n3 = handler.create_system_notification("Test", "This is a test notification")
    print(f"   ✅ System notification: {n3}")
    
    # Get notification summary
    summary = handler.get_notification_summary()
    print(f"\n📊 Notification Summary:")
    print(f"   Total: {summary['total_notifications']}")
    print(f"   Unread: {summary['unread_notifications']}")
    print(f"   By type: {summary['notifications_by_type']}")
    
    # Get recent notifications
    recent = handler.get_notifications(limit=5)
    print(f"\n📋 Recent notifications: {len(recent)}")
    for notification in recent:
        print(f"   - {notification['title']} ({notification['type']})")
        
    print(f"\n✅ Notification handler testing complete")


if __name__ == "__main__":
    main()