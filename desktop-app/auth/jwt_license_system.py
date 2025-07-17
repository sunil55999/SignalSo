#!/usr/bin/env python3
"""
JWT License System for SignalOS Desktop Application

Implements JWT-based license validation and authentication using FastAPI.
Manages license verification, activation, and expiration handling.
"""

import jwt
import json
import logging
import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import platform
import psutil
import requests
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

class LicenseStatus(Enum):
    """License status enumeration"""
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    REVOKED = "revoked"
    NOT_FOUND = "not_found"
    HARDWARE_MISMATCH = "hardware_mismatch"

class LicenseType(Enum):
    """License type enumeration"""
    TRIAL = "trial"
    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

@dataclass
class LicenseInfo:
    """License information structure"""
    license_key: str
    license_type: LicenseType
    user_id: str
    email: str
    issued_at: datetime
    expires_at: datetime
    hardware_id: str
    features: List[str]
    max_accounts: int
    status: LicenseStatus

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['license_type'] = self.license_type.value
        result['status'] = self.status.value
        result['issued_at'] = self.issued_at.isoformat()
        result['expires_at'] = self.expires_at.isoformat()
        return result

    def is_expired(self) -> bool:
        """Check if license is expired"""
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

class JWTLicenseSystem:
    """JWT-based license validation system"""
    
    def __init__(self, config_file: str = "config.json", license_file: str = "license.json"):
        self.config_file = config_file
        self.license_file = license_file
        self.config = self._load_config()
        self._setup_logging()
        
        # JWT configuration
        self.secret_key = self.config.get("secret_key", self._generate_secret_key())
        self.algorithm = self.config.get("algorithm", "HS256")
        self.issuer = self.config.get("issuer", "SignalOS")
        
        # License server configuration
        self.license_server_url = self.config.get("license_server_url", "https://api.signalos.com")
        self.offline_grace_period = self.config.get("offline_grace_period_hours", 72)
        
        # Current license info
        self.current_license: Optional[LicenseInfo] = None
        self.hardware_id = self._generate_hardware_id()
        
        # FastAPI app for license server
        self.app = FastAPI(title="SignalOS License Server", version="1.0.0")
        self._setup_routes()
        
        # Load existing license
        self._load_license()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load license system configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('jwt_license_system', self._get_default_config())
        except FileNotFoundError:
            return self._create_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default license configuration"""
        return {
            "secret_key": None,  # Will be generated
            "algorithm": "HS256",
            "issuer": "SignalOS",
            "license_server_url": "https://api.signalos.com",
            "offline_grace_period_hours": 72,
            "validation_interval_hours": 24,
            "auto_validate": True,
            "require_internet_activation": True,
            "trial_period_days": 7,
            "features": {
                "trial": ["basic_signals", "manual_trading"],
                "personal": ["basic_signals", "manual_trading", "auto_trading", "telegram_bot"],
                "professional": ["basic_signals", "manual_trading", "auto_trading", "telegram_bot", "ocr_signals", "advanced_strategies"],
                "enterprise": ["basic_signals", "manual_trading", "auto_trading", "telegram_bot", "ocr_signals", "advanced_strategies", "multi_account", "api_access"]
            }
        }
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration and save to file"""
        default_config = {
            "jwt_license_system": self._get_default_config()
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
            
        return default_config["jwt_license_system"]
    
    def _setup_logging(self):
        """Setup logging for license system"""
        self.logger = logging.getLogger('JWTLicenseSystem')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _generate_secret_key(self) -> str:
        """Generate a random secret key for JWT signing"""
        return str(uuid.uuid4().hex + uuid.uuid4().hex)
    
    def _generate_hardware_id(self) -> str:
        """Generate unique hardware ID for license binding"""
        try:
            # Collect hardware information
            system_info = {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "machine": platform.machine(),
                "node": platform.node()
            }
            
            # Add MAC address if available
            try:
                import uuid
                mac = ':'.join(f'{(uuid.getnode() >> elements) & 0xff:02x}' for elements in range(0,2*6,2))[::-1]
                system_info["mac"] = mac
            except:
                pass
            
            # Add CPU count
            system_info["cpu_count"] = psutil.cpu_count()
            
            # Create hash from system info
            info_string = json.dumps(system_info, sort_keys=True)
            hardware_id = hashlib.sha256(info_string.encode()).hexdigest()[:16]
            
            self.logger.info(f"Generated hardware ID: {hardware_id}")
            return hardware_id
            
        except Exception as e:
            self.logger.error(f"Error generating hardware ID: {e}")
            # Fallback to platform-based ID
            return hashlib.sha256(platform.platform().encode()).hexdigest()[:16]
    
    def _setup_routes(self):
        """Setup FastAPI routes for license validation"""
        security = HTTPBearer()
        
        @self.app.post("/activate")
        async def activate_license(license_key: str, user_email: str):
            """Activate a license key"""
            try:
                result = await self.activate_license(license_key, user_email)
                return {"success": True, "license": result.to_dict() if result else None}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/validate")
        async def validate_license(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """Validate current license"""
            try:
                token = credentials.credentials
                result = self.validate_jwt_token(token)
                return {"success": True, "valid": result is not None, "license": result.to_dict() if result else None}
            except Exception as e:
                raise HTTPException(status_code=401, detail=str(e))
        
        @self.app.get("/status")
        async def license_status():
            """Get current license status"""
            if self.current_license:
                return {"success": True, "status": self.current_license.status.value, "license": self.current_license.to_dict()}
            else:
                return {"success": False, "status": "not_found", "license": None}
        
        @self.app.post("/refresh")
        async def refresh_license(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """Refresh license validation"""
            try:
                await self.refresh_license_validation()
                return {"success": True, "license": self.current_license.to_dict() if self.current_license else None}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
    
    def create_jwt_token(self, license_info: LicenseInfo) -> str:
        """Create JWT token from license information"""
        try:
            payload = {
                "iss": self.issuer,
                "sub": license_info.user_id,
                "email": license_info.email,
                "license_key": license_info.license_key,
                "license_type": license_info.license_type.value,
                "hardware_id": license_info.hardware_id,
                "features": license_info.features,
                "max_accounts": license_info.max_accounts,
                "iat": int(license_info.issued_at.timestamp()),
                "exp": int(license_info.expires_at.timestamp())
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return token
            
        except Exception as e:
            self.logger.error(f"Error creating JWT token: {e}")
            raise
    
    def validate_jwt_token(self, token: str) -> Optional[LicenseInfo]:
        """Validate JWT token and return license information"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], issuer=self.issuer)
            
            # Extract license information
            license_info = LicenseInfo(
                license_key=payload["license_key"],
                license_type=LicenseType(payload["license_type"]),
                user_id=payload["sub"],
                email=payload["email"],
                issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                hardware_id=payload["hardware_id"],
                features=payload["features"],
                max_accounts=payload["max_accounts"],
                status=LicenseStatus.VALID
            )
            
            # Validate hardware ID
            if license_info.hardware_id != self.hardware_id:
                license_info.status = LicenseStatus.HARDWARE_MISMATCH
                self.logger.warning(f"Hardware ID mismatch: expected {license_info.hardware_id}, got {self.hardware_id}")
                return license_info
            
            # Check expiration
            if license_info.is_expired():
                license_info.status = LicenseStatus.EXPIRED
                self.logger.warning(f"License expired at {license_info.expires_at}")
                return license_info
            
            return license_info
            
        except jwt.ExpiredSignatureError:
            self.logger.error("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.error(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error validating JWT token: {e}")
            return None
    
    async def activate_license(self, license_key: str, user_email: str) -> Optional[LicenseInfo]:
        """Activate a license key online"""
        try:
            # Make request to license server
            activation_data = {
                "license_key": license_key,
                "user_email": user_email,
                "hardware_id": self.hardware_id,
                "platform": platform.platform(),
                "app_version": "1.0.0"
            }
            
            url = f"{self.license_server_url}/api/licenses/activate"
            response = requests.post(url, json=activation_data, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Create license info from response
                license_info = LicenseInfo(
                    license_key=license_key,
                    license_type=LicenseType(data["license_type"]),
                    user_id=data["user_id"],
                    email=user_email,
                    issued_at=datetime.fromisoformat(data["issued_at"]),
                    expires_at=datetime.fromisoformat(data["expires_at"]),
                    hardware_id=self.hardware_id,
                    features=data["features"],
                    max_accounts=data["max_accounts"],
                    status=LicenseStatus.VALID
                )
                
                # Save license locally
                self.current_license = license_info
                self._save_license()
                
                self.logger.info(f"License activated successfully for {user_email}")
                return license_info
                
            else:
                error_msg = f"License activation failed: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.RequestException as e:
            # Try offline activation for trial licenses
            if self.config.get("trial_period_days", 0) > 0:
                return self._create_trial_license(user_email)
            else:
                self.logger.error(f"License activation failed (offline): {e}")
                raise Exception("License activation requires internet connection")
    
    def _create_trial_license(self, user_email: str) -> LicenseInfo:
        """Create a trial license for offline use"""
        trial_days = self.config.get("trial_period_days", 7)
        features = self.config.get("features", {}).get("trial", ["basic_signals"])
        
        license_info = LicenseInfo(
            license_key="TRIAL-" + str(uuid.uuid4())[:8].upper(),
            license_type=LicenseType.TRIAL,
            user_id="trial-" + str(uuid.uuid4())[:8],
            email=user_email,
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=trial_days),
            hardware_id=self.hardware_id,
            features=features,
            max_accounts=1,
            status=LicenseStatus.VALID
        )
        
        self.current_license = license_info
        self._save_license()
        
        self.logger.info(f"Trial license created for {user_email} (expires in {trial_days} days)")
        return license_info
    
    async def refresh_license_validation(self):
        """Refresh license validation with server"""
        if not self.current_license:
            raise Exception("No license to refresh")
        
        try:
            url = f"{self.license_server_url}/api/licenses/validate"
            validation_data = {
                "license_key": self.current_license.license_key,
                "hardware_id": self.hardware_id
            }
            
            response = requests.post(url, json=validation_data, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data["valid"]:
                    self.current_license.status = LicenseStatus.VALID
                    self.logger.info("License validation successful")
                else:
                    self.current_license.status = LicenseStatus(data["status"])
                    self.logger.warning(f"License validation failed: {data['status']}")
            else:
                self.logger.warning(f"License validation server error: {response.status_code}")
                
        except requests.RequestException as e:
            # Use offline grace period
            last_validation = getattr(self.current_license, 'last_validation', self.current_license.issued_at)
            grace_period = timedelta(hours=self.offline_grace_period)
            
            if datetime.now(timezone.utc) - last_validation.replace(tzinfo=timezone.utc) > grace_period:
                self.current_license.status = LicenseStatus.INVALID
                self.logger.error(f"License validation failed and grace period expired: {e}")
            else:
                self.logger.warning(f"License validation failed but within grace period: {e}")
    
    def _save_license(self):
        """Save current license to file"""
        try:
            if self.current_license:
                license_data = {
                    "license_info": self.current_license.to_dict(),
                    "hardware_id": self.hardware_id,
                    "last_saved": datetime.now().isoformat()
                }
                
                with open(self.license_file, 'w') as f:
                    json.dump(license_data, f, indent=4)
                    
        except Exception as e:
            self.logger.error(f"Failed to save license: {e}")
    
    def _load_license(self):
        """Load license from file"""
        try:
            if Path(self.license_file).exists():
                with open(self.license_file, 'r') as f:
                    license_data = json.load(f)
                
                # Verify hardware ID
                if license_data.get("hardware_id") != self.hardware_id:
                    self.logger.warning("License hardware ID mismatch, removing license")
                    Path(self.license_file).unlink()
                    return
                
                # Reconstruct license info
                info = license_data["license_info"]
                self.current_license = LicenseInfo(
                    license_key=info["license_key"],
                    license_type=LicenseType(info["license_type"]),
                    user_id=info["user_id"],
                    email=info["email"],
                    issued_at=datetime.fromisoformat(info["issued_at"]),
                    expires_at=datetime.fromisoformat(info["expires_at"]),
                    hardware_id=info["hardware_id"],
                    features=info["features"],
                    max_accounts=info["max_accounts"],
                    status=LicenseStatus(info["status"])
                )
                
                # Check if expired
                if self.current_license.is_expired():
                    self.current_license.status = LicenseStatus.EXPIRED
                
                self.logger.info(f"Loaded license: {self.current_license.license_type.value} - {self.current_license.status.value}")
                
        except Exception as e:
            self.logger.error(f"Failed to load license: {e}")
    
    def has_feature(self, feature: str) -> bool:
        """Check if current license has a specific feature"""
        if not self.current_license or self.current_license.status != LicenseStatus.VALID:
            return False
        
        return feature in self.current_license.features
    
    def get_license_status(self) -> Dict[str, Any]:
        """Get current license status"""
        if not self.current_license:
            return {
                "status": LicenseStatus.NOT_FOUND.value,
                "license": None,
                "hardware_id": self.hardware_id
            }
        
        return {
            "status": self.current_license.status.value,
            "license": self.current_license.to_dict(),
            "hardware_id": self.hardware_id
        }
    
    async def start_license_server(self, host: str = "127.0.0.1", port: int = 8001):
        """Start the license validation server"""
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        
        self.logger.info(f"Starting license server on {host}:{port}")
        await server.serve()


# Example usage and testing
async def main():
    """Example usage of JWT license system"""
    license_system = JWTLicenseSystem()
    
    # Example: Activate a trial license
    try:
        license_info = await license_system.activate_license("TRIAL-KEY", "test@example.com")
        print(f"License activated: {license_info.license_type.value}")
        print(f"Features: {license_info.features}")
        print(f"Expires: {license_info.expires_at}")
        
        # Test feature checking
        print(f"Has basic_signals: {license_system.has_feature('basic_signals')}")
        print(f"Has advanced_strategies: {license_system.has_feature('advanced_strategies')}")
        
        # Get status
        status = license_system.get_license_status()
        print(f"License status: {json.dumps(status, indent=2)}")
        
    except Exception as e:
        print(f"License activation failed: {e}")
    
    # Optionally start license server
    # await license_system.start_license_server()


if __name__ == "__main__":
    asyncio.run(main())