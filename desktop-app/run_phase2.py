#!/usr/bin/env python3
"""
Quick launcher for Phase 2: Advanced AI Parser and Strategy Builder
"""

import subprocess
import sys
import os

def main():
    """Run the Phase 2 implementation"""
    os.chdir('desktop-app')
    subprocess.run([sys.executable, 'main.py'])

if __name__ == "__main__":
    main()