"""Extracción de registros de asistencia desde un PDF de marcas de reloj."""

import re
from datetime import date, time
from pathlib import Path

import pypdf

# Patrón: DD/MM/YYYY HH:MM HH:MM (con cualquier separación entre columnas)
_RECORD_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\s+(\d{2}:\d{2})")

# Patrón para extraer el período desde el encabezado: "PERIODO ABRIL 2026"
_PERIOD_RE = re.compile(r"PERIODO\s+(\w+)\s+(\d{4})", re.IGNORECASE)

_SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def extract_attendance(pdf_source) -> list[dict]:
    """Lee el PDF de asistencia y devuelve una lista de registros ordenados por fecha.

    pdf_source puede ser una Path/str o un objeto file-like (BytesIO).

    Cada registro es un dict con:
        date  : datetime.date
        entry : datetime.time  (hora de entrada)
        exit  : datetime.time  (hora de salida)
    """
    full_text = _extract_text(pdf_source)
    records = _parse_records(full_text)

    name = getattr(pdf_source, "name", str(pdf_source))
    if not records:
        raise ValueError(
            f"No se encontraron registros de asistencia en '{name}'. "
            "Verifique que el PDF contenga el formato esperado."
        )

    return sorted(records, key=lambda r: r["date"])


def extract_period_label(pdf_source) -> str:
    """Devuelve un string descriptivo del período, p.ej. 'Abril_2026'.

    pdf_source puede ser una Path/str o un objeto file-like (BytesIO).
    """
    try:
        text = _extract_text(pdf_source)
    except Exception:
        return ""
    match = _PERIOD_RE.search(text)
    if match:
        return f"{match.group(1).capitalize()}_{match.group(2)}"
    return ""


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _extract_text(pdf_source) -> str:
    text_parts = []
    if hasattr(pdf_source, "read"):
        # Objeto file-like (BytesIO, UploadedFile de Streamlit, etc.)
        reader = pypdf.PdfReader(pdf_source)
    else:
        pdf_path = Path(pdf_source)
        if not pdf_path.exists():
            raise FileNotFoundError(f"Archivo PDF no encontrado: {pdf_path}")
        with open(pdf_path, "rb") as fh:
            reader = pypdf.PdfReader(fh)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts)

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)


def _parse_records(text: str) -> list[dict]:
    records = []
    for match in _RECORD_RE.finditer(text):
        date_str, entry_str, exit_str = match.groups()
        try:
            day, month, year = map(int, date_str.split("/"))
            entry_h, entry_m = map(int, entry_str.split(":"))
            exit_h, exit_m = map(int, exit_str.split(":"))
            records.append({
                "date": date(year, month, day),
                "entry": time(entry_h, entry_m),
                "exit": time(exit_h, exit_m),
            })
        except ValueError:
            # Ignorar líneas con formato inesperado
            continue
    return records
