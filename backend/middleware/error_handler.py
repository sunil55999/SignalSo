"""
Error handling middleware
"""

import traceback
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logging_config import get_logger

logger = get_logger("middleware.error")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error handling"""
        
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as exc:
            # FastAPI HTTP exceptions
            logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
            
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": "HTTP Error",
                    "message": exc.detail,
                    "status_code": exc.status_code
                }
            )
            
        except ValueError as exc:
            # Validation errors
            logger.warning(f"Validation error: {str(exc)}")
            
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Validation Error",
                    "message": str(exc),
                    "status_code": 400
                }
            )
            
        except PermissionError as exc:
            # Permission errors
            logger.warning(f"Permission error: {str(exc)}")
            
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Permission Denied",
                    "message": "Insufficient permissions",
                    "status_code": 403
                }
            )
            
        except Exception as exc:
            # Unexpected errors
            error_id = id(exc)
            error_trace = traceback.format_exc()
            
            logger.error(f"Unexpected error [{error_id}]: {str(exc)}\n{error_trace}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "error_id": error_id,
                    "status_code": 500
                }
            )