#!/usr/bin/env python3
"""
License API Server
FastAPI server for license validation and management
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, Depends, status
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

from auth.license_checker import LicenseChecker


class LicenseRequest(BaseModel):
    """License validation request model"""
    telegram_id: Optional[str] = None
    machine_info: Optional[Dict[str, Any]] = None


class LicenseResponse(BaseModel):
    """License validation response model"""
    valid: bool
    message: str
    license_info: Dict[str, Any]
    expires_at: Optional[str] = None


class LicenseAPIServer:
    """FastAPI-based license validation server"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.checker = LicenseChecker()
        
        if FASTAPI_AVAILABLE:
            self.app = self._create_app()
        else:
            self.app = None
            print("❌ FastAPI not available - server cannot start")
            
    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(
            title="SignalOS License API",
            description="License validation and management API",
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
                "service": "SignalOS License API",
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
                "license_checker": "operational"
            }
            
        @app.post("/validate", response_model=LicenseResponse)
        async def validate_license(
            request: LicenseRequest,
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """Validate license token"""
            token = credentials.credentials
            
            # Validate token
            is_valid, message, token_data = self.checker.validate_token(
                token, 
                request.telegram_id
            )
            
            # Get license info
            license_info = self.checker.get_license_info()
            
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
                
            return LicenseResponse(
                valid=is_valid,
                message=message,
                license_info=license_info,
                expires_at=license_info.get('expires_at')
            )
            
        @app.get("/info")
        async def get_license_info(
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """Get license information"""
            token = credentials.credentials
            
            # Validate token first
            is_valid, message, token_data = self.checker.validate_token(token)
            
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message
                )
                
            return self.checker.get_license_info()
            
        @app.post("/demo-token")
        async def generate_demo_token(
            duration_days: int = 7,
            telegram_id: Optional[str] = None
        ):
            """Generate demo license token"""
            if duration_days > 30:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Demo duration cannot exceed 30 days"
                )
                
            token = self.checker.generate_demo_token(duration_days, telegram_id)
            
            return {
                "token": token,
                "duration_days": duration_days,
                "telegram_id": telegram_id,
                "expires_at": (datetime.now() + timedelta(days=duration_days)).isoformat()
            }
            
        @app.get("/machine-info")
        async def get_machine_info():
            """Get machine identification info"""
            return {
                "machine_id": self.checker.machine_id,
                "platform": self.checker._generate_machine_id()
            }
            
        return app
        
    def run(self):
        """Run the license API server"""
        if not self.app:
            print("❌ Cannot start server - FastAPI not available")
            return
            
        print(f"🚀 Starting License API Server on {self.host}:{self.port}")
        try:
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
        except Exception as e:
            print(f"❌ Server failed to start: {e}")
            
    async def run_async(self):
        """Run server asynchronously"""
        if not self.app:
            print("❌ Cannot start server - FastAPI not available")
            return
            
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


class MockLicenseServer:
    """Mock license server for environments without FastAPI"""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.checker = LicenseChecker()
        self.running = False
        
    def run(self):
        """Run mock server"""
        print(f"🎭 Mock License Server running on {self.host}:{self.port}")
        print("📝 Available endpoints:")
        print("   GET /health - Health check")
        print("   POST /validate - Validate license")
        print("   GET /info - License information")
        print("   POST /demo-token - Generate demo token")
        
        self.running = True
        print("✅ Mock server ready (no actual HTTP server)")
        
    def validate_license(self, token: str, telegram_id: Optional[str] = None) -> Dict[str, Any]:
        """Mock license validation"""
        is_valid, message, token_data = self.checker.validate_token(token, telegram_id)
        license_info = self.checker.get_license_info()
        
        return {
            "valid": is_valid,
            "message": message,
            "license_info": license_info,
            "expires_at": license_info.get('expires_at')
        }
        
    def generate_demo_token(self, duration_days: int = 7, telegram_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate demo token"""
        token = self.checker.generate_demo_token(duration_days, telegram_id)
        
        return {
            "token": token,
            "duration_days": duration_days,
            "telegram_id": telegram_id,
            "expires_at": (datetime.now() + timedelta(days=duration_days)).isoformat()
        }


def main():
    """Test the license API server"""
    print("🔐 Testing License API Server")
    print("=" * 50)
    
    # Try to start FastAPI server
    if FASTAPI_AVAILABLE:
        server = LicenseAPIServer(port=8001)  # Use different port for testing
        print("✅ FastAPI server initialized")
        
        # Test demo token generation
        demo_response = server.checker.generate_demo_token(7, "123456789")
        print(f"📝 Demo token: {demo_response[:50]}...")
        
    else:
        # Use mock server
        server = MockLicenseServer(port=8001)
        server.run()
        
        # Test validation
        demo_token = server.checker.generate_demo_token(7, "123456789")
        result = server.validate_license(demo_token, "123456789")
        print(f"📊 Validation result: {result}")


if __name__ == "__main__":
    main()