"""
SignalOS Two-Factor Authentication System
Handles TOTP, SMS, and email-based 2FA
"""

import secrets
import base64
import qrcode
import io
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pyotp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from db.models import TwoFactorAuth, User
from utils.logging_config import get_logger

logger = get_logger(__name__)


class TwoFactorAuthEngine:
    """Core 2FA engine"""
    
    def __init__(self):
        self.otp_codes = {}  # Temporary storage for OTP codes
        self.backup_codes = {}  # Backup codes storage
        
    async def initialize(self):
        """Initialize 2FA engine"""
        try:
            logger.info("2FA engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize 2FA engine: {e}")
            raise
    
    async def setup_totp(self, user_id: str, issuer: str = "SignalOS") -> Dict[str, Any]:
        """Setup TOTP authentication for user"""
        try:
            # Generate secret key
            secret = pyotp.random_base32()
            
            # Create TOTP instance
            totp = pyotp.TOTP(secret)
            
            # Generate provisioning URI
            provisioning_uri = totp.provisioning_uri(
                name=user_id,
                issuer_name=issuer
            )
            
            # Generate QR code
            qr_code = await self._generate_qr_code(provisioning_uri)
            
            # Generate backup codes
            backup_codes = await self._generate_backup_codes()
            
            # Store in database (pending activation)
            await self._store_2fa_setup(user_id, "TOTP", {
                "secret": secret,
                "backup_codes": backup_codes,
                "is_active": False
            })
            
            logger.info(f"TOTP setup initiated for user {user_id}")
            
            return {
                "success": True,
                "setup_data": {
                    "secret": secret,
                    "qr_code": qr_code,
                    "backup_codes": backup_codes,
                    "provisioning_uri": provisioning_uri
                },
                "message": "TOTP setup ready. Please verify with your authenticator app."
            }
            
        except Exception as e:
            logger.error(f"TOTP setup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def setup_sms(self, user_id: str, phone_number: str) -> Dict[str, Any]:
        """Setup SMS authentication for user"""
        try:
            # Validate phone number format
            if not await self._validate_phone_number(phone_number):
                return {
                    "success": False,
                    "error": "Invalid phone number format"
                }
            
            # Generate and send verification code
            verification_code = await self._generate_verification_code()
            
            # Store temporarily
            self.otp_codes[user_id] = {
                "code": verification_code,
                "expires": datetime.now() + timedelta(minutes=5),
                "phone_number": phone_number,
                "verified": False
            }
            
            # Send SMS
            sms_result = await self._send_sms(phone_number, verification_code)
            
            if not sms_result["success"]:
                return {
                    "success": False,
                    "error": "Failed to send SMS verification code"
                }
            
            logger.info(f"SMS 2FA setup initiated for user {user_id}")
            
            return {
                "success": True,
                "message": f"Verification code sent to {phone_number}",
                "expires_in": 300  # 5 minutes
            }
            
        except Exception as e:
            logger.error(f"SMS setup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def setup_email(self, user_id: str, email: str) -> Dict[str, Any]:
        """Setup email authentication for user"""
        try:
            # Validate email format
            if not await self._validate_email(email):
                return {
                    "success": False,
                    "error": "Invalid email format"
                }
            
            # Generate and send verification code
            verification_code = await self._generate_verification_code()
            
            # Store temporarily
            self.otp_codes[user_id] = {
                "code": verification_code,
                "expires": datetime.now() + timedelta(minutes=10),
                "email": email,
                "verified": False
            }
            
            # Send email
            email_result = await self._send_email(email, verification_code)
            
            if not email_result["success"]:
                return {
                    "success": False,
                    "error": "Failed to send email verification code"
                }
            
            logger.info(f"Email 2FA setup initiated for user {user_id}")
            
            return {
                "success": True,
                "message": f"Verification code sent to {email}",
                "expires_in": 600  # 10 minutes
            }
            
        except Exception as e:
            logger.error(f"Email setup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_totp_setup(self, user_id: str, code: str) -> Dict[str, Any]:
        """Verify TOTP setup with user-provided code"""
        try:
            # Get pending setup
            setup_data = await self._get_pending_2fa_setup(user_id, "TOTP")
            
            if not setup_data:
                return {
                    "success": False,
                    "error": "No pending TOTP setup found"
                }
            
            # Verify code
            totp = pyotp.TOTP(setup_data["secret"])
            
            if not totp.verify(code, valid_window=1):
                return {
                    "success": False,
                    "error": "Invalid verification code"
                }
            
            # Activate 2FA
            await self._activate_2fa(user_id, "TOTP", setup_data)
            
            logger.info(f"TOTP 2FA activated for user {user_id}")
            
            return {
                "success": True,
                "message": "TOTP 2FA activated successfully",
                "backup_codes": setup_data["backup_codes"]
            }
            
        except Exception as e:
            logger.error(f"TOTP verification failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_sms_setup(self, user_id: str, code: str) -> Dict[str, Any]:
        """Verify SMS setup with user-provided code"""
        try:
            if user_id not in self.otp_codes:
                return {
                    "success": False,
                    "error": "No pending SMS setup found"
                }
            
            otp_data = self.otp_codes[user_id]
            
            # Check expiry
            if datetime.now() > otp_data["expires"]:
                del self.otp_codes[user_id]
                return {
                    "success": False,
                    "error": "Verification code expired"
                }
            
            # Verify code
            if otp_data["code"] != code:
                return {
                    "success": False,
                    "error": "Invalid verification code"
                }
            
            # Generate backup codes
            backup_codes = await self._generate_backup_codes()
            
            # Activate 2FA
            await self._activate_2fa(user_id, "SMS", {
                "phone_number": otp_data["phone_number"],
                "backup_codes": backup_codes
            })
            
            # Clean up
            del self.otp_codes[user_id]
            
            logger.info(f"SMS 2FA activated for user {user_id}")
            
            return {
                "success": True,
                "message": "SMS 2FA activated successfully",
                "backup_codes": backup_codes
            }
            
        except Exception as e:
            logger.error(f"SMS verification failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_email_setup(self, user_id: str, code: str) -> Dict[str, Any]:
        """Verify email setup with user-provided code"""
        try:
            if user_id not in self.otp_codes:
                return {
                    "success": False,
                    "error": "No pending email setup found"
                }
            
            otp_data = self.otp_codes[user_id]
            
            # Check expiry
            if datetime.now() > otp_data["expires"]:
                del self.otp_codes[user_id]
                return {
                    "success": False,
                    "error": "Verification code expired"
                }
            
            # Verify code
            if otp_data["code"] != code:
                return {
                    "success": False,
                    "error": "Invalid verification code"
                }
            
            # Generate backup codes
            backup_codes = await self._generate_backup_codes()
            
            # Activate 2FA
            await self._activate_2fa(user_id, "EMAIL", {
                "email": otp_data["email"],
                "backup_codes": backup_codes
            })
            
            # Clean up
            del self.otp_codes[user_id]
            
            logger.info(f"Email 2FA activated for user {user_id}")
            
            return {
                "success": True,
                "message": "Email 2FA activated successfully",
                "backup_codes": backup_codes
            }
            
        except Exception as e:
            logger.error(f"Email verification failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_2fa_code(self, user_id: str, code: str) -> Dict[str, Any]:
        """Verify 2FA code during authentication"""
        try:
            # Get user's 2FA method
            auth_method = await self._get_user_2fa_method(user_id)
            
            if not auth_method:
                return {
                    "success": False,
                    "error": "2FA not enabled for user"
                }
            
            if auth_method["method"] == "TOTP":
                return await self._verify_totp_code(user_id, code, auth_method)
            elif auth_method["method"] == "SMS":
                return await self._verify_sms_code(user_id, code, auth_method)
            elif auth_method["method"] == "EMAIL":
                return await self._verify_email_code(user_id, code, auth_method)
            else:
                return {
                    "success": False,
                    "error": "Unknown 2FA method"
                }
                
        except Exception as e:
            logger.error(f"2FA verification failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _verify_totp_code(self, user_id: str, code: str, auth_method: Dict[str, Any]) -> Dict[str, Any]:
        """Verify TOTP code"""
        try:
            # First check if it's a backup code
            if await self._is_backup_code(user_id, code):
                await self._use_backup_code(user_id, code)
                return {
                    "success": True,
                    "message": "Backup code verified",
                    "method": "backup_code"
                }
            
            # Verify TOTP code
            totp = pyotp.TOTP(auth_method["secret"])
            
            if totp.verify(code, valid_window=1):
                await self._update_2fa_last_used(user_id)
                return {
                    "success": True,
                    "message": "TOTP code verified",
                    "method": "totp"
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid TOTP code"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _verify_sms_code(self, user_id: str, code: str, auth_method: Dict[str, Any]) -> Dict[str, Any]:
        """Verify SMS code"""
        try:
            # Check if there's a pending SMS code
            if user_id not in self.otp_codes:
                return {
                    "success": False,
                    "error": "No SMS code requested"
                }
            
            otp_data = self.otp_codes[user_id]
            
            # Check expiry
            if datetime.now() > otp_data["expires"]:
                del self.otp_codes[user_id]
                return {
                    "success": False,
                    "error": "SMS code expired"
                }
            
            # Verify code
            if otp_data["code"] == code:
                del self.otp_codes[user_id]
                await self._update_2fa_last_used(user_id)
                return {
                    "success": True,
                    "message": "SMS code verified",
                    "method": "sms"
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid SMS code"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _verify_email_code(self, user_id: str, code: str, auth_method: Dict[str, Any]) -> Dict[str, Any]:
        """Verify email code"""
        try:
            # Check if there's a pending email code
            if user_id not in self.otp_codes:
                return {
                    "success": False,
                    "error": "No email code requested"
                }
            
            otp_data = self.otp_codes[user_id]
            
            # Check expiry
            if datetime.now() > otp_data["expires"]:
                del self.otp_codes[user_id]
                return {
                    "success": False,
                    "error": "Email code expired"
                }
            
            # Verify code
            if otp_data["code"] == code:
                del self.otp_codes[user_id]
                await self._update_2fa_last_used(user_id)
                return {
                    "success": True,
                    "message": "Email code verified",
                    "method": "email"
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid email code"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def request_2fa_code(self, user_id: str) -> Dict[str, Any]:
        """Request new 2FA code for SMS/Email methods"""
        try:
            auth_method = await self._get_user_2fa_method(user_id)
            
            if not auth_method:
                return {
                    "success": False,
                    "error": "2FA not enabled for user"
                }
            
            if auth_method["method"] == "SMS":
                return await self._send_sms_code(user_id, auth_method["phone_number"])
            elif auth_method["method"] == "EMAIL":
                return await self._send_email_code(user_id, auth_method["email"])
            else:
                return {
                    "success": False,
                    "error": "Code request not supported for this 2FA method"
                }
                
        except Exception as e:
            logger.error(f"2FA code request failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_sms_code(self, user_id: str, phone_number: str) -> Dict[str, Any]:
        """Send SMS code to user"""
        try:
            verification_code = await self._generate_verification_code()
            
            # Store temporarily
            self.otp_codes[user_id] = {
                "code": verification_code,
                "expires": datetime.now() + timedelta(minutes=5),
                "phone_number": phone_number
            }
            
            # Send SMS
            sms_result = await self._send_sms(phone_number, verification_code)
            
            if sms_result["success"]:
                return {
                    "success": True,
                    "message": "SMS code sent",
                    "expires_in": 300
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to send SMS"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_email_code(self, user_id: str, email: str) -> Dict[str, Any]:
        """Send email code to user"""
        try:
            verification_code = await self._generate_verification_code()
            
            # Store temporarily
            self.otp_codes[user_id] = {
                "code": verification_code,
                "expires": datetime.now() + timedelta(minutes=10),
                "email": email
            }
            
            # Send email
            email_result = await self._send_email(email, verification_code)
            
            if email_result["success"]:
                return {
                    "success": True,
                    "message": "Email code sent",
                    "expires_in": 600
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to send email"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def disable_2fa(self, user_id: str) -> Dict[str, Any]:
        """Disable 2FA for user"""
        try:
            # Remove from database
            await self._remove_2fa_from_db(user_id)
            
            # Clean up temporary data
            if user_id in self.otp_codes:
                del self.otp_codes[user_id]
            
            if user_id in self.backup_codes:
                del self.backup_codes[user_id]
            
            logger.info(f"2FA disabled for user {user_id}")
            
            return {
                "success": True,
                "message": "2FA disabled successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to disable 2FA: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def regenerate_backup_codes(self, user_id: str) -> Dict[str, Any]:
        """Regenerate backup codes for user"""
        try:
            # Generate new backup codes
            new_backup_codes = await self._generate_backup_codes()
            
            # Update database
            await self._update_backup_codes(user_id, new_backup_codes)
            
            logger.info(f"Backup codes regenerated for user {user_id}")
            
            return {
                "success": True,
                "backup_codes": new_backup_codes,
                "message": "Backup codes regenerated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to regenerate backup codes: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_2fa_status(self, user_id: str) -> Dict[str, Any]:
        """Get 2FA status for user"""
        try:
            auth_method = await self._get_user_2fa_method(user_id)
            
            if not auth_method:
                return {
                    "enabled": False,
                    "method": None,
                    "message": "2FA not enabled"
                }
            
            return {
                "enabled": True,
                "method": auth_method["method"],
                "last_used": auth_method.get("last_used"),
                "backup_codes_remaining": await self._count_remaining_backup_codes(user_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to get 2FA status: {e}")
            return {
                "enabled": False,
                "error": str(e)
            }
    
    # Helper methods
    
    async def _generate_qr_code(self, provisioning_uri: str) -> str:
        """Generate QR code for TOTP setup"""
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            img_io = io.BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            
            return base64.b64encode(img_io.read()).decode('utf-8')
            
        except Exception as e:
            logger.error(f"QR code generation failed: {e}")
            raise
    
    async def _generate_backup_codes(self) -> List[str]:
        """Generate backup codes"""
        codes = []
        for _ in range(10):  # Generate 10 backup codes
            code = secrets.token_hex(4).upper()  # 8 character codes
            codes.append(code)
        return codes
    
    async def _generate_verification_code(self) -> str:
        """Generate verification code"""
        return str(secrets.randbelow(900000) + 100000)  # 6-digit code
    
    async def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        # Basic validation - in production, use proper phone validation
        return len(phone_number) >= 10 and phone_number.replace('+', '').replace('-', '').replace(' ', '').isdigit()
    
    async def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    async def _send_sms(self, phone_number: str, code: str) -> Dict[str, Any]:
        """Send SMS (mock implementation)"""
        # In production, integrate with Twilio, AWS SNS, etc.
        logger.info(f"SMS would be sent to {phone_number}: {code}")
        return {
            "success": True,
            "message": "SMS sent successfully"
        }
    
    async def _send_email(self, email: str, code: str) -> Dict[str, Any]:
        """Send email (mock implementation)"""
        # In production, integrate with SMTP, SendGrid, etc.
        logger.info(f"Email would be sent to {email}: {code}")
        return {
            "success": True,
            "message": "Email sent successfully"
        }
    
    async def _store_2fa_setup(self, user_id: str, method: str, data: Dict[str, Any]):
        """Store 2FA setup in database"""
        # This would store in your database
        logger.info(f"2FA setup stored: {user_id} -> {method}")
    
    async def _get_pending_2fa_setup(self, user_id: str, method: str) -> Optional[Dict[str, Any]]:
        """Get pending 2FA setup from database"""
        # This would query your database
        # For now, return mock data
        return {
            "secret": "JBSWY3DPEHPK3PXP",
            "backup_codes": ["12345678", "87654321"]
        }
    
    async def _activate_2fa(self, user_id: str, method: str, data: Dict[str, Any]):
        """Activate 2FA in database"""
        # This would update your database
        logger.info(f"2FA activated: {user_id} -> {method}")
    
    async def _get_user_2fa_method(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's 2FA method from database"""
        # This would query your database
        # For now, return None (no 2FA enabled)
        return None
    
    async def _is_backup_code(self, user_id: str, code: str) -> bool:
        """Check if code is a backup code"""
        # This would check against database
        return False
    
    async def _use_backup_code(self, user_id: str, code: str):
        """Mark backup code as used"""
        # This would update your database
        logger.info(f"Backup code used: {user_id} -> {code}")
    
    async def _update_2fa_last_used(self, user_id: str):
        """Update last used timestamp"""
        # This would update your database
        logger.info(f"2FA last used updated: {user_id}")
    
    async def _remove_2fa_from_db(self, user_id: str):
        """Remove 2FA from database"""
        # This would delete from your database
        logger.info(f"2FA removed from DB: {user_id}")
    
    async def _update_backup_codes(self, user_id: str, backup_codes: List[str]):
        """Update backup codes in database"""
        # This would update your database
        logger.info(f"Backup codes updated: {user_id}")
    
    async def _count_remaining_backup_codes(self, user_id: str) -> int:
        """Count remaining backup codes"""
        # This would query your database
        return 10  # Mock data