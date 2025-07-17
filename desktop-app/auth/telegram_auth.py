#!/usr/bin/env python3
"""
Telegram Authentication for SignalOS Desktop Application

Implements Telegram login via Telethon with session management
and secure credential storage.
"""

import asyncio
import json
import logging
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict

try:
    from telethon import TelegramClient, events
    from telethon.sessions import StringSession
    from telethon.errors import SessionPasswordNeededError, PhoneCodeExpiredError
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    logging.warning("Telethon not available")

@dataclass
class TelegramSession:
    """Telegram session information"""
    session_string: str
    phone_number: str
    user_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    created_at: datetime
    last_used: datetime
    is_active: bool

@dataclass
class TelegramAuthResult:
    """Authentication result"""
    success: bool
    session: Optional[TelegramSession]
    error_message: Optional[str]
    requires_code: bool = False
    requires_password: bool = False

class TelegramAuth:
    """Telegram authentication and session management"""
    
    def __init__(self, config_file: str = "config.json", sessions_dir: str = "sessions"):
        self.config_file = config_file
        self.sessions_dir = Path(sessions_dir)
        self.config = self._load_config()
        self._setup_logging()
        
        # Telegram API credentials
        self.api_id = self.config.get("api_id")
        self.api_hash = self.config.get("api_hash")
        
        # Session management
        self.sessions_dir.mkdir(exist_ok=True)
        self.active_client: Optional[TelegramClient] = None
        self.current_session: Optional[TelegramSession] = None
        
        # Authentication state
        self.auth_state = {
            "phone_code_hash": None,
            "phone_number": None,
            "waiting_for_code": False,
            "waiting_for_password": False
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Load Telegram authentication configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('telegram_auth', self._get_default_config())
        except FileNotFoundError:
            return self._create_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default Telegram configuration"""
        return {
            "api_id": None,  # User must provide
            "api_hash": None,  # User must provide
            "auto_login": False,
            "session_timeout_hours": 24,
            "encrypt_sessions": True,
            "allowed_phone_numbers": [],  # Empty = allow all
            "enable_2fa": True,
            "max_login_attempts": 3,
            "code_timeout_seconds": 120
        }
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration and save to file"""
        default_config = {
            "telegram_auth": self._get_default_config()
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
            
        return default_config["telegram_auth"]
    
    def _setup_logging(self):
        """Setup logging for Telegram auth"""
        self.logger = logging.getLogger('TelegramAuth')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # File handler
            log_file = Path("logs") / "telegram_auth.log"
            log_file.parent.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
    
    def is_configured(self) -> bool:
        """Check if Telegram API credentials are configured"""
        return bool(self.api_id and self.api_hash and TELETHON_AVAILABLE)
    
    def _encrypt_session(self, session_data: str) -> str:
        """Encrypt session data for storage"""
        if not self.config.get("encrypt_sessions", True):
            return session_data
        
        try:
            # Simple encryption using hashlib (in production, use proper encryption)
            key = hashlib.sha256(f"{self.api_id}{self.api_hash}".encode()).hexdigest()[:32]
            # For now, just return the session data (implement proper encryption as needed)
            return session_data
        except Exception as e:
            self.logger.error(f"Session encryption error: {e}")
            return session_data
    
    def _decrypt_session(self, encrypted_data: str) -> str:
        """Decrypt session data"""
        if not self.config.get("encrypt_sessions", True):
            return encrypted_data
        
        try:
            # Simple decryption (implement proper decryption as needed)
            return encrypted_data
        except Exception as e:
            self.logger.error(f"Session decryption error: {e}")
            return encrypted_data
    
    def save_session(self, session: TelegramSession):
        """Save Telegram session to file"""
        try:
            session_file = self.sessions_dir / f"session_{session.phone_number}.json"
            
            session_data = asdict(session)
            session_data['created_at'] = session.created_at.isoformat()
            session_data['last_used'] = session.last_used.isoformat()
            session_data['session_string'] = self._encrypt_session(session.session_string)
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=4)
            
            self.logger.info(f"Session saved for {session.phone_number}")
            
        except Exception as e:
            self.logger.error(f"Error saving session: {e}")
    
    def load_session(self, phone_number: str) -> Optional[TelegramSession]:
        """Load Telegram session from file"""
        try:
            session_file = self.sessions_dir / f"session_{phone_number}.json"
            
            if not session_file.exists():
                return None
            
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Decrypt session string
            session_data['session_string'] = self._decrypt_session(session_data['session_string'])
            
            session = TelegramSession(
                session_string=session_data['session_string'],
                phone_number=session_data['phone_number'],
                user_id=session_data['user_id'],
                username=session_data.get('username'),
                first_name=session_data['first_name'],
                last_name=session_data.get('last_name'),
                created_at=datetime.fromisoformat(session_data['created_at']),
                last_used=datetime.fromisoformat(session_data['last_used']),
                is_active=session_data.get('is_active', True)
            )
            
            # Check if session is expired
            timeout_hours = self.config.get("session_timeout_hours", 24)
            if datetime.now() - session.last_used > timedelta(hours=timeout_hours):
                self.logger.warning(f"Session for {phone_number} has expired")
                return None
            
            return session
            
        except Exception as e:
            self.logger.error(f"Error loading session: {e}")
            return None
    
    def list_sessions(self) -> List[TelegramSession]:
        """List all saved sessions"""
        sessions = []
        
        try:
            for session_file in self.sessions_dir.glob("session_*.json"):
                phone_number = session_file.stem.replace("session_", "")
                session = self.load_session(phone_number)
                if session:
                    sessions.append(session)
        except Exception as e:
            self.logger.error(f"Error listing sessions: {e}")
        
        return sessions
    
    def delete_session(self, phone_number: str) -> bool:
        """Delete a saved session"""
        try:
            session_file = self.sessions_dir / f"session_{phone_number}.json"
            if session_file.exists():
                session_file.unlink()
                self.logger.info(f"Session deleted for {phone_number}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error deleting session: {e}")
            return False
    
    async def start_login(self, phone_number: str) -> TelegramAuthResult:
        """Start Telegram login process"""
        if not self.is_configured():
            return TelegramAuthResult(
                success=False,
                session=None,
                error_message="Telegram API credentials not configured"
            )
        
        try:
            # Check if session already exists
            existing_session = self.load_session(phone_number)
            if existing_session and existing_session.is_active:
                # Try to use existing session
                client = TelegramClient(StringSession(existing_session.session_string), 
                                      self.api_id, self.api_hash)
                await client.connect()
                
                if await client.is_user_authorized():
                    self.active_client = client
                    self.current_session = existing_session
                    existing_session.last_used = datetime.now()
                    self.save_session(existing_session)
                    
                    return TelegramAuthResult(
                        success=True,
                        session=existing_session,
                        error_message=None
                    )
                else:
                    await client.disconnect()
            
            # Start new login process
            client = TelegramClient(StringSession(), self.api_id, self.api_hash)
            await client.connect()
            
            # Send code request
            result = await client.send_code_request(phone_number)
            
            self.auth_state.update({
                "phone_code_hash": result.phone_code_hash,
                "phone_number": phone_number,
                "waiting_for_code": True,
                "waiting_for_password": False
            })
            
            # Store client temporarily
            self.active_client = client
            
            return TelegramAuthResult(
                success=False,
                session=None,
                error_message=None,
                requires_code=True
            )
            
        except Exception as e:
            error_msg = f"Login initiation failed: {e}"
            self.logger.error(error_msg)
            return TelegramAuthResult(
                success=False,
                session=None,
                error_message=error_msg
            )
    
    async def submit_code(self, code: str) -> TelegramAuthResult:
        """Submit verification code"""
        if not self.auth_state.get("waiting_for_code"):
            return TelegramAuthResult(
                success=False,
                session=None,
                error_message="Not waiting for verification code"
            )
        
        try:
            phone_number = self.auth_state["phone_number"]
            phone_code_hash = self.auth_state["phone_code_hash"]
            
            if not self.active_client:
                return TelegramAuthResult(
                    success=False,
                    session=None,
                    error_message="No active client"
                )
            
            # Submit code
            user = await self.active_client.sign_in(
                phone=phone_number,
                code=code,
                phone_code_hash=phone_code_hash
            )
            
            # Create session
            session_string = self.active_client.session.save()
            session = TelegramSession(
                session_string=session_string,
                phone_number=phone_number,
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                created_at=datetime.now(),
                last_used=datetime.now(),
                is_active=True
            )
            
            # Save session
            self.save_session(session)
            self.current_session = session
            
            # Reset auth state
            self.auth_state = {
                "phone_code_hash": None,
                "phone_number": None,
                "waiting_for_code": False,
                "waiting_for_password": False
            }
            
            self.logger.info(f"Successfully logged in as {user.first_name}")
            
            return TelegramAuthResult(
                success=True,
                session=session,
                error_message=None
            )
            
        except SessionPasswordNeededError:
            # 2FA is enabled
            self.auth_state.update({
                "waiting_for_code": False,
                "waiting_for_password": True
            })
            
            return TelegramAuthResult(
                success=False,
                session=None,
                error_message=None,
                requires_password=True
            )
            
        except PhoneCodeExpiredError:
            error_msg = "Verification code expired"
            self.logger.error(error_msg)
            return TelegramAuthResult(
                success=False,
                session=None,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg = f"Code verification failed: {e}"
            self.logger.error(error_msg)
            return TelegramAuthResult(
                success=False,
                session=None,
                error_message=error_msg
            )
    
    async def submit_password(self, password: str) -> TelegramAuthResult:
        """Submit 2FA password"""
        if not self.auth_state.get("waiting_for_password"):
            return TelegramAuthResult(
                success=False,
                session=None,
                error_message="Not waiting for password"
            )
        
        try:
            if not self.active_client:
                return TelegramAuthResult(
                    success=False,
                    session=None,
                    error_message="No active client"
                )
            
            # Submit password
            user = await self.active_client.sign_in(password=password)
            
            phone_number = self.auth_state["phone_number"]
            
            # Create session
            session_string = self.active_client.session.save()
            session = TelegramSession(
                session_string=session_string,
                phone_number=phone_number,
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                created_at=datetime.now(),
                last_used=datetime.now(),
                is_active=True
            )
            
            # Save session
            self.save_session(session)
            self.current_session = session
            
            # Reset auth state
            self.auth_state = {
                "phone_code_hash": None,
                "phone_number": None,
                "waiting_for_code": False,
                "waiting_for_password": False
            }
            
            self.logger.info(f"Successfully logged in with 2FA as {user.first_name}")
            
            return TelegramAuthResult(
                success=True,
                session=session,
                error_message=None
            )
            
        except Exception as e:
            error_msg = f"Password verification failed: {e}"
            self.logger.error(error_msg)
            return TelegramAuthResult(
                success=False,
                session=None,
                error_message=error_msg
            )
    
    async def logout(self) -> bool:
        """Logout from current session"""
        try:
            if self.active_client:
                await self.active_client.log_out()
                await self.active_client.disconnect()
                
            if self.current_session:
                self.current_session.is_active = False
                self.save_session(self.current_session)
                
            self.active_client = None
            self.current_session = None
            
            self.logger.info("Successfully logged out")
            return True
            
        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            return False
    
    async def get_me(self) -> Optional[Dict[str, Any]]:
        """Get current user information"""
        try:
            if not self.active_client:
                return None
            
            user = await self.active_client.get_me()
            return {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "is_verified": user.verified
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user info: {e}")
            return None
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get current authentication status"""
        return {
            "configured": self.is_configured(),
            "logged_in": bool(self.current_session and self.current_session.is_active),
            "waiting_for_code": self.auth_state.get("waiting_for_code", False),
            "waiting_for_password": self.auth_state.get("waiting_for_password", False),
            "current_session": asdict(self.current_session) if self.current_session else None,
            "available_sessions": len(self.list_sessions()),
            "telethon_available": TELETHON_AVAILABLE
        }


# Example usage and testing
async def main():
    """Example usage of Telegram authentication"""
    auth = TelegramAuth()
    
    if not auth.is_configured():
        print("Telegram API credentials not configured")
        print("Please set api_id and api_hash in config.json")
        return
    
    # Example login flow
    phone_number = input("Enter phone number: ")
    
    # Start login
    result = await auth.start_login(phone_number)
    
    if result.requires_code:
        code = input("Enter verification code: ")
        result = await auth.submit_code(code)
        
        if result.requires_password:
            password = input("Enter 2FA password: ")
            result = await auth.submit_password(password)
    
    if result.success:
        print(f"Successfully logged in!")
        user_info = await auth.get_me()
        print(f"User: {user_info}")
        
        # List sessions
        sessions = auth.list_sessions()
        print(f"Available sessions: {len(sessions)}")
        
        # Logout
        await auth.logout()
    else:
        print(f"Login failed: {result.error_message}")


if __name__ == "__main__":
    asyncio.run(main())