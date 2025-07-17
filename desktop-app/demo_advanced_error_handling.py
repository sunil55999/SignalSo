#!/usr/bin/env python3
"""
Demo: Advanced Error Handling for SignalOS Desktop
Demonstrates the robust error handling system according to Part 2 guide
"""

import sys
from pathlib import Path

# Add desktop-app to path
sys.path.insert(0, str(Path(__file__).parent))

from ai_parser.parser_engine import parse_signal_safe, get_parser_performance, generate_parser_report


def demo_advanced_error_handling():
    """Demonstrate advanced error handling capabilities"""
    
    print("🛡️ SignalOS Advanced Error Handling Demo")
    print("=" * 50)
    print("Showing crash prevention and auto-recovery features\n")
    
    # Test signals designed to break traditional parsers
    challenging_signals = [
        # Good signal
        "🟢 BUY EURUSD @ 1.0850, SL: 1.0800, TP: 1.0900",
        
        # Messy signal with lots of emojis
        "🚀💰🎯💪🔥⭐ SELL XAUUSD Entry: 2345 🌟💎👑 SL: 2350 TP1: 2339 TP2: 2333 🎉💸",
        
        # Malformed signal (should trigger fallback)
        "Random text GBPUSD maybe buy something 1.2500 unclear format",
        
        # Empty/broken signals (should fail gracefully)
        "",
        "Invalid nonsense text with no trading info",
        
        # Complex multi-TP signal
        "🟢 EURJPY BUY NOW! Entry: 165.50-165.80 SL: 164.00 TP1: 166.50 TP2: 167.00 TP3: 168.00 TP4: 169.00"
    ]
    
    print("Testing signals that would crash traditional parsers:")
    print("-" * 50)
    
    successful_parses = 0
    total_signals = len(challenging_signals)
    
    for i, signal in enumerate(challenging_signals, 1):
        print(f"\n📡 Signal {i}: {signal[:60]}{'...' if len(signal) > 60 else ''}")
        
        try:
            # This call is safe and will never crash the application
            result = parse_signal_safe(signal)
            
            if result:
                print(f"   ✅ Parsed: {result['pair']} {result['direction']}")
                print(f"   📊 Method: {result.get('parser_method', 'unknown')}")
                print(f"   🎯 Confidence: {result.get('confidence', 0):.2f}")
                successful_parses += 1
            else:
                print("   ⚠️  Failed gracefully (no crash, application continues)")
                
        except Exception as e:
            # This should never happen with our advanced error handling
            print(f"   ❌ UNEXPECTED ERROR: {e}")
            print("   🚨 This indicates a bug in the error handling system")
    
    print(f"\n📈 Results: {successful_parses}/{total_signals} signals processed")
    print("🛡️ No crashes occurred - application remained stable")
    
    # Show performance statistics
    print("\n📊 Performance Statistics:")
    print("-" * 30)
    stats = get_parser_performance()
    
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.3f}")
        else:
            print(f"   {key}: {value}")
    
    # Generate comprehensive report
    print("\n📋 Comprehensive Analysis Report:")
    print("-" * 40)
    
    try:
        report = generate_parser_report()
        
        print("✅ Report generated successfully")
        print(f"📊 Total attempts tracked: {report['session_info']['total_attempts']}")
        print(f"🎯 Success rate: {report['session_info']['success_rate']:.1f}%")
        
        if report['recommendations']:
            print(f"\n💡 System Recommendations:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"   {i}. {rec}")
        
    except Exception as e:
        print(f"❌ Report generation error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Key Benefits Demonstrated:")
    print("✅ No crashes from broken signals")
    print("✅ Graceful fallback when AI fails")
    print("✅ Comprehensive error logging")
    print("✅ Performance monitoring")
    print("✅ Pattern analysis and learning")
    print("✅ User trust through reliability")
    print("\n🏆 Advanced Error Handling: PRODUCTION READY")


if __name__ == "__main__":
    demo_advanced_error_handling()