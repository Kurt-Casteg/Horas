"""Lógica central de cálculo de horas extra efectivas."""

from datetime import date, time, timedelta

from config import OVERTIME_THRESHOLD_MINUTES
from src.schedule_rules import get_base_hours


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

        results.append({
            **rec,
            "is_holiday": is_holiday,
            "base_hours": base_h,
            "worked_td": worked_td,
            "excess_td": excess_td,
            "overtime_td": overtime_td,
            "worked_str": _td_to_str(worked_td),
            "base_str": f"{base_h:02d}:00:00",
            "overtime_str": _td_to_str(overtime_td) if overtime_td > timedelta(0) else "",
        })

    return results


def total_overtime(results: list[dict]) -> timedelta:
    """Suma todas las horas extra del período."""
    return sum((r["overtime_td"] for r in results), timedelta(0))


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _time_to_td(t: time) -> timedelta:
    return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)


def _td_to_str(td: timedelta) -> str:
    total_s = int(td.total_seconds())
    h, rem = divmod(abs(total_s), 3600)
    m, s = divmod(rem, 60)
    sign = "-" if total_s < 0 else ""
    return f"{sign}{h:02d}:{m:02d}:{s:02d}"
