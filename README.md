# Calculadora de Horas Extra Efectivas

Calcula las horas extra efectivas trabajadas en un período, extrayendo los datos desde un PDF de marcas de reloj y contrastándolos contra la jornada laboral institucional.

## Requisitos

- Python 3.10+
- Dependencias: `pip install -r requirements.txt`

## Archivos de entrada

Coloca los archivos en la carpeta `data/` con los nombres indicados, **o** actualiza las rutas en `config.py`:

| Archivo esperado en `data/`     | Archivo original               | Descripción                        |
|---------------------------------|--------------------------------|------------------------------------|
| `registro_asistencia.pdf`       | `Marcas Reloj Imprimir.pdf`    | PDF de marcas de reloj             |
| `feriados_2026.xlsx`            | `feriados_2026.xlsx`           | Listado de feriados oficiales 2026 |
| `calculo_horas_extra.xlsx`      | `HORAS_EXTRA_2026.xlsx`        | Referencia de cálculo (solo lectura) |

> Si los archivos ya están en el directorio raíz del proyecto con sus nombres originales, la aplicación los detecta automáticamente sin necesidad de moverlos.

## Uso

```bash
py main.py
```

El reporte Excel se genera en `output/horas_extra_<Mes>_<Año>.xlsx`.

## Reglas de cálculo

| Día           | Jornada estándar |
|---------------|-----------------|
| Lunes–Jueves  | 9 horas          |
| Viernes       | 8 horas          |
| Sábado/Domingo| No aplica        |

- **Umbral**: el excedente sobre la jornada base debe ser **≥ 20 minutos** para contabilizarse como hora extra.
- **Feriados**: no existe jornada base; cualquier tiempo trabajado es extra efectivo.

## Tests

```bash
py -m pytest tests/ -v
```

## Estructura del proyecto

```
├── config.py                   # Rutas y constantes (modificar aquí para ajustar)
├── main.py                     # Punto de entrada
├── src/
│   ├── pdf_extractor.py        # Extracción desde PDF
│   ├── holidays_loader.py      # Carga de feriados desde Excel
│   ├── schedule_rules.py       # Horas base por día de semana
│   ├── overtime_calculator.py  # Lógica de cálculo
│   └── report_generator.py     # Generación de reportes
├── tests/                      # Pruebas unitarias
├── data/                       # Archivos de entrada
└── output/                     # Reportes generados
```

## Para agregar feriados de otros años

1. Crea `data/feriados_2027.xlsx` con el mismo formato.
2. En `config.py`, actualiza `HOLIDAYS_YEAR = 2027` y ajusta `HOLIDAYS_PATH` si es necesario.
