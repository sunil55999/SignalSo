"""
Secure File Handler for SignalOS Desktop App
Fixes Issue #8: Unsafe file operations with proper path validation
"""

import os
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Union, Optional, List
import hashlib
import json

class SecureFileHandler:
    """
    Secure file operations handler that prevents directory traversal attacks
    and validates file paths before operations
    """
    
    def __init__(self, base_directory: str = ".signalos"):
        """
        Initialize secure file handler
        
        Args:
            base_directory: Base directory for all file operations
        """
        self.base_dir = Path(base_directory).resolve()
        self.logger = logging.getLogger(__name__)
        
        # Create base directory if it doesn't exist
        self.base_dir.mkdir(exist_ok=True, parents=True)
        
        # Allowed file extensions for security
        self.allowed_extensions = {'.json', '.txt', '.log', '.cfg', '.ini'}
        
        # Maximum file size (10MB)
        self.max_file_size = 10 * 1024 * 1024
    
    def _validate_path(self, file_path: Union[str, Path]) -> Path:
        """
        Validate and sanitize file path to prevent directory traversal
        
        Args:
            file_path: File path to validate
            
        Returns:
            Validated and resolved Path object
            
        Raises:
            ValueError: If path is invalid or unsafe
        """
        try:
            # Convert to Path object and resolve
            path = Path(file_path).resolve()
            
            # Ensure path is within base directory
            if not str(path).startswith(str(self.base_dir)):
                # Try to make it relative to base directory
                relative_path = Path(file_path)
                if relative_path.is_absolute():
                    raise ValueError(f"Absolute paths not allowed: {file_path}")
                
                path = (self.base_dir / relative_path).resolve()
                
                # Check again after making relative
                if not str(path).startswith(str(self.base_dir)):
                    raise ValueError(f"Path outside base directory: {file_path}")
            
            # Validate file extension
            if path.suffix.lower() not in self.allowed_extensions:
                raise ValueError(f"File extension not allowed: {path.suffix}")
            
            # Check for dangerous characters
            dangerous_chars = ['..', '<', '>', '|', '*', '?', '"']
            path_str = str(path)
            for char in dangerous_chars:
                if char in path_str:
                    raise ValueError(f"Dangerous character in path: {char}")
            
            return path
            
        except Exception as e:
            self.logger.error(f"Path validation failed for {file_path}: {e}")
            raise ValueError(f"Invalid file path: {e}")
    
    def _check_file_size(self, file_path: Path) -> None:
        """
        Check if file size is within allowed limits
        
        Args:
            file_path: Path to check
            
        Raises:
            ValueError: If file is too large
        """
        if file_path.exists():
            size = file_path.stat().st_size
            if size > self.max_file_size:
                raise ValueError(f"File too large: {size} bytes (max: {self.max_file_size})")
    
    def read_file(self, file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
        """
        Safely read file content
        
        Args:
            file_path: Path to file
            encoding: File encoding
            
        Returns:
            File content as string
            
        Raises:
            ValueError: If path is invalid
            FileNotFoundError: If file doesn't exist
            IOError: If read operation fails
        """
        validated_path = self._validate_path(file_path)
        self._check_file_size(validated_path)
        
        try:
            with open(validated_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            self.logger.debug(f"Successfully read file: {validated_path}")
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to read file {validated_path}: {e}")
            raise IOError(f"Cannot read file: {e}")
    
    def write_file(self, file_path: Union[str, Path], content: str, encoding: str = 'utf-8') -> None:
        """
        Safely write content to file
        
        Args:
            file_path: Path to file
            content: Content to write
            encoding: File encoding
            
        Raises:
            ValueError: If path is invalid or content too large
            IOError: If write operation fails
        """
        validated_path = self._validate_path(file_path)
        
        # Check content size
        content_size = len(content.encode(encoding))
        if content_size > self.max_file_size:
            raise ValueError(f"Content too large: {content_size} bytes")
        
        try:
            # Create parent directories if needed
            validated_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first for atomic operation
            temp_path = validated_path.with_suffix(validated_path.suffix + '.tmp')
            
            with open(temp_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            # Atomic move to final location
            shutil.move(str(temp_path), str(validated_path))
            
            self.logger.debug(f"Successfully wrote file: {validated_path}")
            
        except Exception as e:
            # Clean up temp file if it exists
            temp_path = validated_path.with_suffix(validated_path.suffix + '.tmp')
            if temp_path.exists():
                temp_path.unlink()
            
            self.logger.error(f"Failed to write file {validated_path}: {e}")
            raise IOError(f"Cannot write file: {e}")
    
    def read_json(self, file_path: Union[str, Path]) -> dict:
        """
        Safely read JSON file
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Parsed JSON data
            
        Raises:
            ValueError: If path is invalid or JSON is malformed
            FileNotFoundError: If file doesn't exist
        """
        content = self.read_file(file_path)
        
        try:
            data = json.loads(content)
            self.logger.debug(f"Successfully parsed JSON from: {file_path}")
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in file {file_path}: {e}")
            raise ValueError(f"Invalid JSON format: {e}")
    
    def write_json(self, file_path: Union[str, Path], data: dict, indent: int = 2) -> None:
        """
        Safely write JSON file
        
        Args:
            file_path: Path to JSON file
            data: Data to write
            indent: JSON indentation
            
        Raises:
            ValueError: If path is invalid or data not serializable
            IOError: If write operation fails
        """
        try:
            content = json.dumps(data, indent=indent, ensure_ascii=False)
            self.write_file(file_path, content)
            
        except (TypeError, ValueError) as e:
            self.logger.error(f"Cannot serialize data to JSON: {e}")
            raise ValueError(f"Data not JSON serializable: {e}")
    
    def file_exists(self, file_path: Union[str, Path]) -> bool:
        """
        Check if file exists safely
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            validated_path = self._validate_path(file_path)
            return validated_path.exists() and validated_path.is_file()
        except ValueError:
            return False
    
    def delete_file(self, file_path: Union[str, Path]) -> bool:
        """
        Safely delete file
        
        Args:
            file_path: Path to delete
            
        Returns:
            True if file was deleted, False otherwise
        """
        try:
            validated_path = self._validate_path(file_path)
            
            if validated_path.exists() and validated_path.is_file():
                validated_path.unlink()
                self.logger.debug(f"Successfully deleted file: {validated_path}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    def list_files(self, directory: Union[str, Path] = "", pattern: str = "*") -> List[Path]:
        """
        Safely list files in directory
        
        Args:
            directory: Directory to list (relative to base)
            pattern: File pattern to match
            
        Returns:
            List of file paths
        """
        try:
            if directory:
                dir_path = self._validate_path(directory)
                if not dir_path.is_dir():
                    return []
            else:
                dir_path = self.base_dir
            
            # Ensure directory is within base
            if not str(dir_path.resolve()).startswith(str(self.base_dir)):
                return []
            
            files = []
            for file_path in dir_path.glob(pattern):
                if file_path.is_file() and file_path.suffix.lower() in self.allowed_extensions:
                    files.append(file_path)
            
            return sorted(files)
            
        except Exception as e:
            self.logger.error(f"Failed to list files in {directory}: {e}")
            return []
    
    def get_file_hash(self, file_path: Union[str, Path]) -> str:
        """
        Get SHA-256 hash of file for integrity checking
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex digest of file hash
        """
        validated_path = self._validate_path(file_path)
        
        hash_sha256 = hashlib.sha256()
        try:
            with open(validated_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            
            return hash_sha256.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Failed to hash file {validated_path}: {e}")
            raise IOError(f"Cannot hash file: {e}")

# Global secure file handler instance
secure_file_handler = SecureFileHandler()

def read_config_safely(config_path: str) -> dict:
    """
    Global function to safely read configuration files
    Replaces unsafe file operations in auth.py and other modules
    """
    try:
        return secure_file_handler.read_json(config_path)
    except (FileNotFoundError, ValueError):
        # Return empty config if file doesn't exist or is invalid
        return {}

def write_config_safely(config_path: str, config_data: dict) -> bool:
    """
    Global function to safely write configuration files
    """
    try:
        secure_file_handler.write_json(config_path, config_data)
        return True
    except Exception:
        return False