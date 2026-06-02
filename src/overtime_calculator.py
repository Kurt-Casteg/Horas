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
    """Calcula las horas extra efectivas y su clasificación diurna/nocturna.

    Clasificación diurna/nocturna de las HORAS EXTRA:
    - Día laborable: las horas extra se producen al final de la jornada;
      se clasifican según la franja horaria en que caen (07:30–21:00 diurna,
      el resto nocturna).
    - Fin de semana o feriado: TODAS las horas extra son nocturnas.
    """
    threshold = timedelta(minutes=OVERTIME_THRESHOLD_MINUTES)
    results = []

    for rec in records:
        d: date = rec["date"]
        is_holiday = d in holidays
        is_weekend = d.weekday() >= 5
        base_h = get_base_hours(d, holidays)
        base_td = timedelta(hours=base_h)

        worked_td = _time_to_td(rec["exit"]) - _time_to_td(rec["entry"])
        excess_td = worked_td - base_td

        if base_h == 0:
            overtime_td = max(worked_td, timedelta(0))
        elif excess_td >= threshold:
            overtime_td = excess_td
        else:
            overtime_td = timedelta(0)

        # Clasificar las horas EXTRA en diurnas / nocturnas
        ot_day_td, ot_night_td = _split_overtime_day_night(
            entry=rec["entry"],
            exit_=rec["exit"],
            overtime_td=overtime_td,
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
            "ot_day_td": ot_day_td,
            "ot_night_td": ot_night_td,
            "worked_str": _td_to_str(worked_td),
            "base_str": f"{base_h:02d}:00:00",
            "overtime_str": _td_to_str(overtime_td) if overtime_td > timedelta(0) else "",
            "ot_day_str": _td_to_str(ot_day_td) if ot_day_td > timedelta(0) else "",
            "ot_night_str": _td_to_str(ot_night_td) if ot_night_td > timedelta(0) else "",
        })

    return results


def total_overtime(results: list[dict]) -> timedelta:
    """Suma todas las horas extra del período."""
    return sum((r["overtime_td"] for r in results), timedelta(0))


def total_ot_day(results: list[dict]) -> timedelta:
    """Suma horas extra diurnas del período."""
    return sum((r["ot_day_td"] for r in results), timedelta(0))


def total_ot_night(results: list[dict]) -> timedelta:
    """Suma horas extra nocturnas del período."""
    return sum((r["ot_night_td"] for r in results), timedelta(0))


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _time_to_td(t: time) -> timedelta:
    return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)


def _split_overtime_day_night(
    entry: time,
    exit_: time,
    overtime_td: timedelta,
    force_all_night: bool = False,
) -> tuple[timedelta, timedelta]:
    """Clasifica las horas EXTRA (no las trabajadas) en diurnas y nocturnas.

    Lógica:
    - Si no hay horas extra → (0, 0).
    - Fin de semana / feriado → todo nocturno.
    - Día laborable: las horas extra se producen al final de la jornada
      (overtime_start = exit - overtime, overtime_end = exit).
      Se aplica la franja diurna sobre ese intervalo.
    """
    if overtime_td <= timedelta(0):
        return timedelta(0), timedelta(0)

    if force_all_night:
        return timedelta(0), overtime_td

    # Intervalo donde ocurren las horas extra (cola de la jornada)
    exit_td = _time_to_td(exit_)
    ot_start = exit_td - overtime_td

    # Solapamiento del intervalo de overtime con la franja diurna
    overlap_start = max(ot_start, _DAY_START)
    overlap_end = min(exit_td, _DAY_END)
    ot_day = max(overlap_end - overlap_start, timedelta(0))
    ot_night = overtime_td - ot_day

    return ot_day, ot_night


def _td_to_str(td: timedelta) -> str:
    total_s = int(td.total_seconds())
    h, rem = divmod(abs(total_s), 3600)
    m, s = divmod(rem, 60)
    sign = "-" if total_s < 0 else ""
    return f"{sign}{h:02d}:{m:02d}:{s:02d}"
