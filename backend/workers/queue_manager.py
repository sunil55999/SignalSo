"""
Background task queue manager for signal processing and trading operations
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

from utils.logging_config import get_logger

logger = get_logger("queue")


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class QueueTask:
    """Queue task data structure"""
    id: str
    task_type: str
    data: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data


class TaskWorker:
    """Base task worker class"""
    
    def __init__(self, name: str):
        self.name = name
        self.is_running = False
        self.current_task: Optional[QueueTask] = None
    
    async def process_task(self, task: QueueTask) -> Dict[str, Any]:
        """Process a task (to be implemented by subclasses)"""
        raise NotImplementedError("Subclasses must implement process_task")
    
    async def start(self):
        """Start the worker"""
        self.is_running = True
        logger.info(f"Worker {self.name} started")
    
    async def stop(self):
        """Stop the worker"""
        self.is_running = False
        logger.info(f"Worker {self.name} stopped")


class SignalParsingWorker(TaskWorker):
    """Worker for signal parsing tasks"""
    
    def __init__(self):
        super().__init__("signal_parser")
        # Import here to avoid circular imports
        from services.parser_ai import SignalProcessor
        self.signal_processor = SignalProcessor()
    
    async def process_task(self, task: QueueTask) -> Dict[str, Any]:
        """Process signal parsing task"""
        try:
            signal_text = task.data.get("text", "")
            image_data = task.data.get("image_data")
            
            # Process the signal
            parsed_signal = await self.signal_processor.process_signal(signal_text, image_data)
            
            if parsed_signal:
                return {
                    "success": True,
                    "parsed_signal": parsed_signal.to_dict(),
                    "processing_stats": self.signal_processor.get_processing_stats()
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to parse signal",
                    "processing_stats": self.signal_processor.get_processing_stats()
                }
                
        except Exception as e:
            logger.error(f"Signal parsing task error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class TradeExecutionWorker(TaskWorker):
    """Worker for trade execution tasks"""
    
    def __init__(self):
        super().__init__("trade_executor")
    
    async def process_task(self, task: QueueTask) -> Dict[str, Any]:
        """Process trade execution task"""
        try:
            # Simulate trade execution
            signal_data = task.data.get("signal", {})
            
            logger.info(f"Executing trade: {signal_data.get('symbol')} {signal_data.get('signal_type')}")
            
            # Simulate execution delay
            await asyncio.sleep(1)
            
            # Return success result
            return {
                "success": True,
                "trade_id": f"T_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "symbol": signal_data.get("symbol"),
                "signal_type": signal_data.get("signal_type"),
                "executed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Trade execution task error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class QueueManager:
    """Main queue manager for background tasks"""
    
    def __init__(self):
        self.queues: Dict[TaskPriority, List[QueueTask]] = {
            TaskPriority.CRITICAL: [],
            TaskPriority.HIGH: [],
            TaskPriority.NORMAL: [],
            TaskPriority.LOW: []
        }
        
        self.workers: Dict[str, TaskWorker] = {
            "signal_parsing": SignalParsingWorker(),
            "trade_execution": TradeExecutionWorker()
        }
        
        self.task_handlers: Dict[str, str] = {
            "parse_signal": "signal_parsing",
            "execute_trade": "trade_execution"
        }
        
        self.is_running = False
        self.worker_tasks: List[asyncio.Task] = []
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "active_tasks": 0
        }
    
    async def start(self):
        """Start the queue manager and workers"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start all workers
        for worker in self.workers.values():
            await worker.start()
        
        # Start task processing loop
        task = asyncio.create_task(self._process_queue_loop())
        self.worker_tasks.append(task)
        
        logger.info("Queue manager started")
    
    async def stop(self):
        """Stop the queue manager and workers"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        self.worker_tasks.clear()
        
        # Stop all workers
        for worker in self.workers.values():
            await worker.stop()
        
        logger.info("Queue manager stopped")
    
    async def add_task(self, task_type: str, data: Dict[str, Any], 
                      priority: TaskPriority = TaskPriority.NORMAL,
                      max_attempts: int = 3) -> str:
        """Add task to queue"""
        
        task_id = f"{task_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        task = QueueTask(
            id=task_id,
            task_type=task_type,
            data=data,
            priority=priority,
            max_attempts=max_attempts
        )
        
        # Add to appropriate priority queue
        self.queues[priority].append(task)
        self.stats["total_tasks"] += 1
        self.stats["active_tasks"] += 1
        
        logger.info(f"Added task {task_id} with priority {priority.name}")
        
        return task_id
    
    def get_next_task(self) -> Optional[QueueTask]:
        """Get next task from queues (highest priority first)"""
        for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, 
                        TaskPriority.NORMAL, TaskPriority.LOW]:
            queue = self.queues[priority]
            if queue:
                task = queue.pop(0)
                return task
        return None
    
    async def _process_queue_loop(self):
        """Main queue processing loop"""
        while self.is_running:
            try:
                # Get next task
                task = self.get_next_task()
                
                if not task:
                    # No tasks available, wait a bit
                    await asyncio.sleep(0.1)
                    continue
                
                # Process the task
                await self._process_task(task)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)
    
    async def _process_task(self, task: QueueTask):
        """Process a single task"""
        try:
            # Update task status
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.utcnow()
            task.attempts += 1
            
            logger.debug(f"Processing task {task.id} (attempt {task.attempts})")
            
            # Get appropriate worker
            worker_type = self.task_handlers.get(task.task_type)
            if not worker_type or worker_type not in self.workers:
                raise ValueError(f"No worker found for task type: {task.task_type}")
            
            worker = self.workers[worker_type]
            worker.current_task = task
            
            # Process the task
            result = await worker.process_task(task)
            
            # Update task with result
            if result.get("success", False):
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.utcnow()
                
                self.stats["completed_tasks"] += 1
                logger.info(f"Task {task.id} completed successfully")
            else:
                # Task failed
                task.error_message = result.get("error", "Unknown error")
                await self._handle_task_failure(task)
            
            worker.current_task = None
            self.stats["active_tasks"] -= 1
            
        except Exception as e:
            logger.error(f"Task processing error: {e}")
            task.error_message = str(e)
            await self._handle_task_failure(task)
    
    async def _handle_task_failure(self, task: QueueTask):
        """Handle task failure with retry logic"""
        if task.attempts < task.max_attempts:
            # Retry the task
            task.status = TaskStatus.RETRYING
            
            # Calculate retry delay (exponential backoff)
            retry_delay = min(300, 2 ** task.attempts)  # Max 5 minutes
            
            logger.warning(f"Task {task.id} failed, retrying in {retry_delay}s (attempt {task.attempts}/{task.max_attempts})")
            
            # Re-add to queue after delay
            await asyncio.sleep(retry_delay)
            self.queues[task.priority].append(task)
        else:
            # Task failed permanently
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            
            self.stats["failed_tasks"] += 1
            self.stats["active_tasks"] -= 1
            
            logger.error(f"Task {task.id} failed permanently after {task.attempts} attempts")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        queue_lengths = {
            priority.name.lower(): len(queue) 
            for priority, queue in self.queues.items()
        }
        
        return {
            **self.stats,
            "queue_lengths": queue_lengths,
            "is_running": self.is_running,
            "active_workers": len([w for w in self.workers.values() if w.is_running])
        }