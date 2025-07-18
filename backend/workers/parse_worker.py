"""
Parse Worker for SignalOS Backend
Implements Part 2 Guide - Background parsing tasks
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from core.parse import CentralParseController, ParseRequest, ParseType, get_parse_controller
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ParseWorker:
    """Background worker for async signal parsing"""
    
    def __init__(self):
        self.parse_controller = get_parse_controller()
        self.task_queue = asyncio.Queue()
        self.results_cache: Dict[str, Dict[str, Any]] = {}
        self.is_running = False
        self.worker_task = None
    
    async def start(self):
        """Start the parse worker"""
        if self.is_running:
            logger.warning("Parse worker already running")
            return
        
        self.is_running = True
        self.worker_task = asyncio.create_task(self._process_queue())
        logger.info("Parse worker started")
    
    async def stop(self):
        """Stop the parse worker"""
        self.is_running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Parse worker stopped")
    
    async def submit_parse_task(self, task_data: Dict[str, Any]) -> str:
        """Submit async parse task"""
        task_id = task_data.get("request_id", f"task_{datetime.utcnow().timestamp()}")
        
        # Add to queue
        await self.task_queue.put({
            "task_id": task_id,
            "data": task_data,
            "submitted_at": datetime.utcnow()
        })
        
        # Initialize result cache
        self.results_cache[task_id] = {
            "status": "queued",
            "submitted_at": datetime.utcnow().isoformat(),
            "result": None,
            "error": None
        }
        
        logger.info(f"Parse task submitted: {task_id}")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status and result"""
        return self.results_cache.get(task_id)
    
    async def _process_queue(self):
        """Main worker loop to process parse tasks"""
        while self.is_running:
            try:
                # Wait for task with timeout
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                task_id = task["task_id"]
                task_data = task["data"]
                
                logger.info(f"Processing parse task: {task_id}")
                
                # Update status
                self.results_cache[task_id]["status"] = "processing"
                self.results_cache[task_id]["started_at"] = datetime.utcnow().isoformat()
                
                try:
                    # Create parse request
                    parse_request = ParseRequest(
                        request_id=task_id,
                        text=task_data.get("text"),
                        image_data=task_data.get("image_data"),
                        image_file=task_data.get("image_file"),
                        parse_type=ParseType(task_data.get("parse_type", "text")),
                        user_id=task_data.get("user_id", "unknown"),
                        device_id=task_data.get("device_id", "unknown"),
                        auto_execute=task_data.get("auto_execute", False),
                        confidence_threshold=task_data.get("confidence_threshold", 0.7)
                    )
                    
                    # Process parse request
                    result = self.parse_controller.parse_signal(parse_request)
                    
                    # Update result cache
                    self.results_cache[task_id].update({
                        "status": "completed",
                        "completed_at": datetime.utcnow().isoformat(),
                        "result": result.dict(),
                        "success": result.success
                    })
                    
                    logger.info(f"Parse task completed: {task_id}, success: {result.success}")
                    
                except Exception as e:
                    # Update error status
                    self.results_cache[task_id].update({
                        "status": "failed",
                        "completed_at": datetime.utcnow().isoformat(),
                        "error": str(e),
                        "success": False
                    })
                    
                    logger.error(f"Parse task failed: {task_id}, error: {e}")
                
                # Mark task as done
                self.task_queue.task_done()
                
            except asyncio.TimeoutError:
                # No tasks in queue, continue
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status information"""
        return {
            "is_running": self.is_running,
            "queue_size": self.task_queue.qsize(),
            "cached_results": len(self.results_cache),
            "completed_tasks": len([r for r in self.results_cache.values() if r["status"] == "completed"]),
            "failed_tasks": len([r for r in self.results_cache.values() if r["status"] == "failed"]),
            "pending_tasks": len([r for r in self.results_cache.values() if r["status"] in ["queued", "processing"]])
        }
    
    def cleanup_old_results(self, hours: int = 24):
        """Clean up old task results"""
        cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
        
        to_remove = []
        for task_id, result in self.results_cache.items():
            try:
                submitted_time = datetime.fromisoformat(result["submitted_at"]).timestamp()
                if submitted_time < cutoff_time:
                    to_remove.append(task_id)
            except:
                # Invalid timestamp, remove
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.results_cache[task_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old parse results")


# Global parse worker instance
parse_worker = ParseWorker()


def get_parse_worker() -> ParseWorker:
    """Get parse worker instance"""
    return parse_worker