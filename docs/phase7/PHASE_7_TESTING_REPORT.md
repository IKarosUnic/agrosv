# Fase 7 — informe de pruebas y rendimiento

## Resultado

```
.venv/bin/python -m pytest tests -q
559 passed, 33 warnings in 39.41s
```

Composición: 373 pruebas de Fases 1–5 + 96 de Fase 6 + 21 de acceso a datos +
**69 de monitorización de Fase 7**.

Archivo nuevo: `tests/test_phase7_monitoring.py` (69 pruebas, 1,23 s). Cubre
satélite, índices, series, cambio, sanidad, agua, fitosanidad, riesgos, alertas,
campo, integración, API y compatibilidad hacia atrás.

Los avisos son preexistentes (deprecación de `shapely.ops.transform` y un aviso
de área en CRS geográfico en una prueba de Fase 4). No hay omisiones en la
suite de Fase 7.

## Cobertura por subsistema

El archivo cubre, con al menos una prueba por motor:

- **A. satélite:** catálogo y campos obligatorios, lectura por ventana, nodata,
  máscara SCL, STAC local, plan no ejecutado, ocho índices, series, cambio y
  escala.
- **B. sanidad:** estados, evidencia insuficiente, estrés de vegetación, calor y
  anomalías.
- **C. fitosanidad:** integridad del catálogo, riesgo de plaga, riesgo de
  enfermedad y procedencia oficial.
- **D. riesgo:** producto, secas, índice estandarizado, inundación, calor,
  suelo y pérdida.
- **E. alertas:** duplicados, transiciones, verificación, prioridad, notificación
  y aviso temprano.
- **F. integración:** campo, línea temporal, mapa GeoJSON y análisis.
- **API:** contratos, errores y compatibilidad con Fases 1–7 de acceso a datos.

## Rendimiento medido

Entorno: Python 3.12.3, Linux, NumPy 2.5.5, 8 vCPU, sin GPU.
Script: `PYTHONPATH=backend .venv/bin/python scripts/13_phase7_benchmark.py`.

| Operación | Mediana |
|---|---|
| NDVI sobre 1000×1000 píxeles | 24,5 ms |
| Cambio sobre 1000×1000 píxeles | 20,4 ms |
| Anomalía estacional (40 observaciones) | 0,28 ms |
| Riesgo (10.000 evaluaciones) | 91,3 ms (≈ 9 µs cada una) |
| Creación de 2.000 alertas | 34,6 ms |
| `POST /api/monitoring/indices` | 3,14 ms |
| `GET /api/monitoring/meta` | 2,73 ms |

Memoria máxima del proceso (RSS): **150,4 MB** para el conjunto del benchmark.
El detalle se genera con `--json /tmp/phase7_benchmark.json`. El benchmark no
mide precisión científica.

## Reproducir

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/test_phase7_monitoring.py -q
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/13_phase7_benchmark.py --json data/phase7_benchmark.json
```

## Limitaciones de las pruebas

- Los rásteres de prueba son sintéticos (4×4).
- No se prueba autenticación ni red: no hay servicios remotos configurados.
- Las pruebas de API usan `TestClient`, no un servidor desplegado.
- No se prueba concurrencia ni persistencia: los almacenes son en memoria.
