"""
File handling utilities for listing, downloading, and managing files.
"""

import os
import glob
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def list_files(workspace_dir, upload_dir, output_dir):
    """
    List all Excel files from workspace, uploads, and outputs directories.

    Args:
        workspace_dir: Workspace root directory
        upload_dir: Upload directory path
        output_dir: Output directory path

    Returns:
        list: List of file metadata dicts sorted by modification time
    """
    files_data = []

    directories = {
        'output': output_dir,
        'workspace': workspace_dir,
        'uploads': upload_dir
    }

    for dir_type, dir_path in directories.items():
        if not os.path.exists(dir_path):
            continue

        try:
            for filepath in glob.glob(os.path.join(dir_path, "**/*.xlsx"), recursive=True):
                # Skip temp files
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
        except Exception as e:
            logger.error(f"Error listing files in {dir_path}: {e}")

    # Sort by modification time descending
    files_data.sort(key=lambda x: x['modified'], reverse=True)
    return files_data


def get_file_path(filename, workspace_dir, upload_dir, output_dir):
    """
    Safely get the absolute path of a file, preventing directory traversal.

    Args:
        filename: Filename to locate
        workspace_dir: Workspace root directory
        upload_dir: Upload directory path
        output_dir: Output directory path

    Returns:
        str: Absolute file path or None if not found

    Raises:
        ValueError: If filename contains path separators (security check)
    """
    # Security: Prevent directory traversal
    if os.path.sep in filename or '/' in filename or '\\' in filename:
        raise ValueError('Invalid filename: contains path separators')

    filename = os.path.basename(filename)  # Extra safety

    # Check in order: output, workspace, uploads
    for directory in [output_dir, workspace_dir, upload_dir]:
        filepath = os.path.join(directory, filename)

        # Verify the resolved path is still within the allowed directory
        try:
            resolved_path = os.path.abspath(filepath)
            resolved_dir = os.path.abspath(directory)

            if not resolved_path.startswith(resolved_dir):
                continue

            if os.path.exists(resolved_path) and os.path.isfile(resolved_path):
                return resolved_path
        except Exception as e:
            logger.warning(f"Error checking file path: {e}")
            continue

    return None


def ensure_directories(upload_dir, output_dir):
    """
    Ensure required directories exist.

    Args:
        upload_dir: Upload directory path
        output_dir: Output directory path
    """
    for directory in [upload_dir, output_dir]:
        os.makedirs(directory, exist_ok=True)


def create_run_directory(upload_dir):
    """
    Create a unique subdirectory for this processing run.

    Args:
        upload_dir: Base upload directory

    Returns:
        str: Path to the new run directory
    """
    run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = os.path.join(upload_dir, run_timestamp)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def get_file_size_formatted(bytes_size):
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"
