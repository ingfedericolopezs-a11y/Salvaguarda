"""
Validation utilities for file uploads and data processing.
"""

import os
import pandas as pd
from werkzeug.utils import secure_filename
from config import ALLOWED_EXTENSIONS, ALLOWED_MIMETYPES, MAX_FILE_SIZE


def validate_file(file, max_size=MAX_FILE_SIZE):
    """
    Validate uploaded file for security and correctness.

    Args:
        file: File object from Flask request
        max_size: Maximum file size in bytes

    Returns:
        tuple: (is_valid, error_message)
    """
    if not file or file.filename == '':
        return False, 'No file selected'

    filename = secure_filename(file.filename)
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
    file_size = file.tell()
    file.seek(0)

    if file_size > max_size:
        return False, f'File too large (max {max_size / 1024 / 1024}MB)'

    if file_size == 0:
        return False, 'File is empty'

    return True, None


def _check_extension(filename):
    """Check if file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _check_mimetype(file):
    """Check if file has allowed MIME type."""
    if not file.content_type:
        return True  # Allow if MIME type is not provided
    return file.content_type in ALLOWED_MIMETYPES


def clean_id(val):
    """
    Clean and standardize ID values (cédula/documento).

    Args:
        val: Value to clean

    Returns:
        str: Cleaned ID or None if invalid
    """
    if pd.isna(val):
        return None
    try:
        return str(int(float(val))).strip()
    except (ValueError, TypeError):
        return str(val).strip() if val else None


def split_name(full_name, is_ingreso=True):
    """
    Split full name into apellidos (surnames) and nombres (first names).

    Assumes format: "Apellido1 Apellido2 Nombre1 Nombre2..."

    Args:
        full_name: Full name string
        is_ingreso: Whether it's an ingreso (not used, kept for compatibility)

    Returns:
        tuple: (apellidos, nombres)
    """
    if pd.isna(full_name):
        return "", ""

    words = str(full_name).strip().split()
    if not words:
        return "", ""

    if len(words) == 1:
        return words[0], ""

    if len(words) == 2:
        return words[0], words[1]

    # Assume first 2 words are surnames, rest are names
    apellidos = " ".join(words[:2])
    nombres = " ".join(words[2:])
    return apellidos, nombres


def validate_cedula(cedula):
    """
    Validate Colombian cédula format (optional enhancement).

    Args:
        cedula: Cédula number as string

    Returns:
        bool: True if valid format
    """
    if not cedula:
        return False

    cleaned = clean_id(cedula)
    if not cleaned:
        return False

    # Check if it's a valid number and reasonable length (usually 8-10 digits)
    return cleaned.isdigit() and 8 <= len(cleaned) <= 10
