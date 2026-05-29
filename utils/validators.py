"""
Validation utilities for file uploads and data processing.

Provides functions for validating file uploads, cleaning identifiers,
and validating Colombian cédula numbers.
"""

import os
import pandas as pd
from typing import Tuple, Optional, Any
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from config import ALLOWED_EXTENSIONS, ALLOWED_MIMETYPES, MAX_FILE_SIZE


def validate_file(
    file: FileStorage,
    max_size: int = MAX_FILE_SIZE
) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded file for security and correctness.

    Performs comprehensive validation including:
    - File presence and non-empty filename
    - Extension validation (.xlsx only)
    - MIME type validation
    - File size validation
    - Empty file detection

    Args:
        file: File object from Flask request
        max_size: Maximum file size in bytes (default from config)

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
            Returns (True, None) if valid, (False, error_string) otherwise
    """
    if not file or file.filename == '':
        return False, 'No file selected'

    filename: str = secure_filename(file.filename)
    if filename == '':
        return False, 'Invalid filename'

    # Check extension
    if not _check_extension(filename):
        return False, 'Only .xlsx files are allowed'

    # Check MIME type
    if not _check_mimetype(file):
        return False, 'Invalid file format'

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size: int = file.tell()
    file.seek(0)

    if file_size > max_size:
        max_size_mb: float = max_size / 1024 / 1024
        return False, f'File too large (max {max_size_mb}MB)'

    if file_size == 0:
        return False, 'File is empty'

    return True, None


def _check_extension(filename: str) -> bool:
    """
    Check if file has allowed extension.

    Args:
        filename: Filename to check

    Returns:
        bool: True if extension is allowed
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _check_mimetype(file: FileStorage) -> bool:
    """
    Check if file has allowed MIME type.

    Args:
        file: FileStorage object from Flask request

    Returns:
        bool: True if MIME type is allowed or not provided
    """
    if not file.content_type:
        return True  # Allow if MIME type is not provided
    return file.content_type in ALLOWED_MIMETYPES


def clean_id(val: Any) -> Optional[str]:
    """
    Clean and standardize ID values (cédula/documento).

    Converts numeric values through int/float casting to remove decimals,
    handles NaN values, and returns None for invalid inputs.

    Args:
        val: Value to clean (Any type)

    Returns:
        Optional[str]: Cleaned ID string or None if invalid/NaN
    """
    if pd.isna(val):
        return None
    try:
        return str(int(float(val))).strip()
    except (ValueError, TypeError):
        return str(val).strip() if val else None


def split_name(full_name: Any, is_ingreso: bool = True) -> Tuple[str, str]:
    """
    Split full name into apellidos (surnames) and nombres (first names).

    Assumes format: "Apellido1 Apellido2 Nombre1 Nombre2..."
    Algorithm:
    - 1 word: all to apellidos
    - 2 words: word1 to apellidos, word2 to nombres
    - 3+ words: first 2 to apellidos, rest to nombres

    Args:
        full_name: Full name string (Any type)
        is_ingreso: Whether it's an ingreso (not used, kept for compatibility)

    Returns:
        Tuple[str, str]: (apellidos, nombres) tuple of strings
    """
    if pd.isna(full_name):
        return "", ""

    words: list = str(full_name).strip().split()
    if not words:
        return "", ""

    if len(words) == 1:
        return words[0], ""

    if len(words) == 2:
        return words[0], words[1]

    # Assume first 2 words are surnames, rest are names
    apellidos: str = " ".join(words[:2])
    nombres: str = " ".join(words[2:])
    return apellidos, nombres


def validate_cedula(cedula: Any) -> bool:
    """
    Validate Colombian cédula format.

    Validates that the cédula is numeric and within typical length range
    (8-10 digits for Colombian identification numbers).

    Args:
        cedula: Cédula number as string or numeric value

    Returns:
        bool: True if valid format, False otherwise
    """
    if not cedula:
        return False

    cleaned: Optional[str] = clean_id(cedula)
    if not cleaned:
        return False

    # Check if it's a valid number and reasonable length (usually 8-10 digits)
    return cleaned.isdigit() and 8 <= len(cleaned) <= 10
