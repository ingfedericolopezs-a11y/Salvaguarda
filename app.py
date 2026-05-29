"""
ROESAN-SALVAGUARDAR: Monthly Reconciliation Web Application

This Flask application processes insurance policy documents and reconciles
monthly movements (entries and withdrawals) for the Salvaguardar policy.
"""

import os
import glob
import logging
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional

import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.exceptions import RequestEntityTooLarge

import config
from utils import (
    validate_file, clean_id, split_name,
    process_excel_files, generate_output_files,
    get_file_path, list_files
)
from utils.file_handler import create_run_directory, ensure_directories


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask app initialization
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = config.MAX_FILE_SIZE

# Ensure directories exist
ensure_directories(config.UPLOAD_DIR, config.OUTPUT_DIR)

EXCEL_MIMETYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


@app.route('/')
def index() -> str:
    """
    Serve the main application page.

    Returns:
        Rendered HTML template string
    """
    return render_template('index.html')


@app.route('/api/history', methods=['GET'])
def get_history() -> Tuple[str, int]:
    """
    List all Excel files available in workspace, uploads, and outputs directories.

    Returns:
        Tuple[str, int]: JSON response with file metadata and HTTP status code
    """
    try:
        files_data = list_files(config.WORKSPACE_DIR, config.UPLOAD_DIR, config.OUTPUT_DIR)
        logger.info(f"Listed {len(files_data)} files successfully")
        return jsonify(files_data), 200
    except OSError as e:
        logger.error(f"File system error listing files: {e}", exc_info=True)
        return jsonify({'error': 'Error accessing file system'}), 500
    except Exception as e:
        logger.error(f"Unexpected error listing files: {e}", exc_info=True)
        return jsonify({'error': 'Error listing files'}), 500


@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename: str) -> Tuple[Any, int]:
    """
    Download a file from outputs or workspace directories.

    Security: Prevents directory traversal attacks.

    Args:
        filename: Name of the file to download

    Returns:
        Tuple[Any, int]: File object with HTTP status or error JSON response
    """
    try:
        filepath = get_file_path(
            filename,
            config.WORKSPACE_DIR,
            config.UPLOAD_DIR,
            config.OUTPUT_DIR
        )

        if not filepath:
            logger.warning(f"File not found: {filename}")
            return jsonify({'error': 'Archivo no encontrado'}), 404

        logger.info(f"Downloading file: {filename}")
        return send_file(
            filepath,
            mimetype=EXCEL_MIMETYPE,
            as_attachment=True,
            download_name=os.path.basename(filepath)
        )
    except ValueError as e:
        logger.warning(f"Invalid file request: {e}")
        return jsonify({'error': 'Invalid file request'}), 400
    except FileNotFoundError as e:
        logger.warning(f"File not found during download {filename}: {e}")
        return jsonify({'error': 'Archivo no encontrado'}), 404
    except OSError as e:
        logger.error(f"File system error downloading {filename}: {e}", exc_info=True)
        return jsonify({'error': 'Error accessing file'}), 500
    except Exception as e:
        logger.error(f"Unexpected error downloading file {filename}: {e}", exc_info=True)
        return jsonify({'error': 'Error downloading file'}), 500


@app.route('/api/process', methods=['POST'])
def process_files() -> Tuple[str, int]:
    """
    Process master template and movement files to generate reconciliation results.

    Expected form data:
        - master_file: Master template file (required)
        - movement_files: One or more movement files (required)

    Returns:
        Tuple[str, int]: JSON response with processing results and HTTP status code
    """
    # Validate request
    if 'master_file' not in request.files:
        return jsonify({'error': 'Falta el archivo maestro de cobro (PLANTILLA CARGUE COBRO).'}), 400

    master_file = request.files['master_file']
    movement_files = request.files.getlist('movement_files')

    # Validate files
    if master_file.filename == '':
        return jsonify({'error': 'El archivo maestro seleccionado es inválido.'}), 400

    if not movement_files or (len(movement_files) == 1 and movement_files[0].filename == ''):
        return jsonify({'error': 'Falta seleccionar los archivos de movimientos.'}), 400

    # Validate master file
    is_valid, error_msg = validate_file(master_file)
    if not is_valid:
        logger.warning(f"Invalid master file: {error_msg}")
        return jsonify({'error': f'Master file: {error_msg}'}), 400

    # Validate movement files
    for mf in movement_files:
        if mf.filename != '':
            is_valid, error_msg = validate_file(mf)
            if not is_valid:
                logger.warning(f"Invalid movement file {mf.filename}: {error_msg}")
                return jsonify({'error': f'Movement file {mf.filename}: {error_msg}'}), 400

    # Process files
    try:
        # Create unique directory for this run
        run_upload_dir = create_run_directory(config.UPLOAD_DIR)

        # Save uploaded files
        master_path = os.path.join(run_upload_dir, master_file.filename)
        master_file.save(master_path)
        logger.info(f"Saved master file: {master_path}")

        saved_movement_paths = []
        for f in movement_files:
            if f.filename != '':
                fpath = os.path.join(run_upload_dir, f.filename)
                f.save(fpath)
                saved_movement_paths.append(fpath)
                logger.info(f"Saved movement file: {fpath}")

        # Process data
        logger.info("Starting data processing...")
        result = process_excel_files(master_path, saved_movement_paths)

        if result['status'] != 'success':
            raise Exception(result.get('error', 'Unknown error'))

        # Generate output files
        output_files = generate_output_files(
            result['dataframes']['movements'],
            result['dataframes']['master'],
            config.OUTPUT_DIR
        )

        logger.info("Processing completed successfully")

        return jsonify({
            'status': 'success',
            'statistics': result['statistics'],
            'filenames': {
                'movements': output_files['movements']['filename'],
                'master': output_files['master']['filename']
            },
            'preview_movements': result['preview']['movements'],
            'preview_master': result['preview']['master'],
            'logs': result['logs']
        })

    except RequestEntityTooLarge:
        logger.error("File upload exceeded size limit")
        return jsonify({'error': 'Uno o más archivos es demasiado grande'}), 413

    except OSError as e:
        logger.error(f"File system error during processing: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': 'Error de sistema de archivos',
            'details': 'Verifique los permisos del servidor'
        }), 500

    except pd.errors.ParserError as e:
        logger.error(f"Excel parsing error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': 'Error al leer archivos Excel',
            'details': 'Verifique el formato de los archivos'
        }), 400

    except Exception as e:
        logger.error(f"Unexpected processing error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'details': 'Check server logs for more information'
        }), 500


