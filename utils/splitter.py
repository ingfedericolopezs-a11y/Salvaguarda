"""
Independent module: split ingresos and egresos into blocks of N people.

Fully self-contained orchestration. It REUSES (read-only) helper functions
from data_processor so the output format is IDENTICAL to the monthly
reconciliation output (PlantillaCargue: 'Descripcion Campos' sheet intact +
Sheet1 with the standard 11 columns). It never modifies that module.
"""

import os
import zipfile
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

import pandas as pd

import config
from .validators import clean_id, split_name
from .data_processor import (
    _read_excel_safe, _find_header_row, _find_column,
    _format_date, _normalize_genero, _write_with_template,
    _open_excel_any,
)

logger = logging.getLogger(__name__)

BLOCK_SIZE = 20

# Same 11 columns / order as the reconciliation output
COLS = [
    'NUMERO_POLIZA', 'APELLIDOS_ASEGURADO', 'NOMBRES_ASEGURADO',
    'TIPO_IDENTIFICACION_ASEGURADO', 'NUMERO_IDENTIFICACION_ASEGURADO',
    'CARGO', 'GENERO', 'FECHA_NACIMIENTO_ASEGURADO', 'VALOR_ASEGURADO_MUERTE',
    'TIPO_NOVEDAD', 'FECHA_NOVEDAD'
]


def analyze_files(master_path: Optional[str], file_paths: List[str]) -> Dict[str, Any]:
    """
    Read the (optional) master file and the data files, classify each record
    into ingreso/egreso and normalize it to the standard 11-column format.

    Returns:
        status, ingreso_records, egreso_records, ingresos_para_genero, logs
    """
    logs: List[str] = []

    # Build master lookup (current state of who is insured)
    id_lookup: Dict[str, Dict[str, Any]] = {}
    if master_path:
        try:
            master_df = _read_excel_safe(master_path)
            for _, row in master_df.iterrows():
                cid = clean_id(row.get('NUMERO_IDENTIFICACION_ASEGURADO'))
                if cid:
                    id_lookup[cid] = {
                        'CARGO': row.get('CARGO'),
                        'GENERO': _normalize_genero(row.get('GENERO')),
                        'FECHA_NACIMIENTO_ASEGURADO': row.get('FECHA_NACIMIENTO_ASEGURADO'),
                        'VALOR_ASEGURADO_MUERTE': row.get('VALOR_ASEGURADO_MUERTE', 5000000),
                    }
            logs.append(f"Archivo madre: {len(id_lookup)} personas registradas")
        except Exception as e:
            logs.append(f"[!] No se pudo leer el archivo madre: {e}")

    ingreso_records: List[Dict[str, Any]] = []
    egreso_records: List[Dict[str, Any]] = []
    seen: set = set()

    for fpath in file_paths:
        fname = os.path.basename(fpath)
        try:
            xl = _open_excel_any(fpath)
        except Exception as e:
            logs.append(f"[!] No se pudo leer {fname}: {e}")
            continue

        handled = False

        # ── Case A: raw movement file with INGRESOS / RETIROS sheets ──
        for sheet_name in xl.sheet_names:
            up = str(sheet_name).strip().upper()
            if up not in ('INGRESOS', 'RETIROS', 'EGRESOS'):
                continue
            is_ingreso = (up == 'INGRESOS')
            recs = _extract_from_raw_sheet(fpath, sheet_name, is_ingreso, id_lookup, seen)
            if recs:
                handled = True
                (ingreso_records if is_ingreso else egreso_records).extend(recs)
                logs.append(f"{fname} [{sheet_name}]: {len(recs)} {'ingresos' if is_ingreso else 'egresos'}")

        if handled:
            continue

        # ── Case B: generated / PlantillaCargue format (Sheet1 + TIPO_NOVEDAD) ──
        sheet = 'Sheet1' if 'Sheet1' in xl.sheet_names else xl.sheet_names[-1]
        try:
            df = pd.read_excel(xl, sheet_name=sheet)
        except Exception as e:
            logs.append(f"[!] Error leyendo {fname}: {e}")
            continue

        cols = [str(c).upper().strip() for c in df.columns]
        df.columns = cols
        tipo_col = _find_column(cols, ['TIPO_NOVEDAD', 'NOVEDAD', 'TIPO'])
        if not tipo_col:
            logs.append(f"[!] {fname}: sin columna de tipo (INGRESO/EGRESO); omitido")
            continue

        n_ing = n_egr = 0
        for _, row in df.iterrows():
            cat = _classify(row.get(tipo_col))
            if cat is None:
                continue
            rec = _normalize_generated_row(row, cat == 'ingreso', id_lookup)
            if rec is None:
                continue
            key = (rec['NUMERO_IDENTIFICACION_ASEGURADO'], rec['TIPO_NOVEDAD'], rec['FECHA_NOVEDAD'])
            if key in seen:
                continue
            seen.add(key)
            if cat == 'ingreso':
                ingreso_records.append(rec); n_ing += 1
            else:
                egreso_records.append(rec); n_egr += 1
        logs.append(f"{fname}: {n_ing} ingresos, {n_egr} egresos")

    # Ingresos that need gender confirmation
    ingresos_para_genero = [{
        'id': r['NUMERO_IDENTIFICACION_ASEGURADO'],
        'apellidos': r['APELLIDOS_ASEGURADO'] or '',
        'nombres': r['NOMBRES_ASEGURADO'] or '',
        'genero': r['GENERO'] or ''
    } for r in ingreso_records]

    return {
        'status': 'success',
        'ingreso_records': ingreso_records,
        'egreso_records': egreso_records,
        'ingresos_para_genero': ingresos_para_genero,
        'logs': logs
    }


