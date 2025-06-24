"""
Terminal Identity Manager for SignalOS
Generates and manages unique terminal fingerprints for desktop application instances
"""

import json
import logging
import os
import platform
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
import subprocess
import psutil

class TerminalIdentityManager:
    """Manages unique terminal identification and fingerprinting"""
    
    def __init__(self, config_dir: str = ".signalos"):
        self.config_dir = Path.home() / config_dir
        self.identity_file = self.config_dir / "terminal_identity.json"
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Identity cache
        self._cached_identity = None
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for terminal identity manager"""
        logger = logging.getLogger('TerminalIdentityManager')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_terminal_id(self) -> str:
        """
        Get unique terminal ID, generating if not exists
        
        Returns:
            Unique terminal identifier string
        """
        # Check cache first
        if self._cached_identity:
            return self._cached_identity['terminal_id']
        
        # Try to load existing identity
        identity = self._load_identity()
        if identity and identity.get('terminal_id'):
            self._cached_identity = identity
            return identity['terminal_id']
        
        # Generate new identity
        identity = self._generate_identity()
        self._save_identity(identity)
        self._cached_identity = identity
        
        self.logger.info(f"Terminal ID: {identity['terminal_id']}")
        return identity['terminal_id']
    
    def _load_identity(self) -> Optional[Dict[str, Any]]:
        """Load existing terminal identity from file"""
        try:
            if self.identity_file.exists():
                with open(self.identity_file, 'r') as f:
                    identity = json.load(f)
                    self.logger.debug("Loaded existing terminal identity")
                    return identity
        except Exception as e:
            self.logger.error(f"Failed to load terminal identity: {e}")
        
        return None
    
    def _generate_identity(self) -> Dict[str, Any]:
        """Generate new terminal identity with fingerprinting"""
        # Generate base UUID
        base_uuid = str(uuid.uuid4())
        
        # Collect system information for fingerprinting
        system_info = self._collect_system_info()
        
        # Create fingerprint hash
        fingerprint_data = f"{base_uuid}:{system_info['os']}:{system_info['mac_address']}"
        fingerprint_hash = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
        
        # Create terminal ID
        terminal_id = f"{system_info['os'].lower()}-{fingerprint_hash}"
        
        identity = {
            'terminal_id': terminal_id,
            'base_uuid': base_uuid,
            'fingerprint_hash': fingerprint_hash,
            'system_info': system_info,
            'created_at': self._get_current_timestamp(),
            'version': '1.0'
        }
        
        self.logger.info(f"Generated new terminal identity: {terminal_id}")
        return identity
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information for fingerprinting"""
        system_info = {
            'os': self._get_os_info(),
            'mac_address': self._get_mac_address(),
            'hostname': self._get_hostname(),
            'cpu_info': self._get_cpu_info(),
            'memory_total': self._get_memory_info(),
            'python_version': self._get_python_version(),
            'architecture': platform.architecture()[0]
        }
        
        return system_info
    
    def _get_os_info(self) -> str:
        """Get operating system information"""
        try:
            system = platform.system()
            version = platform.version()
            
            if system == 'Windows':
                return f"Windows-{platform.release()}"
            elif system == 'Darwin':
                return f"macOS-{platform.mac_ver()[0]}"
            elif system == 'Linux':
                # Try to get distribution info
                try:
                    import distro
                    return f"Linux-{distro.name()}-{distro.version()}"
                except ImportError:
                    return f"Linux-{platform.release()}"
            else:
                return f"{system}-{platform.release()}"
                
        except Exception:
            return "Unknown"
    
    def _get_mac_address(self) -> str:
        """Get MAC address for fingerprinting"""
        try:
            # Get MAC address of first network interface
            mac = uuid.getnode()
            mac_str = ':'.join([f'{(mac >> i) & 0xff:02x}' for i in range(0, 48, 8)][::-1])
            return mac_str
        except Exception:
            return "unknown"
    
    def _get_hostname(self) -> str:
        """Get system hostname"""
        try:
            return platform.node() or "unknown"
        except Exception:
            return "unknown"
    
    def _get_cpu_info(self) -> str:
        """Get CPU information"""
        try:
            return platform.processor() or "unknown"
        except Exception:
            return "unknown"
    
    def _get_memory_info(self) -> int:
        """Get total system memory in GB"""
        try:
            memory_bytes = psutil.virtual_memory().total
            memory_gb = round(memory_bytes / (1024**3))
            return memory_gb
        except Exception:
            return 0
    
    def _get_python_version(self) -> str:
        """Get Python version"""
        try:
            return platform.python_version()
        except Exception:
            return "unknown"
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _save_identity(self, identity: Dict[str, Any]) -> bool:
        """Save terminal identity to file"""
        try:
            with open(self.identity_file, 'w') as f:
                json.dump(identity, f, indent=4)
            
            # Set restrictive permissions
            os.chmod(self.identity_file, 0o600)
            
            self.logger.debug("Terminal identity saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save terminal identity: {e}")
            return False
    
    def get_system_fingerprint(self) -> Dict[str, Any]:
        """Get complete system fingerprint information"""
        if not self._cached_identity:
            self.get_terminal_id()  # This will load or generate identity
        
        return self._cached_identity.copy() if self._cached_identity else {}
    
    def regenerate_identity(self) -> str:
        """Force regeneration of terminal identity"""
        try:
            # Remove existing identity file
            if self.identity_file.exists():
                os.remove(self.identity_file)
            
            # Clear cache
            self._cached_identity = None
            
            # Generate new identity
            new_terminal_id = self.get_terminal_id()
            
            self.logger.info(f"Regenerated terminal identity: {new_terminal_id}")
            return new_terminal_id
            
        except Exception as e:
            self.logger.error(f"Failed to regenerate identity: {e}")
            raise
    
    def get_identity_status(self) -> Dict[str, Any]:
        """Get status information about terminal identity"""
        status = {
            'has_identity': self.identity_file.exists(),
            'identity_file': str(self.identity_file),
            'terminal_id': None,
            'created_at': None,
            'system_info': None
        }
        
        if status['has_identity']:
            identity = self._load_identity()
            if identity:
                status.update({
                    'terminal_id': identity.get('terminal_id'),
                    'created_at': identity.get('created_at'),
                    'system_info': identity.get('system_info', {})
                })
        
        return status
    
    def verify_identity_integrity(self) -> bool:
        """Verify that stored identity matches current system"""
        try:
            if not self.identity_file.exists():
                return False
            
            stored_identity = self._load_identity()
            if not stored_identity:
                return False
            
            # Compare key system characteristics
            current_system = self._collect_system_info()
            stored_system = stored_identity.get('system_info', {})
            
            # Check critical components that shouldn't change
            critical_components = ['mac_address', 'hostname']
            
            for component in critical_components:
                if stored_system.get(component) != current_system.get(component):
                    self.logger.warning(f"Identity integrity check failed: {component} mismatch")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Identity integrity check failed: {e}")
            return False
    
    def get_terminal_metadata(self) -> Dict[str, Any]:
        """Get metadata for terminal registration"""
        fingerprint = self.get_system_fingerprint()
        system_info = fingerprint.get('system_info', {})
        
        return {
            'terminal_id': self.get_terminal_id(),
            'os': system_info.get('os', 'Unknown'),
            'hostname': system_info.get('hostname', 'Unknown'),
            'architecture': system_info.get('architecture', 'Unknown'),
            'python_version': system_info.get('python_version', 'Unknown'),
            'memory_gb': system_info.get('memory_total', 0),
            'version': '1.0.6',
            'app_name': 'SignalOS Desktop',
            'created_at': fingerprint.get('created_at')
        }


# Global instance for easy access
_terminal_identity_manager = None

def get_terminal_id() -> str:
    """
    Global function to get terminal ID
    
    Returns:
        Unique terminal identifier string
    """
    global _terminal_identity_manager
    
    if _terminal_identity_manager is None:
        _terminal_identity_manager = TerminalIdentityManager()
    
    return _terminal_identity_manager.get_terminal_id()

def get_system_fingerprint() -> Dict[str, Any]:
    """Global function to get system fingerprint"""
    global _terminal_identity_manager
    
    if _terminal_identity_manager is None:
        _terminal_identity_manager = TerminalIdentityManager()
    
    return _terminal_identity_manager.get_system_fingerprint()

def get_terminal_metadata() -> Dict[str, Any]:
    """Global function to get terminal metadata for registration"""
    global _terminal_identity_manager
    
    if _terminal_identity_manager is None:
        _terminal_identity_manager = TerminalIdentityManager()
    
    return _terminal_identity_manager.get_terminal_metadata()