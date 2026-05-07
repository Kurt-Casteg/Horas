"""Generación de reportes: Excel en /output, en memoria (BytesIO) y consola."""

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd

from config import OUTPUT_DIR

_DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def generate_report(results: list[dict], period_label: str = "") -> Path:
    """Genera el reporte Excel y muestra el resumen en consola.

    Args:
        results: Lista de registros enriquecidos devuelta por calculate_overtime.
        period_label: Etiqueta del período, p.ej. 'Abril_2026'.

    Returns:
        Ruta del archivo Excel generado.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    rows = _build_rows(results)
    total_td = sum((r["overtime_td"] for r in results), timedelta(0))

    out_path = _write_excel(rows, total_td, period_label)
    _print_summary(results, total_td, period_label)

    return out_path


def generate_excel_bytes(results: list[dict], period_label: str = "") -> bytes:
    """Genera el Excel en memoria y devuelve los bytes para descarga directa."""
    rows = _build_rows(results)
    total_td = sum((r["overtime_td"] for r in results), timedelta(0))
    buffer = BytesIO()
    _write_excel_to(rows, total_td, buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _build_rows(results: list[dict]) -> list[dict]:
    rows = []
    for r in results:
        rows.append({
            "Fecha": r["date"].strftime("%d/%m/%Y"),
            "Día": _DAY_NAMES[r["date"].weekday()],
            "Feriado": "Sí" if r["is_holiday"] else "",
            "Entrada": r["entry"].strftime("%H:%M"),
            "Salida": r["exit"].strftime("%H:%M"),
            "Tiempo Trabajado": r["worked_str"],
            "Tiempo Estándar": r["base_str"],
            "Horas Extra": r["overtime_str"],
        })
    return rows


def _write_excel(rows: list[dict], total_td: timedelta, period_label: str) -> Path:
    filename = f"horas_extra{'_' + period_label if period_label else ''}.xlsx"
    out_path = OUTPUT_DIR / filename
    _write_excel_to(rows, total_td, out_path)
    return out_path


def _write_excel_to(rows: list[dict], total_td: timedelta, dest) -> None:
    """Escribe el Excel en dest (Path o BytesIO)."""
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(dest, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Horas Extra")
        ws = writer.sheets["Horas Extra"]
        total_row = ws.max_row + 2
        ws.cell(row=total_row, column=7, value="TOTAL")
        ws.cell(row=total_row, column=8, value=_td_to_str(total_td))
        col_widths = [13, 11, 9, 9, 9, 17, 17, 12]
        for i, w in enumerate(col_widths, start=1):
            ws.column_dimensions[_col_letter(i)].width = w


def _print_summary(results: list[dict], total_td: timedelta, period_label: str) -> None:
    sep = "=" * 72
    print(f"\n{sep}")
    title = f"  HORAS EXTRA EFECTIVAS{' — ' + period_label.upper().replace('_', ' ') if period_label else ''}"
    print(title)
    print(sep)
    print(f"  {'Fecha':<13}{'Día':<11}{'Entrada':<9}{'Salida':<9}"
          f"{'Trabajado':<12}{'Estándar':<11}{'Extra'}")
    print(f"  {'-' * 68}")

    for r in results:
        day_label = _DAY_NAMES[r["date"].weekday()]
        flag = " *" if r["is_holiday"] else ""
        ot = r["overtime_str"] if r["overtime_str"] else "-"
        print(
            f"  {r['date'].strftime('%d/%m/%Y'):<13}"
            f"{day_label:<11}"
            f"{r['entry'].strftime('%H:%M'):<9}"
            f"{r['exit'].strftime('%H:%M'):<9}"
            f"{r['worked_str']:<12}"
            f"{r['base_str']:<11}"
            f"{ot}{flag}"
        )

    print(f"  {'-' * 68}")
    h, rem = divmod(int(total_td.total_seconds()), 3600)
    m = rem // 60
    print(f"  {'TOTAL HORAS EXTRA:':<55} {h:02d}:{m:02d}")
    print(sep)
    if any(r["is_holiday"] for r in results):
        print("  * = día feriado\n")


def _td_to_str(td: timedelta) -> str:
    total_s = int(td.total_seconds())
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _col_letter(n: int) -> str:
    """Convierte número de columna (1-based) a letra de columna Excel."""
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result
