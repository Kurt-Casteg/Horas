"""Interfaz web Streamlit para la Calculadora de Horas Extra Efectivas."""

import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from config import HOLIDAYS_PATH, HOLIDAYS_YEAR
from src.holidays_loader import load_holidays
from src.overtime_calculator import calculate_overtime, total_overtime
from src.pdf_extractor import extract_attendance, extract_period_label
from src.report_generator import generate_excel_bytes

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Horas Extra",
    page_icon="🕐",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Fondo general de la app */
    .stApp {
        background: linear-gradient(135deg, #e8eaf0 0%, #d5d8e0 100%);
    }

    /* Contenedor principal con efecto glassmorphism */
    .block-container {
        background: rgba(255, 255, 255, 0.55) !important;
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.75);
        box-shadow: 0 8px 32px rgba(60, 70, 110, 0.10);
        padding-top: 2rem !important;
    }

    /* Tarjetas de métricas */
    .metric-card {
        background: rgba(240, 244, 255, 0.75);
        border-left: 4px solid #3b5bdb;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 8px;
        backdrop-filter: blur(6px);
        box-shadow: 0 2px 8px rgba(60, 70, 110, 0.08);
    }
    .metric-card .label { font-size: 13px; color: #555; margin-bottom: 4px; }
    .metric-card .value { font-size: 28px; font-weight: 700; color: #1a1a2e; }
    .metric-highlight {
        border-left-color: #2f9e44;
        background: rgba(240, 255, 244, 0.80);
    }

    /* Tabla */
    .stDataFrame thead tr th { background-color: #e8eaf6 !important; }

    /* Uploader */
    div[data-testid="stFileUploader"] { border-radius: 10px; }

    /* Pie de página */
    .footer {
        margin-top: 3rem;
        padding: 1.5rem 0 0.5rem 0;
        border-top: 1px solid rgba(100, 110, 150, 0.20);
        text-align: center;
        color: #666;
        font-size: 12px;
        line-height: 1.8;
    }
    .footer strong { color: #444; }
    .footer a { color: #3b5bdb; text-decoration: none; }
    .footer a:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------------------
st.title("🕐 Calculadora de Horas Extra")
st.caption("SEREMI de Salud Ñuble · Jornada estándar: Lun–Jue 9h | Vie 8h · Umbral: ≥ 45 min")
st.divider()

# ---------------------------------------------------------------------------
# Carga del PDF
# ---------------------------------------------------------------------------
uploaded_pdf = st.file_uploader(
    "**Sube el PDF de marcas de reloj**",
    type=["pdf"],
    help="Descárgalo desde el sistema de control de asistencia e imprímelo como PDF.",
)

if not uploaded_pdf:
    st.info("Sube el PDF de marcas de reloj para comenzar el cálculo.", icon="📄")
    st.stop()

# ---------------------------------------------------------------------------
# Procesamiento
# ---------------------------------------------------------------------------
with st.spinner("Procesando..."):
    try:
        records = extract_attendance(uploaded_pdf)
        uploaded_pdf.seek(0)
        period_label = extract_period_label(uploaded_pdf)
        holidays = load_holidays(HOLIDAYS_PATH, HOLIDAYS_YEAR)
        results = calculate_overtime(records, holidays)
        total_td = total_overtime(results)
    except (FileNotFoundError, ValueError) as exc:
        st.error(f"Error al procesar el archivo: {exc}", icon="🚨")
        st.stop()

# ---------------------------------------------------------------------------
# Métricas resumen
# ---------------------------------------------------------------------------
total_h, total_rem = divmod(int(total_td.total_seconds()), 3600)
total_m = total_rem // 60
days_with_ot = sum(1 for r in results if r["overtime_td"] > timedelta(0))
period_display = period_label.replace("_", " ") if period_label else "—"

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="metric-card metric-highlight">
        <div class="label">Total horas extra</div>
        <div class="value">{total_h:02d}:{total_m:02d}</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Días trabajados</div>
        <div class="value">{len(results)}</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Días con horas extra</div>
        <div class="value">{days_with_ot}</div>
    </div>""", unsafe_allow_html=True)

st.markdown(f"**Período:** {period_display}")
st.divider()

# ---------------------------------------------------------------------------
# Tabla de detalle
# ---------------------------------------------------------------------------
st.subheader("Detalle por día")

_DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

rows = []
for r in results:
    rows.append({
        "Fecha": r["date"].strftime("%d/%m/%Y"),
        "Día": _DAY_NAMES[r["date"].weekday()],
        "Entrada": r["entry"].strftime("%H:%M"),
        "Salida": r["exit"].strftime("%H:%M"),
        "Trabajado": r["worked_str"],
        "Estándar": r["base_str"],
        "Horas Extra": r["overtime_str"] if r["overtime_str"] else "–",
        "_tiene_extra": r["overtime_td"] > timedelta(0),
        "_es_feriado": r["is_holiday"],
    })

df = pd.DataFrame(rows)


def _style_row(row):
    if row["_es_feriado"]:
        return ["background-color: #fff3e0"] * len(row)
    if row["_tiene_extra"]:
        return ["background-color: #e8f5e9"] * len(row)
    return [""] * len(row)


display_cols = ["Fecha", "Día", "Entrada", "Salida", "Trabajado", "Estándar", "Horas Extra"]
styled = (
    df.style
    .apply(_style_row, axis=1)
    .hide(axis="index")
)

st.dataframe(
    styled,
    column_order=display_cols,
    use_container_width=True,
    height=min(38 * len(df) + 38, 620),
)

if any(r["_es_feriado"] for r in rows):
    st.caption("🟠 Fondo naranja = día feriado trabajado")
st.caption("🟢 Fondo verde = día con horas extra contabilizadas")

# ---------------------------------------------------------------------------
# Descarga del reporte
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Descargar reporte")

excel_bytes = generate_excel_bytes(results, period_label)
filename = f"horas_extra{'_' + period_label if period_label else ''}.xlsx"

st.download_button(
    label="📥 Descargar Excel",
    data=excel_bytes,
    file_name=filename,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# Pie de página
# ---------------------------------------------------------------------------
st.markdown("""
<div class="footer">
    <strong>Calculadora de Horas Extra Efectivas</strong> · v1.0 · 2026<br>
    SEREMI de Salud Ñuble · Departamento de Control de Gestión<br>
    Diseñado por <strong>Kurt Castro Ortega</strong> ·
</div>
""", unsafe_allow_html=True)
