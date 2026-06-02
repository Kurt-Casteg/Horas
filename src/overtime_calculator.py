"""Lógica central de cálculo de horas extra efectivas."""

from datetime import date, time, timedelta

from config import (
    OVERTIME_THRESHOLD_MINUTES,
    DAY_START_HOUR, DAY_START_MINUTE,
    DAY_END_HOUR, DAY_END_MINUTE,
)
from src.schedule_rules import get_base_hours

# Límites de la franja diurna como timedelta desde medianoche
_DAY_START = timedelta(hours=DAY_START_HOUR, minutes=DAY_START_MINUTE)
_DAY_END = timedelta(hours=DAY_END_HOUR, minutes=DAY_END_MINUTE)


def calculate_overtime(
    records: list[dict],
    holidays: set[date],
) -> list[dict]:
    """Calcula las horas extra efectivas para cada registro de asistencia.

    Reglas aplicadas:
    - Día laborable normal: se cuenta como extra el excedente sobre la jornada
      base, SOLO si dicho excedente es >= OVERTIME_THRESHOLD_MINUTES.
    - Día feriado: no existe jornada base; cualquier tiempo trabajado es extra.
    - Fin de semana: jornada base = 0; se aplica el mismo criterio que feriado.

    Cada dict resultante agrega las claves:
        is_holiday   : bool
        base_hours   : int   (horas de jornada estándar)
        worked_td    : timedelta
        excess_td    : timedelta (puede ser negativo si se salió antes)
        overtime_td  : timedelta (>= 0, representa las horas extra efectivas)
        worked_str   : str  "HH:MM:SS"
        base_str     : str  "HH:MM:SS"
        overtime_str : str  "HH:MM:SS" o "" si no hay extra
    """
    threshold = timedelta(minutes=OVERTIME_THRESHOLD_MINUTES)
    results = []

    for rec in records:
        d: date = rec["date"]
        is_holiday = d in holidays
        base_h = get_base_hours(d, holidays)
        base_td = timedelta(hours=base_h)

        worked_td = _time_to_td(rec["exit"]) - _time_to_td(rec["entry"])
        excess_td = worked_td - base_td

        if base_h == 0:
            # Feriado o fin de semana: todo tiempo trabajado es extra
            overtime_td = max(worked_td, timedelta(0))
        elif excess_td >= threshold:
            overtime_td = excess_td
        else:
            overtime_td = timedelta(0)

        # Clasificación diurna / nocturna
        is_weekend = d.weekday() >= 5
        day_td, night_td = _split_day_night(
            rec["entry"], rec["exit"],
            force_all_night=(is_weekend or is_holiday),
        )

        results.append({
            **rec,
            "is_holiday": is_holiday,
            "is_weekend": is_weekend,
            "base_hours": base_h,
            "worked_td": worked_td,
            "excess_td": excess_td,
            "overtime_td": overtime_td,
            "day_hours_td": day_td,
            "night_hours_td": night_td,
            "worked_str": _td_to_str(worked_td),
            "base_str": f"{base_h:02d}:00:00",
            "overtime_str": _td_to_str(overtime_td) if overtime_td > timedelta(0) else "",
            "day_hours_str": _td_to_str(day_td) if day_td > timedelta(0) else "",
            "night_hours_str": _td_to_str(night_td) if night_td > timedelta(0) else "",
        })

    return results


def total_overtime(results: list[dict]) -> timedelta:
    """Suma todas las horas extra del período."""
    return sum((r["overtime_td"] for r in results), timedelta(0))


def total_day_hours(results: list[dict]) -> timedelta:
    """Suma total de horas diurnas del período."""
    return sum((r["day_hours_td"] for r in results), timedelta(0))


def total_night_hours(results: list[dict]) -> timedelta:
    """Suma total de horas nocturnas del período."""
    return sum((r["night_hours_td"] for r in results), timedelta(0))


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _time_to_td(t: time) -> timedelta:
    return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)


def _split_day_night(
    entry: time,
    exit_: time,
    force_all_night: bool = False,
) -> tuple[timedelta, timedelta]:
    """Divide el tiempo trabajado en horas diurnas y nocturnas.

    Diurnas: DAY_START – DAY_END (por defecto 07:30–21:00)
    Nocturnas: antes de DAY_START + después de DAY_END

    Si force_all_night es True (fin de semana o feriado), TODAS las horas
    se imputan como nocturnas.
    """
    entry_td = _time_to_td(entry)
    exit_td = _time_to_td(exit_)
    total_worked = exit_td - entry_td

    if total_worked <= timedelta(0):
        return timedelta(0), timedelta(0)

    if force_all_night:
        return timedelta(0), total_worked

    # Calcular solapamiento con la franja diurna [DAY_START, DAY_END)
    # Solapamiento = max(0, min(exit, DAY_END) - max(entry, DAY_START))
    overlap_start = max(entry_td, _DAY_START)
    overlap_end = min(exit_td, _DAY_END)
    day_td = max(overlap_end - overlap_start, timedelta(0))

    night_td = total_worked - day_td

    return day_td, night_td


def _td_to_str(td: timedelta) -> str:
    total_s = int(td.total_seconds())
    h, rem = divmod(abs(total_s), 3600)
    m, s = divmod(rem, 60)
    sign = "-" if total_s < 0 else ""
    return f"{sign}{h:02d}:{m:02d}:{s:02d}"
