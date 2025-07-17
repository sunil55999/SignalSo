#!/usr/bin/env python3
"""
Trade Execution Engine for SignalOS Phase 1
Async parallel execution with comprehensive trade management
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from trade.mt5_socket_bridge import MT5SocketBridge, TradeRequest, TradeResult
from symbol_mapper import SymbolMapper
from retry_engine import RetryEngine

class ExecutionStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

@dataclass
class ExecutionRequest:
    """Trade execution request"""
    request_id: str
    signal_id: str
    symbol: str
    direction: str  # BUY/SELL
    entry_type: OrderType
    entry_prices: List[float]
    volume: float
    stop_loss: Optional[float] = None
    take_profits: List[float] = None
    max_slippage: int = 10
    comment: str = "SignalOS"
    magic_number: int = 12345
    expiration: Optional[datetime] = None
    risk_percentage: float = 2.0
    
    # Range entry handling
    is_range_entry: bool = False
    range_split_count: int = 1
    
    # Advanced features
    breakeven_enabled: bool = True
    trailing_stop_enabled: bool = False
    partial_close_levels: List[float] = None

@dataclass
class ExecutionResult:
    """Trade execution result"""
    request_id: str
    status: ExecutionStatus
    orders: List[Dict[str, Any]]
    total_volume: float = 0.0
    average_price: float = 0.0
    execution_time: Optional[datetime] = None
    error_message: Optional[str] = None
    partial_fills: List[Dict[str, Any]] = None
    
    # Performance metrics
    latency_ms: float = 0.0
    slippage_pips: float = 0.0

class TradeExecutor:
    """Advanced trade execution engine with parallel processing"""
    
    def __init__(self, config_file: str = "config/trade_executor.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Core components
        self.mt5_bridge = MT5SocketBridge()
        self.symbol_mapper = SymbolMapper()
        self.retry_engine = RetryEngine()
        
        # Execution management
        self.execution_queue = asyncio.Queue()
        self.active_executions: Dict[str, ExecutionRequest] = {}
        self.execution_history: List[ExecutionResult] = []
        
        # Worker management
        self.max_concurrent_executions = self.config.get('max_concurrent_executions', 5)
        self.execution_workers: List[asyncio.Task] = []
        self.is_running = False
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "partial_executions": 0,
            "average_latency": 0.0,
            "start_time": datetime.now()
        }
        
        self.logger.info("Trade Executor initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load execution configuration"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load trade executor config: {e}")
        
        return {
            "enabled": True,
            "max_concurrent_executions": 5,
            "max_retry_attempts": 3,
            "retry_delay_seconds": 1.0,
            "execution_timeout_seconds": 30,
            "default_slippage": 10,
            "default_magic_number": 12345,
            "risk_management": {
                "max_risk_per_trade": 2.0,
                "max_daily_risk": 10.0,
                "max_open_positions": 20,
                "position_sizing": "fixed"  # fixed, percentage, risk_based
            },
            "advanced_features": {
                "breakeven_enabled": True,
                "trailing_stop_enabled": True,
                "partial_close_enabled": True,
                "range_entry_enabled": True
            },
            "symbol_mapping": {
                "auto_detect_suffix": True,
                "broker_suffixes": ["m", "pro", "ecn", ""]
            }
        }
    
    def _setup_logging(self):
        """Setup logging for trade execution"""
        self.logger = logging.getLogger(__name__)
        
        # Create execution-specific log
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "trade_executor.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
    
    async def start(self):
        """Start the trade execution engine"""
        if not self.config.get('enabled', True):
            self.logger.info("Trade execution disabled in config")
            return False
        
        self.logger.info("Starting trade execution engine...")
        
        try:
            # Initialize MT5 bridge
            mt5_connected = await self.mt5_bridge.connect()
            if not mt5_connected:
                raise RuntimeError("Failed to connect to MT5")
            
            # Start execution workers
            self.is_running = True
            self.execution_workers = [
                asyncio.create_task(self._execution_worker(i))
                for i in range(self.max_concurrent_executions)
            ]
            
            self.logger.info(f"Trade execution engine started with {self.max_concurrent_executions} workers")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start trade execution engine: {e}")
            return False
    
    async def stop(self):
        """Stop the trade execution engine"""
        self.logger.info("Stopping trade execution engine...")
        
        self.is_running = False
        
        # Cancel all workers
        for worker in self.execution_workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.execution_workers, return_exceptions=True)
        
        # Disconnect MT5
        await self.mt5_bridge.disconnect()
        
        self.logger.info("Trade execution engine stopped")
    
    async def execute_signal(self, signal: Dict[str, Any], execution_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute a trading signal
        
        Args:
            signal: Parsed signal dictionary
            execution_params: Optional execution parameters
            
        Returns:
            Request ID for tracking
        """
        try:
            # Generate request ID
            request_id = f"exec_{int(datetime.now().timestamp())}_{self.stats['total_requests']}"
            
            # Map symbol to broker format
            broker_symbol = await self.symbol_mapper.map_symbol(signal['pair'])
            
            # Calculate position size
            volume = await self._calculate_position_size(signal, execution_params)
            
            # Handle entry prices (single or range)
            entry_prices = signal.get('entry', [])
            if not isinstance(entry_prices, list):
                entry_prices = [entry_prices]
            
            # Create execution request
            execution_request = ExecutionRequest(
                request_id=request_id,
                signal_id=signal.get('signal_id', 'unknown'),
                symbol=broker_symbol,
                direction=signal['direction'].upper(),
                entry_type=OrderType.MARKET,  # Default to market order
                entry_prices=entry_prices,
                volume=volume,
                stop_loss=signal.get('sl'),
                take_profits=signal.get('tp', []) if isinstance(signal.get('tp'), list) else [signal.get('tp')] if signal.get('tp') else [],
                max_slippage=execution_params.get('slippage', self.config['default_slippage']) if execution_params else self.config['default_slippage'],
                comment=f"SignalOS - {signal.get('provider', 'Unknown')}",
                magic_number=execution_params.get('magic_number', self.config['default_magic_number']) if execution_params else self.config['default_magic_number'],
                risk_percentage=execution_params.get('risk_percentage', 2.0) if execution_params else 2.0,
                is_range_entry=len(entry_prices) > 1,
                range_split_count=len(entry_prices) if len(entry_prices) > 1 else 1,
                breakeven_enabled=self.config['advanced_features']['breakeven_enabled'],
                trailing_stop_enabled=self.config['advanced_features']['trailing_stop_enabled'],
                partial_close_levels=signal.get('partial_close_levels', [])
            )
            
            # Add to execution queue
            await self.execution_queue.put(execution_request)
            self.active_executions[request_id] = execution_request
            
            self.stats['total_requests'] += 1
            
            self.logger.info(f"Signal queued for execution: {request_id} - {broker_symbol} {signal['direction']}")
            
            return request_id
            
        except Exception as e:
            self.logger.error(f"Failed to queue signal for execution: {e}")
            raise
    
    async def _execution_worker(self, worker_id: int):
        """Execution worker for processing trades"""
        self.logger.info(f"Execution worker {worker_id} started")
        
        try:
            while self.is_running:
                try:
                    # Get execution request from queue
                    execution_request = await asyncio.wait_for(
                        self.execution_queue.get(),
                        timeout=1.0
                    )
                    
                    # Process the execution
                    result = await self._process_execution(execution_request)
                    
                    # Update statistics
                    await self._update_execution_stats(result)
                    
                    # Log result
                    await self._log_execution_result(result)
                    
                    # Clean up
                    if execution_request.request_id in self.active_executions:
                        del self.active_executions[execution_request.request_id]
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    self.logger.error(f"Execution worker {worker_id} error: {e}")
                    
        except asyncio.CancelledError:
            self.logger.info(f"Execution worker {worker_id} cancelled")
        except Exception as e:
            self.logger.error(f"Execution worker {worker_id} fatal error: {e}")
    
    async def _process_execution(self, request: ExecutionRequest) -> ExecutionResult:
        """Process a single execution request"""
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Processing execution: {request.request_id}")
            
            result = ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.EXECUTING,
                orders=[],
                execution_time=start_time
            )
            
            # Risk management checks
            if not await self._risk_check(request):
                result.status = ExecutionStatus.FAILED
                result.error_message = "Risk management check failed"
                return result
            
            # Handle different entry types
            if request.is_range_entry:
                # Split volume across multiple entry points
                orders = await self._execute_range_entry(request)
            else:
                # Single entry execution
                orders = await self._execute_single_entry(request)
            
            result.orders = orders
            
            # Calculate execution metrics
            if orders:
                result.total_volume = sum(order.get('volume', 0) for order in orders)
                result.average_price = sum(order.get('price', 0) * order.get('volume', 0) for order in orders) / result.total_volume if result.total_volume > 0 else 0
                result.status = ExecutionStatus.COMPLETED if all(order.get('success', False) for order in orders) else ExecutionStatus.PARTIAL
            else:
                result.status = ExecutionStatus.FAILED
                result.error_message = "No orders executed"
            
            # Calculate latency
            result.latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Setup post-execution features
            if result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.PARTIAL]:
                await self._setup_post_execution_features(request, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Execution processing error: {e}")
            return ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.FAILED,
                orders=[],
                error_message=str(e),
                execution_time=start_time,
                latency_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    async def _risk_check(self, request: ExecutionRequest) -> bool:
        """Perform risk management checks"""
        try:
            # Check maximum open positions
            open_positions = await self.mt5_bridge.get_open_positions()
            if len(open_positions) >= self.config['risk_management']['max_open_positions']:
                self.logger.warning(f"Maximum open positions reached: {len(open_positions)}")
                return False
            
            # Check daily risk exposure
            daily_risk = await self._calculate_daily_risk_exposure()
            max_daily_risk = self.config['risk_management']['max_daily_risk']
            
            if daily_risk + request.risk_percentage > max_daily_risk:
                self.logger.warning(f"Daily risk limit exceeded: {daily_risk + request.risk_percentage} > {max_daily_risk}")
                return False
            
            # Check symbol-specific limits
            symbol_positions = [pos for pos in open_positions if pos.get('symbol') == request.symbol]
            if len(symbol_positions) >= 5:  # Max 5 positions per symbol
                self.logger.warning(f"Too many positions for symbol {request.symbol}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Risk check error: {e}")
            return False
    
    async def _execute_single_entry(self, request: ExecutionRequest) -> List[Dict[str, Any]]:
        """Execute single entry order"""
        try:
            entry_price = request.entry_prices[0] if request.entry_prices else None
            
            trade_request = TradeRequest(
                action="buy" if request.direction == "BUY" else "sell",
                symbol=request.symbol,
                volume=request.volume,
                price=entry_price,
                sl=request.stop_loss,
                tp=request.take_profits[0] if request.take_profits else None,
                deviation=request.max_slippage,
                magic=request.magic_number,
                comment=request.comment
            )
            
            # Execute trade with retry
            trade_result = await self.retry_engine.execute_with_retry(
                self.mt5_bridge.execute_trade,
                trade_request,
                max_attempts=self.config.get('max_retry_attempts', 3),
                delay=self.config.get('retry_delay_seconds', 1.0)
            )
            
            order_result = {
                "success": trade_result.success,
                "order_id": trade_result.order_id,
                "volume": trade_result.volume,
                "price": trade_result.price,
                "error_code": trade_result.error_code,
                "error_message": trade_result.error_message
            }
            
            return [order_result]
            
        except Exception as e:
            self.logger.error(f"Single entry execution error: {e}")
            return []
    
    async def _execute_range_entry(self, request: ExecutionRequest) -> List[Dict[str, Any]]:
        """Execute range entry orders"""
        try:
            orders = []
            volume_per_order = request.volume / request.range_split_count
            
            for i, entry_price in enumerate(request.entry_prices):
                trade_request = TradeRequest(
                    action="buy" if request.direction == "BUY" else "sell",
                    symbol=request.symbol,
                    volume=volume_per_order,
                    price=entry_price,
                    sl=request.stop_loss,
                    tp=request.take_profits[0] if request.take_profits else None,
                    deviation=request.max_slippage,
                    magic=request.magic_number,
                    comment=f"{request.comment} - Range {i+1}/{request.range_split_count}"
                )
                
                # Execute with retry
                trade_result = await self.retry_engine.execute_with_retry(
                    self.mt5_bridge.execute_trade,
                    trade_request,
                    max_attempts=2,  # Reduced retries for range entries
                    delay=0.5
                )
                
                order_result = {
                    "success": trade_result.success,
                    "order_id": trade_result.order_id,
                    "volume": trade_result.volume,
                    "price": trade_result.price,
                    "error_code": trade_result.error_code,
                    "error_message": trade_result.error_message,
                    "range_index": i
                }
                
                orders.append(order_result)
                
                # Small delay between range orders
                await asyncio.sleep(0.1)
            
            return orders
            
        except Exception as e:
            self.logger.error(f"Range entry execution error: {e}")
            return []
    
    async def _calculate_position_size(self, signal: Dict[str, Any], params: Optional[Dict[str, Any]]) -> float:
        """Calculate appropriate position size"""
        try:
            # Default to configured lot size
            default_volume = 0.01
            
            sizing_method = self.config['risk_management']['position_sizing']
            
            if sizing_method == "fixed":
                return default_volume
            elif sizing_method == "percentage":
                # Calculate based on account percentage
                account_balance = await self.mt5_bridge.get_account_balance()
                risk_amount = account_balance * (params.get('risk_percentage', 2.0) if params else 2.0) / 100
                
                # Calculate position size based on stop loss
                if signal.get('sl') and signal.get('entry'):
                    entry_price = signal['entry'][0] if isinstance(signal['entry'], list) else signal['entry']
                    sl_price = signal['sl']
                    
                    pip_value = await self.mt5_bridge.get_pip_value(signal['pair'])
                    pips_risk = abs(entry_price - sl_price) / pip_value
                    
                    if pips_risk > 0:
                        volume = risk_amount / (pips_risk * pip_value * 100000)  # Adjust for forex
                        return max(0.01, min(volume, 10.0))  # Limit between 0.01 and 10.0
                
                return default_volume
            else:
                return default_volume
                
        except Exception as e:
            self.logger.error(f"Position size calculation error: {e}")
            return 0.01  # Safe default
    
    async def _calculate_daily_risk_exposure(self) -> float:
        """Calculate current daily risk exposure"""
        try:
            # This would calculate the total risk from open positions
            # For now, return a placeholder
            return 0.0
        except Exception as e:
            self.logger.error(f"Daily risk calculation error: {e}")
            return 0.0
    
    async def _setup_post_execution_features(self, request: ExecutionRequest, result: ExecutionResult):
        """Setup breakeven, trailing stop, and other post-execution features"""
        try:
            # This would setup advanced features like:
            # - Breakeven management
            # - Trailing stop
            # - Partial close levels
            # - Multiple TP management
            
            self.logger.info(f"Setting up post-execution features for {request.request_id}")
            
        except Exception as e:
            self.logger.error(f"Post-execution setup error: {e}")
    
    async def _update_execution_stats(self, result: ExecutionResult):
        """Update execution statistics"""
        if result.status == ExecutionStatus.COMPLETED:
            self.stats['successful_executions'] += 1
        elif result.status == ExecutionStatus.PARTIAL:
            self.stats['partial_executions'] += 1
        else:
            self.stats['failed_executions'] += 1
        
        # Update average latency
        if result.latency_ms > 0:
            total_executions = self.stats['successful_executions'] + self.stats['partial_executions'] + self.stats['failed_executions']
            self.stats['average_latency'] = (
                (self.stats['average_latency'] * (total_executions - 1)) + result.latency_ms
            ) / total_executions
    
    async def _log_execution_result(self, result: ExecutionResult):
        """Log execution result"""
        try:
            log_file = Path("logs/execution_results.jsonl")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "request_id": result.request_id,
                    "status": result.status.value,
                    "total_volume": result.total_volume,
                    "average_price": result.average_price,
                    "latency_ms": result.latency_ms,
                    "orders_count": len(result.orders),
                    "error_message": result.error_message
                }
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            self.logger.error(f"Failed to log execution result: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get execution engine status"""
        return {
            "enabled": self.config.get('enabled', False),
            "running": self.is_running,
            "active_executions": len(self.active_executions),
            "worker_count": len(self.execution_workers),
            "statistics": self.stats,
            "uptime": (datetime.now() - self.stats["start_time"]).total_seconds()
        }
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent execution history"""
        return [asdict(result) for result in self.execution_history[-limit:]]