"""Carga y validación de días feriados desde un archivo Excel."""

import re
from datetime import date
from pathlib import Path

import pandas as pd

_SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# Acepta "1 de enero", "1 enero", "01 de enero", etc.
_DATE_RE = re.compile(r"(\d{1,2})(?:\s+de)?\s+(\w+)", re.IGNORECASE)


def load_holidays(holidays_path: Path, year: int) -> set[date]:
    """Carga los feriados del archivo Excel y devuelve un set de objetos date.

    El archivo debe tener los días en la primera columna con formato texto
    como '1 de enero', '3 de abril', etc.
    """
    holidays_path = Path(holidays_path)
    if not holidays_path.exists():
        raise FileNotFoundError(f"Archivo de feriados no encontrado: {holidays_path}")

    df = pd.read_excel(holidays_path)
    if df.empty:
        raise ValueError(f"El archivo de feriados está vacío: {holidays_path}")

    date_col = df.columns[0]
    holidays: set[date] = set()

    for raw_val in df[date_col]:
        parsed = _parse_spanish_date(str(raw_val), year)
        if parsed is not None:
            holidays.add(parsed)

    if not holidays:
        raise ValueError(
            f"No se pudo interpretar ninguna fecha en la columna '{date_col}' "
            f"de '{holidays_path.name}'."
        )

    return holidays


# ---------------------------------------------------------------------------
# Helper privado
# ---------------------------------------------------------------------------

def _parse_spanish_date(text: str, year: int) -> date | None:
    """Convierte un string tipo '1 de enero' en un datetime.date del año dado."""
    match = _DATE_RE.search(text.strip().lower())
    if not match:
        return None
    day_str, month_str = match.group(1), match.group(2)
    month_num = _SPANISH_MONTHS.get(month_str)
    if month_num is None or not day_str.isdigit():
        return None
    try:
        return date(year, month_num, int(day_str))
    except ValueError:
        return None
