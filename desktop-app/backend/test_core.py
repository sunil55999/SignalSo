#!/usr/bin/env python3
"""
Test core functionality without complex dependencies
"""

import sys
import asyncio
from pathlib import Path

# Add desktop-app directory to Python path
desktop_app_dir = Path(__file__).parent / "desktop-app"
sys.path.insert(0, str(desktop_app_dir))

async def test_jwt_system():
    """Test JWT license system"""
    print("Testing JWT License System...")
    try:
        from auth.jwt_license_system import JWTLicenseSystem
        jwt_system = JWTLicenseSystem()
        status = jwt_system.get_license_status()
        print(f"✓ JWT License System loaded successfully")
        print(f"  Status: {status['status']}")
        return True
    except Exception as e:
        print(f"✗ JWT License System failed: {e}")
        return False

async def test_auto_updater():
    """Test auto updater"""
    print("Testing Auto Updater...")
    try:
        from updater.auto_updater import AutoUpdater
        updater = AutoUpdater()
        progress = updater.get_update_progress()
        print(f"✓ Auto Updater loaded successfully")
        print(f"  Status: {progress['status']}")
        return True
    except Exception as e:
        print(f"✗ Auto Updater failed: {e}")
        return False

async def test_multilingual_parser():
    """Test multilingual parser"""
    print("Testing Multilingual Parser...")
    try:
        from parser.multilingual_parser import MultilingualSignalParser
        parser = MultilingualSignalParser()
        
        # Test parsing a simple signal
        test_signal = "Buy EURUSD at 1.1200, SL: 1.1150, TP: 1.1250"
        result = parser.parse_signal(test_signal)
        
        print(f"✓ Multilingual Parser loaded successfully")
        print(f"  Detected language: {result.detected_language}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Parsed symbol: {result.parsed_data.get('symbol')}")
        return True
    except Exception as e:
        print(f"✗ Multilingual Parser failed: {e}")
        return False

async def test_prop_firm_mode():
    """Test prop firm mode"""
    print("Testing Prop Firm Mode...")
    try:
        from strategy.prop_firm_mode import PropFirmMode
        prop_firm = PropFirmMode()
        status = prop_firm.get_status()
        print(f"✓ Prop Firm Mode loaded successfully")
        print(f"  Active: {status['active']}")
        return True
    except Exception as e:
        print(f"✗ Prop Firm Mode failed: {e}")
        return False

async def test_mt5_bridge():
    """Test MT5 bridge"""
    print("Testing MT5 Bridge...")
    try:
        from trade.mt5_socket_bridge import MT5SocketBridge
        bridge = MT5SocketBridge()
        stats = bridge.get_statistics()
        print(f"✓ MT5 Bridge loaded successfully")
        print(f"  MT5 available: {stats['configuration']['mt5_available']}")
        return True
    except Exception as e:
        print(f"✗ MT5 Bridge failed: {e}")
        return False

async def test_telegram_auth():
    """Test Telegram authentication"""
    print("Testing Telegram Auth...")
    try:
        from auth.telegram_auth import TelegramAuth
        auth = TelegramAuth()
        status = auth.get_auth_status()
        print(f"✓ Telegram Auth loaded successfully")
        print(f"  Configured: {status['configured']}")
        print(f"  Telethon available: {status['telethon_available']}")
        return True
    except Exception as e:
        print(f"✗ Telegram Auth failed: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 60)
    print("SignalOS Desktop Application - Core Features Test")
    print("=" * 60)
    
    tests = [
        test_jwt_system,
        test_auto_updater,
        test_multilingual_parser,
        test_prop_firm_mode,
        test_mt5_bridge,
        test_telegram_auth
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
        print()
    
    print("=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All core features loaded successfully!")
        print("The SignalOS Desktop Application is ready for deployment.")
    else:
        print(f"\n⚠️  {total-passed} tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())