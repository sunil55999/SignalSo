#!/usr/bin/env python3
"""
Main Entry Point for SignalOS Desktop Application
Phase 2: Advanced AI Parser and Strategy Builder

This is the main entry point that demonstrates the Phase 2 implementation
with advanced AI parsing, OCR support, confidence scoring, and strategy management.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add the desktop-app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/main.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import Phase 2 components
from advanced_signal_processor import AdvancedSignalProcessor
from parser.parser_core import SignalType
from parser.prompt_to_config import PromptType

class SignalOSApp:
    """Main SignalOS Desktop Application"""
    
    def __init__(self):
        self.processor = AdvancedSignalProcessor()
        self.is_running = False
        logger.info("SignalOS Desktop Application initialized")
    
    async def start(self):
        """Start the application"""
        logger.info("🚀 Starting SignalOS Desktop Application - Phase 2")
        
        try:
            # Start the advanced signal processor
            await self.processor.start()
            self.is_running = True
            
            # Display system status
            await self.display_system_status()
            
            # Run demonstration
            await self.run_demonstration()
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            raise
    
    async def stop(self):
        """Stop the application"""
        logger.info("🛑 Stopping SignalOS Desktop Application")
        
        self.is_running = False
        await self.processor.stop()
    
    async def display_system_status(self):
        """Display system status and capabilities"""
        print("\n" + "="*80)
        print("🎯 SignalOS Desktop Application - Phase 2: Advanced AI Parser & Strategy Builder")
        print("="*80)
        
        status = self.processor.get_system_status()
        
        print(f"📊 System Status: {'🟢 Running' if status['running'] else '🔴 Stopped'}")
        print(f"🔧 Components Status:")
        
        for component, active in status['components'].items():
            status_icon = "✅" if active else "❌"
            component_name = component.replace('_', ' ').title()
            print(f"   {status_icon} {component_name}")
        
        print(f"\n📈 Processing Statistics:")
        stats = status['processing_stats']
        print(f"   Total Processed: {stats['total_processed']}")
        print(f"   Successful: {stats['successful_processing']}")
        print(f"   Failed: {stats['failed_processing']}")
        print(f"   Average Time: {stats['avg_processing_time']:.2f}s")
        
        print("\n🔍 Phase 2 Features:")
        print("   ✅ AI Parser Core (Phi-3/Mistral + Regex Fallback)")
        print("   ✅ Enhanced OCR Engine (EasyOCR + Multilingual)")
        print("   ✅ Confidence System (Learning + Provider Analytics)")
        print("   ✅ Strategy Core (Risk Management + Breakeven + Partial Close)")
        print("   ✅ Natural Language Config Generator")
        print("   ✅ Advanced Signal Processor Integration")
        
        print("\n" + "="*80)
    
    async def run_demonstration(self):
        """Run Phase 2 demonstration"""
        print("\n🎮 Running Phase 2 Demonstration...\n")
        
        # Demo signals
        demo_signals = [
            {
                'signal': "EURUSD BUY @ 1.0850 SL: 1.0800 TP1: 1.0900 TP2: 1.0950",
                'provider': "ForexSignals",
                'description': "Classic forex signal with multiple TPs"
            },
            {
                'signal': "GOLD SELL LIMIT 1950 SL 1960 TP 1940",
                'provider': "GoldTrader",
                'description': "Gold trading signal with limit order"
            },
            {
                'signal': "GBPUSD شراء 1.2500 وقف 1.2450 هدف 1.2550",
                'provider': "ArabicSignals",
                'description': "Arabic language signal (Buy GBPUSD)"
            }
        ]
        
        # Process demo signals
        for i, demo in enumerate(demo_signals, 1):
            print(f"📡 Demo Signal {i}: {demo['description']}")
            print(f"   Provider: {demo['provider']}")
            print(f"   Signal: {demo['signal']}")
            
            # Process the signal
            result = await self.processor.process_signal(
                demo['signal'],
                SignalType.TEXT,
                demo['provider'],
                10000.0  # $10,000 account balance
            )
            
            print(f"   📊 Processing Result:")
            print(f"      Signal ID: {result.signal_id}")
            print(f"      Stage: {result.stage.value}")
            print(f"      Confidence: {result.confidence_score:.3f}")
            print(f"      Execution Approved: {'✅' if result.execution_approved else '❌'}")
            print(f"      Processing Time: {result.processing_time:.2f}s")
            
            if result.parsed_signal:
                print(f"      Parsed Data:")
                print(f"         Symbol: {result.parsed_signal.symbol}")
                print(f"         Direction: {result.parsed_signal.direction}")
                print(f"         Entry: {result.parsed_signal.entry_price}")
                print(f"         Stop Loss: {result.parsed_signal.stop_loss}")
                print(f"         Take Profits: {result.parsed_signal.take_profits}")
                print(f"         Parsing Method: {result.parsed_signal.parsing_method.value}")
            
            if result.trade_execution:
                print(f"      Trade Execution:")
                print(f"         Position Size: {result.trade_execution.position_size.lot_size}")
                print(f"         Risk Amount: ${result.trade_execution.position_size.risk_amount:.2f}")
                print(f"         Risk Percent: {result.trade_execution.position_size.risk_percent:.1f}%")
            
            print()
        
        # Demo natural language configuration
        print("🗣️ Natural Language Configuration Demo:")
        
        config_prompts = [
            ("I want to risk 2% per trade with conservative position sizing", PromptType.RISK_MANAGEMENT),
            ("Set up breakeven when price moves 50% to first target", PromptType.BREAKEVEN_CONFIG),
            ("Close 60% at TP1, 30% at TP2, keep 10% running", PromptType.PARTIAL_CLOSE)
        ]
        
        for prompt_text, prompt_type in config_prompts:
            print(f"   💬 Prompt: {prompt_text}")
            
            response = await self.processor.generate_config_from_prompt(prompt_text, prompt_type)
            
            if response:
                print(f"   📝 Generated Config:")
                print(f"      {json.dumps(response.config_json, indent=6)}")
                print(f"   📖 Explanation: {response.explanation}")
                print(f"   🎯 Confidence: {response.confidence_score:.2f}")
                
                if response.warnings:
                    print(f"   ⚠️  Warnings: {', '.join(response.warnings)}")
                
                if response.suggestions:
                    print(f"   💡 Suggestions: {', '.join(response.suggestions)}")
            else:
                print("   ❌ Failed to generate configuration")
            
            print()
        
        # Display final statistics
        print("📊 Final System Statistics:")
        stats = self.processor.get_processing_stats()
        print(f"   Parser Success Rate: {stats.get('parser_stats', {}).get('success_rate', 0):.1%}")
        print(f"   AI Parse Rate: {stats.get('parser_stats', {}).get('ai_success_rate', 0):.1%}")
        print(f"   Cache Hit Rate: {stats.get('parser_stats', {}).get('cache_hit_rate', 0):.1%}")
        
        if 'confidence_stats' in stats:
            conf_stats = stats['confidence_stats']
            print(f"   Confidence System: {conf_stats.get('total_signals', 0)} signals tracked")
            print(f"   Win Rate: {conf_stats.get('win_rate', 0):.1%}")
        
        print("\n🎉 Phase 2 demonstration completed successfully!")

async def main():
    """Main application entry point"""
    app = SignalOSApp()
    
    try:
        await app.start()
        
        # Keep the application running
        print("\n💤 Application is running. Press Ctrl+C to stop.")
        
        while app.is_running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Application error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await app.stop()

if __name__ == "__main__":
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Run the application
    asyncio.run(main())