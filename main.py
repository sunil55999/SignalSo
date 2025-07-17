#!/usr/bin/env python3
"""
SignalOS - Trading Automation Desktop Application
Entry point for the SignalOS trading automation system.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the desktop-app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "desktop-app"))

def main():
    """Main entry point for SignalOS desktop application."""
    print("🚀 SignalOS Trading Automation Platform")
    print("=" * 50)
    
    # Check if desktop-app directory exists
    desktop_app_dir = Path(__file__).parent / "desktop-app"
    if not desktop_app_dir.exists():
        print("❌ Error: desktop-app directory not found!")
        return 1
    
    print(f"📁 Desktop app directory: {desktop_app_dir}")
    print(f"🐍 Python version: {sys.version}")
    print(f"📂 Current directory: {os.getcwd()}")
    
    # List available modules
    print("\n📋 Available modules:")
    python_files = list(desktop_app_dir.glob("*.py"))
    for py_file in sorted(python_files):
        if not py_file.name.startswith("test_"):
            print(f"   • {py_file.name}")
    
    print(f"\n✅ Found {len(python_files)} Python modules")
    print(f"🔧 Configuration files:")
    
    config_files = list(desktop_app_dir.glob("*.json")) + list(desktop_app_dir.glob("config/*.json"))
    for config_file in config_files:
        print(f"   • {config_file.relative_to(desktop_app_dir)}")
    
    print("\n💡 To run specific modules, use:")
    print("   python desktop-app/parser.py")
    print("   python desktop-app/mt5_bridge.py")
    print("   python desktop-app/strategy_runtime.py")
    
    return 0

if __name__ == "__main__":
    exit(main())