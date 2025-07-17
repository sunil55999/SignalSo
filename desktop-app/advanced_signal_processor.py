#!/usr/bin/env python3
"""
Advanced Signal Processor Integration Module for SignalOS Desktop Application

Main integration module that orchestrates the Advanced AI Parser and Strategy Builder.
Coordinates between parser_core, strategy_core, confidence_system, and OCR engine.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Local imports
from parser.parser_core import SignalParserCore, ParsedSignalAdvanced, SignalType
from parser.config_parser import ConfigParser
from parser.confidence_system import SignalConfidenceSystem, SignalOutcome
from parser.ocr_engine import OCREngine
from parser.prompt_to_config import PromptToConfigConverter, ConfigPrompt, PromptType
from strategy.strategy_core import StrategyCore, TradeExecution
from strategy.prop_firm_mode import PropFirmMode

class ProcessingStage(Enum):
    """Signal processing stages"""
    RECEIVED = "received"
    PARSING = "parsing"
    CONFIDENCE_SCORING = "confidence_scoring"
    STRATEGY_EVALUATION = "strategy_evaluation"
    EXECUTION_PLANNING = "execution_planning"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class SignalProcessingResult:
    """Complete signal processing result"""
    # Input data
    raw_input: Union[str, bytes]
    input_type: SignalType
    provider: Optional[str] = None
    
    # Processing stages
    stage: ProcessingStage = ProcessingStage.RECEIVED
    processing_time: float = 0.0
    
    # Parsing results
    parsed_signal: Optional[ParsedSignalAdvanced] = None
    parsing_errors: List[str] = None
    
    # Confidence scoring
    confidence_score: float = 0.0
    confidence_level: str = "unknown"
    should_execute: bool = False
    
    # Strategy evaluation
    trade_execution: Optional[TradeExecution] = None
    strategy_warnings: List[str] = None
    
    # Execution decision
    execution_approved: bool = False
    execution_reason: str = ""
    
    # Metadata
    signal_id: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.parsing_errors is None:
            self.parsing_errors = []
        if self.strategy_warnings is None:
            self.strategy_warnings = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

class AdvancedSignalProcessor:
    """Advanced signal processor integration module"""
    
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/advanced_processor.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Initialize core components
        self.parser_core = SignalParserCore(config_file)
        self.config_parser = ConfigParser(config_file)
        self.confidence_system = SignalConfidenceSystem(config_file)
        self.strategy_core = StrategyCore(config_file)
        self.ocr_engine = OCREngine(config_file) if self.config.get('enable_ocr', True) else None
        self.prompt_converter = PromptToConfigConverter(config_file)
        
        # Processing queue
        self.processing_queue = asyncio.Queue()
        self.active_processors = {}
        self.processing_stats = {
            "total_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "avg_processing_time": 0.0,
            "stage_performance": {stage.value: 0 for stage in ProcessingStage}
        }
        
        # Background tasks
        self.processor_task = None
        self.is_running = False
        
        self.logger.info("Advanced signal processor initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load processor configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('advanced_processor', {
                    'enable_ocr': True,
                    'enable_confidence_scoring': True,
                    'enable_strategy_evaluation': True,
                    'auto_execution_threshold': 0.8,
                    'max_concurrent_processing': 5,
                    'processing_timeout': 120,
                    'log_all_signals': True
                })
        except Exception as e:
            logging.warning(f"Failed to load config: {e}")
            return {'enable_ocr': True, 'enable_confidence_scoring': True}
    
    def _setup_logging(self):
        """Setup logging"""
        self.logger = logging.getLogger('AdvancedProcessor')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    async def start(self):
        """Start the processor"""
        self.is_running = True
        self.processor_task = asyncio.create_task(self._process_signals())
        self.logger.info("Advanced signal processor started")
    
    async def stop(self):
        """Stop the processor"""
        self.is_running = False
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup components
        self.parser_core.cleanup()
        self.confidence_system.cleanup()
        self.strategy_core.cleanup()
        
        self.logger.info("Advanced signal processor stopped")
    
    async def process_signal(self, signal_input: Union[str, bytes], 
                           input_type: SignalType = SignalType.TEXT,
                           provider: Optional[str] = None,
                           account_balance: float = 10000.0) -> SignalProcessingResult:
        """
        Process a signal through the complete pipeline
        
        Args:
            signal_input: Signal text or image data
            input_type: Type of signal input
            provider: Signal provider name
            account_balance: Account balance for position sizing
            
        Returns:
            Complete processing result
        """
        start_time = datetime.now()
        
        # Initialize result
        result = SignalProcessingResult(
            raw_input=signal_input,
            input_type=input_type,
            provider=provider
        )
        
        try:
            # Stage 1: Parsing
            result.stage = ProcessingStage.PARSING
            result.parsed_signal = await self._parse_signal(signal_input, input_type, provider)
            
            if not result.parsed_signal or result.parsed_signal.confidence_score < 0.1:
                result.stage = ProcessingStage.FAILED
                result.parsing_errors.append("Parsing failed or very low confidence")
                return result
            
            # Generate signal ID
            result.signal_id = self._generate_signal_id(result.parsed_signal)
            
            # Stage 2: Confidence Scoring
            if self.config.get('enable_confidence_scoring', True):
                result.stage = ProcessingStage.CONFIDENCE_SCORING
                result.confidence_score, result.should_execute = await self._evaluate_confidence(result.parsed_signal)
                result.confidence_level = self._get_confidence_level(result.confidence_score)
            
            # Stage 3: Strategy Evaluation
            if self.config.get('enable_strategy_evaluation', True) and result.should_execute:
                result.stage = ProcessingStage.STRATEGY_EVALUATION
                result.trade_execution = await self._evaluate_strategy(result.parsed_signal, account_balance)
                
                if result.trade_execution:
                    result.execution_approved = True
                    result.execution_reason = "Strategy evaluation passed"
                else:
                    result.execution_approved = False
                    result.execution_reason = "Strategy evaluation failed"
            
            # Stage 4: Execution Planning
            if result.execution_approved:
                result.stage = ProcessingStage.EXECUTION_PLANNING
                await self._plan_execution(result)
            
            # Stage 5: Completion
            result.stage = ProcessingStage.COMPLETED
            result.processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            self._update_processing_stats(result)
            
            # Log processing if enabled
            if self.config.get('log_all_signals', True):
                self._log_processing_result(result)
            
            self.logger.info(f"Signal processed successfully: {result.signal_id}")
            return result
            
        except Exception as e:
            result.stage = ProcessingStage.FAILED
            result.parsing_errors.append(f"Processing error: {str(e)}")
            result.processing_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.error(f"Signal processing failed: {e}")
            return result
    
    async def _parse_signal(self, signal_input: Union[str, bytes], 
                          input_type: SignalType, provider: Optional[str]) -> Optional[ParsedSignalAdvanced]:
        """Parse signal using the parser core"""
        try:
            # Use advanced parser core
            parsed_signal = await self.parser_core.parse_signal(
                signal_input, 
                input_type, 
                provider
            )
            
            return parsed_signal
            
        except Exception as e:
            self.logger.error(f"Signal parsing failed: {e}")
            return None
    
    async def _evaluate_confidence(self, parsed_signal: ParsedSignalAdvanced) -> Tuple[float, bool]:
        """Evaluate signal confidence"""
        try:
            # Convert parsed signal to dict for confidence system
            signal_data = {
                'provider': parsed_signal.provider,
                'symbol': parsed_signal.symbol,
                'direction': parsed_signal.direction,
                'entry_price': parsed_signal.entry_price,
                'stop_loss': parsed_signal.stop_loss,
                'take_profits': parsed_signal.take_profits,
                'confidence': parsed_signal.confidence_score,
                'parsing_method': parsed_signal.parsing_method.value,
                'language': parsed_signal.language_detected
            }
            
            # Calculate confidence score
            confidence_score = self.confidence_system.calculate_confidence_score(signal_data)
            
            # Determine if should execute
            should_execute = self.confidence_system.should_execute_signal(signal_data)
            
            # Record signal for learning
            signal_id = self.confidence_system.record_signal(signal_data)
            
            return confidence_score, should_execute
            
        except Exception as e:
            self.logger.error(f"Confidence evaluation failed: {e}")
            return 0.0, False
    
    async def _evaluate_strategy(self, parsed_signal: ParsedSignalAdvanced, 
                               account_balance: float) -> Optional[TradeExecution]:
        """Evaluate strategy and create trade execution plan"""
        try:
            # Convert parsed signal to strategy format
            signal_data = {
                'symbol': parsed_signal.symbol,
                'direction': parsed_signal.direction,
                'entry_price': parsed_signal.entry_price,
                'stop_loss': parsed_signal.stop_loss,
                'take_profits': parsed_signal.take_profits,
                'order_type': parsed_signal.order_type or 'MARKET'
            }
            
            # Create trade execution plan
            trade_execution = await self.strategy_core.create_trade_execution(
                signal_data,
                account_balance
            )
            
            return trade_execution
            
        except Exception as e:
            self.logger.error(f"Strategy evaluation failed: {e}")
            return None
    
    async def _plan_execution(self, result: SignalProcessingResult):
        """Plan signal execution details"""
        try:
            # This is where execution planning would occur
            # For now, just mark as ready for execution
            result.execution_reason = "Ready for execution"
            
        except Exception as e:
            result.execution_approved = False
            result.execution_reason = f"Execution planning failed: {str(e)}"
    
    def _generate_signal_id(self, parsed_signal: ParsedSignalAdvanced) -> str:
        """Generate unique signal ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:17]
        provider = parsed_signal.provider or "unknown"
        symbol = parsed_signal.symbol or "unknown"
        
        return f"{provider}_{symbol}_{timestamp}"
    
    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level description"""
        if score >= 0.9:
            return "very_high"
        elif score >= 0.75:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        else:
            return "very_low"
    
    def _update_processing_stats(self, result: SignalProcessingResult):
        """Update processing statistics"""
        self.processing_stats["total_processed"] += 1
        
        if result.stage == ProcessingStage.COMPLETED:
            self.processing_stats["successful_processing"] += 1
        else:
            self.processing_stats["failed_processing"] += 1
        
        # Update stage performance
        self.processing_stats["stage_performance"][result.stage.value] += 1
        
        # Update average processing time
        total_time = (
            self.processing_stats["avg_processing_time"] * 
            (self.processing_stats["total_processed"] - 1) + 
            result.processing_time
        )
        self.processing_stats["avg_processing_time"] = total_time / self.processing_stats["total_processed"]
    
    def _log_processing_result(self, result: SignalProcessingResult):
        """Log processing result for analysis"""
        try:
            log_data = {
                'signal_id': result.signal_id,
                'provider': result.provider,
                'stage': result.stage.value,
                'processing_time': result.processing_time,
                'confidence_score': result.confidence_score,
                'execution_approved': result.execution_approved,
                'timestamp': result.timestamp.isoformat()
            }
            
            if result.parsed_signal:
                log_data['symbol'] = result.parsed_signal.symbol
                log_data['direction'] = result.parsed_signal.direction
                log_data['parsing_method'] = result.parsed_signal.parsing_method.value
            
            # Log to file
            log_path = Path("logs/signal_processing.jsonl")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_path, 'a') as f:
                f.write(json.dumps(log_data) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to log processing result: {e}")
    
    async def _process_signals(self):
        """Background signal processing task"""
        while self.is_running:
            try:
                # Process signals from queue
                await asyncio.sleep(0.1)  # Prevent tight loop
                
                # This would handle queued signals in a full implementation
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Processing task error: {e}")
                await asyncio.sleep(1)
    
    async def record_signal_outcome(self, signal_id: str, outcome: SignalOutcome, 
                                  exit_price: Optional[float] = None, 
                                  pnl_pips: Optional[float] = None):
        """Record signal outcome for learning"""
        try:
            self.confidence_system.record_outcome(signal_id, outcome, exit_price, pnl_pips)
            self.logger.info(f"Recorded outcome for {signal_id}: {outcome.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to record outcome: {e}")
    
    async def generate_config_from_prompt(self, prompt_text: str, 
                                        prompt_type: PromptType = PromptType.GENERAL_CONFIG):
        """Generate configuration from natural language prompt"""
        try:
            prompt = ConfigPrompt(prompt_text, prompt_type)
            response = await self.prompt_converter.convert_prompt(prompt)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to generate config from prompt: {e}")
            return None
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            **self.processing_stats,
            'parser_stats': self.parser_core.get_parser_stats(),
            'confidence_stats': self.confidence_system.get_system_stats(),
            'strategy_stats': self.strategy_core.get_performance_stats()
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            'running': self.is_running,
            'components': {
                'parser_core': True,
                'confidence_system': True,
                'strategy_core': True,
                'ocr_engine': self.ocr_engine is not None,
                'prompt_converter': True
            },
            'processing_stats': self.processing_stats,
            'queue_size': self.processing_queue.qsize() if self.processing_queue else 0
        }

# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Initialize processor
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
        
        print(f"Signal ID: {result.signal_id}")
        print(f"Stage: {result.stage.value}")
        print(f"Confidence: {result.confidence_score:.3f}")
        print(f"Execution Approved: {result.execution_approved}")
        print(f"Processing Time: {result.processing_time:.2f}s")
        
        if result.parsed_signal:
            print(f"Symbol: {result.parsed_signal.symbol}")
            print(f"Direction: {result.parsed_signal.direction}")
            print(f"Entry: {result.parsed_signal.entry_price}")
            print(f"SL: {result.parsed_signal.stop_loss}")
            print(f"TPs: {result.parsed_signal.take_profits}")
        
        # Test configuration generation
        config_response = await processor.generate_config_from_prompt(
            "I want to risk 2% per trade with breakeven at 50%",
            PromptType.RISK_MANAGEMENT
        )
        
        if config_response:
            print(f"Generated config: {json.dumps(config_response.config_json, indent=2)}")
            print(f"Explanation: {config_response.explanation}")
        
        # Get system status
        status = processor.get_system_status()
        print(f"System Status: {json.dumps(status, indent=2)}")
        
        # Stop processor
        await processor.stop()
    
    asyncio.run(main())