"""
Configuration module for ROESAN-SALVAGUARDAR application.
Loads settings from environment variables with sensible defaults.
"""

import os
import sys
from pathlib import Path

# Base directories.
#   RESOURCE_DIR -> read-only bundled files (templates, static, data)
#   DATA_DIR     -> writable files (uploads, outputs, logs)
# When packaged with PyInstaller these differ; in normal mode they are equal.
if getattr(sys, 'frozen', False):
    RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    DATA_DIR = Path(sys.executable).parent
else:
    RESOURCE_DIR = Path(__file__).parent.absolute()
    DATA_DIR = RESOURCE_DIR

# Base directory of the application (kept for backward compatibility)
BASE_DIR = RESOURCE_DIR

# Flask Configuration
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
FLASK_ENV = os.getenv('FLASK_ENV', 'production')
HOST = os.getenv('FLASK_HOST', '0.0.0.0')
PORT = int(os.getenv('FLASK_PORT', 5000))

# File Upload Configuration (writable — next to the exe when packaged)
UPLOAD_DIR = os.getenv('UPLOAD_DIR', os.path.join(DATA_DIR, 'uploads'))
OUTPUT_DIR = os.getenv('OUTPUT_DIR', os.path.join(DATA_DIR, 'outputs'))
WORKSPACE_DIR = os.getenv('WORKSPACE_DIR', DATA_DIR)

# Security Configuration
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10 * 1024 * 1024))  # 10 MB
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
ALLOWED_MIMETYPES = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel'
}

# Processing Configuration
EXCEL_SHEET_NAMES = ['INGRESOS', 'RETIROS']
HEADER_SEARCH_ROWS = 20  # Number of rows to search for headers
NUMERO_POLIZA = 23156894  # Default policy number for all records
CARGO_DEFAULT = 'AGENTES DE SEGURIDAD'  # Default cargo for INGRESOS
TEMPLATE_PATH = os.path.join(RESOURCE_DIR, 'data', 'plantilla_template.xlsx')

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', os.path.join(DATA_DIR, 'app.log'))

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
