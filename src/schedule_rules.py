"""Reglas de jornada laboral: horas base por día de la semana."""

from datetime import date

from config import STANDARD_HOURS


def get_base_hours(d: date, holidays: set[date]) -> int:
    """Devuelve las horas de jornada estándar para la fecha dada.

    Retorna 0 si el día es fin de semana o feriado.
    Retorna 9 para lunes a jueves, 8 para viernes.
    """
    if d in holidays:
        return 0
    return STANDARD_HOURS.get(d.weekday(), 0)


def is_working_day(d: date, holidays: set[date]) -> bool:
    """Indica si una fecha es día laborable (no feriado y no fin de semana)."""
    return get_base_hours(d, holidays) > 0
