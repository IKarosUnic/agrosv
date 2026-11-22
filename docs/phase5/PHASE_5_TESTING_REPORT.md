# Informe de pruebas — Fase 5

**AGROSV · 2026-11-22 · versión 5.0.0**

## 1. Entorno de ejecución

| Componente | Versión |
|---|---|
| Python | 3.12.3 |
| numpy | 2.5.5 |
| rasterio | 1.5.2 |
| geopandas | 1.2.0 |
| shapely | 2.2.0 |
| pyproj | 3.8.0 |
| fastapi | 0.165.0 |
| pytest | 9.2.0 |
| Sistema | Linux, sin red durante las pruebas |

Dependencias instaladas desde `requirements.txt` sin cambiar versiones.

## 2. Resultado global

```bash
.venv/bin/python -m pytest tests -q
# 373 passed, 33 warnings in 24.29s
```

- **373 pruebas pasan, 0 fallan, 0 se omiten.**
- 102 de ellas son específicas de Fase 5.
- Las 271 restantes son de Fase 1–4 y siguen operativas; ninguna se relajó para que
  pasara.

## 3. Pruebas de Fase 5

| Módulo | Pruebas | Cobertura |
|---|---:|---|
| `tests/test_engines_territorial.py` | 19 | coordenadas, cobertura, contención, búsqueda, cuenca, gobernanza |
| `tests/test_engines_soil.py` | 22 | textura USDA, materia orgánica, perfil, reglas, NoData, procedencia |
| `tests/test_engines_hydrology.py` | 10 | ventana, agua superficial, cuenca, Budyko, subterránea |
| `tests/test_engines_climate.py` | 15 | agregaciones, ETCCDI, rachas, anomalías, sequía, normales |
| `tests/test_engines_integration.py` | 36 | 4 regiones, unidades/CRS, reglas, API, caché, rendimiento |
| **Total Fase 5** | **102** | |

### 3.1 Qué comprueba cada bloque

**Territorial (19)**
- rechazo de coordenada fuera del país, NaN y texto;
- niveles ausentes declarados (2023, distritos, cuencas);
- conversión de pendiente, clases de relieve, rumbo del aspecto;
- TRI y TPI sintéticos con resultado analítico;
- perfil real: departamento `SV-SS`, municipio histórico `official: false`;
- búsqueda por nombre y código; búsqueda inexistente sin invención;
- cuenca asociada con truncamiento y unidades.

**Suelo (22)**
- 12 combinaciones del triángulo USDA, incluidas las fronteras;
- suma incoherente → `sin_clasificar`;
- materia orgánica con factor 1,724 y rango declarado;
- intervalo integrado 0–30 y seis intervalos estándar ausentes con motivo;
- reglas de limitación sin puntuación;
- NoData real (San Salvador urbano) devuelve `null` con motivo;
- unidades, resolución 250 m, licencia y `data_class`;
- CENTA no aparece como fuente disponible; conflictos vacíos justificados.

**Hidrología (10)**
- ventanas de 10 m y 100 km rechazadas;
- rejilla de 30 m, EPSG:32616, 100 × 100 para 3 km, sin NoData;
- distancia real y advertencias de caudal/agua subterránea;
- área de cuenca ≤ área de ventana;
- `_budyko_runoff` con límites físicos `0 ≤ Q ≤ P`;
- balance coherente y rango de sensibilidad ordenado;
- potencial ≠ acceso legal.

**Clima (15)**
- haversine (0 en el mismo punto, simetría, ~108 km por grado de longitud);
- períodos incompletos marcados;
- rachas seca/húmeda con fechas;
- agregaciones declaradas y variable inexistente;
- suma anual completa (2019–2025);
- climatología mensual de 12 meses y `not_a_normal`;
- coherencia ETCCDI y umbral de rachas;
- anomalías centradas;
- sequía por percentil y texto explícito «NO es el SPI»;
- normales insuficientes;
- Walter–Lieth y ausencia de temporada agrícola inventada;
- sin estaciones, sin interpolación, sin pronóstico.

**Integración (36)**
- perfil ambiental en Ahuachapán, San Salvador, Chalatenango y La Unión;
- ningún error de componente en las cuatro regiones;
- ausencia de puntuación y de índice compuesto;
- procedencia completa (URL, licencia, clase, resolución, versión);
- incertidumbre por componente y agregado no cuantificado;
- unidades: pendiente %, textura ~100 %, área ≤ ventana;
- CRS ida y vuelta; área nacional −0,35 %;
- reglas de interacción y reglas de ausencia;
- perfil por identificador con punto interior;
- intersección/contención y océano dentro del bbox;
- consulta por profundidad de suelo;
- caché direccionado por contenido, caché corrupto, `use_cache=False`;
- 15 endpoints: meta, cobertura, datasets, ficha, búsqueda, perfil territorial,
  intersección, terreno, suelo, suelo/profundidad, hidrología, clima,
  ambiental y caché; errores 400, 404 y 409;
- rendimiento y extracción por ventana.

## 4. Defectos encontrados y corregidos

### 4.1 Errores de código

