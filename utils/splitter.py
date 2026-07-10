"""
Independent module: split ingresos and egresos into blocks of N people.

This module is fully self-contained and does NOT touch the monthly
reconciliation logic. It reads one or more uploaded Excel files, classifies
records into INGRESOS and EGRESOS, and writes one Excel file per block of
`block_size` records (default 20), preserving the original column structure.
"""

import os
import zipfile
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

import pandas as pd

logger = logging.getLogger(__name__)

BLOCK_SIZE = 20

# Keywords used to locate the header row inside raw movement sheets
_HEADER_KEYWORDS = ['IDENTIFICACION', 'C.C.', 'CEDULA', 'N° DOC', 'DOC', 'DOCUMENTO']


def split_ingresos_egresos(
    file_paths: List[str],
    output_dir: str,
    block_size: int = BLOCK_SIZE
) -> Dict[str, Any]:
    """
    Read files, classify records and write blocks of `block_size`.

    Returns a dict with:
        - status: 'success' or 'error'
        - total_ingresos / total_egresos: record counts
        - ingresos_files / egresos_files: number of files generated
        - files: list of {'filename', 'category'} generated
        - zip_filename: name of the ZIP bundling all generated files
        - logs: processing messages
    """
    logs: List[str] = []

    ingresos_rows: List[Dict[str, Any]] = []
    egresos_rows: List[Dict[str, Any]] = []
    ingresos_cols: List[str] = []
    egresos_cols: List[str] = []

    for fpath in file_paths:
        fname = os.path.basename(fpath)
        try:
            xl = pd.ExcelFile(fpath)
        except Exception as e:
            logs.append(f"[!] No se pudo leer {fname}: {e}")
            continue

        handled = False

        # ── Case A: raw movement file with INGRESOS / RETIROS sheets ──
        for sheet_name in xl.sheet_names:
            up = str(sheet_name).strip().upper()
            if up in ('INGRESOS', 'RETIROS', 'EGRESOS'):
                cols, rows = _read_sheet_table(fpath, sheet_name)
                if not rows:
                    continue
                handled = True
                if up == 'INGRESOS':
                    if not ingresos_cols:
                        ingresos_cols = cols
                    ingresos_rows.extend(rows)
                    logs.append(f"{fname} [{sheet_name}]: {len(rows)} ingresos")
                else:
                    if not egresos_cols:
                        egresos_cols = cols
                    egresos_rows.extend(rows)
                    logs.append(f"{fname} [{sheet_name}]: {len(rows)} egresos")

        if handled:
            continue

        # ── Case B: generated / PlantillaCargue format with TIPO_NOVEDAD ──
        sheet = 'Sheet1' if 'Sheet1' in xl.sheet_names else xl.sheet_names[-1]
        try:
            df = pd.read_excel(fpath, sheet_name=sheet)
        except Exception as e:
            logs.append(f"[!] Error leyendo {fname}: {e}")
            continue

        cols = [str(c) for c in df.columns]
        tipo_col = _find_tipo_column(cols)
        if not tipo_col:
            logs.append(f"[!] {fname}: no se encontró columna de tipo (INGRESO/EGRESO); omitido")
            continue

        n_ing = n_egr = 0
        for _, row in df.iterrows():
            record = {c: _clean(row.get(c)) for c in cols}
            cat = _classify(row.get(tipo_col))
            if cat == 'ingreso':
                if not ingresos_cols:
                    ingresos_cols = cols
                ingresos_rows.append(record)
                n_ing += 1
            elif cat == 'egreso':
                if not egresos_cols:
                    egresos_cols = cols
                egresos_rows.append(record)
                n_egr += 1

        logs.append(f"{fname}: {n_ing} ingresos, {n_egr} egresos")

    # ── Write blocks directly into output_dir (so downloads resolve by name) ──
    os.makedirs(output_dir, exist_ok=True)
    run_stamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    generated: List[Dict[str, str]] = []
    generated += _write_blocks(ingresos_rows, ingresos_cols, 'Ingresos', 'INGRESOS', output_dir, block_size)
    generated += _write_blocks(egresos_rows, egresos_cols, 'Egresos', 'EGRESOS', output_dir, block_size)

    if not generated:
        return {
            'status': 'error',
            'error': 'No se encontraron registros de ingresos ni egresos en los archivos.',
            'logs': logs
        }

    # ── Bundle everything into a ZIP ──
    zip_filename = f"DIVISION_INGRESOS_EGRESOS_{run_stamp}.zip"
    zip_path = os.path.join(output_dir, zip_filename)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in generated:
            zf.write(os.path.join(output_dir, item['filename']), arcname=item['filename'])

    ingresos_files = sum(1 for g in generated if g['category'] == 'Ingresos')
    egresos_files = sum(1 for g in generated if g['category'] == 'Egresos')

    logs.append(f"Generados {ingresos_files} archivos de ingresos y {egresos_files} de egresos")

    return {
        'status': 'success',
        'total_ingresos': len(ingresos_rows),
        'total_egresos': len(egresos_rows),
        'ingresos_files': ingresos_files,
        'egresos_files': egresos_files,
        'files': generated,
        'zip_filename': zip_filename,
        'logs': logs
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _write_blocks(
    rows: List[Dict[str, Any]],
    cols: List[str],
    label: str,
    sheet_name: str,
    out_dir: str,
    block_size: int
) -> List[Dict[str, str]]:
    """Write `rows` in chunks of `block_size` as label_01.xlsx, label_02.xlsx…"""
    if not rows:
        return []
    if not cols:
        cols = list(rows[0].keys())

    written: List[Dict[str, str]] = []
    total_blocks = (len(rows) + block_size - 1) // block_size
    for i in range(total_blocks):
        chunk = rows[i * block_size:(i + 1) * block_size]
        block_df = pd.DataFrame(chunk, columns=cols)
        filename = f"{label}_{i + 1:02d}.xlsx"
        path = os.path.join(out_dir, filename)
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            block_df.to_excel(writer, index=False, sheet_name=sheet_name)
        written.append({'filename': filename, 'category': label})
    return written


def _read_sheet_table(fpath: str, sheet_name: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Read a raw movement sheet: locate the header row, return columns and records."""
    try:
        raw = pd.read_excel(fpath, sheet_name=sheet_name, header=None)
    except Exception:
        return [], []

    header_idx = -1
    for i in range(min(25, len(raw))):
        row_str = " ".join(str(x).upper() for x in raw.iloc[i].values)
        if any(kw in row_str for kw in _HEADER_KEYWORDS):
            header_idx = i
            break
    if header_idx == -1:
        return [], []

    cols = [str(c).strip() for c in raw.iloc[header_idx].values]
    # De-duplicate / clean empty column names
    clean_cols = []
    for idx, c in enumerate(cols):
        if not c or c.lower() == 'nan':
            c = f"COL_{idx + 1}"
        clean_cols.append(c)

    rows: List[Dict[str, Any]] = []
    for _, r in raw.iloc[header_idx + 1:].iterrows():
        values = list(r.values)
        # Skip fully empty rows
        if all(_is_empty(v) for v in values):
            continue
        record = {clean_cols[j]: _clean(values[j]) for j in range(min(len(clean_cols), len(values)))}
        rows.append(record)
    return clean_cols, rows


def _find_tipo_column(cols: List[str]) -> Optional[str]:
    """Find the column that holds the movement type."""
    for c in cols:
        cu = str(c).upper()
        if 'TIPO_NOVEDAD' in cu or 'TIPO NOVEDAD' in cu or cu == 'TIPO' or 'NOVEDAD' in cu:
            return c
    return None


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


def _clean(val: Any) -> Any:
    """Return None for null-like values so Excel cells stay blank."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(val, str):
        s = val.strip()
        if s.lower() in ('nan', 'nat', 'none', ''):
            return None
        return s
    return val


def _is_empty(val: Any) -> bool:
    try:
        if pd.isna(val):
            return True
    except (TypeError, ValueError):
        pass
    return str(val).strip() == '' or str(val).strip().lower() == 'nan'
