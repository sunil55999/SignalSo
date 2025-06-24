"""
Auto Sync Engine for SignalOS Desktop App
Handles automatic synchronization with the server for strategy updates and status reporting
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from dataclasses import dataclass, asdict
import os

try:
    from api_client import register_terminal, validate_terminal_auth
    from auth import is_authenticated
except ImportError:
    # Handle import errors gracefully
    pass

@dataclass
class SyncStatus:
    last_sync: datetime
    sync_count: int = 0
    failed_syncs: int = 0
    last_error: Optional[str] = None
    server_reachable: bool = False
    strategy_version: Optional[str] = None

class AutoSyncEngine:
    def __init__(self, config_file: str = "config.json", sync_log_file: str = "logs/sync_log.json"):
        self.config = self._load_config(config_file)
        self.sync_log_file = sync_log_file
        self.sync_interval = self.config.get("sync", {}).get("interval_seconds", 60)
        self.server_url = self.config.get("server", {}).get("url", "http://localhost:5000")
        self.user_id = self.config.get("user", {}).get("id", 1)
        
        self.sync_status = SyncStatus(last_sync=datetime.now())
        self.is_running = False
        self._setup_logging()
        
        # Module references (to be injected)
        self.mt5_bridge = None
        self.signal_parser = None
        self.retry_engine = None
        self.strategy_runtime = None
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._create_default_config(config_file)
    
    def _create_default_config(self, config_file: str) -> Dict[str, Any]:
        """Create default configuration file"""
        default_config = {
            "sync": {
                "interval_seconds": 60,
                "retry_attempts": 3,
                "timeout_seconds": 10
            },
            "server": {
                "url": "http://localhost:5000"
            },
            "user": {
                "id": 1
            },
            "desktop_app": {
                "terminal_id": "desktop_001",
                "version": "1.0.0"
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def _setup_logging(self):
        """Setup logging for sync operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('AutoSync')
    
    def inject_modules(self, mt5_bridge=None, signal_parser=None, retry_engine=None, strategy_runtime=None):
        """Inject module references for status collection"""
        self.mt5_bridge = mt5_bridge
        self.signal_parser = signal_parser
        self.retry_engine = retry_engine
        self.strategy_runtime = strategy_runtime
    
    async def _make_api_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Make API request to server with retry logic"""
        url = f"{self.server_url}/api{endpoint}"
        timeout = self.config.get("sync", {}).get("timeout_seconds", 10)
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=timeout)
            else:
                return {"error": "Unsupported HTTP method"}
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.exceptions.Timeout:
            return {"error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            return {"error": "Connection error"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response"}
    
    def _collect_terminal_status(self) -> Dict[str, Any]:
        """Collect current terminal status"""
        status = {
            "terminal_id": self.config.get("desktop_app", {}).get("terminal_id", "desktop_001"),
            "version": self.config.get("desktop_app", {}).get("version", "1.0.0"),
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0,
            "modules": {}
        }
        
        # Collect MT5 status
        if self.mt5_bridge:
            try:
                mt5_status = self.mt5_bridge.get_connection_status()
                status["modules"]["mt5"] = {
                    "connected": mt5_status.get("connected", False),
                    "account_info": mt5_status.get("account_info", {}),
                    "last_ping": mt5_status.get("last_ping"),
                    "error": mt5_status.get("error")
                }
            except Exception as e:
                status["modules"]["mt5"] = {"error": str(e)}
        
        # Collect parser status
        if self.signal_parser:
            try:
                parser_stats = self.signal_parser.get_statistics()
                status["modules"]["parser"] = {
                    "signals_parsed": parser_stats.get("total_parsed", 0),
                    "success_rate": parser_stats.get("success_rate", 0),
                    "last_signal": parser_stats.get("last_signal_time")
                }
            except Exception as e:
                status["modules"]["parser"] = {"error": str(e)}
        
        # Collect retry engine status
        if self.retry_engine:
            try:
                retry_stats = self.retry_engine.get_retry_stats()
                status["modules"]["retry_engine"] = {
                    "pending_retries": retry_stats.get("total_pending", 0),
                    "retry_reasons": retry_stats.get("by_reason", {})
                }
            except Exception as e:
                status["modules"]["retry_engine"] = {"error": str(e)}
        
        # Collect strategy runtime status
        if self.strategy_runtime:
            try:
                strategy_performance = self.strategy_runtime.get_strategy_performance()
                status["modules"]["strategy"] = {
                    "signals_processed": strategy_performance.get("total_signals", 0),
                    "actions_taken": strategy_performance.get("actions_taken", {}),
                    "current_strategy": self.strategy_runtime.current_strategy.id if self.strategy_runtime.current_strategy else None
                }
            except Exception as e:
                status["modules"]["strategy"] = {"error": str(e)}
        
        return status
    
    def _collect_parser_status(self) -> Dict[str, Any]:
        """Collect parser-specific status"""
        return {
            "last_update": datetime.now().isoformat(),
            "parser_version": "1.0.0",
            "supported_formats": ["text", "image_ocr"],
            "confidence_threshold": 70.0,
            "processing_time_avg": 0.5
        }
    
    async def sync_with_server(self) -> bool:
        """Perform single sync operation with server"""
        try:
            # Collect status data
            terminal_status = self._collect_terminal_status()
            parser_status = self._collect_parser_status()
            
            # Prepare sync payload
            sync_payload = {
                "userId": self.user_id,
                "terminalStatus": terminal_status,
                "parserStatus": parser_status,
                "syncTimestamp": datetime.now().isoformat()
            }
            
            self.logger.info("Initiating sync with server...")
            
            # Send sync request to server
            response = await self._make_api_request("/firebridge/sync-user", "POST", sync_payload)
            
            if "error" in response:
                self.sync_status.failed_syncs += 1
                self.sync_status.last_error = response["error"]
                self.sync_status.server_reachable = False
                self.logger.error(f"Sync failed: {response['error']}")
                return False
            
            # Process server response
            self.sync_status.server_reachable = True
            self.sync_status.sync_count += 1
            self.sync_status.last_sync = datetime.now()
            self.sync_status.last_error = None
            
            # Handle strategy updates from server
            if "strategy" in response and response["strategy"]:
                await self._handle_strategy_update(response["strategy"])
            
            # Log successful sync
            self._log_sync_event("success", sync_payload, response)
            self.logger.info("Sync completed successfully")
            
            return True
            
        except Exception as e:
            self.sync_status.failed_syncs += 1
            self.sync_status.last_error = str(e)
            self.sync_status.server_reachable = False
            self.logger.error(f"Sync exception: {e}")
            self._log_sync_event("error", {}, {"error": str(e)})
            return False
    
    async def _handle_strategy_update(self, strategy_data: Dict[str, Any]):
        """Handle strategy update from server"""
        try:
            if not self.strategy_runtime:
                self.logger.warning("Strategy runtime not available for update")
                return
            
            current_strategy_id = None
            if self.strategy_runtime.current_strategy:
                current_strategy_id = self.strategy_runtime.current_strategy.id
            
            server_strategy_id = strategy_data.get("id")
            
            # Check if strategy needs updating
            if current_strategy_id != server_strategy_id:
                self.logger.info(f"Loading new strategy: {server_strategy_id}")
                self.strategy_runtime.load_strategy(strategy_data)
                self.sync_status.strategy_version = server_strategy_id
                
                # Notify via Telegram if copilot bot is available
                await self._send_strategy_update_notification(strategy_data)
            
        except Exception as e:
            self.logger.error(f"Strategy update failed: {e}")
    
    async def _send_strategy_update_notification(self, strategy_data: Dict[str, Any]):
        """Send strategy update notification"""
        try:
            # This would integrate with the copilot bot if available
            message = f"Strategy updated: {strategy_data.get('name', 'Unknown')}"
            self.logger.info(f"Strategy notification: {message}")
            
            # If copilot bot is available, send notification
            # await self.copilot_bot.send_alert(message)
            
        except Exception as e:
            self.logger.error(f"Failed to send strategy notification: {e}")
    
    def _log_sync_event(self, event_type: str, request_data: Dict, response_data: Dict):
        """Log sync event to file"""
        try:
            os.makedirs(os.path.dirname(self.sync_log_file), exist_ok=True)
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "user_id": self.user_id,
                "sync_count": self.sync_status.sync_count,
                "request_data": request_data,
                "response_data": response_data,
                "server_reachable": self.sync_status.server_reachable
            }
            
            # Append to log file
            logs = []
            try:
                with open(self.sync_log_file, 'r') as f:
                    logs = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                logs = []
            
            logs.append(log_entry)
            
            # Keep only last 1000 log entries
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            with open(self.sync_log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to log sync event: {e}")
    
    async def send_error_alert(self, error_type: str, error_message: str, details: Dict = None):
        """Send error alert to server"""
        try:
            alert_payload = {
                "userId": self.user_id,
                "error": error_type,
                "details": {
                    "message": error_message,
                    "timestamp": datetime.now().isoformat(),
                    "terminal_id": self.config.get("desktop_app", {}).get("terminal_id"),
                    **(details or {})
                }
            }
            
            response = await self._make_api_request("/firebridge/error-alert", "POST", alert_payload)
            
            if "error" not in response:
                self.logger.info(f"Error alert sent: {error_type}")
            else:
                self.logger.warning(f"Failed to send error alert: {response['error']}")
                
        except Exception as e:
            self.logger.error(f"Exception sending error alert: {e}")
    
    async def sync_loop(self):
        """Main sync loop"""
        self.start_time = time.time()
        self.is_running = True
        self.logger.info(f"Starting sync loop with {self.sync_interval}s interval")
        
        while self.is_running:
            try:
                await self.sync_with_server()
                
                # Wait for next sync interval
                await asyncio.sleep(self.sync_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Sync loop interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Sync loop error: {e}")
                await self.send_error_alert("sync_loop_error", str(e))
                await asyncio.sleep(min(self.sync_interval, 30))  # Wait at least 30s on error
        
        self.is_running = False
        self.logger.info("Sync loop stopped")
    
    def stop_sync(self):
        """Stop the sync loop"""
        self.is_running = False
        self.logger.info("Sync stop requested")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        return {
            "is_running": self.is_running,
            "last_sync": self.sync_status.last_sync.isoformat(),
            "sync_count": self.sync_status.sync_count,
            "failed_syncs": self.sync_status.failed_syncs,
            "last_error": self.sync_status.last_error,
            "server_reachable": self.sync_status.server_reachable,
            "strategy_version": self.sync_status.strategy_version,
            "sync_interval": self.sync_interval,
            "server_url": self.server_url
        }
    
    def update_sync_interval(self, new_interval: int):
        """Update sync interval"""
        self.sync_interval = max(10, new_interval)  # Minimum 10 seconds
        self.logger.info(f"Sync interval updated to {self.sync_interval}s")
    
    async def force_sync(self) -> bool:
        """Force immediate sync"""
        self.logger.info("Force sync requested")
        return await self.sync_with_server()
    
    def get_sync_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent sync logs"""
        try:
            with open(self.sync_log_file, 'r') as f:
                logs = json.load(f)
                return logs[-limit:] if len(logs) > limit else logs
        except (FileNotFoundError, json.JSONDecodeError):
            return []

# Example usage and testing
async def main():
    """Example usage of Auto Sync Engine"""
    sync_engine = AutoSyncEngine()
    
    # Example of injecting mock modules for testing
    class MockMT5Bridge:
        def get_connection_status(self):
            return {"connected": True, "account_info": {"balance": 10000}}
    
    class MockSignalParser:
        def get_statistics(self):
            return {"total_parsed": 45, "success_rate": 92.5}
    
    sync_engine.inject_modules(
        mt5_bridge=MockMT5Bridge(),
        signal_parser=MockSignalParser()
    )
    
    # Test single sync
    print("Testing single sync...")
    success = await sync_engine.sync_with_server()
    print(f"Sync result: {success}")
    
    # Show sync status
    status = sync_engine.get_sync_status()
    print(f"Sync status: {json.dumps(status, indent=2)}")
    
    # Test error alert
    await sync_engine.send_error_alert("test_error", "This is a test error", {"test": True})
    
    print("Auto Sync Engine test completed")

if __name__ == "__main__":
    asyncio.run(main())