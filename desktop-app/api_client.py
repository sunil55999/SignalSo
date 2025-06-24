"""
Authenticated API Client for SignalOS Desktop
Handles authenticated requests with retry logic and error handling
"""

import json
import logging
import requests
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from auth import get_auth_token, validate_token
    from terminal_identity import get_terminal_id, get_terminal_metadata
except ImportError:
    # Handle import errors gracefully for testing
    pass

class APIClient:
    """Authenticated API client with retry logic and error handling"""
    
    def __init__(self, server_url: str = None, timeout: int = 30):
        self.server_url = server_url or self._get_server_url()
        self.timeout = timeout
        self.session = self._create_session()
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Request statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_attempts': 0,
            'auth_failures': 0,
            'last_request_time': None
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for API client"""
        logger = logging.getLogger('APIClient')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _get_server_url(self) -> str:
        """Get server URL from environment or default"""
        import os
        return os.getenv('SIGNALOS_SERVER_URL', 'http://localhost:5000')
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()
        
        # Define retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers with current token"""
        try:
            token = get_auth_token()
            if not token:
                raise ValueError("No authentication token available")
            
            return {'Authorization': f'Bearer {token}'}
        except Exception as e:
            self.logger.error(f"Failed to get auth headers: {e}")
            raise
    
    def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None,
                     headers: Dict[str, str] = None, authenticated: bool = True) -> Dict[str, Any]:
        """
        Make authenticated HTTP request with retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/api/register_terminal')
            data: Request payload
            headers: Additional headers
            authenticated: Whether to include auth headers
            
        Returns:
            Response JSON data
            
        Raises:
            APIException: For API-related errors
        """
        self.stats['total_requests'] += 1
        self.stats['last_request_time'] = datetime.now().isoformat()
        
        url = f"{self.server_url}{endpoint}"
        request_headers = headers or {}
        
        # Add authentication headers if required
        if authenticated:
            try:
                auth_headers = self._get_auth_headers()
                request_headers.update(auth_headers)
            except Exception as e:
                self.stats['auth_failures'] += 1
                raise APIException(f"Authentication failed: {e}")
        
        # Add content type for POST requests
        if method.upper() in ['POST', 'PUT', 'PATCH'] and data:
            request_headers['Content-Type'] = 'application/json'
        
        try:
            # Make the request
            response = self.session.request(
                method=method.upper(),
                url=url,
                json=data,
                headers=request_headers,
                timeout=self.timeout
            )
            
            # Handle response
            if response.status_code == 200:
                self.stats['successful_requests'] += 1
                return response.json() if response.content else {}
            elif response.status_code == 401:
                self.stats['auth_failures'] += 1
                raise APIException(f"Unauthorized: {response.text}", status_code=401)
            elif response.status_code == 403:
                self.stats['auth_failures'] += 1
                raise APIException(f"Forbidden: {response.text}", status_code=403)
            elif response.status_code == 404:
                raise APIException(f"Not found: {endpoint}", status_code=404)
            else:
                self.stats['failed_requests'] += 1
                raise APIException(
                    f"Request failed: HTTP {response.status_code} - {response.text}",
                    status_code=response.status_code
                )
                
        except requests.exceptions.RequestException as e:
            self.stats['failed_requests'] += 1
            self.logger.error(f"Request exception for {method} {endpoint}: {e}")
            raise APIException(f"Network error: {e}")
        except Exception as e:
            self.stats['failed_requests'] += 1
            self.logger.error(f"Unexpected error for {method} {endpoint}: {e}")
            raise APIException(f"Unexpected error: {e}")
    
    def register_terminal(self) -> Dict[str, Any]:
        """
        Register terminal with server
        
        Returns:
            Registration response with approval status and config
        """
        try:
            # Get terminal metadata
            terminal_metadata = get_terminal_metadata()
            
            # Prepare registration payload
            payload = {
                'token': get_auth_token(),
                'terminal_id': terminal_metadata['terminal_id'],
                'os': terminal_metadata['os'],
                'version': terminal_metadata['version'],
                'hostname': terminal_metadata['hostname'],
                'architecture': terminal_metadata['architecture'],
                'python_version': terminal_metadata['python_version'],
                'memory_gb': terminal_metadata['memory_gb'],
                'app_name': terminal_metadata['app_name']
            }
            
            self.logger.info(f"Registering terminal: {payload['terminal_id']}")
            
            response = self._make_request('POST', '/api/register_terminal', data=payload)
            
            self.logger.info(f"Terminal registration response: {response.get('status', 'unknown')}")
            return response
            
        except Exception as e:
            self.logger.error(f"Terminal registration failed: {e}")
            raise
    
    def get_terminal_config(self) -> Dict[str, Any]:
        """
        Get terminal configuration from server
        
        Returns:
            Terminal configuration data
        """
        try:
            terminal_id = get_terminal_id()
            
            response = self._make_request('GET', f'/api/terminal_config?terminal_id={terminal_id}')
            
            self.logger.debug(f"Retrieved terminal config for: {terminal_id}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to get terminal config: {e}")
            raise
    
    def report_status(self, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Report terminal status to server
        
        Args:
            status_data: Status information to report
            
        Returns:
            Server response
        """
        try:
            # Add terminal identification
            payload = {
                'terminal_id': get_terminal_id(),
                'timestamp': datetime.now().isoformat(),
                **status_data
            }
            
            response = self._make_request('POST', '/api/report_status', data=payload)
            
            self.logger.debug(f"Status reported for terminal: {payload['terminal_id']}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to report status: {e}")
            raise
    
    def validate_terminal_auth(self) -> bool:
        """
        Validate terminal authentication with server
        
        Returns:
            True if terminal is authenticated and approved
        """
        try:
            # First validate the token
            if not validate_token():
                self.logger.error("Token validation failed")
                return False
            
            # Then check terminal registration
            response = self.get_terminal_config()
            
            approved = response.get('approved', False)
            if not approved:
                self.logger.warning("Terminal not approved by server")
                return False
            
            self.logger.info("Terminal authentication validated")
            return True
            
        except Exception as e:
            self.logger.error(f"Terminal auth validation failed: {e}")
            return False
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Get current user profile information"""
        try:
            response = self._make_request('GET', '/api/me')
            return response
        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")
            raise
    
    def update_terminal_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update terminal metadata on server"""
        try:
            payload = {
                'terminal_id': get_terminal_id(),
                'metadata': metadata
            }
            
            response = self._make_request('PUT', '/api/terminal_metadata', data=payload)
            return response
        except Exception as e:
            self.logger.error(f"Failed to update terminal metadata: {e}")
            raise
    
    def get_server_time(self) -> Dict[str, Any]:
        """Get server time for synchronization"""
        try:
            response = self._make_request('GET', '/api/time', authenticated=False)
            return response
        except Exception as e:
            self.logger.error(f"Failed to get server time: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection to server"""
        try:
            self._make_request('GET', '/api/health', authenticated=False)
            return True
        except Exception:
            return False
    
    def get_api_statistics(self) -> Dict[str, Any]:
        """Get API client statistics"""
        stats = self.stats.copy()
        if stats['total_requests'] > 0:
            stats['success_rate'] = stats['successful_requests'] / stats['total_requests']
            stats['failure_rate'] = stats['failed_requests'] / stats['total_requests']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        return stats
    
    def reset_statistics(self):
        """Reset API client statistics"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_attempts': 0,
            'auth_failures': 0,
            'last_request_time': None
        }


class APIException(Exception):
    """Custom exception for API-related errors"""
    
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


# Global API client instance
_api_client = None

def get_api_client() -> APIClient:
    """Get global API client instance"""
    global _api_client
    
    if _api_client is None:
        _api_client = APIClient()
    
    return _api_client

def register_terminal() -> Dict[str, Any]:
    """Global function to register terminal"""
    return get_api_client().register_terminal()

def get_terminal_config() -> Dict[str, Any]:
    """Global function to get terminal config"""
    return get_api_client().get_terminal_config()

def report_status(status_data: Dict[str, Any]) -> Dict[str, Any]:
    """Global function to report status"""
    return get_api_client().report_status(status_data)

def validate_terminal_auth() -> bool:
    """Global function to validate terminal authentication"""
    return get_api_client().validate_terminal_auth()