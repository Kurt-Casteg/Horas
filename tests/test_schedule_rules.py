"""Tests para src/schedule_rules.py."""

from datetime import date

from src.schedule_rules import get_base_hours, is_working_day

# Semana de referencia: lunes 6 al domingo 12 de abril de 2026
MONDAY = date(2026, 4, 6)
TUESDAY = date(2026, 4, 7)
WEDNESDAY = date(2026, 4, 8)
THURSDAY = date(2026, 4, 9)
FRIDAY = date(2026, 4, 10)
SATURDAY = date(2026, 4, 11)
SUNDAY = date(2026, 4, 12)

NO_HOLIDAYS: set = set()


class TestGetBaseHours:
    def test_monday_is_9_hours(self):
        assert get_base_hours(MONDAY, NO_HOLIDAYS) == 9

    def test_tuesday_is_9_hours(self):
        assert get_base_hours(TUESDAY, NO_HOLIDAYS) == 9

    def test_wednesday_is_9_hours(self):
        assert get_base_hours(WEDNESDAY, NO_HOLIDAYS) == 9

    def test_thursday_is_9_hours(self):
        assert get_base_hours(THURSDAY, NO_HOLIDAYS) == 9

    def test_friday_is_8_hours(self):
        assert get_base_hours(FRIDAY, NO_HOLIDAYS) == 8

    def test_saturday_is_0_hours(self):
        assert get_base_hours(SATURDAY, NO_HOLIDAYS) == 0

    def test_sunday_is_0_hours(self):
        assert get_base_hours(SUNDAY, NO_HOLIDAYS) == 0

    def test_holiday_is_0_hours(self):
        viernes_santo = date(2026, 4, 3)
        holidays = {viernes_santo}
        assert get_base_hours(viernes_santo, holidays) == 0

    def test_holiday_overrides_weekday(self):
        # 18 de septiembre 2026 es viernes Y feriado → 0 horas
        sept18 = date(2026, 9, 18)
        assert sept18.weekday() == 4  # Es viernes
        holidays = {sept18}
        assert get_base_hours(sept18, holidays) == 0


class TestIsWorkingDay:
    def test_weekday_is_working(self):
        assert is_working_day(MONDAY, NO_HOLIDAYS) is True
        assert is_working_day(FRIDAY, NO_HOLIDAYS) is True

    def test_weekend_is_not_working(self):
        assert is_working_day(SATURDAY, NO_HOLIDAYS) is False
        assert is_working_day(SUNDAY, NO_HOLIDAYS) is False

    def test_holiday_is_not_working(self):
        assert is_working_day(date(2026, 4, 3), {date(2026, 4, 3)}) is False
