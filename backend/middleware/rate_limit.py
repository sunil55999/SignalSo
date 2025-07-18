"""
Rate limiting middleware for API endpoints
"""

import time
import asyncio
from typing import Dict, Any, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib

from utils.logging_config import get_logger

logger = get_logger("rate_limit")


class RateLimitRule:
    """Rate limiting rule definition"""
    
    def __init__(self, requests: int, window: int, burst: int = None):
        self.requests = requests  # Number of requests allowed
        self.window = window      # Time window in seconds
        self.burst = burst or requests  # Burst limit
        self.reset_time = window


class RateLimitStorage:
    """In-memory rate limit storage"""
    
    def __init__(self):
        self.storage: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def _cleanup_expired(self):
        """Clean up expired rate limit entries"""
        current_time = time.time()
        
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        expired_keys = []
        for key, data in self.storage.items():
            if current_time - data.get('last_access', 0) > 3600:  # 1 hour
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.storage[key]
        
        self.last_cleanup = current_time
    
    def get_bucket(self, key: str) -> Dict[str, Any]:
        """Get rate limit bucket for key"""
        self._cleanup_expired()
        
        if key not in self.storage:
            self.storage[key] = {
                'count': 0,
                'window_start': time.time(),
                'last_access': time.time()
            }
        
        self.storage[key]['last_access'] = time.time()
        return self.storage[key]
    
    def update_bucket(self, key: str, bucket: Dict[str, Any]):
        """Update rate limit bucket"""
        self.storage[key] = bucket


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, default_rule: RateLimitRule = None):
        super().__init__(app)
        self.storage = RateLimitStorage()
        self.default_rule = default_rule or RateLimitRule(requests=100, window=60)
        
        # Define specific rules for different endpoints
        self.rules = {
            "/api/v1/auth/login": RateLimitRule(requests=5, window=60),
            "/api/v1/auth/register": RateLimitRule(requests=3, window=300),
            "/api/v1/trades/open": RateLimitRule(requests=10, window=60),
            "/api/v1/trades/close": RateLimitRule(requests=20, window=60),
            "/api/v1/signals/parse": RateLimitRule(requests=30, window=60),
            "/api/v1/analytics/report/pdf": RateLimitRule(requests=5, window=300),
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        try:
            # Skip rate limiting for health checks and docs
            if request.url.path in ["/health", "/", "/api/docs", "/api/redoc"]:
                return await call_next(request)
            
            # Get client identifier
            client_id = self._get_client_id(request)
            
            # Get rate limit rule
            rule = self._get_rule_for_path(request.url.path)
            
            # Check rate limit
            allowed, headers = self._check_rate_limit(client_id, rule, request.url.path)
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for {client_id} on {request.url.path}")
                
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {rule.requests} per {rule.window} seconds",
                        "retry_after": headers.get("Retry-After", rule.window)
                    }
                )
                
                # Add rate limit headers
                for key, value in headers.items():
                    response.headers[key] = str(value)
                
                return response
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to successful responses
            for key, value in headers.items():
                response.headers[key] = str(value)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Priority order: user_id > api_key > ip_address
        
        # Check for authenticated user
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return f"api_key:{key_hash}"
        
        # Fallback to IP address
        client_ip = request.client.host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _get_rule_for_path(self, path: str) -> RateLimitRule:
        """Get rate limit rule for specific path"""
        # Check for exact match
        if path in self.rules:
            return self.rules[path]
        
        # Check for pattern matches
        for rule_path, rule in self.rules.items():
            if path.startswith(rule_path.replace("*", "")):
                return rule
        
        # Return default rule
        return self.default_rule
    
    def _check_rate_limit(self, client_id: str, rule: RateLimitRule, path: str) -> tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limit"""
        bucket_key = f"{client_id}:{path}"
        bucket = self.storage.get_bucket(bucket_key)
        
        current_time = time.time()
        window_start = bucket['window_start']
        request_count = bucket['count']
        
        # Check if we're in a new window
        if current_time - window_start >= rule.window:
            # Reset the window
            bucket['window_start'] = current_time
            bucket['count'] = 1
            request_count = 1
        else:
            # Increment count in current window
            request_count += 1
            bucket['count'] = request_count
        
        # Update bucket
        self.storage.update_bucket(bucket_key, bucket)
        
        # Calculate remaining requests and reset time
        remaining = max(0, rule.requests - request_count)
        reset_time = int(window_start + rule.window)
        retry_after = max(1, int(reset_time - current_time))
        
        # Prepare headers
        headers = {
            "X-RateLimit-Limit": rule.requests,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Reset": reset_time,
            "X-RateLimit-Window": rule.window
        }
        
        # Check if limit exceeded
        if request_count > rule.requests:
            headers["Retry-After"] = retry_after
            return False, headers
        
        return True, headers


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> RateLimitMiddleware:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimitMiddleware(None)
    return _rate_limiter