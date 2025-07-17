# Authentication package
from .jwt_license_system import JWTLicenseSystem, LicenseStatus
from .telegram_auth import TelegramAuth

# Main authentication manager
class AuthTokenManager:
    """Main authentication token manager"""
    
    def __init__(self, config_file: str = "config.json"):
        self.jwt_system = JWTLicenseSystem(config_file)
        self.telegram_auth = TelegramAuth(config_file)
        
    def get_license_status(self):
        """Get current license status"""
        return self.jwt_system.get_license_status()
        
    def has_feature(self, feature: str) -> bool:
        """Check if current license has feature"""
        return self.jwt_system.has_feature(feature)
        
    async def activate_license(self, license_key: str, email: str):
        """Activate license"""
        return await self.jwt_system.activate_license(license_key, email)

def get_auth_token():
    """Get authentication token - for compatibility"""
    return "auth_token_placeholder"