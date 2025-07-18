"""
Authentication middleware
"""

from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from core.auth import AuthService
from utils.logging_config import get_logger

logger = get_logger("middleware.auth")
security = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for protected routes"""
    
    def __init__(self, app):
        super().__init__(app)
        self.auth_service = AuthService()
        self.excluded_paths = {
            "/",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/docs",
            "/api/redoc",
            "/openapi.json"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication"""
        
        # Skip authentication for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Skip for OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"Missing or invalid authorization header for {request.url.path}")
            return Response(
                content='{"detail": "Authorization header required"}',
                status_code=401,
                media_type="application/json"
            )
        
        # Extract token
        token = auth_header.split(" ")[1]
        
        # Verify token
        token_data = self.auth_service.verify_token(token)
        
        if not token_data:
            logger.warning(f"Invalid token for {request.url.path}")
            return Response(
                content='{"detail": "Invalid or expired token"}',
                status_code=401,
                media_type="application/json"
            )
        
        # Add user info to request state
        request.state.user_id = token_data.user_id
        request.state.device_id = token_data.device_id
        request.state.license_key = token_data.license_key
        
        logger.debug(f"Authenticated request for user {token_data.user_id}")
        
        return await call_next(request)