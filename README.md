# AGROSV — Fundación geoespacial e infraestructura científica

Plataforma geoespacial de El Salvador que servirá de base a los módulos
agrícolas, climáticos y edafológicos de AGROSV. Esta fase entrega **territorio,
topografía, infraestructura, suelos, API y mapa interactivo**, con procedencia
y limitaciones documentadas para cada capa.

## Qué hay aquí

| Módulo | Contenido | Salida |
|---|---|---|
| 1 · Territorio | Límite nacional, 14 departamentos, 272 municipios históricos | `data/processed/territory/territory.gpkg` |
| 2 · Topografía | Elevación, pendiente, orientación, hillshade, clases de relieve | `data/processed/topography/*.tif` |
| 3 · Infraestructura | Caminos, ríos, cuerpos de agua, asentamientos, infraestructura | `data/processed/infrastructure/infrastructure.gpkg` |
| 4 · Suelos | pH, C orgánico, N total, arcilla, arena, limo (0–30 cm) | `data/processed/soils/rasters/*.tif` |
| 5 · Backend | FastAPI con consultas puntuales, GeoJSON y teselas | `backend/agrosv/api.py` |
| 6 · Interfaz | React + TypeScript + MapLibre GL | `frontend/` (compila a `frontend/dist`) |
| 7 · Calidad | 469 pruebas de integridad, cobertura, CRS, endpoints, ciencia, gobernanza sintética y rendimiento | `tests/` |
| 8 · Fase 6 | Inteligencia agrícola, población sintética y simulación socio-agrícola | `backend/agrosv/{agriculture,social,socio}/` |
| 9 · Fase 7 (datos) | Incorporación controlada de datos externos y correspondencia 2023 | `backend/agrosv/onboarding/` |
| 10 · Fase 7 (monitorización) | Satélite, sanidad, plagas, riesgos, alertas y campo | `backend/agrosv/monitoring/` |

Documentación obligatoria: [`docs/DATA_PROVENANCE.md`](docs/DATA_PROVENANCE.md)
(fuentes, licencias, transformaciones), [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md)
(resolución y cobertura) y [`docs/ADR-001-architecture-decisions.md`](docs/ADR-001-architecture-decisions.md)
(decisiones y por qué se apartaron de lo previsto en Fase 0).

## Estructura

```
/backend     código de la API (paquete agrosv) — sin datos
/frontend    React + TypeScript + MapLibre
/data/raw    descargas originales (no versionadas)
/data/interim  archivos temporales de escritura
/data/processed  capas listas + manifiestos .provenance.json + *_stats.json
/docs        procedencia, limitaciones, ADR
/scripts     pipelines reproducibles 01..04 y descarga de datos
/tests       pytest
```

Los datos crudos pesan ~420 MB y **no se versionan**; se regeneran con
`bash scripts/download_data.sh all`. Las capas procesadas sí se versionan
(suman ~150 MB) porque son el entregable verificable.

## Puesta en marcha y ejecución

### Opción 1: Modo Producción Unificado (Recomendado)
FastAPI sirve la interfaz compilada de React, la PWA, los mapas raster/vectoriales y todos los endpoints de las Fases 1 a 8 en un solo puerto (`8000`).

```powershell
# En Windows (PowerShell):
# 1. Compilar frontend (si se realizaron cambios)
cd frontend
npm run build
cd ..

# 2. Iniciar el servidor unificado
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn agrosv.api:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# En Linux / macOS:
cd frontend && npm run build && cd ..
export PYTHONPATH="backend"
.venv/bin/python -m uvicorn agrosv.api:app --host 0.0.0.0 --port 8000 --reload
```

