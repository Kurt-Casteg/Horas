"""Tests para src/overtime_calculator.py.

Umbral vigente: >= 45 min para contabilizar horas extra.
La clasificación diurna/nocturna se aplica SOLO a las horas extra:
  - Diurnas: 07:30–21:00
  - Nocturnas: 21:00–07:30
  - Sáb/Dom/Feriados: 100% nocturnas
"""

from datetime import date, time, timedelta

import pytest

from src.overtime_calculator import (
    calculate_overtime, total_overtime,
    total_ot_day, total_ot_night,
    _time_to_td, _td_to_str, _split_overtime_day_night,
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
        r = next(r for r in self.results if r["date"] == date(2026, 4, 14))
        assert r["overtime_td"] == timedelta(0)

    def test_april_7_is_not_counted(self):
        r = next(r for r in self.results if r["date"] == date(2026, 4, 7))
        assert r["overtime_td"] == timedelta(0)

    def test_all_records_have_ot_day_night_fields(self):
        for r in self.results:
            assert "ot_day_td" in r
            assert "ot_night_td" in r
            assert "is_weekend" in r
            # Día-extra + Noche-extra = Total extra
            assert r["ot_day_td"] + r["ot_night_td"] == r["overtime_td"]

    def test_all_april_extra_is_daytime(self):
        """Abril 2026: todas las horas extra caen antes de las 21:00 → diurnas."""
        for r in self.results:
            assert r["ot_night_td"] == timedelta(0)
        ot_day = total_ot_day(self.results)
        assert ot_day == timedelta(minutes=117)
        assert total_ot_night(self.results) == timedelta(0)


class TestOvertimeThreshold:
    def _make_record(self, d: date, entry: time, exit_: time) -> dict:
        return {"date": d, "entry": entry, "exit": exit_}

    def test_exactly_45_min_excess_counts(self):
        rec = [self._make_record(date(2026, 4, 9), time(9, 0), time(18, 45))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["overtime_td"] == timedelta(minutes=45)

    def test_44_min_excess_does_not_count(self):
        rec = [self._make_record(date(2026, 4, 9), time(9, 0), time(18, 44))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["overtime_td"] == timedelta(0)

    def test_holiday_all_hours_count(self):
        holiday = date(2026, 4, 3)
        rec = [self._make_record(holiday, time(9, 0), time(12, 0))]
        results = calculate_overtime(rec, {holiday})
        assert results[0]["overtime_td"] == timedelta(hours=3)

    def test_weekend_all_hours_count(self):
        saturday = date(2026, 4, 11)
        rec = [self._make_record(saturday, time(9, 0), time(11, 30))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["overtime_td"] == timedelta(hours=2, minutes=30)


class TestOvertimeDayNightSplit:
    """Tests para la clasificación diurna/nocturna de las HORAS EXTRA."""

    def test_no_overtime_no_day_night(self):
        """Sin horas extra → diurna=0, nocturna=0."""
        ot_day, ot_night = _split_overtime_day_night(
            time(8, 0), time(17, 0), timedelta(0))
        assert ot_day == timedelta(0)
        assert ot_night == timedelta(0)

    def test_weekday_overtime_within_daytime(self):
        """Jueves 08:16–18:15 → 59 min extra, todo dentro de 07:30–21:00."""
        ot_day, ot_night = _split_overtime_day_night(
            time(8, 16), time(18, 15), timedelta(minutes=59))
        assert ot_day == timedelta(minutes=59)
        assert ot_night == timedelta(0)

    def test_weekday_overtime_crosses_into_night(self):
        """08:00–22:00 en día de 9h base → 5h extra (17:00–22:00).
        Diurna: 17:00–21:00 = 4h, Nocturna: 21:00–22:00 = 1h."""
        ot_day, ot_night = _split_overtime_day_night(
            time(8, 0), time(22, 0), timedelta(hours=5))
        assert ot_day == timedelta(hours=4)
        assert ot_night == timedelta(hours=1)

    def test_weekday_overtime_fully_in_night(self):
        """08:00–23:00 en día de 9h, overtime 6h (17:00–23:00).
        Diurna: 17:00–21:00 = 4h, Nocturna: 21:00–23:00 = 2h."""
        ot_day, ot_night = _split_overtime_day_night(
            time(8, 0), time(23, 0), timedelta(hours=6))
        assert ot_day == timedelta(hours=4)
        assert ot_night == timedelta(hours=2)

    def test_exit_exactly_at_day_end(self):
        """Exit at 21:00 → toda la extra es diurna."""
        ot_day, ot_night = _split_overtime_day_night(
            time(8, 0), time(21, 0), timedelta(hours=4))
        assert ot_day == timedelta(hours=4)
        assert ot_night == timedelta(0)

    def test_force_all_night_weekend(self):
        """Fin de semana: toda extra es nocturna."""
        ot_day, ot_night = _split_overtime_day_night(
            time(9, 0), time(14, 0), timedelta(hours=5), force_all_night=True)
        assert ot_day == timedelta(0)
        assert ot_night == timedelta(hours=5)

    def test_force_all_night_holiday(self):
        """Feriado: toda extra es nocturna."""
        ot_day, ot_night = _split_overtime_day_night(
            time(8, 0), time(17, 0), timedelta(hours=9), force_all_night=True)
        assert ot_day == timedelta(0)
        assert ot_night == timedelta(hours=9)

    def test_day_plus_night_equals_overtime(self):
        """ot_day + ot_night siempre debe ser = overtime_td."""
        cases = [
            (time(8, 0), time(22, 30), timedelta(hours=5, minutes=30)),
            (time(6, 0), time(17, 0), timedelta(hours=2)),
            (time(9, 0), time(21, 45), timedelta(minutes=45)),
        ]
        for entry, exit_, ot in cases:
            d, n = _split_overtime_day_night(entry, exit_, ot)
            assert d + n == ot, f"Failed for {entry}-{exit_}, OT={ot}"


class TestOvertimeDayNightInCalculation:
    """Verifica campos ot_day/ot_night a través de calculate_overtime."""

    def _make_record(self, d: date, entry: time, exit_: time) -> dict:
        return {"date": d, "entry": entry, "exit": exit_}

    def test_weekday_all_ot_daytime(self):
        """Jueves: 59 min extra, sale a las 18:15 → todo diurno."""
        rec = [self._make_record(date(2026, 4, 9), time(8, 16), time(18, 15))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["ot_day_td"] == timedelta(minutes=59)
        assert results[0]["ot_night_td"] == timedelta(0)

    def test_weekday_ot_partial_night(self):
        """Jueves: 08:00–22:00 = 14h trabajadas, 5h extra (17:00–22:00).
        Diurna: 4h (17:00–21:00), Nocturna: 1h (21:00–22:00)."""
        rec = [self._make_record(date(2026, 4, 9), time(8, 0), time(22, 0))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["overtime_td"] == timedelta(hours=5)
        assert results[0]["ot_day_td"] == timedelta(hours=4)
        assert results[0]["ot_night_td"] == timedelta(hours=1)

    def test_saturday_all_ot_nighttime(self):
        saturday = date(2026, 4, 11)
        rec = [self._make_record(saturday, time(9, 0), time(14, 0))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["ot_day_td"] == timedelta(0)
        assert results[0]["ot_night_td"] == timedelta(hours=5)

    def test_holiday_all_ot_nighttime(self):
        holiday = date(2026, 4, 3)
        rec = [self._make_record(holiday, time(8, 0), time(16, 0))]
        results = calculate_overtime(rec, {holiday})
        assert results[0]["ot_day_td"] == timedelta(0)
        assert results[0]["ot_night_td"] == timedelta(hours=8)

    def test_no_overtime_no_day_night(self):
        """Sin horas extra → ambos en 0."""
        rec = [self._make_record(date(2026, 4, 9), time(9, 0), time(17, 0))]
        results = calculate_overtime(rec, NO_HOLIDAYS)
        assert results[0]["ot_day_td"] == timedelta(0)
        assert results[0]["ot_night_td"] == timedelta(0)

    def test_total_ot_day_and_night_functions(self):
        records = [
            self._make_record(date(2026, 4, 9), time(8, 0), time(22, 0)),   # 5h OT: 4h day + 1h night
            self._make_record(date(2026, 4, 11), time(9, 0), time(14, 0)),  # 5h OT: all night (sat)
        ]
        results = calculate_overtime(records, NO_HOLIDAYS)
        assert total_ot_day(results) == timedelta(hours=4)
        assert total_ot_night(results) == timedelta(hours=6)


class TestHelpers:
    def test_td_to_str(self):
        assert _td_to_str(timedelta(hours=2, minutes=17)) == "02:17:00"
        assert _td_to_str(timedelta(minutes=59)) == "00:59:00"
        assert _td_to_str(timedelta(0)) == "00:00:00"

    def test_time_to_td(self):
        assert _time_to_td(time(8, 30)) == timedelta(hours=8, minutes=30)
        assert _time_to_td(time(0, 0)) == timedelta(0)
