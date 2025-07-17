#!/usr/bin/env python3
"""
Start script for SignalOS Desktop Application

This script starts the SignalOS desktop application with proper
Python environment and module loading.
"""

import sys
import asyncio
from pathlib import Path

# Add desktop-app directory to Python path
desktop_app_dir = Path(__file__).parent / "desktop-app"
sys.path.insert(0, str(desktop_app_dir))

# Import and run the main application
from main import main

if __name__ == "__main__":
    print("Starting SignalOS Desktop Application...")
    asyncio.run(main())