- **Plataforma Web / PWA:** [http://localhost:8000](http://localhost:8000)
- **Documentación OpenAPI / Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Opción 2: Modo Desarrollo (con Hot-Reload en Frontend)
Recomendado al desarrollar componentes visuales en React:

1. **Terminal 1 — Backend FastAPI:**
   ```powershell
   # Windows PowerShell
   $env:PYTHONPATH="backend"
   .\.venv\Scripts\python.exe -m uvicorn agrosv.api:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **Terminal 2 — Frontend Vite:**
   ```powershell
   cd frontend
   npm run dev
   ```

- **Aplicación Vite en desarrollo:** [http://localhost:5173](http://localhost:5173)  
*(Vite redirige automáticamente las peticiones `/api` y teselas al backend en el puerto `8000`)*.

---

### Verificación y Tests

```powershell
# Tests unitarios del frontend (Vitest / Testing Library):
cd frontend
npm test

# Tests del backend y ciencia (Pytest):
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m pytest tests -q
```

## API

| Endpoint | Devuelve |
|---|---|
| `GET /api/health` | estado y capas ausentes |
| `GET /api/meta` | CRS, resolución, licencia y atribución por conjunto |
| `GET /api/limitations` | `LIMITATIONS.md` en texto |
| `GET /api/territory/departments?simplify=` | GeoJSON de los 14 departamentos |
| `GET /api/territory/departments/{code}` | indicadores topográficos y de suelo |
| `GET /api/territory/municipalities?department=` | municipios **históricos** (`official: false`) |
| `GET /api/topography/elevation?lat=&lon=` | elevación, pendiente, orientación, clase |
| `GET /api/topography/stats` | nacional y por departamento |
| `GET /api/infrastructure/summary` | conteos, longitudes y notas de cobertura |
| `GET /api/infrastructure/{layer}?west=&south=&east=&north=` | capa OSM acotada |
| `GET /api/soils/summary` | medias nacionales, fuentes nacionales, advertencias |
| `GET /api/soils/point?lat=&lon=` | propiedades 0–30 cm en un punto |
| `GET /api/tiles/{hillshade,slope,relief}/{z}/{x}/{y}.png` | teselas del DEM (z 7–14) |

No hay claves de API ni servicios comerciales: el mapa base es el hillshade
derivado del propio DEM y las teselas se generan desde los COG.

## Pruebas

```bash
.venv/bin/python -m pytest tests -q
```

Cubren integridad geométrica, ausencia de solapes, cobertura territorial,
CRS y transformaciones, valores raster ausentes, contrato de endpoints,
umbrales de rendimiento, gobernanza de capas sintéticas, motores de Fase 6 y
validación e incorporación de datos externos de Fase 7.
Las pruebas se **omiten** si falta un artefacto, nunca pasan en falso. Suite
actual: **559 pruebas** (373 de Fase 1–5 + 96 de Fase 6 + 21 de acceso a
datos + 69 de monitorización de Fase 7).

## Reglas respetadas

- Sin datos inventados: toda capa procede de una fuente descargable y hasheada.
- ADM2 se publica como histórica y con `official: false`.
- No se descargan archivos innecesarios (SoilGrids: 138 teselas de 7.692).
- Sin dependencias comerciales obligatorias (sin Mapbox, sin Google).
- Licencias documentadas y atribución presente en la UI y en cada respuesta.
- Nada se declara terminado sin una comprobación que lo respalde.

## Licencias de los datos

geoBoundaries **CC BY-SA 2.0** · Copernicus DEM GLO-30 **DLR/Airbus, uso libre
con atribución** · OpenStreetMap **ODbL 1.0** · SoilGrids 2.0 **CC BY 4.0**.
Detalle y texto de atribución en [`docs/DATA_PROVENANCE.md`](docs/DATA_PROVENANCE.md).

## Fase 2 — infraestructura científica (implementada en parte)

`backend/agrosv/science/` contiene los motores transversales que hacen
publicable un resultado: contrato con etiqueta/resolución/incertidumbre,
versionado por hash, QC geoespacial, validación V0–V4, reproducibilidad y
orquestación por lotes. Además hay dos motores ejecutables:

- **hidrología** — priority-flood, D8, acumulación, cuenca y factor LS sobre el
  DEM de Fase 1 (sin calibrar: no hay aforos);
- **índices espectrales** — NDVI, EVI, NDWI, NDMI, NBR y máscara de cambio
  (aritmética verificada; la adquisición satelital no está implementada).

API científica versionada, en un router aparte que no toca los 13 endpoints de
Fase 1:

| Endpoint | Devuelve |
|---|---|
| `GET /api/v1/meta` | versión, datasets versionados, licencias, fichas de índices |
| `GET /api/v1/sources` | catálogo con `sha256` y licencia (`?verify=true` recalcula) |
| `GET /api/v1/provenance/{id}` | manifiesto completo del artefacto |
| `GET /api/v1/qc` | QC vectorial (con `?include_rasters=true`, también ráster) |
| `GET /api/v1/hydro/watershed?lat=&lon=&size_m=` | cuenca aguas arriba y su área |
| `GET /api/v1/hydro/aoi?lat=&lon=&size_m=` | pendiente, LS y red de drenaje |
| `GET /api/v1/indices` | fórmulas, resolución nativa y lo que falta |
| `GET /api/v1/offline/{dept}.zip` | paquete territorial con manifiesto y atribución |
| `GET /api/v1/validation/policy` | niveles V0–V4 y estado real por capa |

Estado honesto de la fase y resultados de pruebas en
[`docs/PHASE_2_IMPLEMENTATION_REPORT.md`](docs/PHASE_2_IMPLEMENTATION_REPORT.md).

## Fase 5 — motores territoriales y ambientales

Cinco motores sobre los datos verificados de Fase 1–4, en un router nuevo que no
altera `/api`, `/api/v1` ni `/api/data`:

| Motor | Responde | Estado |
|---|---|---|
| `TerritorialEngine` | identificación administrativa, terreno, cuenca asociada | implementado |
| Análisis de terreno | elevación, pendiente, aspecto, TRI, TPI, clase | implementado |
| `SoilEngine` | textura, pH, SOC, N, limitaciones por regla | solo 0–30 cm |
| `HydrologyEngine` | agua superficial, cuenca D8, balance P−ET0 | sin agua subterránea ni caudales |
| `ClimateEngine` | climatología del período, ETCCDI, rachas, sequía | 2 puntos de reanálisis |
| `EnvironmentalInteractionEngine` | perfil ambiental con reglas y procedencia | sin índice compuesto |

| Endpoint | Devuelve |
|---|---|
| `GET /api/engines/meta` | motores, versiones y política científica |
| `GET /api/engines/coverage` | cobertura geográfica y temporal real |
| `GET /api/engines/datasets` | disponibilidad comprobada y variables ausentes |
| `GET /api/engines/datasets/{id}` | ficha §8 y procedencia |
| `GET /api/engines/territory/search?q=&level=` | búsqueda por id, código o nombre |
| `GET /api/engines/territory/profile?q=&level=` | perfil en un punto interior del territorio |
| `GET /api/engines/territory/intersect?west=&south=&east=&north=` | intersección y contención |
| `GET /api/engines/territorial?lat=&lon=` | perfil territorial |
| `GET /api/engines/terrain?lat=&lon=` | características del terreno |
| `GET /api/engines/soil?lat=&lon=` | suelo 0–30 cm |
| `GET /api/engines/soil/profile?lat=&lon=&top_cm=&bottom_cm=` | consulta por profundidad |
| `GET /api/engines/hydrology?lat=&lon=` | agua superficial, cuenca y balance |
| `GET /api/engines/climate?lat=&lon=` | climatología, extremos y sequía |
| `GET /api/engines/environmental?lat=&lon=` | perfil ambiental integrado |
| `GET /api/engines/cache` | estado del caché derivado |

Un punto fuera del rectángulo nacional devuelve 400; una variable ausente se declara
con su motivo en lugar de rellenarse. No hay índice ambiental compuesto: el perfil
devuelve hechos, reglas y procedencia.

Documentación: [`docs/phase5/PHASE_5_FINAL_REPORT.md`](docs/phase5/PHASE_5_FINAL_REPORT.md)
y los nueve documentos de método, validación y pruebas de `docs/phase5/`.
Rendimiento reproducible con `scripts/09_phase5_benchmark.py`.

## Fase 6 — inteligencia agrícola y socio-agrícola

Tres subsistemas nuevos, con prefijos de API propios y sin cambiar los contratos
anteriores:

| Subsistema | Motores | Estado |
|---|---|---|
| A. Agrícola | catálogo, fenología, aptitud, agua/nutrientes, simulación, calendario | 6 implementados |
| B. Social sintético | población, persona, hogar, comportamiento, economía, adopción, resiliencia, multiagente | 8 implementados |
| C. Integrado | integración, decisión, escenarios A–G, análisis | 4 implementados |

| Endpoint | Devuelve |
|---|---|
| `GET /api/agriculture/crops` | catálogo de 22 cultivos con estado por parámetro |
| `GET /api/agriculture/suitability` | clase S1/S2/S3/N o `not_evaluated` y factores limitantes |
| `GET /api/agriculture/phenology` | etapas por tiempo térmico |
| `POST /api/agriculture/water` | balance FAO-56 con AWC y Kc del usuario |
| `POST /api/agriculture/simulate` | adaptador AGROSV; externos detectados, no integrados |
| `GET /api/agriculture/calendar` | ventanas y riesgos derivados, no oficiales |
| `POST /api/social/population` | población sintética reproducible |
| `POST /api/social/adoption` | propensión tecnológica (índice, no probabilidad) |
| `POST /api/social/resilience` | impacto de un choque (índice sintético) |
| `POST /api/social/multiagent` | difusión reproducible en red sintética |
| `POST /api/socio/decision` | decisión MAUT con restricciones científicas |
| `POST /api/socio/scenario` | escenarios de sequía, tecnología, costos, mercado, diversificación, clima y apoyo |
| `POST /api/socio/analysis` | comparación de escenarios y hallazgos de simulación |

Ninguna persona generada representa a una persona real. Los resultados no son
pronósticos y no tienen calibración ni validación local. Los cultivos sin
parámetros se publican como `null` + `GAP`.

Documentación: [`docs/phase6/PHASE_6_FINAL_REPORT.md`](docs/phase6/PHASE_6_FINAL_REPORT.md),
25 documentos en `docs/phase6/`. Rendimiento reproducible con
`scripts/10_phase6_benchmark.py`.

Suite completa: **490 pruebas** (373 de Fase 1–5 + 96 de Fase 6 + 21 de
Fase 7).

## Fase 7 · etapa de acceso a datos externos

No se descargaron series nuevas. Se añadió el registro de seis fuentes, sus
validadores estrictos y **la única fuente adquirida**: la correspondencia
oficial de los 262 distritos a los 44 municipios del Decreto 762 (vigente
desde 2024-05-01).

| Fuente | Estado |
|---|---|
| Correspondencia municipal 2023 | **adquirida** (14/44/262), con SHA-256 |
| Series SNET/MARN | metadatos públicos; series por solicitud |
| Laboratorio de Suelos CENTA | restringido por solicitud |
| Cuencas oficiales MARN | portal público sin capa vectorial confirmada |
| Aforos y caudales MARN | metadatos públicos; series por solicitud |
| Vértices GNSS del CNR | servicio arancelado |

| Endpoint | Devuelve |
|---|---|
| `GET /api/onboarding/sources` | registro de fuentes, requisitos y sustituto declarado |
| `GET /api/onboarding/municipalities/summary` | 14 departamentos / 44 municipios / 262 distritos |
| `GET /api/onboarding/municipalities/lookup?district=` | municipio vigente de un distrito histórico |
| `POST /api/onboarding/validate` | validación de un CSV/GeoJSON en `data/external/` |
| `POST /api/onboarding/dem-error` | sesgo, MAE y RMSE del DEM con puntos GNSS |

Los validadores no imputan valores: rechazan o advierten. El error del DEM
solo se calcula si hay alturas ortométricas (o elipsoidales + ondulación
declarada); sin puntos no se declara exactitud.

Documentación: [`docs/phase7/DATA_ACCESS_AND_ONBOARDING.md`](docs/phase7/DATA_ACCESS_AND_ONBOARDING.md)
y [`docs/phase7/DATA_REQUEST_TEMPLATES.md`](docs/phase7/DATA_REQUEST_TEMPLATES.md).
La suite completa es **559 pruebas**.

## Fase 7 — monitorización agrícola, sanidad y alertas

Seis subsistemas y 31 motores en `backend/agrosv/monitoring/`, con API propia
bajo `/api/monitoring`. **No hay escenas satelitales ni series de campo
integradas**: los adaptadores leen archivos locales y los motores declaran la
ausencia en lugar de sustituirla.

| Subsistema | Motores |
|---|---|
| A. Satélite y teledetección | datos, índices, cambio, series, contexto |
| B. Sanidad del cultivo | salud, estrés, agua, calor, anomalías |
| C. Plagas y enfermedades | 5 plagas y 4 enfermedades con fuente |
| D. Riesgo agrícola | riesgo, sequía, inundación, calor, suelo, pérdida |
| E. Alertas | alerta, aviso temprano, prioridad, verificación, notificación |
| F. Integración | monitorización, línea temporal, mapas, campo, análisis |

| Endpoint | Devuelve |
|---|---|
| `GET /api/monitoring/meta` | motores, fuentes y política científica |
| `GET /api/monitoring/sources` | 11 fuentes satelitales evaluadas |
| `GET /api/monitoring/indices` | 8 índices con fórmula y límites |
| `POST /api/monitoring/indices` | índice sobre bandas en memoria |
| `POST /api/monitoring/timeseries/anomaly` | anomalía estacional robusta |
| `POST /api/monitoring/change` | cambio entre dos fechas |
| `GET /api/monitoring/pests` | catálogo de plagas con presencia |
| `POST /api/monitoring/pest-risk` | idoneidad y riesgo (no presencia) |
| `POST /api/monitoring/crop-health` | estado interpretativo del cultivo |
| `POST /api/monitoring/water-stress` | cinco categorías de sequía |
| `POST /api/monitoring/drought` | índice estandarizado (≥ 30 años) |
| `POST /api/monitoring/risk` | peligro × exposición × vulnerabilidad |
| `POST /api/monitoring/alerts` | alerta con evidencia y ciclo de vida |
| `POST /api/monitoring/alerts/{id}/verify` | verificación con verificador fuerte |
| `POST /api/monitoring/field-observations` | observación de campo con controles |
| `POST /api/monitoring/risk-map` | GeoJSON con metadatos de capa |

Ninguna observación de campo se publica como registro verificado. Un riesgo no
es un evento, una alerta no es un diagnóstico y un pronóstico no es una
observación. Documentación: `docs/phase7/` (31 fichas de motor y 6 documentos de
gobernanza). Rendimiento reproducible con `scripts/13_phase7_benchmark.py`.

Suite completa: **559 pruebas** (69 de monitorización).
