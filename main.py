"""Punto de entrada: orquesta extracción → carga de reglas → cálculo → reporte."""

import sys
from pathlib import Path

from config import PDF_PATH, HOLIDAYS_PATH, HOLIDAYS_YEAR
from src.pdf_extractor import extract_attendance, extract_period_label
from src.holidays_loader import load_holidays
from src.overtime_calculator import calculate_overtime, total_overtime
from src.report_generator import generate_report


def main() -> None:
    print("=" * 40)
    print("  Calculadora de Horas Extra Efectivas")
    print("=" * 40)

    # 1. Extracción del PDF
    print(f"\n[1/4] Leyendo PDF: {PDF_PATH.name}")
    try:
        records = extract_attendance(PDF_PATH)
        period_label = extract_period_label(PDF_PATH)
    except (FileNotFoundError, ValueError) as exc:
        print(f"  ERROR: {exc}")
        sys.exit(1)
    print(f"       {len(records)} registro(s) encontrado(s) — período: {period_label}")

    # 2. Carga de feriados
    print(f"\n[2/4] Cargando feriados: {HOLIDAYS_PATH.name}")
    try:
        holidays = load_holidays(HOLIDAYS_PATH, HOLIDAYS_YEAR)
    except (FileNotFoundError, ValueError) as exc:
        print(f"  ERROR: {exc}")
        sys.exit(1)
    print(f"       {len(holidays)} feriado(s) cargado(s) para {HOLIDAYS_YEAR}")

    # 3. Cálculo
    print("\n[3/4] Calculando horas extra...")
    results = calculate_overtime(records, holidays)
    total_td = total_overtime(results)
    days_with_ot = sum(1 for r in results if r["overtime_td"].total_seconds() > 0)
    print(f"       {days_with_ot} día(s) con horas extra")

    # 4. Generación del reporte
    print("\n[4/4] Generando reporte...")
    try:
        out_path = generate_report(results, period_label)
    except Exception as exc:
        print(f"  ERROR al generar reporte: {exc}")
        sys.exit(1)

    print(f"\nReporte guardado en: {out_path}")


if __name__ == "__main__":
    main()
