"""File handling utility functions."""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


def ensure_directory_exists(directory_path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, create it if it doesn't.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        Path object of the directory
    """
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_unique_filename(original_filename: Optional[str] = None, extension: Optional[str] = None) -> str:
    """
    Generate a unique filename using UUID.
    
    Args:
        original_filename: Original filename to extract extension from
        extension: File extension to use (overrides original_filename extension)
        
    Returns:
        Unique filename with UUID
    """
    if extension:
        if not extension.startswith('.'):
            extension = f'.{extension}'
    elif original_filename:
        extension = Path(original_filename).suffix
    else:
        extension = ''
    
    return f"{uuid.uuid4()}{extension}"


def safe_remove_file(file_path: Union[str, Path]) -> bool:
    """
    Safely remove a file, handling errors gracefully.
    
    Args:
        file_path: Path to the file to remove
        
    Returns:
        True if file was removed or didn't exist, False on error
    """
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info(f"Removed file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error removing file {file_path}: {e}")
        return False


def get_file_size(file_path: Union[str, Path]) -> Optional[int]:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes or None if file doesn't exist or error occurs
    """
    try:
        return Path(file_path).stat().st_size
    except Exception as e:
        logger.error(f"Error getting file size for {file_path}: {e}")
        return None


def is_valid_file_extension(filename: str, allowed_extensions: list) -> bool:
    """
    Check if file has a valid extension.
    
    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions (with or without dots)
        
    Returns:
        True if extension is allowed, False otherwise
    """
    file_ext = Path(filename).suffix.lower().lstrip('.')
    normalized_extensions = [ext.lower().lstrip('.') for ext in allowed_extensions]
    return file_ext in normalized_extensions