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
from utils.report_generator import ReportGenerator
from utils.history_manager import HistoryManager


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

# Initialize report generator and history manager
report_generator = ReportGenerator(config.OUTPUT_DIR)
history_dir = os.path.join(config.OUTPUT_DIR, 'historical_records')
history_manager = HistoryManager(history_dir)

# Global storage for last processed data (for report generation)
last_processed_data: Dict[str, Any] = {
    'movements_df': None,
    'master_df': None,
    'next_month_df': None,
    'analytics': None,
    'cobro_mes': 0,
    'cobro_anio': 0
}

EXCEL_MIMETYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


@app.route('/')
def index() -> str:
    """
    Serve the main application page.

    Returns:
        Rendered HTML template string
    """
    return render_template('index.html')


@app.route('/api/finalize', methods=['POST'])
def finalize_files() -> Tuple[str, int]:
    """
    Apply gender updates to ingresos and generate output Excel files.
    Called after the user confirms gender for each new ingreso.
    """
    if last_processed_data['movements_df'] is None:
        return jsonify({'error': 'No hay datos procesados. Procesa los archivos primero.'}), 400

    try:
        data = request.get_json(force=True)
        gender_updates = {item['id']: item['genero'] for item in data.get('gender_updates', [])}

        movements_df = last_processed_data['movements_df'].copy()
        master_df    = last_processed_data['master_df'].copy()
        next_month_df = last_processed_data.get('next_month_df')
        if next_month_df is not None:
            next_month_df = next_month_df.copy()

        # Apply gender updates to all DataFrames
        def apply_gender(df):
            if df is None:
                return None
            for idx, row in df.iterrows():
                nid = str(row.get('NUMERO_IDENTIFICACION_ASEGURADO', ''))
                if nid in gender_updates and gender_updates[nid]:
                    df.at[idx, 'GENERO'] = gender_updates[nid]
            return df

        movements_df  = apply_gender(movements_df)
        master_df     = apply_gender(master_df)
        next_month_df = apply_gender(next_month_df)

        output_files = generate_output_files(
            movements_df,
            master_df,
            config.OUTPUT_DIR,
            cobro_mes=last_processed_data.get('cobro_mes', 0),
            cobro_anio=last_processed_data.get('cobro_anio', 0),
            next_month_df=next_month_df
        )

        # Save to history
        analytics = last_processed_data['analytics']
        history_manager.save_processing(movements_df, master_df, analytics)

        filenames = {
            'movements': output_files['movements']['filename'],
            'master':    output_files['master']['filename']
        }
        if 'next_month' in output_files:
            filenames['next_month'] = output_files['next_month']['filename']

        return jsonify({
            'status': 'success',
            'filenames': filenames
        })

    except Exception as e:
        logger.error(f"Error in finalize: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


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

        # Cobro month/year drives the 26-of-previous-month cutoff
        cobro_mes  = int(request.form.get('cobro_mes',  0))
        cobro_anio = int(request.form.get('cobro_anio', 0))

        # Process data
        logger.info("Starting data processing...")
        result = process_excel_files(master_path, saved_movement_paths,
                                     cobro_mes=cobro_mes, cobro_anio=cobro_anio)

        if result['status'] != 'success':
            raise Exception(result.get('error', 'Unknown error'))

        # Store DataFrames and cobro params for finalize step
        movements_df  = result['dataframes']['movements']
        master_df     = result['dataframes']['master']
        next_month_df = result['dataframes'].get('next_month')

        last_processed_data['movements_df']  = movements_df
        last_processed_data['master_df']     = master_df
        last_processed_data['next_month_df'] = next_month_df
        last_processed_data['cobro_mes']     = cobro_mes
        last_processed_data['cobro_anio']    = cobro_anio
        last_processed_data['analytics']     = report_generator.generate_movement_analytics(movements_df, master_df)

        # Build list of ingresos for gender confirmation (current + next month)
        ingresos_sin_genero = []
        frames = [movements_df]
        if next_month_df is not None:
            frames.append(next_month_df)
        for frame in frames:
            for _, row in frame.iterrows():
                if str(row.get('TIPO_NOVEDAD', '')).strip().lower() == 'ingreso':
                    ingresos_sin_genero.append({
                        'id':       str(row.get('NUMERO_IDENTIFICACION_ASEGURADO', '')),
                        'apellidos': str(row.get('APELLIDOS_ASEGURADO', '')),
                        'nombres':   str(row.get('NOMBRES_ASEGURADO', '')),
                        'genero':    str(row.get('GENERO', '') or '')
                    })

        logger.info("Processing completed — awaiting gender confirmation")

        return jsonify({
            'status': 'success',
            'statistics': result['statistics'],
            'ingresos_para_genero': ingresos_sin_genero,
            'preview_movements': result['preview']['movements'],
            'preview_master':    result['preview']['master'],
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


@app.route('/api/history/list', methods=['GET'])
def get_history_list() -> Tuple[str, int]:
    """
    Get list of all historical processing records

    Returns:
        Tuple[str, int]: JSON list of records and HTTP status code
    """
    try:
        records = history_manager.get_history_list()
        logger.info(f"Retrieved {len(records)} historical records")
        return jsonify(records), 200
    except Exception as e:
        logger.error(f"Error retrieving history list: {e}", exc_info=True)
        return jsonify({'error': 'Error retrieving history'}), 500


@app.route('/api/history/compare', methods=['POST'])
def compare_history() -> Tuple[str, int]:
    """
    Compare old historical record with current movements

    Expected JSON:
        - record_id: ID of historical record to compare with

    Returns:
        Tuple[str, int]: Comparison results and HTTP status code
    """
    try:
        data = request.get_json()
        record_id = data.get('record_id')

        if not record_id:
            return jsonify({'error': 'record_id required'}), 400

        if last_processed_data['movements_df'] is None:
            return jsonify({'error': 'No current data to compare. Process files first.'}), 400

        comparison = history_manager.compare_records(
            record_id,
            last_processed_data['movements_df']
        )

        if 'error' in comparison:
            return jsonify(comparison), 404

        logger.info(f"Comparison completed: Added={comparison['summary']['added_count']}, "
                   f"Removed={comparison['summary']['removed_count']}, "
                   f"Modified={comparison['summary']['modified_count']}")

        return jsonify(comparison), 200

    except Exception as e:
        logger.error(f"Error comparing history: {e}", exc_info=True)
        return jsonify({'error': 'Error comparing records'}), 500


@app.route('/api/reports/pdf', methods=['POST'])
def generate_pdf_report() -> Tuple[str, int]:
    """
    Generate an advanced PDF report from the last processed data.

    Returns:
        Tuple[str, int]: JSON response with report filename or error message
    """
    try:
        # Check if data has been processed
        if (last_processed_data['movements_df'] is None or
            last_processed_data['master_df'] is None):
            return jsonify({
                'status': 'error',
                'error': 'No se han procesado datos aún. Por favor, procese archivos primero.'
            }), 400

        # Generate PDF report
        movements_df = last_processed_data['movements_df']
        master_df = last_processed_data['master_df']
        analytics = last_processed_data['analytics']

        pdf_path = report_generator.generate_pdf_report(
            movements_df, master_df, analytics
        )

        filename = os.path.basename(pdf_path)
        logger.info(f"Generated PDF report: {filename}")

        return jsonify({
            'status': 'success',
            'filename': filename,
            'filepath': pdf_path,
            'message': 'Reporte PDF generado exitosamente'
        }), 200

    except Exception as e:
        logger.error(f"Error generating PDF report: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': 'Error al generar reporte PDF',
            'details': str(e)
        }), 500


@app.route('/api/reports/excel', methods=['POST'])
def generate_excel_report() -> Tuple[str, int]:
    """
    Generate an advanced Excel report from the last processed data.

    Returns:
        Tuple[str, int]: JSON response with report filename or error message
    """
    try:
        # Check if data has been processed
        if (last_processed_data['movements_df'] is None or
            last_processed_data['master_df'] is None):
            return jsonify({
                'status': 'error',
                'error': 'No se han procesado datos aún. Por favor, procese archivos primero.'
            }), 400

        # Generate Excel report
        movements_df = last_processed_data['movements_df']
        master_df = last_processed_data['master_df']
        analytics = last_processed_data['analytics']

        excel_path = report_generator.export_to_excel(
            movements_df, master_df, analytics
        )

        filename = os.path.basename(excel_path)
        logger.info(f"Generated Excel report: {filename}")

        return jsonify({
            'status': 'success',
            'filename': filename,
            'filepath': excel_path,
            'message': 'Reporte Excel generado exitosamente'
        }), 200

    except Exception as e:
        logger.error(f"Error generating Excel report: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': 'Error al generar reporte Excel',
            'details': str(e)
        }), 500


@app.route('/api/reports/download/<path:filename>', methods=['GET'])
def download_report(filename: str) -> Tuple[Any, int]:
    """
    Download a generated report file (PDF or Excel).

    Security: Prevents directory traversal attacks.

    Args:
        filename: Name of the report file to download

    Returns:
        Tuple[Any, int]: File object with HTTP status or error JSON response
    """
    try:
        filepath = get_file_path(filename, config.OUTPUT_DIR)

        if not filepath:
            logger.warning(f"Report file not found: {filename}")
            return jsonify({'error': 'Reporte no encontrado'}), 404

        # Determine MIME type based on file extension
        if filename.lower().endswith('.pdf'):
            mimetype = 'application/pdf'
        elif filename.lower().endswith('.xlsx'):
            mimetype = EXCEL_MIMETYPE
        else:
            mimetype = 'application/octet-stream'

        logger.info(f"Downloading report: {filename}")
        return send_file(
            filepath,
            mimetype=mimetype,
            as_attachment=True,
            download_name=os.path.basename(filepath)
        )

    except ValueError as e:
        logger.warning(f"Invalid report file request: {e}")
        return jsonify({'error': 'Solicitud de archivo inválida'}), 400
    except FileNotFoundError as e:
        logger.warning(f"Report file not found during download {filename}: {e}")
        return jsonify({'error': 'Reporte no encontrado'}), 404
    except OSError as e:
        logger.error(f"File system error downloading report {filename}: {e}", exc_info=True)
        return jsonify({'error': 'Error al acceder al archivo'}), 500
    except Exception as e:
        logger.error(f"Unexpected error downloading report {filename}: {e}", exc_info=True)
        return jsonify({'error': 'Error descargando reporte'}), 500


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
