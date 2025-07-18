"""
Trade Retry Worker for SignalOS Backend
Implements Part 2 Guide - Re-send failed MT5 trades
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

from core.trade import TradeExecutor
from utils.logging_config import get_logger

logger = get_logger(__name__)


class RetryStatus(str, Enum):
    """Retry task status"""
    PENDING = "pending"
    RETRYING = "retrying"
    SUCCESS = "success"
    FAILED = "failed"
    ABANDONED = "abandoned"


class RetryTask:
    """Retry task model"""
    def __init__(self, task_id: str, trade_data: Dict[str, Any], 
                 max_retries: int = 3, retry_delay: int = 5):
        self.task_id = task_id
        self.trade_data = trade_data
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_count = 0
        self.status = RetryStatus.PENDING
        self.created_at = datetime.utcnow()
        self.last_attempt = None
        self.next_retry = datetime.utcnow()
        self.error_history: List[str] = []
        self.final_result = None


class TradeRetryWorker:
    """Background worker for retrying failed trades"""
    
    def __init__(self):
        self.trading_engine = TradeExecutor()
        self.retry_tasks: Dict[str, RetryTask] = {}
        self.is_running = False
        self.worker_task = None
        self.retry_queue = asyncio.Queue()
        
        # Retry configuration
        self.default_max_retries = 3
        self.default_retry_delay = 5  # seconds
        self.exponential_backoff = True
        self.max_retry_delay = 300  # 5 minutes
    
    async def start(self):
        """Start the retry worker"""
        if self.is_running:
            logger.warning("Trade retry worker already running")
            return
        
        self.is_running = True
        self.worker_task = asyncio.create_task(self._process_retries())
        logger.info("Trade retry worker started")
    
    async def stop(self):
        """Stop the retry worker"""
        self.is_running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Trade retry worker stopped")
    
    async def submit_retry_task(self, trade_data: Dict[str, Any], 
                               max_retries: Optional[int] = None,
                               retry_delay: Optional[int] = None) -> str:
        """Submit trade for retry"""
        task_id = f"retry_{datetime.utcnow().timestamp()}_{trade_data.get('order_id', 'unknown')}"
        
        retry_task = RetryTask(
            task_id=task_id,
            trade_data=trade_data,
            max_retries=max_retries or self.default_max_retries,
            retry_delay=retry_delay or self.default_retry_delay
        )
        
        self.retry_tasks[task_id] = retry_task
        await self.retry_queue.put(task_id)
        
        logger.info(f"Trade retry task submitted: {task_id}")
        return task_id
    
    async def get_retry_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get retry task status"""
        task = self.retry_tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "created_at": task.created_at.isoformat(),
            "last_attempt": task.last_attempt.isoformat() if task.last_attempt else None,
            "next_retry": task.next_retry.isoformat() if task.next_retry else None,
            "error_history": task.error_history,
            "final_result": task.final_result
        }
    
    async def cancel_retry_task(self, task_id: str) -> bool:
        """Cancel retry task"""
        task = self.retry_tasks.get(task_id)
        if not task:
            return False
        
        if task.status in [RetryStatus.PENDING, RetryStatus.RETRYING]:
            task.status = RetryStatus.ABANDONED
            logger.info(f"Retry task cancelled: {task_id}")
            return True
        
        return False
    
    async def _process_retries(self):
        """Main worker loop to process retry tasks"""
        while self.is_running:
            try:
                # Check for due retries
                await self._check_due_retries()
                
                # Process new retry tasks
                try:
                    task_id = await asyncio.wait_for(self.retry_queue.get(), timeout=1.0)
                    await self._schedule_retry(task_id)
                    self.retry_queue.task_done()
                except asyncio.TimeoutError:
                    # No new tasks, continue with due retries
                    continue
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Retry worker error: {e}")
                await asyncio.sleep(1)
    
    async def _check_due_retries(self):
        """Check for retries that are due to be executed"""
        now = datetime.utcnow()
        
        for task_id, task in list(self.retry_tasks.items()):
            if (task.status == RetryStatus.PENDING and 
                task.next_retry and task.next_retry <= now):
                await self._execute_retry(task)
    
    async def _schedule_retry(self, task_id: str):
        """Schedule initial retry"""
        task = self.retry_tasks.get(task_id)
        if not task:
            logger.warning(f"Retry task not found: {task_id}")
            return
        
        # Execute immediately if this is the first attempt
        if task.retry_count == 0:
            await self._execute_retry(task)
    
    async def _execute_retry(self, task: RetryTask):
        """Execute retry attempt"""
        if task.status == RetryStatus.ABANDONED:
            return
        
        if task.retry_count >= task.max_retries:
            task.status = RetryStatus.FAILED
            logger.warning(f"Retry task max attempts reached: {task.task_id}")
            return
        
        task.status = RetryStatus.RETRYING
        task.retry_count += 1
        task.last_attempt = datetime.utcnow()
        
        logger.info(f"Executing retry {task.retry_count}/{task.max_retries} for task: {task.task_id}")
        
        try:
            # Attempt to execute trade
            result = await self._execute_trade_retry(task.trade_data)
            
            if result.get("success"):
                task.status = RetryStatus.SUCCESS
                task.final_result = result
                logger.info(f"Retry successful: {task.task_id}")
            else:
                # Retry failed, schedule next attempt
                error_msg = result.get("error", "Unknown error")
                task.error_history.append(f"Attempt {task.retry_count}: {error_msg}")
                
                if task.retry_count < task.max_retries:
                    # Calculate next retry time with exponential backoff
                    delay = self._calculate_retry_delay(task)
                    task.next_retry = datetime.utcnow() + timedelta(seconds=delay)
                    task.status = RetryStatus.PENDING
                    
                    logger.warning(f"Retry failed, next attempt in {delay}s: {task.task_id}")
                else:
                    task.status = RetryStatus.FAILED
                    task.final_result = result
                    logger.error(f"Retry task failed permanently: {task.task_id}")
                
        except Exception as e:
            error_msg = str(e)
            task.error_history.append(f"Attempt {task.retry_count}: {error_msg}")
            
            if task.retry_count < task.max_retries:
                delay = self._calculate_retry_delay(task)
                task.next_retry = datetime.utcnow() + timedelta(seconds=delay)
                task.status = RetryStatus.PENDING
                
                logger.error(f"Retry attempt failed: {task.task_id}, error: {error_msg}")
            else:
                task.status = RetryStatus.FAILED
                task.final_result = {"success": False, "error": error_msg}
                logger.error(f"Retry task failed permanently: {task.task_id}")
    
    async def _execute_trade_retry(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual trade retry"""
        try:
            # Determine retry action based on original trade type
            action = trade_data.get("action", "execute")
            
            if action == "execute":
                # Retry trade execution
                signal_data = trade_data.get("signal_data", {})
                result = self.trading_engine.execute_signal(signal_data)
            elif action == "close":
                # Retry trade closure
                order_id = trade_data.get("order_id")
                result = self.trading_engine.close_order(order_id)
            elif action == "modify":
                # Retry trade modification
                order_id = trade_data.get("order_id")
                modifications = trade_data.get("modifications", {})
                result = self.trading_engine.modify_order(order_id, modifications)
            else:
                return {"success": False, "error": f"Unknown retry action: {action}"}
            
            return result
            
        except Exception as e:
            logger.error(f"Trade retry execution error: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_retry_delay(self, task: RetryTask) -> int:
        """Calculate delay for next retry with exponential backoff"""
        base_delay = task.retry_delay
        
        if self.exponential_backoff:
            # Exponential backoff: base_delay * 2^(retry_count - 1)
            delay = base_delay * (2 ** (task.retry_count - 1))
            return min(delay, self.max_retry_delay)
        else:
            return base_delay
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get retry worker status"""
        tasks_by_status = {}
        for status in RetryStatus:
            tasks_by_status[status.value] = len([
                task for task in self.retry_tasks.values() 
                if task.status == status
            ])
        
        return {
            "is_running": self.is_running,
            "total_tasks": len(self.retry_tasks),
            "queue_size": self.retry_queue.qsize(),
            "tasks_by_status": tasks_by_status,
            "configuration": {
                "default_max_retries": self.default_max_retries,
                "default_retry_delay": self.default_retry_delay,
                "exponential_backoff": self.exponential_backoff,
                "max_retry_delay": self.max_retry_delay
            }
        }
    
    def cleanup_old_tasks(self, hours: int = 24):
        """Clean up old completed/failed tasks"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        to_remove = []
        for task_id, task in self.retry_tasks.items():
            if (task.status in [RetryStatus.SUCCESS, RetryStatus.FAILED, RetryStatus.ABANDONED] and
                task.created_at < cutoff_time):
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.retry_tasks[task_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old retry tasks")
    
    def update_configuration(self, config: Dict[str, Any]):
        """Update retry configuration"""
        if "default_max_retries" in config:
            self.default_max_retries = config["default_max_retries"]
        if "default_retry_delay" in config:
            self.default_retry_delay = config["default_retry_delay"]
        if "exponential_backoff" in config:
            self.exponential_backoff = config["exponential_backoff"]
        if "max_retry_delay" in config:
            self.max_retry_delay = config["max_retry_delay"]
        
        logger.info("Retry worker configuration updated")


# Global retry worker instance
retry_worker = TradeRetryWorker()


def get_retry_worker() -> TradeRetryWorker:
    """Get retry worker instance"""
    return retry_worker