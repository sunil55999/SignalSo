#!/usr/bin/env python3
"""
Retry Engine for SignalOS Desktop Application

Handles failed operations with exponential backoff and retry logic.
Manages retry queues for various operation types like signal processing,
trade execution, and API calls.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Awaitable
from uuid import uuid4

class OperationType(Enum):
    """Types of operations that can be retried"""
    SIGNAL_PARSE = "signal_parse"
    TRADE_EXECUTE = "trade_execute"
    API_CALL = "api_call"
    MT5_CONNECT = "mt5_connect"
    TELEGRAM_SEND = "telegram_send"
    SYNC_DATA = "sync_data"

class RetryStatus(Enum):
    """Status of retry operations"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"

@dataclass
class RetryOperation:
    """Represents an operation that can be retried"""
    id: str
    operation_type: OperationType
    data: Dict[str, Any]
    max_attempts: int
    current_attempts: int
    next_retry_time: datetime
    status: RetryStatus
    created_at: datetime
    last_error: Optional[str] = None
    backoff_factor: float = 2.0
    base_delay: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['operation_type'] = self.operation_type.value
        result['status'] = self.status.value
        result['next_retry_time'] = self.next_retry_time.isoformat()
        result['created_at'] = self.created_at.isoformat()
        return result

class RetryEngine:
    """Engine for handling failed operations with retry logic"""
    
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/retry_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Retry queues by operation type
        self.retry_queues: Dict[OperationType, List[RetryOperation]] = {
            op_type: [] for op_type in OperationType
        }
        
        # Operation handlers
        self.operation_handlers: Dict[OperationType, Callable] = {}
        
        # Processing state
        self.is_running = False
        self.processing_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_operations": 0,
            "successful_retries": 0,
            "failed_operations": 0,
            "expired_operations": 0,
            "operations_by_type": {op_type.value: 0 for op_type in OperationType}
        }
        
        # Load existing retry operations
        self._load_retry_history()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load retry engine configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('retry_engine', self._get_default_config())
        except FileNotFoundError:
            return self._create_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default retry configuration"""
        return {
            "processing_interval": 5.0,  # Check for retries every 5 seconds
            "max_queue_size": 1000,
            "operation_defaults": {
                "signal_parse": {
                    "max_attempts": 3,
                    "base_delay": 2.0,
                    "backoff_factor": 2.0,
                    "max_delay": 300.0
                },
                "trade_execute": {
                    "max_attempts": 5,
                    "base_delay": 1.0,
                    "backoff_factor": 1.5,
                    "max_delay": 60.0
                },
                "api_call": {
                    "max_attempts": 3,
                    "base_delay": 1.0,
                    "backoff_factor": 2.0,
                    "max_delay": 30.0
                },
                "mt5_connect": {
                    "max_attempts": 10,
                    "base_delay": 5.0,
                    "backoff_factor": 1.2,
                    "max_delay": 60.0
                },
                "telegram_send": {
                    "max_attempts": 3,
                    "base_delay": 1.0,
                    "backoff_factor": 2.0,
                    "max_delay": 30.0
                },
                "sync_data": {
                    "max_attempts": 5,
                    "base_delay": 10.0,
                    "backoff_factor": 1.5,
                    "max_delay": 300.0
                }
            },
            "cleanup_expired_after_hours": 24,
            "log_all_operations": True
        }
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration and save to file"""
        default_config = {
            "retry_engine": self._get_default_config()
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
            
        return default_config["retry_engine"]
    
    def _setup_logging(self):
        """Setup logging for retry engine"""
        self.logger = logging.getLogger('RetryEngine')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _load_retry_history(self):
        """Load existing retry operations from log file"""
        try:
            if Path(self.log_file).exists():
                with open(self.log_file, 'r') as f:
                    history_data = json.load(f)
                    
                # Restore pending operations
                for op_data in history_data.get('pending_operations', []):
                    try:
                        op = RetryOperation(
                            id=op_data['id'],
                            operation_type=OperationType(op_data['operation_type']),
                            data=op_data['data'],
                            max_attempts=op_data['max_attempts'],
                            current_attempts=op_data['current_attempts'],
                            next_retry_time=datetime.fromisoformat(op_data['next_retry_time']),
                            status=RetryStatus(op_data['status']),
                            created_at=datetime.fromisoformat(op_data['created_at']),
                            last_error=op_data.get('last_error'),
                            backoff_factor=op_data.get('backoff_factor', 2.0),
                            base_delay=op_data.get('base_delay', 1.0)
                        )
                        
                        if op.status in [RetryStatus.PENDING, RetryStatus.RUNNING]:
                            self.retry_queues[op.operation_type].append(op)
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to restore retry operation: {e}")
                        
                # Load statistics
                if 'statistics' in history_data:
                    self.stats.update(history_data['statistics'])
                    
        except Exception as e:
            self.logger.warning(f"Failed to load retry history: {e}")
    
    def _save_retry_history(self):
        """Save current retry operations to log file"""
        try:
            # Ensure log directory exists
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Collect all pending operations
            pending_operations = []
            for queue in self.retry_queues.values():
                for op in queue:
                    if op.status in [RetryStatus.PENDING, RetryStatus.RUNNING]:
                        pending_operations.append(op.to_dict())
            
            history_data = {
                "pending_operations": pending_operations,
                "statistics": self.stats,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.log_file, 'w') as f:
                json.dump(history_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Failed to save retry history: {e}")
    
    def register_handler(self, operation_type: OperationType, handler: Callable[[Dict[str, Any]], Awaitable[bool]]):
        """Register a handler for a specific operation type"""
        self.operation_handlers[operation_type] = handler
        self.logger.info(f"Registered handler for {operation_type.value}")
    
    def add_operation(self, operation_type: OperationType, data: Dict[str, Any], 
                     max_attempts: Optional[int] = None, base_delay: Optional[float] = None,
                     backoff_factor: Optional[float] = None) -> str:
        """Add an operation to the retry queue"""
        
        # Get configuration for this operation type
        op_config = self.config.get("operation_defaults", {}).get(operation_type.value, {})
        
        if max_attempts is None:
            max_attempts = op_config.get("max_attempts", 3)
        if base_delay is None:
            base_delay = op_config.get("base_delay", 1.0)
        if backoff_factor is None:
            backoff_factor = op_config.get("backoff_factor", 2.0)
        
        # Create retry operation
        operation = RetryOperation(
            id=str(uuid4()),
            operation_type=operation_type,
            data=data,
            max_attempts=max_attempts,
            current_attempts=0,
            next_retry_time=datetime.now(),
            status=RetryStatus.PENDING,
            created_at=datetime.now(),
            base_delay=base_delay,
            backoff_factor=backoff_factor
        )
        
        # Add to appropriate queue
        queue = self.retry_queues[operation_type]
        queue.append(operation)
        
        # Update statistics
        self.stats["total_operations"] += 1
        self.stats["operations_by_type"][operation_type.value] += 1
        
        self.logger.info(f"Added {operation_type.value} operation {operation.id} to retry queue")
        
        # Save to persistent storage
        self._save_retry_history()
        
        return operation.id
    
    def _calculate_next_retry_time(self, operation: RetryOperation) -> datetime:
        """Calculate the next retry time for an operation"""
        delay = operation.base_delay * (operation.backoff_factor ** operation.current_attempts)
        
        # Apply maximum delay limit
        op_config = self.config.get("operation_defaults", {}).get(operation.operation_type.value, {})
        max_delay = op_config.get("max_delay", 300.0)
        delay = min(delay, max_delay)
        
        return datetime.now() + timedelta(seconds=delay)
    
    async def _process_operation(self, operation: RetryOperation) -> bool:
        """Process a single retry operation"""
        if operation.operation_type not in self.operation_handlers:
            self.logger.error(f"No handler registered for {operation.operation_type.value}")
            return False
        
        try:
            operation.status = RetryStatus.RUNNING
            operation.current_attempts += 1
            
            handler = self.operation_handlers[operation.operation_type]
            success = await handler(operation.data)
            
            if success:
                operation.status = RetryStatus.SUCCESS
                self.stats["successful_retries"] += 1
                self.logger.info(f"Successfully processed {operation.operation_type.value} operation {operation.id}")
                return True
            else:
                # Operation failed, check if we should retry
                if operation.current_attempts >= operation.max_attempts:
                    operation.status = RetryStatus.FAILED
                    self.stats["failed_operations"] += 1
                    self.logger.error(f"Operation {operation.id} failed after {operation.max_attempts} attempts")
                    return False
                else:
                    operation.status = RetryStatus.PENDING
                    operation.next_retry_time = self._calculate_next_retry_time(operation)
                    self.logger.warning(f"Operation {operation.id} failed, will retry at {operation.next_retry_time}")
                    return False
                    
        except Exception as e:
            operation.last_error = str(e)
            operation.status = RetryStatus.PENDING
            operation.next_retry_time = self._calculate_next_retry_time(operation)
            self.logger.error(f"Error processing operation {operation.id}: {e}")
            return False
    
    async def _process_queues(self):
        """Process all retry queues"""
        current_time = datetime.now()
        operations_processed = 0
        
        for operation_type, queue in self.retry_queues.items():
            # Process operations that are ready for retry
            ready_operations = [
                op for op in queue 
                if op.status == RetryStatus.PENDING and op.next_retry_time <= current_time
            ]
            
            for operation in ready_operations:
                try:
                    await self._process_operation(operation)
                    operations_processed += 1
                except Exception as e:
                    self.logger.error(f"Error processing operation {operation.id}: {e}")
            
            # Remove completed or failed operations
            self.retry_queues[operation_type] = [
                op for op in queue 
                if op.status in [RetryStatus.PENDING, RetryStatus.RUNNING]
            ]
        
        # Cleanup expired operations
        self._cleanup_expired_operations()
        
        if operations_processed > 0:
            self.logger.info(f"Processed {operations_processed} retry operations")
            self._save_retry_history()
    
    def _cleanup_expired_operations(self):
        """Remove operations that have been pending too long"""
        expiry_time = datetime.now() - timedelta(hours=self.config.get("cleanup_expired_after_hours", 24))
        
        for operation_type, queue in self.retry_queues.items():
            expired_count = 0
            for operation in queue[:]:  # Create a copy to iterate over
                if operation.created_at < expiry_time and operation.status == RetryStatus.PENDING:
                    operation.status = RetryStatus.EXPIRED
                    queue.remove(operation)
                    expired_count += 1
                    self.stats["expired_operations"] += 1
            
            if expired_count > 0:
                self.logger.info(f"Cleaned up {expired_count} expired {operation_type.value} operations")
    
    async def start_processing(self):
        """Start the retry processing loop"""
        if self.is_running:
            self.logger.warning("Retry engine is already running")
            return
        
        self.is_running = True
        self.logger.info("Starting retry engine processing loop")
        
        self.processing_task = asyncio.create_task(self._processing_loop())
    
    async def stop_processing(self):
        """Stop the retry processing loop"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("Stopping retry engine processing loop")
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # Save final state
        self._save_retry_history()
    
    async def _processing_loop(self):
        """Main processing loop"""
        try:
            while self.is_running:
                await self._process_queues()
                await asyncio.sleep(self.config.get("processing_interval", 5.0))
        except asyncio.CancelledError:
            self.logger.info("Retry engine processing loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in retry engine processing loop: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retry engine statistics"""
        queue_stats = {}
        for op_type, queue in self.retry_queues.items():
            queue_stats[op_type.value] = {
                "pending": len([op for op in queue if op.status == RetryStatus.PENDING]),
                "running": len([op for op in queue if op.status == RetryStatus.RUNNING]),
                "total": len(queue)
            }
        
        return {
            **self.stats,
            "queues": queue_stats,
            "is_running": self.is_running
        }
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific operation"""
        for queue in self.retry_queues.values():
            for operation in queue:
                if operation.id == operation_id:
                    return operation.to_dict()
        return None


# Example usage and testing
async def main():
    """Example usage of retry engine"""
    engine = RetryEngine()
    
    # Example handlers
    async def example_api_handler(data: Dict[str, Any]) -> bool:
        """Example API call handler"""
        print(f"Processing API call: {data}")
        # Simulate random success/failure
        import random
        return random.random() > 0.7
    
    async def example_trade_handler(data: Dict[str, Any]) -> bool:
        """Example trade execution handler"""
        print(f"Executing trade: {data}")
        # Simulate random success/failure
        import random
        return random.random() > 0.5
    
    # Register handlers
    engine.register_handler(OperationType.API_CALL, example_api_handler)
    engine.register_handler(OperationType.TRADE_EXECUTE, example_trade_handler)
    
    # Start processing
    await engine.start_processing()
    
    # Add some test operations
    engine.add_operation(OperationType.API_CALL, {"endpoint": "/test", "data": {"test": True}})
    engine.add_operation(OperationType.TRADE_EXECUTE, {"symbol": "EURUSD", "volume": 0.1})
    
    # Let it run for a bit
    await asyncio.sleep(30)
    
    # Show statistics
    stats = engine.get_statistics()
    print(f"Retry engine statistics: {json.dumps(stats, indent=2)}")
    
    # Stop processing
    await engine.stop_processing()


if __name__ == "__main__":
    asyncio.run(main())