@app.route('/api/search', methods=['GET'])
def search_cedula() -> Tuple[str, int]:
    """
    Search for a specific document ID (Cédula) across all local Excel files.

    Query parameter:
        cedula: Document number to search for

    Returns:
        Tuple[str, int]: JSON list of matching records with HTTP status code
    """
    query: str = request.args.get('cedula', '').strip()

    if not query:
        return jsonify([]), 200

    # Validate input
    cleaned_query: Optional[str] = clean_id(query)
    if not cleaned_query:
        logger.warning(f"Invalid search query format: {query}")
        return jsonify([]), 200

    results: List[Dict[str, Any]] = []
    search_paths: List[str] = [config.WORKSPACE_DIR, config.UPLOAD_DIR, config.OUTPUT_DIR]
    scanned_files: set = set()

    logger.info(f"Starting search for cedula: {cleaned_query}")
    start_time = datetime.now()

    try:
        for base_path in search_paths:
            if not os.path.exists(base_path):
                logger.debug(f"Search path does not exist: {base_path}")
                continue

            for filepath in glob.glob(os.path.join(base_path, "**/*.xlsx"), recursive=True):
                # Skip temporary Excel files
                if os.path.basename(filepath).startswith('~$'):
                    continue

                abs_path: str = os.path.abspath(filepath)
                if abs_path in scanned_files:
                    continue
                scanned_files.add(abs_path)

                try:
                    xls: pd.ExcelFile = pd.ExcelFile(filepath)
                    for sheet in xls.sheet_names:
                        try:
                            df: pd.DataFrame = pd.read_excel(filepath, sheet_name=sheet)

                            # Optimized search: convert to string only for comparison
                            mask = df.astype(str).apply(
                                lambda col: col.str.contains(cleaned_query, case=False, na=False)
                            )

                            # Get matching rows
                            if mask.any().any():
                                matching_rows: pd.DataFrame = df[mask.any(axis=1)]
                                for idx, row in matching_rows.iterrows():
                                    results.append({
                                        'file': os.path.basename(filepath),
                                        'folder': os.path.basename(os.path.dirname(filepath)) or 'Root',
                                        'sheet': sheet,
                                        'row': int(idx) + 2,
                                        'data': row.to_dict()
                                    })
                        except pd.errors.ParserError as e:
                            logger.debug(f"Parser error reading sheet {sheet} in {filepath}: {e}")
                        except Exception as e:
                            logger.debug(f"Error reading sheet {sheet} in {filepath}: {e}")

                except pd.errors.PythonExcelError as e:
                    logger.debug(f"Excel file error for {filepath}: {e}")
                except Exception as e:
                    logger.debug(f"Error reading file {filepath}: {e}")

        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Search completed in {elapsed_time:.2f}s: found {len(results)} matches for {cleaned_query}")
        return jsonify(results), 200

    except Exception as e:
        logger.error(f"Unexpected error during search: {e}", exc_info=True)
        return jsonify([]), 500


@app.errorhandler(404)
def not_found(error: Exception) -> Tuple[str, int]:
    """
    Handle 404 Not Found errors.

    Args:
        error: The exception object

    Returns:
        Tuple[str, int]: JSON error response with 404 status
    """
    logger.warning(f"404 error: {error}")
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error: Exception) -> Tuple[str, int]:
    """
    Handle 500 Internal Server errors.

    Args:
        error: The exception object

    Returns:
        Tuple[str, int]: JSON error response with 500 status
    """
    logger.error(f"Internal server error: {error}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Starting ROESAN-SALVAGUARDAR Server")
    logger.info(f"Workspace Directory: {config.WORKSPACE_DIR}")
    logger.info(f"Upload Directory: {config.UPLOAD_DIR}")
    logger.info(f"Output Directory: {config.OUTPUT_DIR}")
    logger.info(f"Debug Mode: {config.DEBUG}")
    logger.info("=" * 60)

    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        use_reloader=config.DEBUG
    )
