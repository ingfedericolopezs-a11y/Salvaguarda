"""
Core data processing utilities for Excel file manipulation.

This module handles reading, processing, and writing Excel files for
the ROESAN-SALVAGUARDAR reconciliation application.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, List, Any, Tuple, Optional, Set

import config
from .validators import clean_id, split_name

logger = logging.getLogger(__name__)


def process_excel_files(
    master_path: str,
    movement_paths: List[str],
    header_search_rows: int = 20
) -> Dict[str, Any]:
    """
    Process master template and movement files for reconciliation.

    Reads the master template, extracts insured individuals, then processes
    movement files (INGRESOS/RETIROS) to generate reconciliation results.

    Args:
        master_path: Path to master template file (PLANTILLA CARGUE COBRO)
        movement_paths: List of movement file paths containing INGRESOS/RETIROS
        header_search_rows: Number of rows to search for headers (default: 20)

    Returns:
        Dict[str, Any]: Processing results containing:
            - status: 'success' or 'error'
            - statistics: Movement counts and master row counts
            - dataframes: Processed movements and master DataFrames
            - preview: Preview data for UI
            - logs: Processing log messages
            - error: Error message if status is 'error'

    Raises:
        Exception: If master file cannot be read or processing fails
    """
    logs: List[str] = []
    processed_rows: List[Dict[str, Any]] = []
    all_ingresos_ids: Set[str] = set()
    all_retiros_ids: Set[str] = set()

    # 1. Read Master Template
    try:
        master_df: pd.DataFrame = _read_excel_safe(master_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f'Master file not found: {master_path}')
    except pd.errors.ParserError as e:
        raise ValueError(f'Invalid Excel format in master file: {e}')
    except Exception as e:
        raise Exception(f'Error reading master file: {e}')

    # Build ID lookup from master
    id_lookup: Dict[str, Dict[str, Any]] = {}
    for idx, row in master_df.iterrows():
        cid: Optional[str] = clean_id(row.get('NUMERO_IDENTIFICACION_ASEGURADO'))
        if cid:
            id_lookup[cid] = {
                'CARGO': row.get('CARGO'),
                'GENERO': row.get('GENERO'),
                'FECHA_NACIMIENTO_ASEGURADO': row.get('FECHA_NACIMIENTO_ASEGURADO'),
                'VALOR_ASEGURADO_MUERTE': row.get('VALOR_ASEGURADO_MUERTE', 5000000)
            }

    logs.append(f"Master file loaded: {len(id_lookup)} unique IDs")

    # 2. Process Movement Files
    logs.append(f"Processing {len(movement_paths)} movement files...")

    for fpath in movement_paths:
        fname = os.path.basename(fpath)

        try:
            xl = pd.ExcelFile(fpath)
        except Exception as e:
            logs.append(f"[!] Error reading {fname}: {e}")
            continue

        for sheet_name in ['INGRESOS', 'RETIROS']:
            if sheet_name not in xl.sheet_names:
                continue

            logs.append(f"Processing {fname} - Sheet: {sheet_name}")

            try:
                df_raw = pd.read_excel(fpath, sheet_name=sheet_name, header=None)

                # Locate header row
                header_idx = _find_header_row(df_raw, header_search_rows)

                if header_idx == -1:
                    logs.append(f"  [!] Warning: Headers not found in {fname} - {sheet_name}")
                    continue

                # Extract data
                df = df_raw.iloc[header_idx+1:].copy()
                df.columns = df_raw.iloc[header_idx].values

                # Standardize column names
                cols = [str(c).upper().strip() for c in df.columns]
                df.columns = cols

                # Find relevant columns
                id_col = _find_column(cols, ['IDENTIFICACION', 'C.C.', 'CEDULA', 'DOC'])
                name_col = _find_column(cols, ['NOMBRE', 'RAZON SOCIAL', 'APELLIDO'])
                fecha_nac_col = _find_column(cols, ['NACIMIENTO'])
                fecha_nov_col = _find_column(cols, ['INGRESO', 'RETIRO', 'EGRESO', 'FECHA'])

                if not id_col or not name_col:
                    logs.append(f"  [!] Error: Required columns not found in {fname} - {sheet_name}")
                    continue

                # Process rows
                count_records = 0
                for _, row in df.iterrows():
                    n_id = clean_id(row.get(id_col))
                    if not n_id or n_id == 'NAN':
                        continue

                    full_name = row.get(name_col)
                    is_ingreso = sheet_name == 'INGRESOS'
                    apellidos, nombres = split_name(full_name)

                    # Get info from master lookup
                    lookup_data = id_lookup.get(n_id, {})
                    cargo = lookup_data.get('CARGO')
                    genero = lookup_data.get('GENERO')
                    valor_aseg = lookup_data.get('VALOR_ASEGURADO_MUERTE', 5000000)

                    # Birth date
                    fecha_nac = None
                    if fecha_nac_col and pd.notna(row.get(fecha_nac_col)):
                        fecha_nac = row.get(fecha_nac_col)
                    if pd.isna(fecha_nac):
                        fecha_nac = lookup_data.get('FECHA_NACIMIENTO_ASEGURADO')
                    fecha_nac = _format_date(fecha_nac)

                    # Movement date
                    fecha_novedad = row.get(fecha_nov_col) if fecha_nov_col else None
                    fecha_novedad = _format_date(fecha_novedad)

                    tipo_novedad = 'INGRESO' if is_ingreso else 'RETIRO'

                    if is_ingreso:
                        all_ingresos_ids.add(n_id)
                    else:
                        all_retiros_ids.add(n_id)

                    processed_rows.append({
                        'NUMERO_POLIZA': config.NUMERO_POLIZA,
                        'APELLIDOS_ASEGURADO': apellidos,
                        'NOMBRES_ASEGURADO': nombres,
                        'TIPO_IDENTIFICACION_ASEGURADO': 'CC',
                        'NUMERO_IDENTIFICACION_ASEGURADO': n_id,
                        'CARGO': cargo,
                        'GENERO': genero,
                        'FECHA_NACIMIENTO_ASEGURADO': fecha_nac,
                        'VALOR_ASEGURADO_MUERTE': valor_aseg,
                        'TIPO_NOVEDAD': tipo_novedad,
                        'FECHA_NOVEDAD': fecha_novedad
                    })
                    count_records += 1

                logs.append(f"  -> Processed {count_records} valid records")

            except Exception as e:
                logs.append(f"  [!] Error processing {sheet_name}: {e}")
                logger.error(f"Error processing {fname} - {sheet_name}: {e}")

    # 3. Generate output DataFrames
    expected_cols = [
        'NUMERO_POLIZA', 'APELLIDOS_ASEGURADO', 'NOMBRES_ASEGURADO',
        'TIPO_IDENTIFICACION_ASEGURADO', 'NUMERO_IDENTIFICACION_ASEGURADO',
        'CARGO', 'GENERO', 'FECHA_NACIMIENTO_ASEGURADO', 'VALOR_ASEGURADO_MUERTE',
        'TIPO_NOVEDAD', 'FECHA_NOVEDAD'
    ]

    result_df = pd.DataFrame(processed_rows, columns=expected_cols)

    # Update master with new ingresos and remove retiros
    new_master_rows = []
    for idx, row in master_df.iterrows():
        c_id = clean_id(row.get('NUMERO_IDENTIFICACION_ASEGURADO'))
        if c_id and c_id != 'NAN' and c_id not in all_retiros_ids:
            row_dict = row.to_dict()
            if 'FECHA_NACIMIENTO_ASEGURADO' in row_dict:
                row_dict['FECHA_NACIMIENTO_ASEGURADO'] = _format_date(row_dict['FECHA_NACIMIENTO_ASEGURADO'])
            new_master_rows.append(row_dict)

    # Add new ingresos
    for row in processed_rows:
        if row['TIPO_NOVEDAD'] == 'INGRESO':
            new_master_rows.append(dict(row))

    new_master_df = pd.DataFrame(new_master_rows)
    for col in expected_cols:
        if col not in new_master_df.columns:
            new_master_df[col] = None
    new_master_df = new_master_df[expected_cols]

    logs.append("Processing completed successfully")

    # Create preview data
    preview_movs = result_df.head(50).replace({np.nan: None}).to_dict(orient='records')
    preview_master = new_master_df.head(50).replace({np.nan: None}).to_dict(orient='records')

    return {
        'status': 'success',
        'statistics': {
            'total_movements': len(result_df),
            'total_ingresos': len(all_ingresos_ids),
            'total_retiros': len(all_retiros_ids),
            'master_total_before': len(master_df),
            'master_total_after': len(new_master_df)
        },
        'dataframes': {
            'movements': result_df,
            'master': new_master_df
        },
        'preview': {
            'movements': preview_movs,
            'master': preview_master
        },
        'logs': logs
    }


def generate_output_files(
    movements_df: pd.DataFrame,
    master_df: pd.DataFrame,
    output_dir: str
) -> Dict[str, Dict[str, str]]:
    """
    Write processed DataFrames to Excel files.

    Creates two Excel files:
    - INGRESOS_Y_RETIROS_GENERADOS_[MONTH]_[YEAR].xlsx
    - PLANTILLA_CARGUE_COBRO_[MONTH]_[YEAR].xlsx

    Args:
        movements_df: Processed movements DataFrame
        master_df: Updated master DataFrame
        output_dir: Output directory path

    Returns:
        Dict[str, Dict[str, str]]: File metadata with keys 'movements' and 'master',
            each containing 'filename' and 'path'

    Raises:
        FileNotFoundError: If output directory does not exist
        Exception: If file writing fails
    """
    current_month: str = datetime.now().strftime('%B_%Y').upper()

    filenames = {
        'movements': f"INGRESOS_Y_RETIROS_GENERADOS_{current_month}.xlsx",
        'master': f"PLANTILLA_CARGUE_COBRO_{current_month}.xlsx"
    }

    expected_cols = [
        'NUMERO_POLIZA', 'APELLIDOS_ASEGURADO', 'NOMBRES_ASEGURADO',
        'TIPO_IDENTIFICACION_ASEGURADO', 'NUMERO_IDENTIFICACION_ASEGURADO',
        'CARGO', 'GENERO', 'FECHA_NACIMIENTO_ASEGURADO', 'VALOR_ASEGURADO_MUERTE',
        'TIPO_NOVEDAD', 'FECHA_NOVEDAD'
    ]

    try:
        # Write movements file
        movements_path = os.path.join(output_dir, filenames['movements'])
        with pd.ExcelWriter(movements_path, engine='openpyxl') as writer:
            movements_df.to_excel(writer, index=False, sheet_name='GENERAL', columns=expected_cols)

        # Write master file
        master_path = os.path.join(output_dir, filenames['master'])
        with pd.ExcelWriter(master_path, engine='openpyxl') as writer:
            master_df.to_excel(writer, index=False, sheet_name='Sheet1')

        logger.info(f"Output files generated: {filenames['movements']}, {filenames['master']}")

        return {
            'movements': {'filename': filenames['movements'], 'path': movements_path},
            'master': {'filename': filenames['master'], 'path': master_path}
        }
    except Exception as e:
        logger.error(f"Error generating output files: {e}")
        raise


# Helper functions

def _read_excel_safe(filepath: str) -> pd.DataFrame:
    """
    Read Excel file safely, trying different sheet names.

    Attempts to read 'Sheet1' first, then falls back to the last sheet
    in the workbook if Sheet1 is not found.

    Args:
        filepath: Path to the Excel file

    Returns:
        pd.DataFrame: The read Excel data

    Raises:
        FileNotFoundError: If file does not exist
        pd.errors.ParserError: If file cannot be parsed
    """
    try:
        return pd.read_excel(filepath, sheet_name="Sheet1")
    except ValueError:
        xls: pd.ExcelFile = pd.ExcelFile(filepath)
        return pd.read_excel(filepath, sheet_name=xls.sheet_names[-1])


def _find_header_row(df_raw: pd.DataFrame, max_rows: int) -> int:
    """
    Find header row by searching for identification-related keywords.

    Scans up to max_rows looking for common header keywords like
    IDENTIFICACION, C.C., CEDULA, etc.

    Args:
        df_raw: Raw DataFrame read without headers
        max_rows: Maximum number of rows to search

    Returns:
        int: 0-based index of header row, or -1 if not found
    """
    keywords: List[str] = ['IDENTIFICACION', 'C.C.', 'CEDULA', 'N° DOC', 'DOC']

    for i in range(min(max_rows, len(df_raw))):
        row_str: str = " ".join([str(x).upper() for x in df_raw.iloc[i].values])
        if any(kw in row_str for kw in keywords):
            return i

    return -1


def _find_column(columns: List[str], keywords: List[str]) -> Optional[str]:
    """
    Find first column matching any of the keywords.

    Performs a case-sensitive substring match against column names.

    Args:
        columns: List of column names to search
        keywords: List of keywords to match against

    Returns:
        str: First matching column name, or None if no match found
    """
    for col in columns:
        for kw in keywords:
            if kw in col:
                return col
    return None


def _format_date(date_val: Any) -> str:
    """
    Format date value to YYYY-MM-DD string.

    Handles pandas Timestamp, datetime, and string date values,
    converting them all to YYYY-MM-DD format.

    Args:
        date_val: Date value to format (Any type)

    Returns:
        str: Formatted date string in YYYY-MM-DD format, or empty string if None/NaN
    """
    if pd.isna(date_val):
        return ""

    if isinstance(date_val, (pd.Timestamp, datetime)):
        return date_val.strftime('%Y-%m-%d')

    return str(date_val).strip() if date_val else ""
