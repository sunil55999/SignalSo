#!/usr/bin/env python3
"""
Config API Server
FastAPI server for configuration management and cloud sync
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    print("⚠️ FastAPI not available. Install with: pip install fastapi uvicorn")
    FASTAPI_AVAILABLE = False

import sys
sys.path.append(str(Path(__file__).parent.parent))

from config.cloud_sync import CloudConfigSync


class ConfigUpdateRequest(BaseModel):
    """Configuration update request model"""
    config: Dict[str, Any]
    force: bool = False


class SyncConfigRequest(BaseModel):
    """Sync configuration request model"""
    api_key: str
    user_id: str
    auto_sync: bool = True


class ConfigAPIServer:
    """FastAPI-based configuration management server"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8001):
        self.host = host
        self.port = port
        self.sync_manager = CloudConfigSync()
        
        if FASTAPI_AVAILABLE:
            self.app = self._create_app()
        else:
            self.app = None
            print("❌ FastAPI not available - server cannot start")
            
    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(
            title="SignalOS Config API",
            description="Configuration management and cloud sync API",
            version="1.0.0"
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Security scheme
        security = HTTPBearer()
        
        @app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "service": "SignalOS Config API",
                "version": "1.0.0",
                "status": "running",
                "timestamp": datetime.now().isoformat()
            }
            
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "sync_manager": "operational"
            }
            
        @app.get("/config/status")
        async def get_sync_status():
            """Get current sync status"""
            status = self.sync_manager.get_sync_status()
            return {
                "status": "success",
                "data": status,
                "timestamp": datetime.now().isoformat()
            }
            
        @app.get("/config/local")
        async def get_local_config():
            """Get local configuration"""
            try:
                local_config, local_hash = self.sync_manager._load_local_config()
                return {
                    "status": "success",
                    "config": local_config,
                    "hash": local_hash,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to load local config: {str(e)}"
                )
                
        @app.post("/config/local")
        async def update_local_config(request: ConfigUpdateRequest):
            """Update local configuration"""
            try:
                self.sync_manager._save_local_config(request.config)
                new_hash = self.sync_manager._calculate_config_hash(request.config)
                
                return {
                    "status": "success",
                    "message": "Local config updated successfully",
                    "new_hash": new_hash,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update local config: {str(e)}"
                )
                
        @app.get("/config/cloud")
        async def get_cloud_config():
            """Fetch configuration from cloud"""
            try:
                success, cloud_config = await self.sync_manager.fetch_cloud_config()
                
                if success:
                    return {
                        "status": "success",
                        "config": cloud_config,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=cloud_config.get("error", "Failed to fetch cloud config")
                    )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Cloud config fetch error: {str(e)}"
                )
                
        @app.post("/config/push")
        async def push_to_cloud(force: bool = False):
            """Push local config to cloud"""
            try:
                success, message = await self.sync_manager.upload_local_config(force=force)
                
                if success:
                    return {
                        "status": "success",
                        "message": message,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=message
                    )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Push to cloud failed: {str(e)}"
                )
                
        @app.post("/config/pull")
        async def pull_from_cloud(force: bool = False):
            """Pull config from cloud to local"""
            try:
                success, message = await self.sync_manager.download_cloud_config(force=force)
                
                if success:
                    return {
                        "status": "success",
                        "message": message,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=message
                    )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Pull from cloud failed: {str(e)}"
                )
                
        @app.post("/config/sync")
        async def auto_sync(background_tasks: BackgroundTasks):
            """Perform automatic sync"""
            try:
                success, message = await self.sync_manager.auto_sync()
                
                return {
                    "status": "success" if success else "error",
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Auto sync failed: {str(e)}"
                )
                
        @app.post("/config/setup")
        async def configure_sync(request: SyncConfigRequest):
            """Configure cloud sync settings"""
            try:
                self.sync_manager.configure_sync(
                    request.api_key,
                    request.user_id,
                    request.auto_sync
                )
                
                return {
                    "status": "success",
                    "message": "Sync configuration updated",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to configure sync: {str(e)}"
                )
                
        @app.get("/config/backup")
        async def create_backup():
            """Create configuration backup"""
            try:
                local_config, _ = self.sync_manager._load_local_config()
                backup_path = Path("config/backups")
                backup_path.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = backup_path / f"config_backup_{timestamp}.json"
                
                with open(backup_file, 'w') as f:
                    json.dump(local_config, f, indent=2)
                    
                return {
                    "status": "success",
                    "message": "Backup created successfully",
                    "backup_file": str(backup_file),
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Backup creation failed: {str(e)}"
                )
                
        @app.get("/config/backups")
        async def list_backups():
            """List available configuration backups"""
            try:
                backup_path = Path("config/backups")
                if not backup_path.exists():
                    return {
                        "status": "success",
                        "backups": [],
                        "timestamp": datetime.now().isoformat()
                    }
                    
                backups = []
                for backup_file in backup_path.glob("config_backup_*.json"):
                    stat = backup_file.stat()
                    backups.append({
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
                    
                backups.sort(key=lambda x: x["created"], reverse=True)
                
                return {
                    "status": "success",
                    "backups": backups,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to list backups: {str(e)}"
                )
                
        return app
        
    def run(self):
        """Run the config API server"""
        if not self.app:
            print("❌ Cannot start server - FastAPI not available")
            return
            
        print(f"🚀 Starting Config API Server on {self.host}:{self.port}")
        try:
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
        except Exception as e:
            print(f"❌ Server failed to start: {e}")


class MockConfigServer:
    """Mock config server for environments without FastAPI"""
    
    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.sync_manager = CloudConfigSync()
        
    def run(self):
        """Run mock server"""
        print(f"🎭 Mock Config Server running on {self.host}:{self.port}")
        print("📝 Available endpoints:")
        print("   GET /config/status - Sync status")
        print("   GET /config/local - Local configuration")
        print("   POST /config/push - Push to cloud")
        print("   POST /config/pull - Pull from cloud")
        print("   POST /config/sync - Auto sync")
        
        status = self.sync_manager.get_sync_status()
        print(f"\n📊 Current Status:")
        for key, value in status.items():
            print(f"   {key}: {value}")
            
        print("✅ Mock server ready (no actual HTTP server)")


def main():
    """Test the config API server"""
    print("⚙️ Testing Config API Server")
    print("=" * 50)
    
    # Try to start FastAPI server
    if FASTAPI_AVAILABLE:
        server = ConfigAPIServer(port=8002)  # Use different port for testing
        print("✅ FastAPI server initialized")
        
        # Test sync manager
        status = server.sync_manager.get_sync_status()
        print("📊 Sync Status:")
        for key, value in status.items():
            print(f"   {key}: {value}")
            
    else:
        # Use mock server
        server = MockConfigServer(port=8002)
        server.run()


if __name__ == "__main__":
    main()