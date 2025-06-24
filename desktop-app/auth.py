"""
Desktop Auth Token Manager for SignalOS
Handles JWT token storage, validation, and secure session management
"""

import json
import logging
import os
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import base64
import jwt

class AuthTokenManager:
    """Manages authentication tokens for desktop application"""
    
    def __init__(self, config_dir: str = ".signalos", server_url: str = None):
        self.config_dir = Path.home() / config_dir
        self.config_file = self.config_dir / "config.json"
        self.token_file = self.config_dir / "auth_token"
        self.server_url = server_url or self._get_server_url()
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Token cache
        self._cached_token = None
        self._token_validated_at = None
        self._validation_cache_duration = timedelta(minutes=5)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for auth manager"""
        logger = logging.getLogger('AuthTokenManager')
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
        """Get server URL from config or environment"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('server_url', 'http://localhost:5000')
        except Exception:
            pass
        
        # Check environment variables
        return os.getenv('SIGNALOS_SERVER_URL', 'http://localhost:5000')
    
    def get_auth_token(self) -> Optional[str]:
        """
        Get authentication token from cache, file, or config
        
        Returns:
            JWT token string or None if not available
        """
        # Check cache first
        if self._cached_token:
            return self._cached_token
        
        # Try to read from token file
        token = self._read_token_from_file()
        if token:
            self._cached_token = token
            return token
        
        # Try to read from config file
        token = self._read_token_from_config()
        if token:
            self._cached_token = token
            return token
        
        self.logger.warning("No authentication token found")
        return None
    
    def _read_token_from_file(self) -> Optional[str]:
        """Read token from dedicated token file"""
        try:
            if self.token_file.exists():
                with open(self.token_file, 'r') as f:
                    token = f.read().strip()
                    if token:
                        self.logger.debug("Token loaded from token file")
                        return token
        except Exception as e:
            self.logger.error(f"Failed to read token from file: {e}")
        
        return None
    
    def _read_token_from_config(self) -> Optional[str]:
        """Read token from config.json file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    token = config.get('auth_token')
                    if token:
                        self.logger.debug("Token loaded from config file")
                        return token
        except Exception as e:
            self.logger.error(f"Failed to read token from config: {e}")
        
        return None
    
    def store_auth_token(self, token: str) -> bool:
        """
        Store authentication token securely
        
        Args:
            token: JWT token string
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Validate token format before storing
            if not self._is_valid_jwt_format(token):
                self.logger.error("Invalid JWT token format")
                return False
            
            # Store in dedicated token file
            with open(self.token_file, 'w') as f:
                f.write(token)
            
            # Set restrictive permissions (owner read/write only)
            os.chmod(self.token_file, 0o600)
            
            # Update config file with token reference
            self._update_config_with_token_info()
            
            # Update cache
            self._cached_token = token
            self._token_validated_at = None  # Force revalidation
            
            self.logger.info("Authentication token stored successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store authentication token: {e}")
            return False
    
    def _is_valid_jwt_format(self, token: str) -> bool:
        """Check if token has valid JWT format"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False
            
            # Try to decode header and payload (without verification)
            header = base64.b64decode(parts[0] + '==')
            payload = base64.b64decode(parts[1] + '==')
            
            # Check if they're valid JSON
            json.loads(header)
            json.loads(payload)
            
            return True
        except Exception:
            return False
    
    def _update_config_with_token_info(self):
        """Update config file with token metadata"""
        try:
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            
            config.update({
                'auth_configured': True,
                'token_stored_at': datetime.now().isoformat(),
                'server_url': self.server_url
            })
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
        except Exception as e:
            self.logger.warning(f"Failed to update config metadata: {e}")
    
    def validate_token(self, token: str = None) -> bool:
        """
        Validate token by calling server /api/me endpoint
        
        Args:
            token: Token to validate (uses stored token if None)
            
        Returns:
            True if token is valid, False otherwise
        """
        if token is None:
            token = self.get_auth_token()
        
        if not token:
            self.logger.error("No token available for validation")
            return False
        
        # Check validation cache
        if (self._token_validated_at and 
            datetime.now() - self._token_validated_at < self._validation_cache_duration and
            token == self._cached_token):
            return True
        
        try:
            # Call server validation endpoint
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{self.server_url}/api/me",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                self.logger.info(f"Token validated for user: {user_data.get('username', 'Unknown')}")
                self._token_validated_at = datetime.now()
                return True
            elif response.status_code == 401:
                self.logger.error("Token validation failed: Unauthorized")
                self._clear_invalid_token()
                return False
            else:
                self.logger.error(f"Token validation failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Token validation network error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Token validation error: {e}")
            return False
    
    def _clear_invalid_token(self):
        """Clear invalid token from cache and storage"""
        try:
            self._cached_token = None
            self._token_validated_at = None
            
            if self.token_file.exists():
                os.remove(self.token_file)
                self.logger.info("Cleared invalid token from storage")
        except Exception as e:
            self.logger.error(f"Failed to clear invalid token: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        token = self.get_auth_token()
        if not token:
            return False
        
        return self.validate_token(token)
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information from server"""
        token = self.get_auth_token()
        if not token or not self.validate_token(token):
            return None
        
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{self.server_url}/api/me",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get user info: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting user info: {e}")
            return None
    
    def logout(self) -> bool:
        """Logout and clear stored tokens"""
        try:
            # Clear cache
            self._cached_token = None
            self._token_validated_at = None
            
            # Remove token file
            if self.token_file.exists():
                os.remove(self.token_file)
            
            # Update config
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                config.update({
                    'auth_configured': False,
                    'logged_out_at': datetime.now().isoformat()
                })
                
                with open(self.config_file, 'w') as f:
                    json.dump(config, f, indent=4)
            
            self.logger.info("Successfully logged out")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during logout: {e}")
            return False
    
    def refresh_token(self) -> bool:
        """Attempt to refresh expired token"""
        token = self.get_auth_token()
        if not token:
            return False
        
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.post(
                f"{self.server_url}/api/refresh",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data.get('token')
                if new_token:
                    self.store_auth_token(new_token)
                    self.logger.info("Token refreshed successfully")
                    return True
            
            self.logger.error(f"Token refresh failed: HTTP {response.status_code}")
            return False
            
        except Exception as e:
            self.logger.error(f"Token refresh error: {e}")
            return False
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get information about current token"""
        token = self.get_auth_token()
        info = {
            'has_token': token is not None,
            'token_validated': False,
            'user_info': None,
            'config_dir': str(self.config_dir),
            'server_url': self.server_url
        }
        
        if token:
            info['token_validated'] = self.validate_token(token)
            if info['token_validated']:
                info['user_info'] = self.get_user_info()
        
        return info


# Global instance for easy access
_auth_manager = None

def get_auth_token() -> Optional[str]:
    """
    Global function to get authentication token
    
    Returns:
        JWT token string or None if not available
    """
    global _auth_manager
    
    if _auth_manager is None:
        _auth_manager = AuthTokenManager()
    
    return _auth_manager.get_auth_token()

def store_auth_token(token: str) -> bool:
    """
    Global function to store authentication token
    
    Args:
        token: JWT token string
        
    Returns:
        True if stored successfully, False otherwise
    """
    global _auth_manager
    
    if _auth_manager is None:
        _auth_manager = AuthTokenManager()
    
    return _auth_manager.store_auth_token(token)

def validate_token(token: str = None) -> bool:
    """
    Global function to validate authentication token
    
    Args:
        token: Token to validate (uses stored token if None)
        
    Returns:
        True if token is valid, False otherwise
    """
    global _auth_manager
    
    if _auth_manager is None:
        _auth_manager = AuthTokenManager()
    
    return _auth_manager.validate_token(token)

def is_authenticated() -> bool:
    """Global function to check if user is authenticated"""
    global _auth_manager
    
    if _auth_manager is None:
        _auth_manager = AuthTokenManager()
    
    return _auth_manager.is_authenticated()

def get_user_info() -> Optional[Dict[str, Any]]:
    """Global function to get current user information"""
    global _auth_manager
    
    if _auth_manager is None:
        _auth_manager = AuthTokenManager()
    
    return _auth_manager.get_user_info()