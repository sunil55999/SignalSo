"""
License Engine for SignalOS Backend
Implements comprehensive licensing system with device binding and validation
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pydantic import BaseModel, field_validator
from utils.logging_config import get_logger

logger = get_logger(__name__)


class License(BaseModel):
    """License model following Part 2 guide"""
    id: str
    key: str
    user_id: str
    expires_at: datetime
    device_id: str
    active: bool
    plan_type: str = "standard"
    max_devices: int = 1
    created_at: datetime
    updated_at: datetime
    features: List[str] = []
    
    @field_validator("key")
    @classmethod
    def validate_license_key(cls, v):
        if len(v) != 32:
            raise ValueError("License key must be 32 characters")
        return v.upper()


class LicenseActivation(BaseModel):
    """License activation request"""
    license_key: str
    device_uuid: str
    device_fingerprint: str
    user_id: str


class LicenseRenewal(BaseModel):
    """License renewal request"""
    license_key: str
    renewal_period_days: int = 30
    payment_reference: Optional[str] = None


class LicenseStatus(BaseModel):
    """License status response"""
    license_key: str
    is_valid: bool
    is_active: bool
    expires_at: datetime
    days_remaining: int
    device_id: str
    plan_type: str
    features: List[str]
    max_devices: int
    devices_count: int


class LicenseEngine:
    """Comprehensive license management engine"""
    
    def __init__(self):
        self.licenses: Dict[str, License] = {}  # In production, use database
        self.device_licenses: Dict[str, str] = {}  # device_id -> license_key
        self.license_features = {
            "basic": ["signal_parsing", "manual_trading"],
            "standard": ["signal_parsing", "manual_trading", "auto_execution", "basic_analytics"],
            "premium": ["signal_parsing", "manual_trading", "auto_execution", "advanced_analytics", 
                       "custom_strategies", "multi_account"],
            "enterprise": ["signal_parsing", "manual_trading", "auto_execution", "advanced_analytics",
                          "custom_strategies", "multi_account", "api_access", "priority_support"]
        }
    
    def generate_license_key(self, user_id: str, plan_type: str = "standard") -> str:
        """Generate unique license key"""
        timestamp = int(datetime.utcnow().timestamp())
        data = f"{user_id}-{plan_type}-{timestamp}-{uuid.uuid4().hex[:8]}"
        hash_obj = hashlib.sha256(data.encode())
        license_key = hash_obj.hexdigest()[:32].upper()
        
        logger.info(f"Generated license key for user {user_id}, plan {plan_type}")
        return license_key
    
    def create_license(self, user_id: str, plan_type: str = "standard", 
                      duration_days: int = 30, device_id: str = None) -> License:
        """Create new license"""
        license_key = self.generate_license_key(user_id, plan_type)
        expires_at = datetime.utcnow() + timedelta(days=duration_days)
        
        # Set max devices based on plan
        max_devices_map = {"basic": 1, "standard": 2, "premium": 5, "enterprise": 10}
        max_devices = max_devices_map.get(plan_type, 1)
        
        license_obj = License(
            id=uuid.uuid4().hex,
            key=license_key,
            user_id=user_id,
            expires_at=expires_at,
            device_id=device_id or "",
            active=True,
            plan_type=plan_type,
            max_devices=max_devices,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            features=self.license_features.get(plan_type, [])
        )
        
        # Store license
        self.licenses[license_key] = license_obj
        
        if device_id:
            self.device_licenses[device_id] = license_key
        
        logger.info(f"Created license {license_key} for user {user_id}")
        return license_obj
    
    def activate_license(self, activation: LicenseActivation) -> bool:
        """Activate license for device"""
        license_obj = self.licenses.get(activation.license_key)
        
        if not license_obj:
            logger.warning(f"License {activation.license_key} not found")
            return False
        
        if not license_obj.active:
            logger.warning(f"License {activation.license_key} is not active")
            return False
        
        if license_obj.expires_at < datetime.utcnow():
            logger.warning(f"License {activation.license_key} has expired")
            return False
        
        if license_obj.user_id != activation.user_id:
            logger.warning(f"License {activation.license_key} user mismatch")
            return False
        
        # Generate device ID
        device_data = f"{activation.user_id}_{activation.device_uuid}_{activation.device_fingerprint}"
        device_id = hashlib.sha256(device_data.encode()).hexdigest()[:16]
        
        # Check device limit
        current_devices = sum(1 for did, lic_key in self.device_licenses.items() 
                            if lic_key == activation.license_key)
        
        if current_devices >= license_obj.max_devices:
            logger.warning(f"License {activation.license_key} device limit exceeded")
            return False
        
        # Activate for device
        license_obj.device_id = device_id
        license_obj.updated_at = datetime.utcnow()
        self.device_licenses[device_id] = activation.license_key
        
        logger.info(f"License {activation.license_key} activated for device {device_id}")
        return True
    
    def renew_license(self, renewal: LicenseRenewal) -> bool:
        """Renew license"""
        license_obj = self.licenses.get(renewal.license_key)
        
        if not license_obj:
            logger.warning(f"License {renewal.license_key} not found for renewal")
            return False
        
        # Extend expiration
        if license_obj.expires_at < datetime.utcnow():
            # License already expired, start from now
            license_obj.expires_at = datetime.utcnow() + timedelta(days=renewal.renewal_period_days)
        else:
            # License still valid, extend from current expiration
            license_obj.expires_at += timedelta(days=renewal.renewal_period_days)
        
        license_obj.updated_at = datetime.utcnow()
        
        logger.info(f"License {renewal.license_key} renewed for {renewal.renewal_period_days} days")
        return True
    
    def get_license_status(self, license_key: str) -> Optional[LicenseStatus]:
        """Get comprehensive license status"""
        license_obj = self.licenses.get(license_key)
        
        if not license_obj:
            return None
        
        now = datetime.utcnow()
        days_remaining = max(0, (license_obj.expires_at - now).days)
        is_valid = license_obj.active and license_obj.expires_at > now
        
        # Count active devices
        devices_count = sum(1 for did, lic_key in self.device_licenses.items() 
                          if lic_key == license_key)
        
        return LicenseStatus(
            license_key=license_key,
            is_valid=is_valid,
            is_active=license_obj.active,
            expires_at=license_obj.expires_at,
            days_remaining=days_remaining,
            device_id=license_obj.device_id,
            plan_type=license_obj.plan_type,
            features=license_obj.features,
            max_devices=license_obj.max_devices,
            devices_count=devices_count
        )
    
    def validate_license_for_device(self, license_key: str, device_id: str) -> bool:
        """Validate license for specific device"""
        license_obj = self.licenses.get(license_key)
        
        if not license_obj:
            logger.warning(f"License {license_key} not found")
            return False
        
        if not license_obj.active:
            logger.warning(f"License {license_key} is not active")
            return False
        
        if license_obj.expires_at < datetime.utcnow():
            logger.warning(f"License {license_key} has expired")
            return False
        
        # Check if device is bound to this license
        bound_license = self.device_licenses.get(device_id)
        if bound_license != license_key:
            logger.warning(f"Device {device_id} not bound to license {license_key}")
            return False
        
        return True
    
    def deactivate_license(self, license_key: str, reason: str = "manual") -> bool:
        """Deactivate license"""
        license_obj = self.licenses.get(license_key)
        
        if not license_obj:
            logger.warning(f"License {license_key} not found for deactivation")
            return False
        
        license_obj.active = False
        license_obj.updated_at = datetime.utcnow()
        
        # Remove device bindings
        devices_to_remove = [did for did, lic_key in self.device_licenses.items() 
                           if lic_key == license_key]
        for device_id in devices_to_remove:
            del self.device_licenses[device_id]
        
        logger.info(f"License {license_key} deactivated, reason: {reason}")
        return True
    
    def unbind_device(self, license_key: str, device_id: str) -> bool:
        """Unbind device from license"""
        if device_id in self.device_licenses and self.device_licenses[device_id] == license_key:
            del self.device_licenses[device_id]
            
            # Update license
            license_obj = self.licenses.get(license_key)
            if license_obj:
                license_obj.updated_at = datetime.utcnow()
                if license_obj.device_id == device_id:
                    license_obj.device_id = ""
            
            logger.info(f"Device {device_id} unbound from license {license_key}")
            return True
        
        logger.warning(f"Device {device_id} not bound to license {license_key}")
        return False
    
    def check_feature_access(self, license_key: str, feature: str) -> bool:
        """Check if license has access to specific feature"""
        license_obj = self.licenses.get(license_key)
        
        if not license_obj:
            return False
        
        if not self.validate_license_for_device(license_key, license_obj.device_id):
            return False
        
        return feature in license_obj.features
    
    def get_user_licenses(self, user_id: str) -> List[License]:
        """Get all licenses for user"""
        return [license_obj for license_obj in self.licenses.values() 
                if license_obj.user_id == user_id]
    
    def cleanup_expired_licenses(self) -> int:
        """Clean up expired licenses"""
        now = datetime.utcnow()
        expired_count = 0
        
        for license_key, license_obj in list(self.licenses.items()):
            if license_obj.expires_at < now and license_obj.active:
                self.deactivate_license(license_key, "expired")
                expired_count += 1
        
        logger.info(f"Cleaned up {expired_count} expired licenses")
        return expired_count


# Global license engine instance
license_engine = LicenseEngine()


def get_license_engine() -> LicenseEngine:
    """Get license engine instance"""
    return license_engine