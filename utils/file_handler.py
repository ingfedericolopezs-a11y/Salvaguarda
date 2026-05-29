"""
File handling utilities for listing, downloading, and managing files.

Provides functions for safely listing Excel files, retrieving file paths
with directory traversal protection, and managing file system operations.
"""

import os
import glob
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


def list_files(
    workspace_dir: str,
    upload_dir: str,
    output_dir: str
) -> List[Dict[str, Any]]:
    """
    List all Excel files from workspace, uploads, and outputs directories.

    Recursively searches for .xlsx files in specified directories and returns
    metadata including size, modification time, and file type classification.

    Args:
        workspace_dir: Workspace root directory
        upload_dir: Upload directory path
        output_dir: Output directory path

    Returns:
        List[Dict[str, Any]]: List of file metadata dicts sorted by modification
            time (newest first). Each dict contains:
            - name: Filename
            - type: Directory type ('output', 'workspace', 'uploads')
            - size: File size in bytes
            - modified: Formatted modification timestamp (YYYY-MM-DD HH:MM:SS)
            - path: Absolute file path
    """
    files_data: List[Dict[str, Any]] = []

    directories: Dict[str, str] = {
        'output': output_dir,
        'workspace': workspace_dir,
        'uploads': upload_dir
    }

    for dir_type, dir_path in directories.items():
        if not os.path.exists(dir_path):
            continue

        try:
            for filepath in glob.glob(os.path.join(dir_path, "**/*.xlsx"), recursive=True):
                # Skip temporary Excel files
                if os.path.basename(filepath).startswith('~$'):
                    continue

                stat = os.stat(filepath)
                files_data.append({
                    'name': os.path.basename(filepath),
                    'type': dir_type,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'path': filepath
                })
        except OSError as e:
            logger.error(f"OS error listing files in {dir_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing files in {dir_path}: {e}")

    # Sort by modification time descending (newest first)
    files_data.sort(key=lambda x: x['modified'], reverse=True)
    return files_data


def get_file_path(
    filename: str,
    workspace_dir: str,
    upload_dir: str,
    output_dir: str
) -> Optional[str]:
    """
    Safely get the absolute path of a file, preventing directory traversal attacks.

    Implements multiple security checks to ensure the resolved path is within
    the allowed directories, preventing path traversal exploits.

    Args:
        filename: Filename to locate
        workspace_dir: Workspace root directory
        upload_dir: Upload directory path
        output_dir: Output directory path

    Returns:
        Optional[str]: Absolute file path if found, None otherwise

    Raises:
        ValueError: If filename contains path separators (security check)
    """
    # Security: Prevent directory traversal attacks
    if os.path.sep in filename or '/' in filename or '\\' in filename:
        raise ValueError('Invalid filename: contains path separators')

    filename = os.path.basename(filename)  # Extra safety layer

    # Check in order: output, workspace, uploads
    for directory in [output_dir, workspace_dir, upload_dir]:
        filepath: str = os.path.join(directory, filename)

        # Verify the resolved path is still within the allowed directory
        try:
            resolved_path: str = os.path.abspath(filepath)
            resolved_dir: str = os.path.abspath(directory)

            # Ensure resolved path stays within the directory
            if not resolved_path.startswith(resolved_dir):
                logger.debug(f"Path traversal attempt blocked for {filename}")
                continue

            if os.path.exists(resolved_path) and os.path.isfile(resolved_path):
                return resolved_path
        except Exception as e:
            logger.warning(f"Error checking file path for {filename}: {e}")
            continue

    return None


def ensure_directories(upload_dir: str, output_dir: str) -> None:
    """
    Ensure required directories exist, creating them if necessary.

    Args:
        upload_dir: Upload directory path
        output_dir: Output directory path

    Raises:
        OSError: If directory creation fails
    """
    for directory in [upload_dir, output_dir]:
        os.makedirs(directory, exist_ok=True)


def create_run_directory(upload_dir: str) -> str:
    """
    Create a unique subdirectory for this processing run.

    Creates a timestamped directory to organize files from each processing run,
    enabling isolation and historical tracking of operations.

    Args:
        upload_dir: Base upload directory

    Returns:
        str: Path to the new run directory (format: upload_dir/YYYYMMDD_HHMMSS)

    Raises:
        OSError: If directory creation fails
    """
    run_timestamp: str = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir: str = os.path.join(upload_dir, run_timestamp)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def get_file_size_formatted(bytes_size: float) -> str:
    """
    Format bytes into human-readable size.

    Converts byte values to appropriate units (B, KB, MB, GB, TB) with
    2 decimal places.

    Args:
        bytes_size: Size in bytes

    Returns:
        str: Formatted size string (e.g., "1.25 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"
