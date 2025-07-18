"""
Authentication middleware for SignalOS API
"""

from fastapi import HTTPException, status, Request, Response
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, Callable

security = HTTPBearer()


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for all requests"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add authentication"""
        # Skip auth for health check endpoints
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            response = await call_next(request)
            return response
        
        # For now, just pass through - in production would validate JWT
        response = await call_next(request)
        return response


async def verify_token(token: str = None) -> Dict[str, Any]:
    """
    Verify JWT token and return user info
    Mock implementation for testing
    """
    # In a real implementation, this would:
    # 1. Validate the JWT token
    # 2. Extract user information
    # 3. Check permissions
    # 4. Return user data or raise HTTPException
    
    # For now, return mock user data
    return {
        "user_id": "test_user_123",
        "username": "test@example.com",
        "permissions": ["read", "write", "admin"]
    }


def get_current_user(token: str = None) -> Dict[str, Any]:
    """
    Get current user from token (sync version)
    """
    return {
        "user_id": "test_user_123",
        "username": "test@example.com",
        "permissions": ["read", "write", "admin"]
    }