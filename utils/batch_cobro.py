"""
Independent module: generate one COBRO plantilla per month in a range.

Given the initial master (current state) and all movement files, it produces a
separate PLANTILLA_CARGUE_COBRO for each month between a start and an end month.
Every row is dated the 26 of the month before its cobro month, matching the
monthly billing rule. Output format is IDENTICAL to the reconciliation output.

Fully self-contained; reuses (read-only) helpers from data_processor / splitter.
"""

import os
import zipfile
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

import pandas as pd

import config
from .validators import clean_id
from .data_processor import (
    _read_excel_safe, _write_with_template,
    _format_date, _normalize_genero, _parse_full_date,
)
from .splitter import analyze_files, COLS

logger = logging.getLogger(__name__)

MESES = {
    1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL', 5: 'MAYO', 6: 'JUNIO',
    7: 'JULIO', 8: 'AGOSTO', 9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'
}


def analyze_batch(master_path: Optional[str], file_paths: List[str]) -> Dict[str, Any]:
    """Read master roster + all movements. Return records and ingresos needing gender."""
    logs: List[str] = []

    base_records: List[Dict[str, Any]] = []
    base_ids: set = set()
    if master_path:
        try:
            df = _read_excel_safe(master_path)
            for _, row in df.iterrows():
                cid = clean_id(row.get('NUMERO_IDENTIFICACION_ASEGURADO'))
                if not cid or cid == 'NAN' or cid in base_ids:
                    continue
                base_ids.add(cid)
                base_records.append({
                    'NUMERO_POLIZA': config.NUMERO_POLIZA,
                    'APELLIDOS_ASEGURADO': row.get('APELLIDOS_ASEGURADO'),
                    'NOMBRES_ASEGURADO': row.get('NOMBRES_ASEGURADO'),
                    'TIPO_IDENTIFICACION_ASEGURADO': 'CC',
                    'NUMERO_IDENTIFICACION_ASEGURADO': cid,
                    'CARGO': row.get('CARGO'),
                    'GENERO': _normalize_genero(row.get('GENERO')),
                    'FECHA_NACIMIENTO_ASEGURADO': _format_date(row.get('FECHA_NACIMIENTO_ASEGURADO')),
                    'VALOR_ASEGURADO_MUERTE': row.get('VALOR_ASEGURADO_MUERTE', 5000000),
                    'TIPO_NOVEDAD': 'Cobro',
                    'FECHA_NOVEDAD': '',
                })
            logs.append(f"Archivo madre: {len(base_records)} personas en estado inicial")
        except Exception as e:
            logs.append(f"[!] No se pudo leer el archivo madre: {e}")

    # Reuse the splitter's normalization to read all movements
    mv = analyze_files(master_path, file_paths)
    if mv['status'] != 'success':
        return {'status': 'error', 'error': mv.get('error', 'Error al leer movimientos'), 'logs': logs}

    logs += mv.get('logs', [])

    return {
        'status': 'success',
        'base_records': base_records,
        'ingreso_records': mv['ingreso_records'],
        'egreso_records': mv['egreso_records'],
        'ingresos_para_genero': mv['ingresos_para_genero'],
        'logs': logs
    }


def generate_batch(
    base_records: List[Dict[str, Any]],
    ingreso_records: List[Dict[str, Any]],
    egreso_records: List[Dict[str, Any]],
    start_mes: int, start_anio: int,
    end_mes: int, end_anio: int,
    output_dir: str
) -> Dict[str, Any]:
    """Generate one cobro plantilla per month in [start, end]. Bundle a ZIP."""
    os.makedirs(output_dir, exist_ok=True)

    # Build a chronological list of movement events
    events: List[Tuple[datetime, str, Dict[str, Any]]] = []
    for r in ingreso_records:
        events.append((_parse_full_date(r['FECHA_NOVEDAD']), 'ingreso', r))
    for r in egreso_records:
        events.append((_parse_full_date(r['FECHA_NOVEDAD']), 'egreso', r))
    events.sort(key=lambda e: e[0] or datetime.min)

    months = _month_range(start_mes, start_anio, end_mes, end_anio)
    if not months:
        return {'status': 'error', 'error': 'Rango de meses inválido.'}

    run_stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    generated: List[Dict[str, Any]] = []

    for (mes, anio) in months:
        cutoff = _cutoff_date(mes, anio)        # 26 of the previous month
        fecha_cobro = cutoff.strftime('%d/%m/%Y')

        # Active roster as of the cutoff: start from base master, apply events in order
        active: Dict[str, Dict[str, Any]] = {
            r['NUMERO_IDENTIFICACION_ASEGURADO']: r for r in base_records
        }
        for (d, kind, r) in events:
            if d is not None and d > cutoff:
                break  # events are sorted ascending
            nid = r['NUMERO_IDENTIFICACION_ASEGURADO']
            if kind == 'ingreso':
                active[nid] = r
            else:
                active.pop(nid, None)

        # Build the cobro rows: everyone active, dated 26 of previous month
        rows = []
        for r in active.values():
            row = dict(r)
            row['TIPO_NOVEDAD'] = 'Cobro'
            row['FECHA_NOVEDAD'] = fecha_cobro
            rows.append(row)

        df = pd.DataFrame(rows, columns=COLS)
        fname = f"PLANTILLA_CARGUE_COBRO_{MESES[mes]}_{anio}.xlsx"
        _write_with_template(df, COLS, os.path.join(output_dir, fname))
        generated.append({
            'filename': fname,
            'mes': MESES[mes].capitalize(),
            'anio': anio,
            'fecha_cobro': fecha_cobro,
            'total': len(rows)
        })

    # Bundle all monthly plantillas into a ZIP
    zip_filename = f"CUENTAS_DE_COBRO_{run_stamp}.zip"
    zip_path = os.path.join(output_dir, zip_filename)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in generated:
            zf.write(os.path.join(output_dir, item['filename']), arcname=item['filename'])

    return {
        'status': 'success',
        'meses_generados': len(generated),
        'files': generated,
        'zip_filename': zip_filename
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _cutoff_date(cobro_mes: int, cobro_anio: int) -> datetime:
    """26 of the month BEFORE the cobro month."""
    prev_mes = 12 if cobro_mes == 1 else cobro_mes - 1
    prev_anio = cobro_anio - 1 if cobro_mes == 1 else cobro_anio
    return datetime(prev_anio, prev_mes, 26)


def _month_range(sm: int, sy: int, em: int, ey: int) -> List[Tuple[int, int]]:
    """Inclusive list of (month, year) from start to end."""
    if (sy, sm) > (ey, em):
        return []
    out = []
    m, y = sm, sy
    # Safety cap of 60 months
    for _ in range(60):
        out.append((m, y))
        if (y, m) == (ey, em):
            break
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out