def generate_split_files(
    ingreso_records: List[Dict[str, Any]],
    egreso_records: List[Dict[str, Any]],
    output_dir: str,
    block_size: int = BLOCK_SIZE
) -> Dict[str, Any]:
    """Write blocks of `block_size` in PlantillaCargue format and bundle a ZIP."""
    os.makedirs(output_dir, exist_ok=True)
    run_stamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    generated: List[Dict[str, str]] = []
    generated += _write_blocks(ingreso_records, 'Ingresos', output_dir, block_size)
    generated += _write_blocks(egreso_records, 'Egresos', output_dir, block_size)

    if not generated:
        return {'status': 'error',
                'error': 'No se encontraron registros de ingresos ni egresos.'}

    zip_filename = f"DIVISION_INGRESOS_EGRESOS_{run_stamp}.zip"
    zip_path = os.path.join(output_dir, zip_filename)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in generated:
            zf.write(os.path.join(output_dir, item['filename']), arcname=item['filename'])

    return {
        'status': 'success',
        'total_ingresos': len(ingreso_records),
        'total_egresos': len(egreso_records),
        'ingresos_files': sum(1 for g in generated if g['category'] == 'Ingresos'),
        'egresos_files': sum(1 for g in generated if g['category'] == 'Egresos'),
        'files': generated,
        'zip_filename': zip_filename
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _write_blocks(records: List[Dict[str, Any]], label: str,
                  out_dir: str, block_size: int) -> List[Dict[str, str]]:
    """Write records in chunks of block_size using the PlantillaCargue template."""
    if not records:
        return []
    written: List[Dict[str, str]] = []
    total = (len(records) + block_size - 1) // block_size
    for i in range(total):
        chunk = records[i * block_size:(i + 1) * block_size]
        block_df = pd.DataFrame(chunk, columns=COLS)
        filename = f"{label}_{i + 1:02d}.xlsx"
        _write_with_template(block_df, COLS, os.path.join(out_dir, filename))
        written.append({'filename': filename, 'category': label})
    return written


def _extract_from_raw_sheet(fpath: str, sheet_name: str, is_ingreso: bool,
                            id_lookup: Dict[str, Dict[str, Any]],
                            seen: set) -> List[Dict[str, Any]]:
    """Extract normalized records from a raw INGRESOS/RETIROS sheet."""
    try:
        df_raw = pd.read_excel(_open_excel_any(fpath), sheet_name=sheet_name, header=None)
    except Exception:
        return []

    header_idx = _find_header_row(df_raw, 25)
    if header_idx == -1:
        return []

    df = df_raw.iloc[header_idx + 1:].copy()
    cols = [str(c).upper().strip() for c in df_raw.iloc[header_idx].values]
    df.columns = cols

    id_col = _find_column(cols, ['IDENTIFICACION', 'C.C.', 'CEDULA', 'DOC'])
    name_col = _find_column(cols, ['NOMBRE', 'RAZON SOCIAL', 'APELLIDO'])
    fecha_nac_col = _find_column(cols, ['NACIMIENTO'])
    fecha_nov_col = None
    for c in cols:
        cu = c.upper() if c else ''
        if 'FECHA' in cu and ('INGRESO' in cu or 'RETIRO' in cu):
            fecha_nov_col = c
            break
    if not fecha_nov_col:
        fecha_nov_col = _find_column(cols, ['NOVEDAD', 'INGRESO', 'RETIRO', 'EGRESO', 'FECHA'])

    if not id_col or not name_col:
        return []

    recs: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        n_id = clean_id(row.get(id_col))
        if not n_id or n_id == 'NAN':
            continue
        apellidos, nombres = split_name(row.get(name_col))
        lookup = id_lookup.get(n_id, {})

        fecha_nac = row.get(fecha_nac_col) if fecha_nac_col else None
        try:
            if pd.isna(fecha_nac):
                fecha_nac = lookup.get('FECHA_NACIMIENTO_ASEGURADO')
        except (TypeError, ValueError):
            pass

        fecha_nov = _format_date(row.get(fecha_nov_col)) if fecha_nov_col else ''
        tipo = 'Ingreso' if is_ingreso else 'Retiro'

        key = (n_id, tipo, fecha_nov)
        if key in seen:
            continue
        seen.add(key)

        recs.append({
            'NUMERO_POLIZA': config.NUMERO_POLIZA,
            'APELLIDOS_ASEGURADO': apellidos,
            'NOMBRES_ASEGURADO': nombres,
            'TIPO_IDENTIFICACION_ASEGURADO': 'CC',
            'NUMERO_IDENTIFICACION_ASEGURADO': n_id,
            'CARGO': config.CARGO_DEFAULT if is_ingreso else lookup.get('CARGO'),
            'GENERO': _normalize_genero(lookup.get('GENERO')),
            'FECHA_NACIMIENTO_ASEGURADO': _format_date(fecha_nac),
            'VALOR_ASEGURADO_MUERTE': lookup.get('VALOR_ASEGURADO_MUERTE', 5000000),
            'TIPO_NOVEDAD': tipo,
            'FECHA_NOVEDAD': fecha_nov,
        })
    return recs


def _normalize_generated_row(row, is_ingreso: bool,
                             id_lookup: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Map a row from a PlantillaCargue-format file to a normalized record."""
    n_id = clean_id(row.get('NUMERO_IDENTIFICACION_ASEGURADO'))
    if not n_id or n_id == 'NAN':
        return None
    lookup = id_lookup.get(n_id, {})

    genero = _normalize_genero(row.get('GENERO')) or _normalize_genero(lookup.get('GENERO'))

    cargo = row.get('CARGO')
    if cargo is None or (isinstance(cargo, float) and cargo != cargo) or not str(cargo).strip() or str(cargo).lower() == 'nan':
        cargo = config.CARGO_DEFAULT if is_ingreso else lookup.get('CARGO')

    valor = row.get('VALOR_ASEGURADO_MUERTE')
    try:
        if pd.isna(valor):
            valor = lookup.get('VALOR_ASEGURADO_MUERTE', 5000000)
    except (TypeError, ValueError):
        pass

    fecha_nac = row.get('FECHA_NACIMIENTO_ASEGURADO')
    try:
        if pd.isna(fecha_nac):
            fecha_nac = lookup.get('FECHA_NACIMIENTO_ASEGURADO')
    except (TypeError, ValueError):
        pass

    return {
        'NUMERO_POLIZA': config.NUMERO_POLIZA,
        'APELLIDOS_ASEGURADO': row.get('APELLIDOS_ASEGURADO'),
        'NOMBRES_ASEGURADO': row.get('NOMBRES_ASEGURADO'),
        'TIPO_IDENTIFICACION_ASEGURADO': 'CC',
        'NUMERO_IDENTIFICACION_ASEGURADO': n_id,
        'CARGO': cargo,
        'GENERO': genero,
        'FECHA_NACIMIENTO_ASEGURADO': _format_date(fecha_nac),
        'VALOR_ASEGURADO_MUERTE': valor,
        'TIPO_NOVEDAD': 'Ingreso' if is_ingreso else 'Retiro',
        'FECHA_NOVEDAD': _format_date(row.get('FECHA_NOVEDAD')),
    }


def _classify(value: Any) -> Optional[str]:
    """Return 'ingreso', 'egreso', or None from a TIPO_NOVEDAD value."""
    if value is None:
        return None
    s = str(value).strip().lower()
    if s.startswith('ingres'):
        return 'ingreso'
    if s.startswith('retir') or s.startswith('egres'):
        return 'egreso'
    return None
