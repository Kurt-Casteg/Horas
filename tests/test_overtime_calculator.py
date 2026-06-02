"""Tests para src/overtime_calculator.py.

Umbral vigente: >= 45 min para contabilizar horas extra.
Con umbral 45 min para abril 2026:
  - Días con extra: 09/04 (00:59), 10/04 (00:58)
  - Total horas extra: 01:57:00 = 117 minutos
  - 14/04 tenía 20 min (ya NO cuenta con umbral 45 min)
"""

from datetime import date, time, timedelta

import pytest

from src.overtime_calculator import (
    calculate_overtime, total_overtime,
    total_day_hours, total_night_hours,
    _time_to_td, _td_to_str, _split_day_night,
)

NO_HOLIDAYS: set = set()

# Registros reales de abril 2026 (extraídos del PDF)
APRIL_2026_RECORDS = [
    {"date": date(2026, 4, 6),  "entry": time(8, 38), "exit": time(17, 41)},
    {"date": date(2026, 4, 7),  "entry": time(8, 12), "exit": time(17, 31)},
    {"date": date(2026, 4, 8),  "entry": time(8, 4),  "exit": time(17, 9)},
    {"date": date(2026, 4, 9),  "entry": time(8, 16), "exit": time(18, 15)},  # +59min
    {"date": date(2026, 4, 10), "entry": time(8, 9),  "exit": time(17, 7)},   # +58min
    {"date": date(2026, 4, 13), "entry": time(8, 34), "exit": time(17, 38)},
    {"date": date(2026, 4, 14), "entry": time(8, 12), "exit": time(17, 32)},  # +20min < 45
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
    """Verifica el cálculo con umbral de 45 min."""

    def setup_method(self):
        self.results = calculate_overtime(APRIL_2026_RECORDS, APRIL_HOLIDAYS)

    def test_total_matches_reference(self):
        """Total horas extra = 01:57:00 = 117 minutos (umbral 45 min)."""
        total = total_overtime(self.results)
        assert int(total.total_seconds()) == 117 * 60

    def test_two_days_have_overtime(self):
        days_with_ot = [r for r in self.results if r["overtime_td"] > timedelta(0)]
        assert len(days_with_ot) == 2

    def test_april_9_has_59_min(self):
        r = next(r for r in self.results if r["date"] == date(2026, 4, 9))
        assert r["overtime_td"] == timedelta(minutes=59)

    def test_april_10_has_58_min(self):
        r = next(r for r in self.results if r["date"] == date(2026, 4, 10))
        assert r["overtime_td"] == timedelta(minutes=58)

    def test_april_14_no_longer_counts(self):
        """20 min de excedente: menor que el umbral de 45 min → no cuenta."""
        r = next(r for r in self.results if r["date"] == date(2026, 4, 14))
        assert r["overtime_td"] == timedelta(0)

    def test_april_7_is_not_counted(self):
        """19 min de excedente → no cuenta."""
        r = next(r for r in self.results if r["date"] == date(2026, 4, 7))
        assert r["overtime_td"] == timedelta(0)

    def test_all_records_have_day_night_fields(self):
        for r in self.results:
            assert "day_hours_td" in r
            assert "night_hours_td" in r
            assert "is_weekend" in r
            # Día + Noche = Trabajado
            assert r["day_hours_td"] + r["night_hours_td"] == r["worked_td"]


class TestOvertimeThreshold:
    def _make_record(self, d: date, entry: time, exit_: time) -> dict:
        return {"date": d, "entry": entry, "exit": exit_}

    def test_exactly_45_min_excess_counts(self):
        # Jueves (9h base): 09:00–18:45 = 9h 45m → 45m extra
        rec = [self._make_record(date(2026, 4, 9), time(9, 0), time(18, 45))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["overtime_td"] == timedelta(minutes=45)

    def test_44_min_excess_does_not_count(self):
        rec = [self._make_record(date(2026, 4, 9), time(9, 0), time(18, 44))]
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


class TestDayNightSplit:
    """Tests para la clasificación diurna/nocturna."""

    def test_full_day_within_daytime_band(self):
        """08:00–17:00 → todo diurno (dentro de 07:30–21:00)."""
        day_td, night_td = _split_day_night(time(8, 0), time(17, 0))
        assert day_td == timedelta(hours=9)
        assert night_td == timedelta(0)

    def test_entry_before_day_start(self):
        """06:00–17:00 → 1.5h nocturnas (06:00–07:30), 9.5h diurnas."""
        day_td, night_td = _split_day_night(time(6, 0), time(17, 0))
        assert night_td == timedelta(hours=1, minutes=30)
        assert day_td == timedelta(hours=9, minutes=30)

    def test_exit_after_day_end(self):
        """08:00–22:00 → 12.5h diurnas (08:00–21:00), 1h nocturna (21:00–22:00)."""
        day_td, night_td = _split_day_night(time(8, 0), time(22, 0))
        assert day_td == timedelta(hours=13)
        assert night_td == timedelta(hours=1)

    def test_both_outside_daytime(self):
        """06:00–22:00 → 13.5h diurnas, 2.5h nocturnas."""
        day_td, night_td = _split_day_night(time(6, 0), time(22, 0))
        assert day_td == timedelta(hours=13, minutes=30)
        assert night_td == timedelta(hours=2, minutes=30)

    def test_entirely_before_day_start(self):
        """05:00–07:00 → todo nocturno."""
        day_td, night_td = _split_day_night(time(5, 0), time(7, 0))
        assert day_td == timedelta(0)
        assert night_td == timedelta(hours=2)

    def test_entirely_after_day_end(self):
        """21:30–23:00 → todo nocturno."""
        day_td, night_td = _split_day_night(time(21, 30), time(23, 0))
        assert day_td == timedelta(0)
        assert night_td == timedelta(hours=1, minutes=30)

    def test_force_all_night_weekend(self):
        """Fin de semana: 09:00–14:00 → todo nocturno."""
        day_td, night_td = _split_day_night(time(9, 0), time(14, 0), force_all_night=True)
        assert day_td == timedelta(0)
        assert night_td == timedelta(hours=5)

    def test_force_all_night_holiday(self):
        """Feriado: 08:00–17:00 → todo nocturno."""
        day_td, night_td = _split_day_night(time(8, 0), time(17, 0), force_all_night=True)
        assert day_td == timedelta(0)
        assert night_td == timedelta(hours=9)

    def test_day_plus_night_equals_total(self):
        """La suma de diurnas + nocturnas debe ser igual al total trabajado."""
        for entry_h in range(5, 10):
            for exit_h in range(16, 23):
                day_td, night_td = _split_day_night(time(entry_h, 0), time(exit_h, 0))
                assert day_td + night_td == timedelta(hours=exit_h - entry_h)


class TestDayNightInCalculation:
    """Verifica que calculate_overtime incluye correctamente los campos day/night."""

    def _make_record(self, d: date, entry: time, exit_: time) -> dict:
        return {"date": d, "entry": entry, "exit": exit_}

    def test_weekday_all_daytime(self):
        rec = [self._make_record(date(2026, 4, 6), time(8, 0), time(17, 0))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["day_hours_td"] == timedelta(hours=9)
        assert results[0]["night_hours_td"] == timedelta(0)

    def test_saturday_all_nighttime(self):
        saturday = date(2026, 4, 11)
        rec = [self._make_record(saturday, time(9, 0), time(14, 0))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["day_hours_td"] == timedelta(0)
        assert results[0]["night_hours_td"] == timedelta(hours=5)
        assert results[0]["is_weekend"] is True

    def test_sunday_all_nighttime(self):
        sunday = date(2026, 4, 12)
        rec = [self._make_record(sunday, time(10, 0), time(15, 0))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["day_hours_td"] == timedelta(0)
        assert results[0]["night_hours_td"] == timedelta(hours=5)
        assert results[0]["is_weekend"] is True

    def test_holiday_all_nighttime(self):
        holiday = date(2026, 4, 3)  # Viernes Santo
        rec = [self._make_record(holiday, time(8, 0), time(16, 0))]
        results = calculate_overtime(rec, {holiday})
        assert results[0]["day_hours_td"] == timedelta(0)
        assert results[0]["night_hours_td"] == timedelta(hours=8)
        assert results[0]["is_holiday"] is True

    def test_total_day_and_night_functions(self):
        records = [
            self._make_record(date(2026, 4, 6), time(8, 0), time(17, 0)),   # 9h day
            self._make_record(date(2026, 4, 11), time(9, 0), time(14, 0)),  # 5h night (sat)
        ]
        results = calculate_overtime(records, NO_HOLIDAYS)
        assert total_day_hours(results) == timedelta(hours=9)
        assert total_night_hours(results) == timedelta(hours=5)


class TestHelpers:
    def test_td_to_str(self):
        assert _td_to_str(timedelta(hours=2, minutes=17)) == "02:17:00"
        assert _td_to_str(timedelta(minutes=59)) == "00:59:00"
        assert _td_to_str(timedelta(0)) == "00:00:00"

    def test_time_to_td(self):
        assert _time_to_td(time(8, 30)) == timedelta(hours=8, minutes=30)
        assert _time_to_td(time(0, 0)) == timedelta(0)
