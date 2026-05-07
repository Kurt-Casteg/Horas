"""Tests para src/holidays_loader.py."""

import pytest
from datetime import date

from src.holidays_loader import _parse_spanish_date, load_holidays


class TestParseSpanishDate:
    def test_standard_format(self):
        assert _parse_spanish_date("1 de enero", 2026) == date(2026, 1, 1)

    def test_without_de(self):
        assert _parse_spanish_date("1 enero", 2026) == date(2026, 1, 1)

    def test_two_digit_day(self):
        assert _parse_spanish_date("25 de diciembre", 2026) == date(2026, 12, 25)

    def test_all_months(self):
        months = [
            ("enero", 1), ("febrero", 2), ("marzo", 3), ("abril", 4),
            ("mayo", 5), ("junio", 6), ("julio", 7), ("agosto", 8),
            ("septiembre", 9), ("octubre", 10), ("noviembre", 11), ("diciembre", 12),
        ]
        for name, num in months:
            result = _parse_spanish_date(f"15 de {name}", 2026)
            assert result == date(2026, num, 15), f"Failed for {name}"

    def test_returns_none_for_invalid_text(self):
        assert _parse_spanish_date("NaT", 2026) is None
        assert _parse_spanish_date("", 2026) is None
        assert _parse_spanish_date("nan", 2026) is None

    def test_case_insensitive(self):
        assert _parse_spanish_date("1 DE ENERO", 2026) == date(2026, 1, 1)
        assert _parse_spanish_date("25 De Diciembre", 2026) == date(2026, 12, 25)


class TestLoadHolidays:
    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_holidays(tmp_path / "no_existe.xlsx", 2026)

    def test_loads_real_holidays_file(self):
        """Integración: verifica que el archivo real carga los 18 feriados de 2026."""
        from config import HOLIDAYS_PATH, HOLIDAYS_YEAR
        if not HOLIDAYS_PATH.exists():
            pytest.skip("Archivo feriados_2026.xlsx no disponible")

        holidays = load_holidays(HOLIDAYS_PATH, HOLIDAYS_YEAR)

        assert len(holidays) == 18
        # Feriados conocidos de abril 2026
        assert date(2026, 4, 3) in holidays   # Viernes Santo
        assert date(2026, 4, 4) in holidays   # Sábado Santo
        # Feriados fijos
        assert date(2026, 1, 1) in holidays   # Año Nuevo
        assert date(2026, 12, 25) in holidays  # Navidad
        assert date(2026, 5, 1) in holidays   # Día del Trabajo

    def test_april_holiday_is_excluded_from_attendance(self):
        """Viernes Santo (3 abril) no debe aparecer en registros de asistencia."""
        from config import HOLIDAYS_PATH, HOLIDAYS_YEAR
        if not HOLIDAYS_PATH.exists():
            pytest.skip("Archivo feriados_2026.xlsx no disponible")

        holidays = load_holidays(HOLIDAYS_PATH, HOLIDAYS_YEAR)
        assert date(2026, 4, 3) in holidays
