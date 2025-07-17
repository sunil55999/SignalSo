#!/usr/bin/env python3
"""
Version Manager for SignalOS Model Updates
Helper functions for version comparison and management
"""

import re
import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from datetime import datetime
import logging


class VersionManager:
    """Manages version comparisons and remote version fetching"""
    
    def __init__(self, backend_url: str = "https://api.signalojs.com"):
        self.backend_url = backend_url.rstrip('/')
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / "version_manager.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def parse_version(self, version_string: str) -> Tuple[List[int], str]:
        """
        Parse version string into components
        Returns (version_numbers, prerelease_info)
        """
        try:
            # Handle semantic versioning: 1.2.3-beta.1+build.123
            version_pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?(?:\+([a-zA-Z0-9\-\.]+))?$'
            match = re.match(version_pattern, version_string.strip())
            
            if match:
                major, minor, patch, prerelease, build = match.groups()
                version_numbers = [int(major), int(minor), int(patch)]
                prerelease_info = prerelease or ""
                
                return version_numbers, prerelease_info
            else:
                # Fallback to simple dot-separated numbers
                parts = version_string.split('.')
                version_numbers = [int(part) for part in parts if part.isdigit()]
                return version_numbers, ""
                
        except Exception as e:
            self.logger.warning(f"Failed to parse version '{version_string}': {e}")
            return [1, 0, 0], ""
            
    def compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings
        Returns: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        try:
            v1_numbers, v1_pre = self.parse_version(version1)
            v2_numbers, v2_pre = self.parse_version(version2)
            
            # Pad shorter version with zeros
            max_len = max(len(v1_numbers), len(v2_numbers))
            v1_numbers.extend([0] * (max_len - len(v1_numbers)))
            v2_numbers.extend([0] * (max_len - len(v2_numbers)))
            
            # Compare version numbers
            for v1, v2 in zip(v1_numbers, v2_numbers):
                if v1 < v2:
                    return -1
                elif v1 > v2:
                    return 1
                    
            # If version numbers are equal, compare prerelease
            if v1_pre != v2_pre:
                # Release version > prerelease version
                if not v1_pre and v2_pre:
                    return 1
                elif v1_pre and not v2_pre:
                    return -1
                elif v1_pre and v2_pre:
                    # Compare prerelease versions lexicographically
                    if v1_pre < v2_pre:
                        return -1
                    elif v1_pre > v2_pre:
                        return 1
                        
            return 0  # Versions are equal
            
        except Exception as e:
            self.logger.error(f"Version comparison failed: {e}")
            return 0
            
    def is_newer_version(self, current_version: str, new_version: str) -> bool:
        """Check if new_version is newer than current_version"""
        return self.compare_versions(current_version, new_version) < 0
        
    async def fetch_version_info(self, endpoint: str = "/api/models/version.json") -> Optional[Dict[str, Any]]:
        """Fetch version information from remote endpoint"""
        try:
            url = f"{self.backend_url}{endpoint}"
            timeout = aiohttp.ClientTimeout(total=30)
            
            self.logger.info(f"Fetching version info from: {url}")
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        version_data = await response.json()
                        self.logger.info(f"Fetched version: {version_data.get('version', 'unknown')}")
                        return version_data
                    else:
                        self.logger.error(f"Failed to fetch version info: HTTP {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Error fetching version info: {e}")
            return None
            
    def validate_version_data(self, version_data: Dict[str, Any]) -> bool:
        """Validate that version data contains required fields"""
        required_fields = ['version', 'model_url']
        optional_fields = ['checksum', 'size', 'model_name', 'release_date']
        
        # Check required fields
        for field in required_fields:
            if field not in version_data:
                self.logger.error(f"Missing required field in version data: {field}")
                return False
                
        # Validate version format
        version = version_data.get('version', '')
        if not re.match(r'^\d+\.\d+\.\d+', version):
            self.logger.error(f"Invalid version format: {version}")
            return False
            
        # Validate model URL
        model_url = version_data.get('model_url', '')
        if not model_url.startswith(('http://', 'https://')):
            self.logger.error(f"Invalid model URL: {model_url}")
            return False
            
        self.logger.info("Version data validation passed")
        return True
        
    def create_version_info(self, version: str, model_url: str, **kwargs) -> Dict[str, Any]:
        """Create standardized version info dictionary"""
        version_info = {
            "version": version,
            "model_url": model_url,
            "model_name": kwargs.get("model_name", "signalojs_ai_model"),
            "checksum": kwargs.get("checksum", ""),
            "size": kwargs.get("size", 0),
            "release_date": kwargs.get("release_date", datetime.now().isoformat()),
            "changelog": kwargs.get("changelog", []),
            "required_restart": kwargs.get("required_restart", False)
        }
        
        return version_info
        
    def get_version_history(self, versions_file: str = "models/version_history.json") -> List[Dict[str, Any]]:
        """Get version history from file"""
        try:
            history_file = Path(versions_file)
            if history_file.exists():
                with open(history_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load version history: {e}")
            
        return []
        
    def save_version_history(self, version_data: Dict[str, Any], versions_file: str = "models/version_history.json"):
        """Save version to history file"""
        try:
            history_file = Path(versions_file)
            history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing history
            history = self.get_version_history(versions_file)
            
            # Add new version with timestamp
            version_entry = {
                **version_data,
                "installed_at": datetime.now().isoformat()
            }
            
            history.append(version_entry)
            
            # Keep only last 10 versions
            history = history[-10:]
            
            # Save updated history
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
            self.logger.info(f"Version history updated: {version_data.get('version')}")
            
        except Exception as e:
            self.logger.error(f"Failed to save version history: {e}")


# Convenience functions for external use
def compare_model_versions(current: str, new: str) -> bool:
    """Check if new version is newer than current version"""
    manager = VersionManager()
    return manager.is_newer_version(current, new)


async def fetch_latest_version(backend_url: str = "https://api.signalojs.com") -> Optional[Dict[str, Any]]:
    """Fetch latest model version information"""
    manager = VersionManager(backend_url)
    return await manager.fetch_version_info()


def validate_model_version_data(version_data: Dict[str, Any]) -> bool:
    """Validate model version data structure"""
    manager = VersionManager()
    return manager.validate_version_data(version_data)


def create_mock_version_data(version: str = "2.1.0") -> Dict[str, Any]:
    """Create mock version data for testing"""
    manager = VersionManager()
    return manager.create_version_info(
        version=version,
        model_url="https://api.signalojs.com/models/signalojs_ai_model_v2.1.0.tar.gz",
        model_name="signalojs_ai_model",
        checksum="abc123def456",
        size=157286400,  # ~150MB
        changelog=[
            "Improved signal parsing accuracy by 15%",
            "Added support for new currency pairs",
            "Enhanced risk management algorithms",
            "Bug fixes and performance improvements"
        ],
        required_restart=True
    )


# Main function for testing
async def main():
    """Test the version manager"""
    print("📦 Testing SignalOS Version Manager")
    print("=" * 50)
    
    manager = VersionManager()
    
    # Test version parsing and comparison
    test_versions = [
        ("1.0.0", "1.0.1"),
        ("1.5.2", "2.0.0"),
        ("2.1.0-beta.1", "2.1.0"),
        ("1.9.9", "1.10.0")
    ]
    
    print("🔍 Testing version comparisons:")
    for v1, v2 in test_versions:
        is_newer = manager.is_newer_version(v1, v2)
        comparison = manager.compare_versions(v1, v2)
        print(f"   {v1} vs {v2}: {'✅ newer' if is_newer else '❌ not newer'} (comparison: {comparison})")
    
    # Test version validation
    print(f"\n📋 Testing version data validation:")
    mock_data = create_mock_version_data()
    is_valid = manager.validate_version_data(mock_data)
    print(f"   Mock data valid: {'✅' if is_valid else '❌'}")
    
    # Test remote fetch (will fail in test environment)
    print(f"\n🌐 Testing remote version fetch:")
    try:
        remote_data = await manager.fetch_version_info()
        if remote_data:
            print(f"   ✅ Remote version: {remote_data.get('version', 'unknown')}")
        else:
            print("   ❌ Failed to fetch remote version (expected in test environment)")
    except Exception as e:
        print(f"   ❌ Remote fetch error: {str(e)[:50]}...")
    
    print(f"\n✅ Version manager testing complete")


if __name__ == "__main__":
    asyncio.run(main())