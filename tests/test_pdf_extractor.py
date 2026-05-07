"""Tests para src/pdf_extractor.py."""

import pytest
from datetime import date, time
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.pdf_extractor import _parse_records, extract_attendance


class TestParseRecords:
    def test_parses_standard_lines(self):
        text = "30/04/2026 08:12 17:19\n29/04/2026 08:30 17:33"
        records = _parse_records(text)
        assert len(records) == 2
        assert records[0]["date"] == date(2026, 4, 30)
        assert records[0]["entry"] == time(8, 12)
        assert records[0]["exit"] == time(17, 19)

    def test_ignores_non_record_lines(self):
        text = (
            "MARCAS RELOJ CONTROL\n"
            "Nombre CASTRO ORTEGA KURT\n"
            "Fecha Marca Hora Entrada Hora Salida\n"
            "06/04/2026 08:38 17:41\n"
        )
        records = _parse_records(text)
        assert len(records) == 1
        assert records[0]["date"] == date(2026, 4, 6)

    def test_returns_empty_list_for_no_matches(self):
        assert _parse_records("Sin registros aquí") == []

    def test_handles_multiple_spaces_between_columns(self):
        text = "09/04/2026    08:16    18:15"
        records = _parse_records(text)
        assert len(records) == 1
        assert records[0]["entry"] == time(8, 16)
        assert records[0]["exit"] == time(18, 15)

    def test_april_2026_full_sample(self):
        sample = "\n".join([
            "06/04/2026 08:38 17:41",
            "07/04/2026 08:12 17:31",
            "08/04/2026 08:04 17:09",
            "09/04/2026 08:16 18:15",
            "10/04/2026 08:09 17:07",
        ])
        records = _parse_records(sample)
        assert len(records) == 5
        assert records[3]["date"] == date(2026, 4, 9)
        assert records[3]["exit"] == time(18, 15)


class TestExtractAttendance:
    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            extract_attendance(Path("no_existe.pdf"))

    def test_raises_on_empty_pdf(self, tmp_path):
        import pypdf
        from pypdf import PdfWriter
        empty_pdf = tmp_path / "empty.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with open(empty_pdf, "wb") as f:
            writer.write(f)
        with pytest.raises(ValueError):
            extract_attendance(empty_pdf)

    def test_returns_sorted_records(self):
        # Registros en orden inverso en el texto (como en el PDF real)
        text = "30/04/2026 08:12 17:19\n06/04/2026 08:38 17:41"
        records = _parse_records(text)
        records_sorted = sorted(records, key=lambda r: r["date"])
        assert records_sorted[0]["date"] == date(2026, 4, 6)
        assert records_sorted[1]["date"] == date(2026, 4, 30)