| # | Defecto | Efecto | Corrección |
|---|---|---|---|
| 1 | Clasificador USDA trataba arcilla 20–27 % + limo ≥ 28 % como «franco arcilloso» | clase textural incorrecta en una franja del triángulo | se eliminó la rama; esas combinaciones caen en «franco» si cumplen la definición |
| 2 | El modelo de perfil no incluía el intervalo integrado 0–30 cm | perfil incoherente con el dato disponible | 0–30 se publica como intervalo integrado; los seis estándar se declaran ausentes |
| 3 | `dem_window_metric` aceptaba ventanas menores que una celda | una «cuenca» de 10 m desde un DEM de 30 m | se exige al menos dos celdas de resolución |
| 4 | El rango de Budyko se devolvía descendente y sin explicar | un rango `[1446, 857]` parece un error | se ordena `[ω=3,0; ω=1,5]` y se documenta que mayor ω implica menos escorrentía |
| 5 | Las reglas de ausencia nunca se ejecutaban | `sin_dato_de_profundidad` y `cobertura_hidrica_incompleta` eran código muerto | `allow_missing` permite ejecutar reglas que declaran una ausencia |
| 6 | `require()` fallaba con rutas relativas | una prueba de Fase 4 abortaba en Linux en vez de omitirse | el helper resuelve rutas relativas contra la raíz |
| 7 | Manifiestos y catálogo de Fase 4 con rutas `C:\GIT HUB\...` | linaje, monitoreo y perfil de rásteres fallaban fuera de Windows | se regeneraron con `scripts/08_build_phase4_integration.py --rebuild` |

### 4.2 Expectativas de prueba incorrectas

Tres pruebas de la etapa inicial no describían la matemática implementada; se
corrigieron **las expectativas**, no el código:

| Prueba | Esperado antes | Correcto |
|---|---|---|
| TRI de un plano de 1 m/celda | √14 | √6 (la suma real de los 8 vecinos es 6) |
| TPI en el centro de un plano | −0,125 | 0,0 (la media de los 8 vecinos es 99,0) |
| `slope_pct(30)` | precisión 1 × 10⁻⁹ | la función redondea a 2 decimales por diseño |

Ninguna prueba se debilitó para ocultar un fallo: las tres sustituyen una expectativa
errónea por la que corresponde a la definición publicada.

### 4.3 Estado de artefactos

- La base SQLite de Fase 4 está en `.gitignore`; se regeneró con el script documentado.
- La muestra CHIRPS de un día está en `.gitignore`; se recuperó con
  `scripts/07_fetch_phase3_samples.py` (hash `1769f6f4fffe`, idéntico al manifiesto).
- El catálogo volvió a 22 datasets, 13 rásteres y 5 derivaciones, `monitoring_ok: true`.

## 5. Datos de prueba

- **Reales:** DEM, límites, OSM, SoilGrids, series NASA/Open-Meteo, CHIRPS de un día.
- **Sintéticos, claramente etiquetados:** plano de 1 m/celda para TRI/TPI, triángulo
  textural, series de 10 días para agregación, caché con `tmp_path`.
- No se inventó ningún fixture que simule una estación o un laboratorio.

## 6. Rendimiento

`scripts/09_phase5_benchmark.py --repeats 5`, una sola máquina, sin red:

| Operación | Mediana | Mín. | Máx. |
|---|---:|---:|---:|
| `territorial.profile` | 0,1433 s | 0,1412 | 0,4956 |
| `terrain.terrain_metrics` | 0,0193 s | 0,0190 | 0,0201 |
| `soil.sample` | 0,0185 s | 0,0184 | 0,0186 |
| `hydrology.watershed` (3 km) | 0,0317 s | 0,0314 | 0,0319 |
| `hydrology.profile` (3 km, sin caché) | 0,0368 s | 0,0365 | 0,0671 |
| `climate.profile` | 0,0117 s | 0,0117 | 0,0264 |
| `environmental.profile` (3 km, sin caché) | 0,0921 s | 0,0919 | 0,0936 |
| `territories_in_bbox` (nacional, 287) | 0,0166 s | 0,0163 | 0,0176 |
| `availability_report` | 0,1212 s | 0,1206 | 0,1900 |

Caché: primera llamada 0,1822 s; segunda 0,0014 s (**≈130×**), `hit: true`.

Memoria: RSS 194,4 → 195,4 MiB (+1,0 MiB) durante un perfil de 6 km;
pico de asignaciones Python 4,0 MB (`tracemalloc`). Las reservas de GDAL/rasterio no las
contabiliza `tracemalloc`; por eso se informa también el RSS. Detalle completo en
`docs/phase5/benchmark_phase5.json`.

## 7. Límites de estas pruebas

1. **No son validación científica.** Verifican comportamiento y trazabilidad, no
   exactitud frente a la realidad.
2. Los umbrales de rendimiento son holgados: detectan regresiones graves, no miden la
   máquina.
3. No se probó concurrencia ni múltiples procesos.
4. Los tiempos son de un host; no son un SLA.
5. No hay prueba de acuerdo con estaciones, laboratorio, aforos o GNSS porque esos
   datos no existen en el repositorio.
6. Las pruebas se omiten si falta un artefacto; en esta ejecución no se omitió ninguna.

## 8. Reproducción

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/07_fetch_phase3_samples.py        # muestras, ~15 MB
.venv/bin/python scripts/08_build_phase4_integration.py --rebuild
.venv/bin/python scripts/09_phase5_benchmark.py --repeats 5
.venv/bin/python -m pytest tests -q
```
