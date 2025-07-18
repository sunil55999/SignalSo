"""
SignalOS Offline-First Operation Core
Handles offline signal parsing, queuing, and sync operations
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from enum import Enum

from services.parser_ai import AISignalParser
from db.models import OfflineAction, SyncConflict
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ConflictResolution(Enum):
    MERGE = "merge"
    USE_LOCAL = "use_local"
    USE_SERVER = "use_server"
    MANUAL = "manual"


class OfflineOperationEngine:
    """Core offline operations engine"""
    
    def __init__(self, user_id: str, offline_db_path: str = "offline.db"):
        self.user_id = user_id
        self.offline_db_path = offline_db_path
        self.parser_service = AISignalParser()
        self.sync_queue = []
        self.is_online = False
        
    async def initialize(self):
        """Initialize offline database and components"""
        try:
            await self._setup_offline_database()
            await self.parser_service.initialize()
            logger.info(f"Offline engine initialized for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize offline engine: {e}")
            raise
    
    async def _setup_offline_database(self):
        """Setup local SQLite database for offline storage"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        # Create offline actions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_actions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                synced INTEGER DEFAULT 0,
                sync_attempts INTEGER DEFAULT 0,
                sync_error TEXT,
                conflict_resolution TEXT
            )
        ''')
        
        # Create offline signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_signals (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                parsed_data TEXT,
                confidence REAL,
                timestamp TEXT NOT NULL,
                synced INTEGER DEFAULT 0
            )
        ''')
        
        # Create offline trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_trades (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                volume REAL,
                price REAL,
                sl REAL,
                tp REAL,
                timestamp TEXT NOT NULL,
                synced INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def parse_signal_offline(self, signal_text: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Parse signal offline using local AI models"""
        try:
            # Use offline AI parser
            parsed_signal = await self.parser_service.parse_offline(
                text=signal_text,
                image_data=image_data
            )
            
            # Store in offline database
            await self._store_offline_signal(parsed_signal)
            
            # Queue for sync when online
            await self._queue_offline_action("SIGNAL_PARSE", {
                "text": signal_text,
                "image_data": image_data,
                "parsed_result": parsed_signal
            })
            
            logger.info(f"Signal parsed offline: {parsed_signal['symbol']}")
            return parsed_signal
            
        except Exception as e:
            logger.error(f"Offline signal parsing failed: {e}")
            raise
    
    async def execute_trade_offline(self, trade_params: Dict[str, Any]) -> Dict[str, Any]:
        """Queue trade for execution when online"""
        try:
            # Store trade in offline queue
            trade_id = await self._queue_offline_action("TRADE_OPEN", trade_params)
            
            # Store in offline trades table
            await self._store_offline_trade(trade_params)
            
            logger.info(f"Trade queued for offline execution: {trade_params['symbol']}")
            return {
                "success": True,
                "trade_id": trade_id,
                "status": "queued_offline",
                "message": "Trade queued for execution when online"
            }
            
        except Exception as e:
            logger.error(f"Offline trade queuing failed: {e}")
            raise
    
    async def _store_offline_signal(self, signal_data: Dict[str, Any]):
        """Store parsed signal in offline database"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO offline_signals 
            (id, user_id, raw_text, parsed_data, confidence, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            signal_data.get("id"),
            self.user_id,
            signal_data.get("raw_text", ""),
            json.dumps(signal_data),
            signal_data.get("confidence", 0.0),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_offline_trade(self, trade_data: Dict[str, Any]):
        """Store trade in offline database"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO offline_trades 
            (id, user_id, symbol, trade_type, volume, price, sl, tp, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data.get("id"),
            self.user_id,
            trade_data.get("symbol"),
            trade_data.get("type"),
            trade_data.get("volume"),
            trade_data.get("price"),
            trade_data.get("sl"),
            trade_data.get("tp"),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    async def _queue_offline_action(self, action_type: str, payload: Dict[str, Any]) -> str:
        """Queue action for sync when online"""
        import uuid
        
        action_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO offline_actions 
            (id, user_id, action_type, payload, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            action_id,
            self.user_id,
            action_type,
            json.dumps(payload),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return action_id
    
    async def sync_offline_actions(self) -> Dict[str, Any]:
        """Sync all offline actions with server"""
        try:
            offline_actions = await self._get_unsynced_actions()
            
            sync_results = {
                "total_actions": len(offline_actions),
                "successful": 0,
                "failed": 0,
                "conflicts": 0
            }
            
            for action in offline_actions:
                try:
                    result = await self._sync_single_action(action)
                    
                    if result["success"]:
                        sync_results["successful"] += 1
                        await self._mark_action_synced(action["id"])
                    elif result.get("conflict"):
                        sync_results["conflicts"] += 1
                        await self._handle_sync_conflict(action, result["conflict_data"])
                    else:
                        sync_results["failed"] += 1
                        await self._record_sync_error(action["id"], result["error"])
                        
                except Exception as e:
                    sync_results["failed"] += 1
                    await self._record_sync_error(action["id"], str(e))
                    logger.error(f"Sync failed for action {action['id']}: {e}")
            
            logger.info(f"Sync completed: {sync_results}")
            return sync_results
            
        except Exception as e:
            logger.error(f"Sync process failed: {e}")
            raise
    
    async def _get_unsynced_actions(self) -> List[Dict[str, Any]]:
        """Get all unsynced offline actions"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_id, action_type, payload, timestamp, sync_attempts
            FROM offline_actions 
            WHERE synced = 0 AND sync_attempts < 3
            ORDER BY timestamp ASC
        ''')
        
        actions = []
        for row in cursor.fetchall():
            actions.append({
                "id": row[0],
                "user_id": row[1],
                "action_type": row[2],
                "payload": json.loads(row[3]),
                "timestamp": row[4],
                "sync_attempts": row[5]
            })
        
        conn.close()
        return actions
    
    async def _sync_single_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Sync a single offline action with server"""
        # This would integrate with your existing API endpoints
        # For now, we'll simulate the sync process
        
        try:
            # Simulate API call based on action type
            if action["action_type"] == "SIGNAL_PARSE":
                # Call signal parsing API
                result = await self._sync_signal_parse(action["payload"])
            elif action["action_type"] == "TRADE_OPEN":
                # Call trade opening API
                result = await self._sync_trade_open(action["payload"])
            else:
                result = {"success": False, "error": "Unknown action type"}
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _sync_signal_parse(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sync signal parsing with server"""
        # This would call your existing signal parsing API
        # For now, return success
        return {"success": True}
    
    async def _sync_trade_open(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sync trade opening with server"""
        # This would call your existing trade opening API
        # For now, return success
        return {"success": True}
    
    async def _handle_sync_conflict(self, action: Dict[str, Any], conflict_data: Dict[str, Any]):
        """Handle sync conflict resolution"""
        # Store conflict for manual resolution
        # This would integrate with your conflict resolution system
        logger.warning(f"Sync conflict detected for action {action['id']}")
    
    async def _mark_action_synced(self, action_id: str):
        """Mark action as successfully synced"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE offline_actions 
            SET synced = 1, sync_attempts = sync_attempts + 1
            WHERE id = ?
        ''', (action_id,))
        
        conn.commit()
        conn.close()
    
    async def _record_sync_error(self, action_id: str, error: str):
        """Record sync error for action"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE offline_actions 
            SET sync_attempts = sync_attempts + 1, sync_error = ?
            WHERE id = ?
        ''', (error, action_id))
        
        conn.commit()
        conn.close()
    
    async def get_offline_status(self) -> Dict[str, Any]:
        """Get offline operation status"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        # Count unsynced actions
        cursor.execute('SELECT COUNT(*) FROM offline_actions WHERE synced = 0')
        unsynced_actions = cursor.fetchone()[0]
        
        # Count offline signals
        cursor.execute('SELECT COUNT(*) FROM offline_signals WHERE synced = 0')
        unsynced_signals = cursor.fetchone()[0]
        
        # Count offline trades
        cursor.execute('SELECT COUNT(*) FROM offline_trades WHERE synced = 0')
        unsynced_trades = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "is_online": self.is_online,
            "unsynced_actions": unsynced_actions,
            "unsynced_signals": unsynced_signals,
            "unsynced_trades": unsynced_trades,
            "offline_mode_active": not self.is_online
        }
    
    async def set_online_status(self, is_online: bool):
        """Set online/offline status"""
        self.is_online = is_online
        
        if is_online:
            logger.info("Going online - starting sync process")
            await self.sync_offline_actions()
        else:
            logger.info("Going offline - enabling offline mode")
    
    async def cleanup_old_actions(self, days_old: int = 30):
        """Clean up old synced actions"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
        
        cursor.execute('''
            DELETE FROM offline_actions 
            WHERE synced = 1 AND timestamp < ?
        ''', (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {deleted_count} old offline actions")
        return deleted_count