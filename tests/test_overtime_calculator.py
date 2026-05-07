"""Tests para src/overtime_calculator.py.

Los valores de referencia se basan en HORAS_EXTRA_2026.xlsx (abril 2026):
  - Total horas extra: 02:17:00
  - Días con extra: 09/04 (00:59), 10/04 (00:58), 14/04 (00:20)
  - Umbral: excedente >= 20 min se cuenta; < 20 min NO se cuenta
"""

from datetime import date, time, timedelta

import pytest

from src.overtime_calculator import calculate_overtime, total_overtime, _time_to_td, _td_to_str

NO_HOLIDAYS: set = set()

# Registros reales de abril 2026 (extraídos del PDF)
APRIL_2026_RECORDS = [
    {"date": date(2026, 4, 6),  "entry": time(8, 38), "exit": time(17, 41)},
    {"date": date(2026, 4, 7),  "entry": time(8, 12), "exit": time(17, 31)},
    {"date": date(2026, 4, 8),  "entry": time(8, 4),  "exit": time(17, 9)},
    {"date": date(2026, 4, 9),  "entry": time(8, 16), "exit": time(18, 15)},  # +59min
    {"date": date(2026, 4, 10), "entry": time(8, 9),  "exit": time(17, 7)},   # +58min
    {"date": date(2026, 4, 13), "entry": time(8, 34), "exit": time(17, 38)},
    {"date": date(2026, 4, 14), "entry": time(8, 12), "exit": time(17, 32)},  # +20min
    {"date": date(2026, 4, 15), "entry": time(8, 15), "exit": time(17, 17)},
    {"date": date(2026, 4, 16), "entry": time(8, 15), "exit": time(17, 18)},
    {"date": date(2026, 4, 17), "entry": time(8, 23), "exit": time(16, 27)},
    {"date": date(2026, 4, 20), "entry": time(9, 0),  "exit": time(18, 3)},
    {"date": date(2026, 4, 21), "entry": time(7, 47), "exit": time(16, 47)},
    {"date": date(2026, 4, 22), "entry": time(8, 9),  "exit": time(17, 28)},
    {"date": date(2026, 4, 23), "entry": time(8, 9),  "exit": time(17, 13)},
    {"date": date(2026, 4, 24), "entry": time(8, 32), "exit": time(16, 41)},
    {"date": date(2026, 4, 27), "entry": time(8, 0),  "exit": time(17, 12)},
    {"date": date(2026, 4, 28), "entry": time(8, 10), "exit": time(17, 10)},
    {"date": date(2026, 4, 29), "entry": time(8, 30), "exit": time(17, 33)},
    {"date": date(2026, 4, 30), "entry": time(8, 12), "exit": time(17, 19)},
]

# Feriados de abril reales (Viernes Santo y Sábado Santo — ambos no trabajados)
APRIL_HOLIDAYS = {date(2026, 4, 3), date(2026, 4, 4)}


class TestCalculateOvertimeApril2026:
    """Verifica que el cálculo reproduce exactamente los resultados del Excel."""

    def setup_method(self):
        self.results = calculate_overtime(APRIL_2026_RECORDS, APRIL_HOLIDAYS)

    def test_total_matches_reference(self):
        """Total horas extra debe ser 02:17:00 = 137 minutos."""
        total = total_overtime(self.results)
        assert int(total.total_seconds()) == 137 * 60

    def test_three_days_have_overtime(self):
        days_with_ot = [r for r in self.results if r["overtime_td"] > timedelta(0)]
        assert len(days_with_ot) == 3

    def test_april_9_has_59_min(self):
        r = next(r for r in self.results if r["date"] == date(2026, 4, 9))
        assert r["overtime_td"] == timedelta(minutes=59)

    def test_april_10_has_58_min(self):
        r = next(r for r in self.results if r["date"] == date(2026, 4, 10))
        assert r["overtime_td"] == timedelta(minutes=58)

    def test_april_14_has_20_min(self):
        r = next(r for r in self.results if r["date"] == date(2026, 4, 14))
        assert r["overtime_td"] == timedelta(minutes=20)

    def test_april_7_is_not_counted(self):
        """19 min de excedente: menor que el umbral de 20 min → no cuenta."""
        r = next(r for r in self.results if r["date"] == date(2026, 4, 7))
        assert r["overtime_td"] == timedelta(0)

    def test_april_22_is_not_counted(self):
        """19 min de excedente: igual caso que abril 7."""
        r = next(r for r in self.results if r["date"] == date(2026, 4, 22))
        assert r["overtime_td"] == timedelta(0)


class TestOvertimeThreshold:
    def _make_record(self, d: date, entry: time, exit_: time) -> dict:
        return {"date": d, "entry": entry, "exit": exit_}

    def test_exactly_20_min_excess_counts(self):
        # Jueves (9h base): sale a las 18:20 → 9h 20m trabajadas → 20m extra
        rec = [self._make_record(date(2026, 4, 9), time(9, 0), time(18, 20))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["overtime_td"] == timedelta(minutes=20)

    def test_19_min_excess_does_not_count(self):
        rec = [self._make_record(date(2026, 4, 9), time(9, 0), time(18, 19))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["overtime_td"] == timedelta(0)

    def test_holiday_all_hours_count(self):
        """En feriado, cualquier tiempo trabajado es extra (sin umbral)."""
        holiday = date(2026, 4, 3)
        rec = [self._make_record(holiday, time(9, 0), time(12, 0))]
        results = calculate_overtime(rec, {holiday})
        assert results[0]["overtime_td"] == timedelta(hours=3)

    def test_weekend_all_hours_count(self):
        saturday = date(2026, 4, 11)
        rec = [self._make_record(saturday, time(9, 0), time(11, 30))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["overtime_td"] == timedelta(hours=2, minutes=30)


class TestHelpers:
    def test_td_to_str(self):
        assert _td_to_str(timedelta(hours=2, minutes=17)) == "02:17:00"
        assert _td_to_str(timedelta(minutes=59)) == "00:59:00"
        assert _td_to_str(timedelta(0)) == "00:00:00"

    def test_time_to_td(self):
        assert _time_to_td(time(8, 30)) == timedelta(hours=8, minutes=30)
        assert _time_to_td(time(0, 0)) == timedelta(0)
