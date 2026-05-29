"""
ROESAN-SALVAGUARDAR: Monthly Reconciliation Web Application

This Flask application processes insurance policy documents and reconciles
monthly movements (entries and withdrawals) for the Salvaguardar policy.
"""

import os
import glob
import logging
from datetime import datetime

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
def index():
    """Serve the main application page."""
    return render_template('index.html')


@app.route('/api/history', methods=['GET'])
def get_history():
    """
    List all Excel files available in workspace, uploads, and outputs directories.

    Returns:
        JSON: List of file metadata sorted by modification time
    """
    try:
        files_data = list_files(config.WORKSPACE_DIR, config.UPLOAD_DIR, config.OUTPUT_DIR)
        logger.info(f"Listed {len(files_data)} files")
        return jsonify(files_data)
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({'error': 'Error listing files'}), 500


@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """
    Download a file from outputs or workspace directories.

    Security: Prevents directory traversal attacks.

    Args:
        filename: Name of the file to download

    Returns:
        File object or error response
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
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return jsonify({'error': 'Error downloading file'}), 500


@app.route('/api/process', methods=['POST'])
def process_files():
    """
    Process master template and movement files to generate reconciliation results.

    Expected form data:
        - master_file: Master template file (required)
        - movement_files: One or more movement files (required)

    Returns:
        JSON: Processing results with statistics, previews, and file information
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
        logger.error("File too large")
        return jsonify({'error': 'Uno o más archivos es demasiado grande'}), 413

    except Exception as e:
        logger.error(f"Processing error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'details': 'Check server logs for more information'
        }), 500


@app.route('/api/search', methods=['GET'])
def search_cedula():
    """
    Search for a specific document ID (Cédula) across all local Excel files.

    Query parameter:
        cedula: Document number to search for

    Returns:
        JSON: List of matching records with file and location information
    """
    import pandas as pd

    query = request.args.get('cedula', '').strip()

    if not query:
        return jsonify([])

    # Validate input
    cleaned_query = clean_id(query)
    if not cleaned_query:
        logger.warning(f"Invalid search query: {query}")
        return jsonify([])

    results = []
    search_paths = [config.WORKSPACE_DIR, config.UPLOAD_DIR, config.OUTPUT_DIR]
    scanned_files = set()

    logger.info(f"Searching for cedula: {cleaned_query}")

    for base_path in search_paths:
        if not os.path.exists(base_path):
            continue

        for filepath in glob.glob(os.path.join(base_path, "**/*.xlsx"), recursive=True):
            if os.path.basename(filepath).startswith('~$'):
                continue

            abs_path = os.path.abspath(filepath)
            if abs_path in scanned_files:
                continue
            scanned_files.add(abs_path)

            try:
                xls = pd.ExcelFile(filepath)
                for sheet in xls.sheet_names:
                    try:
                        df = pd.read_excel(filepath, sheet_name=sheet)
                        df_str = df.astype(str)

                        # Search for exact or partial match
                        mask = df_str.apply(lambda col: col.str.contains(cleaned_query, na=False))

                        if mask.any().any():
                            matching_rows = df[mask.any(axis=1)].replace({float('nan'): None})
                            for idx, row in matching_rows.iterrows():
                                results.append({
                                    'file': os.path.basename(filepath),
                                    'folder': os.path.basename(os.path.dirname(filepath)) or 'Root',
                                    'sheet': sheet,
                                    'row': int(idx) + 2,
                                    'data': row.to_dict()
                                })
                    except Exception as e:
                        logger.debug(f"Error reading sheet {sheet} in {filepath}: {e}")

            except Exception as e:
                logger.debug(f"Error reading file {filepath}: {e}")

    logger.info(f"Search completed: found {len(results)} matches for {cleaned_query}")
    return jsonify(results)


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
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
