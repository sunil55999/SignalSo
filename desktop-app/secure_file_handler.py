"""
Secure File Operations Handler for SignalOS
Prevents directory traversal attacks and validates all file operations
"""

import os
import stat
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

class FileOperationError(Exception):
    """Raised when file operations fail security checks"""
    pass

class AllowedFileType(Enum):
    TEXT = "text"
    JSON = "json"
    LOG = "log"
    CSV = "csv"
    CONFIG = "config"

@dataclass
class FileValidationRules:
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = None
    allowed_paths: List[str] = None
    blocked_patterns: List[str] = None
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = ['.txt', '.json', '.log', '.csv', '.conf', '.ini']
        if self.allowed_paths is None:
            self.allowed_paths = ['logs/', 'config/', 'data/', 'temp/']
        if self.blocked_patterns is None:
            self.blocked_patterns = ['../', '..\\', '~/', '/etc/', '/var/', '/usr/', '/bin/']

class SecureFileHandler:
    """Secure file operations with comprehensive validation"""
    
    def __init__(self, base_directory: str = ".", validation_rules: FileValidationRules = None):
        self.base_directory = Path(base_directory).resolve()
        self.validation_rules = validation_rules or FileValidationRules()
        self.logger = logging.getLogger(__name__)
        
        # Ensure base directory exists
        self.base_directory.mkdir(exist_ok=True)
        
    def _validate_path(self, file_path: str) -> Path:
        """
        Validate file path for security
        
        Args:
            file_path: File path to validate
            
        Returns:
            Resolved and validated Path object
            
        Raises:
            FileOperationError: If path validation fails
        """
        if not file_path or not isinstance(file_path, str):
            raise FileOperationError("Invalid file path")
            
        # Check for blocked patterns
        for pattern in self.validation_rules.blocked_patterns:
            if pattern in file_path:
                raise FileOperationError(f"Blocked path pattern detected: {pattern}")
                
        # Resolve path and check it's within base directory
        try:
            resolved_path = (self.base_directory / file_path).resolve()
        except (OSError, ValueError) as e:
            raise FileOperationError(f"Path resolution failed: {e}")
            
        # Ensure path is within base directory (prevent directory traversal)
        try:
            resolved_path.relative_to(self.base_directory)
        except ValueError:
            raise FileOperationError(f"Path outside base directory: {resolved_path}")
            
        return resolved_path
        
    def _validate_file_extension(self, file_path: Path) -> None:
        """Validate file extension"""
        extension = file_path.suffix.lower()
        if extension not in self.validation_rules.allowed_extensions:
            raise FileOperationError(f"File extension not allowed: {extension}")
            
    def _validate_file_size(self, file_path: Path) -> None:
        """Validate file size"""
        if file_path.exists():
            file_size = file_path.stat().st_size
            if file_size > self.validation_rules.max_file_size:
                raise FileOperationError(f"File too large: {file_size} bytes")
                
    def _validate_permissions(self, file_path: Path, operation: str) -> None:
        """Validate file permissions for operation"""
        if not file_path.exists():
            return
            
        file_stat = file_path.stat()
        
        # Check if file is readable for read operations
        if operation in ['read', 'copy'] and not os.access(file_path, os.R_OK):
            raise FileOperationError(f"No read permission: {file_path}")
            
        # Check if file is writable for write operations
        if operation in ['write', 'append', 'delete'] and not os.access(file_path, os.W_OK):
            raise FileOperationError(f"No write permission: {file_path}")
            
    def secure_read(self, file_path: str, encoding: str = 'utf-8') -> str:
        """
        Securely read file content
        
        Args:
            file_path: Path to file to read
            encoding: File encoding
            
        Returns:
            File content as string
        """
        validated_path = self._validate_path(file_path)
        self._validate_file_extension(validated_path)
        self._validate_file_size(validated_path)
        self._validate_permissions(validated_path, 'read')
        
        try:
            with open(validated_path, 'r', encoding=encoding) as f:
                content = f.read()
                
            self.logger.info(f"File read successfully: {validated_path}")
            return content
            
        except (IOError, UnicodeDecodeError) as e:
            self.logger.error(f"File read failed: {e}")
            raise FileOperationError(f"Failed to read file: {e}")
            
    def secure_write(self, file_path: str, content: str, encoding: str = 'utf-8', 
                    mode: str = 'w') -> bool:
        """
        Securely write content to file
        
        Args:
            file_path: Path to file to write
            content: Content to write
            encoding: File encoding
            mode: Write mode ('w' or 'a')
            
        Returns:
            True if successful
        """
        if not isinstance(content, str):
            raise FileOperationError("Content must be string")
            
        if len(content.encode(encoding)) > self.validation_rules.max_file_size:
            raise FileOperationError("Content too large")
            
        validated_path = self._validate_path(file_path)
        self._validate_file_extension(validated_path)
        
        # Create parent directories if they don't exist
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._validate_permissions(validated_path, 'write')
        
        try:
            with open(validated_path, mode, encoding=encoding) as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
                
            # Set restrictive permissions
            os.chmod(validated_path, stat.S_IRUSR | stat.S_IWUSR)
            
            self.logger.info(f"File written successfully: {validated_path}")
            return True
            
        except (IOError, OSError) as e:
            self.logger.error(f"File write failed: {e}")
            raise FileOperationError(f"Failed to write file: {e}")
            
    def secure_copy(self, source_path: str, dest_path: str) -> bool:
        """
        Securely copy file
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            
        Returns:
            True if successful
        """
        source = self._validate_path(source_path)
        dest = self._validate_path(dest_path)
        
        self._validate_file_extension(source)
        self._validate_file_extension(dest)
        self._validate_file_size(source)
        self._validate_permissions(source, 'read')
        
        if not source.exists():
            raise FileOperationError(f"Source file does not exist: {source}")
            
        try:
            import shutil
            shutil.copy2(source, dest)
            
            # Set restrictive permissions on destination
            os.chmod(dest, stat.S_IRUSR | stat.S_IWUSR)
            
            self.logger.info(f"File copied successfully: {source} -> {dest}")
            return True
            
        except (IOError, OSError) as e:
            self.logger.error(f"File copy failed: {e}")
            raise FileOperationError(f"Failed to copy file: {e}")
            
    def secure_delete(self, file_path: str) -> bool:
        """
        Securely delete file
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if successful
        """
        validated_path = self._validate_path(file_path)
        self._validate_permissions(validated_path, 'delete')
        
        if not validated_path.exists():
            self.logger.warning(f"File does not exist for deletion: {validated_path}")
            return True
            
        try:
            # Secure deletion by overwriting with random data first
            if validated_path.is_file():
                file_size = validated_path.stat().st_size
                with open(validated_path, 'r+b') as f:
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
                    
            validated_path.unlink()
            
            self.logger.info(f"File deleted successfully: {validated_path}")
            return True
            
        except (IOError, OSError) as e:
            self.logger.error(f"File deletion failed: {e}")
            raise FileOperationError(f"Failed to delete file: {e}")
            
    def list_directory(self, directory_path: str = ".") -> List[Dict[str, Any]]:
        """
        Securely list directory contents
        
        Args:
            directory_path: Directory path to list
            
        Returns:
            List of file information dictionaries
        """
        validated_path = self._validate_path(directory_path)
        
        if not validated_path.is_dir():
            raise FileOperationError(f"Not a directory: {validated_path}")
            
        try:
            files = []
            for item in validated_path.iterdir():
                try:
                    item_stat = item.stat()
                    files.append({
                        'name': item.name,
                        'path': str(item.relative_to(self.base_directory)),
                        'size': item_stat.st_size,
                        'modified': item_stat.st_mtime,
                        'is_file': item.is_file(),
                        'is_dir': item.is_dir(),
                        'extension': item.suffix.lower() if item.is_file() else None
                    })
                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue
                    
            return sorted(files, key=lambda x: (not x['is_dir'], x['name'].lower()))
            
        except (OSError, PermissionError) as e:
            self.logger.error(f"Directory listing failed: {e}")
            raise FileOperationError(f"Failed to list directory: {e}")
            
    def get_file_hash(self, file_path: str, algorithm: str = 'sha256') -> str:
        """
        Get file hash for integrity verification
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm (sha256, md5, sha1)
            
        Returns:
            File hash as hex string
        """
        validated_path = self._validate_path(file_path)
        self._validate_permissions(validated_path, 'read')
        
        if algorithm not in ['sha256', 'md5', 'sha1']:
            raise FileOperationError(f"Unsupported hash algorithm: {algorithm}")
            
        try:
            hash_obj = hashlib.new(algorithm)
            
            with open(validated_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)
                    
            return hash_obj.hexdigest()
            
        except (IOError, OSError) as e:
            self.logger.error(f"File hashing failed: {e}")
            raise FileOperationError(f"Failed to hash file: {e}")
            
    def validate_file_integrity(self, file_path: str, expected_hash: str, 
                              algorithm: str = 'sha256') -> bool:
        """
        Validate file integrity using hash comparison
        
        Args:
            file_path: Path to file
            expected_hash: Expected hash value
            algorithm: Hash algorithm
            
        Returns:
            True if file integrity is valid
        """
        actual_hash = self.get_file_hash(file_path, algorithm)
        return actual_hash.lower() == expected_hash.lower()

# Global secure file handler instance
secure_file_handler = SecureFileHandler()

def secure_read_file(file_path: str, encoding: str = 'utf-8') -> str:
    """Global function for secure file reading"""
    return secure_file_handler.secure_read(file_path, encoding)

def secure_write_file(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """Global function for secure file writing"""
    return secure_file_handler.secure_write(file_path, content, encoding)

def secure_delete_file(file_path: str) -> bool:
    """Global function for secure file deletion"""
    return secure_file_handler.secure_delete(file_path)