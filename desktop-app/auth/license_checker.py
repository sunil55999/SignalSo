#!/usr/bin/env python3
"""
License Checker Module
Validates JWT tokens and blocks access for invalid/expired licenses
"""

import json
import jwt
import uuid
import platform
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


class LicenseChecker:
    """Enhanced license validation system with machine binding and Telegram ID support"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/license.json"
        self.secret_key = "signalojs_premium_license_2025"  # In production, use environment variable
        self.machine_id = self._generate_machine_id()
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load license configuration"""
        default_config = {
            "license_server": "https://api.signalojs.com/license",
            "offline_grace_period": 7,  # days
            "bind_to_machine": True,
            "bind_to_telegram": False,
            "last_validation": None,
            "cached_license": None
        }
        
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    return {**default_config, **config}
        except Exception as e:
            print(f"⚠️ License config error: {e}")
            
        return default_config
        
    def _save_config(self):
        """Save license configuration"""
        try:
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save license config: {e}")
            
    def _generate_machine_id(self) -> str:
        """Generate unique machine identifier"""
        try:
            # Combine multiple system identifiers
            system_info = [
                platform.node(),  # Computer name
                platform.machine(),  # Machine type
                platform.processor(),  # Processor info
                str(uuid.getnode()),  # MAC address
            ]
            
            # Create hash from system info
            system_string = "|".join(system_info)
            machine_hash = hashlib.sha256(system_string.encode()).hexdigest()
            return machine_hash[:16]  # Use first 16 characters
            
        except Exception:
            # Fallback to simpler method
            return str(uuid.getnode())[:16]
            
    def validate_token(self, token: str, telegram_id: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate JWT license token
        
        Args:
            token: JWT token string
            telegram_id: Optional Telegram user ID for binding
            
        Returns:
            Tuple of (is_valid, message, token_data)
        """
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            # Check expiration
            exp_timestamp = payload.get('exp')
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                if datetime.now(timezone.utc) > exp_datetime:
                    return False, "License expired", {}
                    
            # Check machine binding if enabled
            if self.config.get("bind_to_machine", True):
                token_machine_id = payload.get('machine_id')
                if token_machine_id and token_machine_id != self.machine_id:
                    return False, "License bound to different machine", {}
                    
            # Check Telegram ID binding if enabled
            if self.config.get("bind_to_telegram", False) and telegram_id:
                token_telegram_id = payload.get('telegram_id')
                if token_telegram_id and str(token_telegram_id) != str(telegram_id):
                    return False, "License bound to different Telegram account", {}
                    
            # Update cache
            self.config['cached_license'] = payload
            self.config['last_validation'] = datetime.now().isoformat()
            self._save_config()
            
            return True, "License valid", payload
            
        except jwt.ExpiredSignatureError:
            return False, "License expired", {}
        except jwt.InvalidTokenError:
            return False, "Invalid license token", {}
        except Exception as e:
            return False, f"License validation error: {str(e)}", {}
            
    def check_offline_grace(self) -> Tuple[bool, str]:
        """Check if offline grace period is still valid"""
        last_validation = self.config.get('last_validation')
        if not last_validation:
            return False, "No previous validation found"
            
        try:
            last_check = datetime.fromisoformat(last_validation)
            grace_period = self.config.get('offline_grace_period', 7)
            grace_expires = last_check.replace(tzinfo=timezone.utc) + timedelta(days=grace_period)
            
            if datetime.now(timezone.utc) < grace_expires:
                remaining_days = (grace_expires - datetime.now(timezone.utc)).days
                return True, f"Offline grace period valid ({remaining_days} days remaining)"
            else:
                return False, "Offline grace period expired"
                
        except Exception as e:
            return False, f"Grace period check failed: {str(e)}"
            
    def generate_demo_token(self, duration_days: int = 7, telegram_id: Optional[str] = None) -> str:
        """
        Generate demo license token for testing
        
        Args:
            duration_days: Token validity in days
            telegram_id: Optional Telegram ID to bind
            
        Returns:
            JWT token string
        """
        exp_datetime = datetime.now(timezone.utc) + timedelta(days=duration_days)
        
        payload = {
            'user_id': 'demo_user',
            'license_type': 'demo',
            'exp': int(exp_datetime.timestamp()),
            'machine_id': self.machine_id,
            'features': ['trading', 'backtesting', 'reports'],
            'iat': int(datetime.now(timezone.utc).timestamp())
        }
        
        if telegram_id:
            payload['telegram_id'] = telegram_id
            
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
        
    def get_license_info(self) -> Dict[str, Any]:
        """Get current license information"""
        cached_license = self.config.get('cached_license', {})
        
        if not cached_license:
            return {
                'status': 'no_license',
                'message': 'No valid license found',
                'machine_id': self.machine_id
            }
            
        exp_timestamp = cached_license.get('exp')
        exp_datetime = None
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            
        return {
            'status': 'active' if exp_datetime and datetime.now(timezone.utc) < exp_datetime else 'expired',
            'user_id': cached_license.get('user_id'),
            'license_type': cached_license.get('license_type'),
            'expires_at': exp_datetime.isoformat() if exp_datetime else None,
            'features': cached_license.get('features', []),
            'machine_id': self.machine_id,
            'telegram_id': cached_license.get('telegram_id')
        }
        
    def block_unauthorized_access(self, token: str = None, telegram_id: str = None) -> bool:
        """
        Main license check function - returns True if access should be allowed
        
        Args:
            token: JWT license token
            telegram_id: Optional Telegram user ID
            
        Returns:
            Boolean indicating if access is authorized
        """
        if not token:
            # Check for cached license with grace period
            if self.config.get('cached_license'):
                is_grace_valid, grace_msg = self.check_offline_grace()
                if is_grace_valid:
                    print(f"✅ {grace_msg}")
                    return True
                else:
                    print(f"❌ {grace_msg}")
                    return False
            else:
                print("❌ No license token provided and no cached license")
                return False
                
        # Validate provided token
        is_valid, message, token_data = self.validate_token(token, telegram_id)
        
        if is_valid:
            print(f"✅ License validation: {message}")
            return True
        else:
            print(f"❌ License validation failed: {message}")
            # Check grace period as fallback
            is_grace_valid, grace_msg = self.check_offline_grace()
            if is_grace_valid:
                print(f"✅ Fallback to grace period: {grace_msg}")
                return True
            return False


# Example usage and testing
def main():
    """Test the license checker"""
    print("🔐 Testing License Checker System")
    print("=" * 50)
    
    # Initialize license checker
    checker = LicenseChecker()
    
    # Generate demo token
    demo_token = checker.generate_demo_token(duration_days=30, telegram_id="123456789")
    print(f"📝 Generated demo token: {demo_token[:50]}...")
    
    # Test validation
    is_authorized = checker.block_unauthorized_access(token=demo_token, telegram_id="123456789")
    
    if is_authorized:
        print("✅ Access granted - application can start")
    else:
        print("❌ Access denied - application blocked")
        
    # Show license info
    license_info = checker.get_license_info()
    print(f"\n📊 License Info:")
    for key, value in license_info.items():
        print(f"   {key}: {value}")
        
    # Test with invalid token
    print(f"\n🧪 Testing with invalid token...")
    is_authorized = checker.block_unauthorized_access(token="invalid_token")
    print(f"Result: {'✅ Authorized' if is_authorized else '❌ Blocked'}")


if __name__ == "__main__":
    main()