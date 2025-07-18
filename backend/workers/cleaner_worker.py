"""
Cleaner Worker for SignalOS Backend
Implements Part 2 Guide - Delete expired sessions, logs
"""

import asyncio
import os
import glob
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from utils.logging_config import get_logger

logger = get_logger(__name__)


class CleanerWorker:
    """Background worker for system cleanup tasks"""
    
    def __init__(self):
        self.is_running = False
        self.worker_task = None
        self.cleanup_interval = 3600  # 1 hour
        self.cleanup_stats = {
            "last_run": None,
            "total_runs": 0,
            "files_cleaned": 0,
            "space_freed": 0,
            "errors": 0
        }
        
        # Cleanup configuration
        self.log_retention_days = 30
        self.session_retention_hours = 24
        self.temp_file_retention_hours = 6
        self.parse_result_retention_days = 7
        self.retry_task_retention_days = 1
    
    async def start(self):
        """Start the cleaner worker"""
        if self.is_running:
            logger.warning("Cleaner worker already running")
            return
        
        self.is_running = True
        self.worker_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Cleaner worker started")
    
    async def stop(self):
        """Stop the cleaner worker"""
        self.is_running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Cleaner worker stopped")
    
    async def run_cleanup_now(self) -> Dict[str, Any]:
        """Run cleanup immediately"""
        logger.info("Running immediate cleanup")
        return await self._run_cleanup()
    
    async def _cleanup_loop(self):
        """Main cleanup loop"""
        while self.is_running:
            try:
                await self._run_cleanup()
                
                # Wait for next cleanup interval
                await asyncio.sleep(self.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                self.cleanup_stats["errors"] += 1
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _run_cleanup(self) -> Dict[str, Any]:
        """Run all cleanup tasks"""
        start_time = datetime.utcnow()
        cleanup_results = {
            "start_time": start_time.isoformat(),
            "tasks": {},
            "total_files_cleaned": 0,
            "total_space_freed": 0,
            "errors": []
        }
        
        try:
            # Clean up log files
            log_result = await self._cleanup_logs()
            cleanup_results["tasks"]["logs"] = log_result
            cleanup_results["total_files_cleaned"] += log_result.get("files_cleaned", 0)
            cleanup_results["total_space_freed"] += log_result.get("space_freed", 0)
            
            # Clean up temporary files
            temp_result = await self._cleanup_temp_files()
            cleanup_results["tasks"]["temp_files"] = temp_result
            cleanup_results["total_files_cleaned"] += temp_result.get("files_cleaned", 0)
            cleanup_results["total_space_freed"] += temp_result.get("space_freed", 0)
            
            # Clean up expired sessions
            session_result = await self._cleanup_sessions()
            cleanup_results["tasks"]["sessions"] = session_result
            cleanup_results["total_files_cleaned"] += session_result.get("files_cleaned", 0)
            
            # Clean up parse results
            parse_result = await self._cleanup_parse_results()
            cleanup_results["tasks"]["parse_results"] = parse_result
            
            # Clean up retry tasks
            retry_result = await self._cleanup_retry_tasks()
            cleanup_results["tasks"]["retry_tasks"] = retry_result
            
            # Update stats
            self.cleanup_stats["last_run"] = datetime.utcnow().isoformat()
            self.cleanup_stats["total_runs"] += 1
            self.cleanup_stats["files_cleaned"] += cleanup_results["total_files_cleaned"]
            self.cleanup_stats["space_freed"] += cleanup_results["total_space_freed"]
            
            end_time = datetime.utcnow()
            cleanup_results["end_time"] = end_time.isoformat()
            cleanup_results["duration"] = (end_time - start_time).total_seconds()
            
            logger.info(f"Cleanup completed: {cleanup_results['total_files_cleaned']} files, "
                       f"{cleanup_results['total_space_freed']} bytes freed")
            
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            cleanup_results["errors"].append(str(e))
            self.cleanup_stats["errors"] += 1
            return cleanup_results
    
    async def _cleanup_logs(self) -> Dict[str, Any]:
        """Clean up old log files"""
        result = {"files_cleaned": 0, "space_freed": 0, "errors": []}
        
        try:
            logs_dir = Path("./logs")
            if not logs_dir.exists():
                return result
            
            cutoff_date = datetime.utcnow() - timedelta(days=self.log_retention_days)
            
            # Find old log files
            log_patterns = ["*.log", "*.log.*", "*.out", "*.err"]
            
            for pattern in log_patterns:
                for log_file in logs_dir.glob(pattern):
                    try:
                        if log_file.is_file():
                            file_modified = datetime.fromtimestamp(log_file.stat().st_mtime)
                            
                            if file_modified < cutoff_date:
                                file_size = log_file.stat().st_size
                                log_file.unlink()
                                
                                result["files_cleaned"] += 1
                                result["space_freed"] += file_size
                                
                                logger.debug(f"Removed old log file: {log_file}")
                    
                    except Exception as e:
                        error_msg = f"Failed to remove log file {log_file}: {e}"
                        result["errors"].append(error_msg)
                        logger.warning(error_msg)
            
            logger.info(f"Log cleanup: {result['files_cleaned']} files, {result['space_freed']} bytes")
            
        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Log cleanup error: {e}")
        
        return result
    
    async def _cleanup_temp_files(self) -> Dict[str, Any]:
        """Clean up temporary files"""
        result = {"files_cleaned": 0, "space_freed": 0, "errors": []}
        
        try:
            temp_dirs = ["./temp", "./tmp", "/tmp/signalos"]
            cutoff_date = datetime.utcnow() - timedelta(hours=self.temp_file_retention_hours)
            
            for temp_dir in temp_dirs:
                temp_path = Path(temp_dir)
                if not temp_path.exists():
                    continue
                
                # Clean up files in temp directory
                for temp_file in temp_path.rglob("*"):
                    try:
                        if temp_file.is_file():
                            file_modified = datetime.fromtimestamp(temp_file.stat().st_mtime)
                            
                            if file_modified < cutoff_date:
                                file_size = temp_file.stat().st_size
                                temp_file.unlink()
                                
                                result["files_cleaned"] += 1
                                result["space_freed"] += file_size
                                
                                logger.debug(f"Removed temp file: {temp_file}")
                    
                    except Exception as e:
                        error_msg = f"Failed to remove temp file {temp_file}: {e}"
                        result["errors"].append(error_msg)
                        logger.warning(error_msg)
            
            logger.info(f"Temp file cleanup: {result['files_cleaned']} files, {result['space_freed']} bytes")
            
        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Temp file cleanup error: {e}")
        
        return result
    
    async def _cleanup_sessions(self) -> Dict[str, Any]:
        """Clean up expired sessions"""
        result = {"files_cleaned": 0, "sessions_cleared": 0, "errors": []}
        
        try:
            # In production, this would clean database sessions
            # For now, clean session files if they exist
            sessions_dir = Path("./sessions")
            if sessions_dir.exists():
                cutoff_date = datetime.utcnow() - timedelta(hours=self.session_retention_hours)
                
                for session_file in sessions_dir.glob("session_*.json"):
                    try:
                        file_modified = datetime.fromtimestamp(session_file.stat().st_mtime)
                        
                        if file_modified < cutoff_date:
                            session_file.unlink()
                            result["files_cleaned"] += 1
                            result["sessions_cleared"] += 1
                            
                            logger.debug(f"Removed expired session: {session_file}")
                    
                    except Exception as e:
                        error_msg = f"Failed to remove session file {session_file}: {e}"
                        result["errors"].append(error_msg)
                        logger.warning(error_msg)
            
            logger.info(f"Session cleanup: {result['sessions_cleared']} sessions cleared")
            
        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Session cleanup error: {e}")
        
        return result
    
    async def _cleanup_parse_results(self) -> Dict[str, Any]:
        """Clean up old parse results"""
        result = {"results_cleaned": 0, "errors": []}
        
        try:
            # Import here to avoid circular imports
            from core.parse import get_parse_controller
            from workers.parse_worker import get_parse_worker
            
            parse_controller = get_parse_controller()
            parse_worker = get_parse_worker()
            
            # Clean old parse results (convert days to hours for the method)
            parse_controller.cleanup_old_results(days=self.parse_result_retention_days)
            
            # Clean old worker results
            parse_worker.cleanup_old_results(hours=self.parse_result_retention_days * 24)
            
            result["results_cleaned"] = 1  # Placeholder since we don't track exact count
            logger.info("Parse results cleanup completed")
            
        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Parse results cleanup error: {e}")
        
        return result
    
    async def _cleanup_retry_tasks(self) -> Dict[str, Any]:
        """Clean up old retry tasks"""
        result = {"tasks_cleaned": 0, "errors": []}
        
        try:
            # Import here to avoid circular imports
            from workers.trade_retry import get_retry_worker
            
            retry_worker = get_retry_worker()
            
            # Clean old retry tasks
            retry_worker.cleanup_old_tasks(hours=self.retry_task_retention_days * 24)
            
            result["tasks_cleaned"] = 1  # Placeholder since we don't track exact count
            logger.info("Retry tasks cleanup completed")
            
        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Retry tasks cleanup error: {e}")
        
        return result
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get cleaner worker status"""
        return {
            "is_running": self.is_running,
            "cleanup_interval": self.cleanup_interval,
            "stats": self.cleanup_stats,
            "configuration": {
                "log_retention_days": self.log_retention_days,
                "session_retention_hours": self.session_retention_hours,
                "temp_file_retention_hours": self.temp_file_retention_hours,
                "parse_result_retention_days": self.parse_result_retention_days,
                "retry_task_retention_days": self.retry_task_retention_days
            }
        }
    
    def update_configuration(self, config: Dict[str, Any]):
        """Update cleaner configuration"""
        if "cleanup_interval" in config:
            self.cleanup_interval = config["cleanup_interval"]
        if "log_retention_days" in config:
            self.log_retention_days = config["log_retention_days"]
        if "session_retention_hours" in config:
            self.session_retention_hours = config["session_retention_hours"]
        if "temp_file_retention_hours" in config:
            self.temp_file_retention_hours = config["temp_file_retention_hours"]
        if "parse_result_retention_days" in config:
            self.parse_result_retention_days = config["parse_result_retention_days"]
        if "retry_task_retention_days" in config:
            self.retry_task_retention_days = config["retry_task_retention_days"]
        
        logger.info("Cleaner worker configuration updated")


# Global cleaner worker instance
cleaner_worker = CleanerWorker()


def get_cleaner_worker() -> CleanerWorker:
    """Get cleaner worker instance"""
    return cleaner_worker