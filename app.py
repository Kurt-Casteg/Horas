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
    page_title="Horas Extra · SEREMI Ñuble",
    page_icon="🕐",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Estilos — tema azul marino oscuro con glow radial
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* ── Fondo principal: azul marino con glow radial central ── */
    .stApp {
        background:
            radial-gradient(ellipse 80% 55% at 50% 42%,
                rgba(90, 130, 220, 0.18) 0%,
                transparent 70%),
            linear-gradient(160deg, #060d26 0%, #0b1640 45%, #07102e 100%);
        background-attachment: fixed;
    }

    /* ── Contenedor principal: cristal oscuro ── */
    .block-container {
        background: rgba(8, 16, 45, 0.55) !important;
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border: 1px solid rgba(90, 140, 255, 0.15);
        border-radius: 18px;
        box-shadow: 0 8px 48px rgba(0, 0, 0, 0.45);
        padding-top: 2.5rem !important;
        max-width: 820px !important;
    }

    /* ── Textos globales ── */
    .stApp p, .stApp li, .stApp span,
    .stApp label, .stApp div { color: #c8d8f8; }
    .stApp h1, .stApp h2, .stApp h3 { color: #ffffff !important; }
    [data-testid="stCaptionContainer"] p { color: #6b90d4 !important; }

    /* ── Título principal ── */
    .main-title {
        font-size: 4rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.3px;
        margin-bottom: 0;
    }
    .main-subtitle {
        font-size: 13px;
        color: #6b90d4;
        margin-top: 4px;
        margin-bottom: 1.2rem;
    }

    /* ── Divisor ── */
    hr { border-color: rgba(90, 140, 255, 0.18) !important; }

    /* ── Tarjetas de métricas ── */
    .metric-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(90, 140, 255, 0.22);
        border-top: 3px solid #3d6fcf;
        border-radius: 12px;
        padding: 18px 20px 14px;
        margin-bottom: 8px;
        backdrop-filter: blur(8px);
        transition: border-color 0.2s;
    }
    .metric-card:hover { border-color: rgba(90, 140, 255, 0.45); }
    .metric-card .label {
        font-size: 11px;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        color: #6b90d4;
        margin-bottom: 8px;
    }
    .metric-card .value {
        font-size: 30px;
        font-weight: 700;
        color: #ffffff;
        line-height: 1;
    }
    .metric-highlight {
        border-top-color: #3ec993;
        background: rgba(62, 201, 147, 0.06);
    }
    .metric-highlight .value { color: #5ddba8; }

    /* ── Info box ── */
    [data-testid="stInfo"] {
        background: rgba(59, 100, 210, 0.12) !important;
        border: 1px solid rgba(90, 140, 255, 0.25) !important;
        border-radius: 10px !important;
        color: #a8c4f0 !important;
    }
    [data-testid="stInfo"] p { color: #a8c4f0 !important; }

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1.5px dashed rgba(90, 140, 255, 0.35) !important;
        border-radius: 12px !important;
        transition: border-color 0.2s;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(90, 140, 255, 0.65) !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] div,
    [data-testid="stFileUploaderDropzoneInstructions"] span {
        color: #7ba3e0 !important;
    }

    /* ── Botón de descarga ── */
    [data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #2352c8 0%, #1a3d9e 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        letter-spacing: 0.3px;
        box-shadow: 0 4px 20px rgba(35, 82, 200, 0.4);
        transition: box-shadow 0.2s, transform 0.15s;
    }
    [data-testid="stDownloadButton"] button:hover {
        box-shadow: 0 6px 28px rgba(35, 82, 200, 0.6) !important;
        transform: translateY(-1px);
    }

    /* ── Spinner ── */
    [data-testid="stSpinner"] p { color: #7ba3e0 !important; }

    /* ── Tabla ── */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(90, 140, 255, 0.15) !important;
        border-radius: 10px !important;
        overflow: hidden;
    }

    /* ── Subheader ── */
    [data-testid="stHeadingWithActionElements"] h2 {
        color: #d0e0ff !important;
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.2px;
    }

    /* ── Pie de página ── */
    .footer {
        margin-top: 3rem;
        padding: 1.6rem 0 0.8rem 0;
        border-top: 1px solid rgba(90, 140, 255, 0.15);
        text-align: center;
        line-height: 2;
    }
    .footer .brand {
        font-size: 13px;
        font-weight: 600;
        color: #a0bef0;
        letter-spacing: 0.3px;
    }
    .footer .meta {
        font-size: 11px;
        color: #4a6a9e;
        margin-top: 2px;
    }
    .footer .designer {
        font-size: 12px;
        color: #5d82c0;
        margin-top: 6px;
    }
    .footer .privacy {
        font-size: 11px;
        color: #364d70;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------------------
st.markdown("""
<p class="main-title">Calculadora de Horas Extra</p> 
<p class="main-subtitle">
    SEREMI de Salud Ñuble &nbsp;·&nbsp;
    Lun–Jue 9h &nbsp;|&nbsp; Vie 8h &nbsp;·&nbsp;
    Umbral ≥ 45 min
</p>
""", unsafe_allow_html=True)
st.divider()

# ---------------------------------------------------------------------------
# Carga del PDF
# ---------------------------------------------------------------------------
uploaded_pdf = st.file_uploader(
    "**Sube el PDF de marcas de reloj**",
    type=["pdf"],
    help="Descárgalo desde el sistema de control de asistencia.",
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

st.markdown(f"<p style='font-size:13px;color:#5d82c0;margin-top:6px'>Período: {period_display}</p>",
            unsafe_allow_html=True)
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
        return ["background-color: rgba(230,130,0,0.18); color: #f0c060"] * len(row)
    if row["_tiene_extra"]:
        return ["background-color: rgba(62,201,147,0.13); color: #5ddba8"] * len(row)
    return ["color: #c8d8f8"] * len(row)


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
    st.caption("🟠 Naranja = día feriado trabajado")
st.caption("🟢 Verde = día con horas extra contabilizadas")

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
    <div class="brand">Calculadora de Horas Extra Efectivas &nbsp;·&nbsp; v1.0 &nbsp;·&nbsp; 2026</div>
    <div class="meta">
        SEREMI de Salud Ñuble &nbsp;·&nbsp; Departamento de Control de Gestión
    </div>
    <div class="designer">
        Diseñado por <strong style="color:#7ba3e0">Kurt Castro Ortega</strong>
    </div>
</div>
""", unsafe_allow_html=True)
