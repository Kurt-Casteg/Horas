from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# ---------------------------------------------------------------------------
# Rutas de archivos de entrada
# Los archivos se buscan primero en DATA_DIR con el nombre estandarizado.
# Si no existen allí, se usan los nombres originales en BASE_DIR.
# ---------------------------------------------------------------------------

def _resolve(data_name: str, fallback_name: str) -> Path:
    candidate = DATA_DIR / data_name
    if candidate.exists():
        return candidate
    return BASE_DIR / fallback_name


PDF_PATH = _resolve("registro_asistencia.pdf", "Marcas Reloj Imprimir.pdf")
HOLIDAYS_PATH = _resolve("feriados_2026.xlsx", "feriados_2026.xlsx")
REFERENCE_CALC_PATH = _resolve("calculo_horas_extra.xlsx", "HORAS_EXTRA_2026.xlsx")

# ---------------------------------------------------------------------------
# Reglas de jornada: horas base por día de la semana (lunes=0 … domingo=6)
# ---------------------------------------------------------------------------
STANDARD_HOURS: dict[int, int] = {
    0: 9,  # Lunes
    1: 9,  # Martes
    2: 9,  # Miércoles
    3: 9,  # Jueves
    4: 8,  # Viernes
    5: 0,  # Sábado  (no laborable)
    6: 0,  # Domingo (no laborable)
}

# Excedente mínimo (en minutos) para que se contabilice como hora extra
OVERTIME_THRESHOLD_MINUTES: int = 45

# Año de referencia para interpretar las fechas de feriados
HOLIDAYS_YEAR: int = 2026
