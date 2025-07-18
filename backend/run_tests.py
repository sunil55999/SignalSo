#!/usr/bin/env python3
"""
Test runner for SignalOS backend audit-required features
"""

import pytest
import sys
import os
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

def run_tests():
    """Run all tests for audit-required features"""
    
    print("🔍 SignalOS Backend Audit Test Suite")
    print("="*50)
    
    # Test files to run
    test_files = [
        "tests/test_offline.py",
        "tests/test_marketplace.py", 
        "tests/test_compliance.py",
        "tests/test_onboarding.py",
        "tests/test_two_factor_auth.py",
        "tests/test_integration.py"
    ]
    
    # Check if test files exist
    missing_files = []
    for test_file in test_files:
        if not os.path.exists(test_file):
            missing_files.append(test_file)
    
    if missing_files:
        print(f"❌ Missing test files: {', '.join(missing_files)}")
        return False
    
    # Run pytest with coverage
    args = [
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "-x",  # Stop on first failure
        "--disable-warnings",  # Disable pytest warnings
        *test_files
    ]
    
    print(f"🚀 Running tests: {', '.join(test_files)}")
    print("-" * 50)
    
    # Run the tests
    result = pytest.main(args)
    
    print("-" * 50)
    if result == 0:
        print("✅ All tests passed!")
        return True
    else:
        print(f"❌ Tests failed with exit code: {result}")
        return False

def check_dependencies():
    """Check if all required dependencies are installed"""
    
    print("📦 Checking dependencies...")
    
    required_packages = [
        "pytest",
        "pytest-asyncio",
        "fastapi",
        "pyotp",
        "qrcode",
        "pillow"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n🔧 Install missing packages: pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ All dependencies installed")
    return True

def main():
    """Main test runner"""
    
    print("🧪 SignalOS Backend Audit Test Suite")
    print("=" * 60)
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    
    # Run tests
    if run_tests():
        print("\n🎉 All audit-required features tested successfully!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Please check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()