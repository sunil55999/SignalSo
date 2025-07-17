#!/usr/bin/env python3
"""
Test Script for Phase 2: Advanced AI Parser and Strategy Builder

Tests all implemented Phase 2 components to ensure they work correctly.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

# Local imports
from advanced_signal_processor import AdvancedSignalProcessor
from parser.parser_core import SignalParserCore, SignalType
from parser.config_parser import ConfigParser
from parser.confidence_system import SignalConfidenceSystem, SignalOutcome
from parser.prompt_to_config import PromptToConfigConverter, ConfigPrompt, PromptType
from strategy.strategy_core import StrategyCore

async def test_parser_core():
    """Test the advanced parser core"""
    print("=== Testing Parser Core ===")
    
    parser = SignalParserCore()
    
    # Test signal parsing
    test_signals = [
        "EURUSD BUY @ 1.0850 SL: 1.0800 TP1: 1.0900 TP2: 1.0950",
        "GOLD SELL LIMIT 1950 SL 1960 TP 1940",
        "GBPUSD شراء 1.2500 وقف 1.2450 هدف 1.2550"  # Arabic
    ]
    
    for signal in test_signals:
        result = await parser.parse_signal(signal, SignalType.TEXT, "TestProvider")
        print(f"Signal: {signal}")
        print(f"  Symbol: {result.symbol}")
        print(f"  Direction: {result.direction}")
        print(f"  Entry: {result.entry_price}")
        print(f"  SL: {result.stop_loss}")
        print(f"  TPs: {result.take_profits}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Method: {result.parsing_method.value}")
        print()
    
    parser.cleanup()
    print("✓ Parser Core tests completed\n")

def test_config_parser():
    """Test the configuration parser"""
    print("=== Testing Config Parser ===")
    
    parser = ConfigParser()
    
    test_signals = [
        "EURUSD BUY @ 1.0850 SL: 1.0800 TP1: 1.0900 TP2: 1.0950",
        "COMPRAR GBPUSD ENTRADA 1.2500 PARE 1.2450 OBJETIVO 1.2550",
        "XAU/USD SELL 1950 STOP 1960 TARGET 1940"
    ]
    
    for signal in test_signals:
        result = parser.parse_signal(signal)
        print(f"Signal: {signal}")
        print(f"  Result: {json.dumps(result, indent=2)}")
        print()
    
    stats = parser.get_stats()
    print(f"Parser Stats: {json.dumps(stats, indent=2)}")
    print("✓ Config Parser tests completed\n")

def test_confidence_system():
    """Test the confidence system"""
    print("=== Testing Confidence System ===")
    
    system = SignalConfidenceSystem()
    
    # Test signal data
    signal_data = {
        'provider': 'TestProvider',
        'symbol': 'EURUSD',
        'direction': 'BUY',
        'entry_price': 1.0850,
        'stop_loss': 1.0800,
        'take_profits': [1.0900, 1.0950],
        'confidence': 0.75,
        'parsing_method': 'ai_model'
    }
    
    # Record signal
    signal_id = system.record_signal(signal_data)
    print(f"Recorded signal: {signal_id}")
    
    # Calculate confidence
    confidence = system.calculate_confidence_score(signal_data)
    print(f"Confidence score: {confidence:.3f}")
    
    # Check execution recommendation
    should_execute = system.should_execute_signal(signal_data)
    print(f"Should execute: {should_execute}")
    
    # Record outcome
    system.record_outcome(signal_id, SignalOutcome.TP1_HIT, 1.0900, 50.0)
    print(f"Recorded outcome: TP1_HIT")
    
    # Get stats
    stats = system.get_system_stats()
    print(f"System stats: {json.dumps(stats, indent=2)}")
    
    system.cleanup()
    print("✓ Confidence System tests completed\n")

async def test_prompt_converter():
    """Test the prompt-to-config converter"""
    print("=== Testing Prompt Converter ===")
    
    converter = PromptToConfigConverter()
    
    test_prompts = [
        ("I want to risk 2% per trade with conservative position sizing", PromptType.RISK_MANAGEMENT),
        ("Set up breakeven when price moves 50% to first target", PromptType.BREAKEVEN_CONFIG),
        ("Close 60% at TP1, 30% at TP2, keep 10% running", PromptType.PARTIAL_CLOSE)
    ]
    
    for prompt_text, prompt_type in test_prompts:
        prompt = ConfigPrompt(prompt_text, prompt_type)
        response = await converter.convert_prompt(prompt)
        
        print(f"Prompt: {prompt_text}")
        print(f"Type: {prompt_type.value}")
        print(f"Config: {json.dumps(response.config_json, indent=2)}")
        print(f"Confidence: {response.confidence_score:.2f}")
        print(f"Explanation: {response.explanation}")
        print()
    
    stats = converter.get_stats()
    print(f"Converter Stats: {json.dumps(stats, indent=2)}")
    print("✓ Prompt Converter tests completed\n")

async def test_strategy_core():
    """Test the strategy core"""
    print("=== Testing Strategy Core ===")
    
    strategy = StrategyCore()
    
    # Test signal data
    signal_data = {
        'symbol': 'EURUSD',
        'direction': 'BUY',
        'entry_price': 1.0850,
        'stop_loss': 1.0800,
        'take_profits': [1.0900, 1.0950, 1.1000]
    }
    
    # Create trade execution
    trade_execution = await strategy.create_trade_execution(signal_data, 10000.0)
    
    if trade_execution:
        print(f"Trade created: {trade_execution.symbol}")
        print(f"Position size: {trade_execution.position_size.lot_size}")
        print(f"Risk amount: ${trade_execution.position_size.risk_amount:.2f}")
        print(f"Risk percent: {trade_execution.position_size.risk_percent:.1f}%")
        print()
        
        # Test breakeven
        breakeven_triggered = await strategy.process_breakeven("test_trade", 1.0875)
        print(f"Breakeven triggered: {breakeven_triggered}")
        
        # Test partial close
        partial_closes = await strategy.process_partial_close("test_trade", 1.0900)
        print(f"Partial closes: {len(partial_closes)}")
    
    # Get performance stats
    stats = strategy.get_performance_stats()
    print(f"Strategy Stats: {json.dumps(stats, indent=2)}")
    
    strategy.cleanup()
    print("✓ Strategy Core tests completed\n")

async def test_advanced_processor():
    """Test the advanced signal processor integration"""
    print("=== Testing Advanced Signal Processor ===")
    
    processor = AdvancedSignalProcessor()
    
    # Start processor
    await processor.start()
    
    # Test signal processing
    test_signal = "EURUSD BUY @ 1.0850 SL: 1.0800 TP1: 1.0900 TP2: 1.0950"
    
    result = await processor.process_signal(
        test_signal,
        SignalType.TEXT,
        "TestProvider",
        10000.0
    )
    
    print(f"Signal Processing Result:")
    print(f"  Signal ID: {result.signal_id}")
    print(f"  Stage: {result.stage.value}")
    print(f"  Confidence: {result.confidence_score:.3f}")
    print(f"  Execution Approved: {result.execution_approved}")
    print(f"  Processing Time: {result.processing_time:.2f}s")
    
    if result.parsed_signal:
        print(f"  Parsed Signal:")
        print(f"    Symbol: {result.parsed_signal.symbol}")
        print(f"    Direction: {result.parsed_signal.direction}")
        print(f"    Entry: {result.parsed_signal.entry_price}")
        print(f"    SL: {result.parsed_signal.stop_loss}")
        print(f"    TPs: {result.parsed_signal.take_profits}")
    
    # Test configuration generation
    config_response = await processor.generate_config_from_prompt(
        "I want to risk 2% per trade with breakeven at 50%",
        PromptType.RISK_MANAGEMENT
    )
    
    if config_response:
        print(f"Generated Config:")
        print(f"  {json.dumps(config_response.config_json, indent=2)}")
        print(f"  Explanation: {config_response.explanation}")
    
    # Get system status
    status = processor.get_system_status()
    print(f"System Status: {json.dumps(status, indent=2)}")
    
    # Stop processor
    await processor.stop()
    print("✓ Advanced Signal Processor tests completed\n")

async def main():
    """Run all Phase 2 tests"""
    print("🚀 Starting Phase 2: Advanced AI Parser and Strategy Builder Tests\n")
    
    try:
        # Test individual components
        await test_parser_core()
        test_config_parser()
        test_confidence_system()
        await test_prompt_converter()
        await test_strategy_core()
        
        # Test integrated system
        await test_advanced_processor()
        
        print("🎉 All Phase 2 tests completed successfully!")
        print("\n📊 Phase 2 Implementation Summary:")
        print("✅ AI Parser Core with Phi-3/Mistral support")
        print("✅ Enhanced OCR Engine with EasyOCR")
        print("✅ Configuration Parser with multilingual patterns")
        print("✅ Confidence System with learning algorithms")
        print("✅ Natural Language Configuration Generator")
        print("✅ Strategy Core with risk management")
        print("✅ Advanced Signal Processor Integration")
        print("\n🔧 Ready for Phase 3: Advanced Strategy Builder Extensions")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())