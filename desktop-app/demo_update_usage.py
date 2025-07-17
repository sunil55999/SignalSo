#!/usr/bin/env python3
"""
Demo: How to Use SignalOS Auto-Update Pusher System
Simple examples showing how to integrate auto-updates into your application
"""

import asyncio
from pathlib import Path

# Import the auto-update system components
from updater.model_updater import check_model_updates, download_model_update, get_current_model_version
from updater.version_manager import compare_model_versions, fetch_latest_version
from updater.notification_handler import notify_update_available, get_unread_notifications
from updater.update_scheduler import start_auto_updates, stop_auto_updates, force_update_check, get_update_status


async def demo_basic_update_check():
    """Demo: Basic update checking"""
    print("📋 Demo: Basic Update Check")
    print("-" * 40)
    
    # Get current model version
    current_version = get_current_model_version()
    print(f"Current model version: {current_version}")
    
    # Check for updates
    update_available, remote_data = await check_model_updates()
    
    if update_available:
        new_version = remote_data.get('version', 'unknown')
        print(f"✅ Update available: {current_version} -> {new_version}")
        
        # Notify user about update
        notification_id = notify_update_available(remote_data, "model")
        print(f"📢 Notification created: {notification_id}")
        
    else:
        print("✅ Model is up to date")


async def demo_manual_update():
    """Demo: Manual update download and installation"""
    print("\n📥 Demo: Manual Update Process")
    print("-" * 40)
    
    # Simulate a manual update with a test URL
    test_model_url = "https://api.signalojs.com/models/test_model.tar.gz"
    test_checksum = "abc123def456"
    
    print(f"Downloading model from: {test_model_url}")
    
    # This would download and install the model
    # success = await download_model_update(test_model_url, test_checksum)
    # print(f"Update result: {'✅ Success' if success else '❌ Failed'}")
    
    print("📝 Note: In production, this would download and extract the model")


def demo_version_comparison():
    """Demo: Version comparison utilities"""
    print("\n🔍 Demo: Version Comparison")
    print("-" * 40)
    
    test_versions = [
        ("1.0.0", "1.0.1"),
        ("2.1.0", "2.0.5"),
        ("1.5.0-beta", "1.5.0"),
        ("3.0.0", "3.0.0")
    ]
    
    for current, new in test_versions:
        is_newer = compare_model_versions(current, new)
        result = "🔄 Update needed" if is_newer else "✅ Up to date"
        print(f"   {current} vs {new}: {result}")


async def demo_auto_scheduler():
    """Demo: Automatic update scheduling"""
    print("\n⏰ Demo: Automatic Update Scheduling")
    print("-" * 40)
    
    # Get current scheduler status
    status = get_update_status()
    print("Scheduler Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Force an immediate update check
    print("\nForcing update check...")
    try:
        result = await force_update_check()
        print(f"Update check result: {'✅ Found updates' if result else '✅ No updates'}")
    except Exception as e:
        print(f"Update check: {str(e)[:50]}...")


def demo_notifications():
    """Demo: Notification management"""
    print("\n🔔 Demo: Notification Management")
    print("-" * 40)
    
    # Get unread notifications
    unread_notifications = get_unread_notifications()
    print(f"Unread notifications: {len(unread_notifications)}")
    
    for notification in unread_notifications[:3]:  # Show first 3
        print(f"   📢 {notification['title']}: {notification['message'][:50]}...")


async def demo_production_usage():
    """Demo: How to integrate in production application"""
    print("\n🚀 Demo: Production Integration Example")
    print("-" * 40)
    
    print("""
# In your main application startup:

from updater.update_scheduler import start_auto_updates, configure_auto_updates

async def startup():
    # Configure auto-updates
    configure_auto_updates(
        check_interval_hours=6,        # Check every 6 hours
        auto_update_enabled=True,      # Auto-download updates
        update_window_start="02:00",   # Update between 2-6 AM
        update_window_end="06:00"
    )
    
    # Start automatic update checking
    await start_auto_updates()
    print("✅ Auto-updates started")

# In your application shutdown:

from updater.update_scheduler import stop_auto_updates

def shutdown():
    stop_auto_updates()
    print("✅ Auto-updates stopped")

# For manual update checks (e.g., user clicks "Check for Updates"):

from updater.model_updater import check_model_updates

async def manual_update_check():
    update_available, remote_data = await check_model_updates()
    if update_available:
        version = remote_data.get('version')
        return f"Update available: {version}"
    else:
        return "No updates available"

# For getting current model version (e.g., in about dialog):

from updater.model_updater import get_current_model_version

def get_app_info():
    model_version = get_current_model_version()
    return f"AI Model Version: {model_version}"
""")


async def main():
    """Run all demos"""
    print("🤖 SignalOS Auto-Update Pusher - Usage Examples")
    print("=" * 60)
    
    # Create required directories
    Path("models").mkdir(exist_ok=True)
    Path("notifications").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Run demos
    await demo_basic_update_check()
    await demo_manual_update()
    demo_version_comparison()
    await demo_auto_scheduler()
    demo_notifications()
    await demo_production_usage()
    
    print("\n" + "=" * 60)
    print("✅ All demos completed!")
    print("📚 Check the individual files in updater/ for more details")
    print("🔧 Modify config/model_config.json and config/scheduler_config.json for your setup")


if __name__ == "__main__":
    asyncio.run(main())