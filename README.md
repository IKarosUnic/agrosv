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
| 7 · Calidad | 161 pruebas de integridad, cobertura, CRS, endpoints, ciencia y rendimiento | `tests/` |

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

## Puesta en marcha

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

bash scripts/download_data.sh all          # ~420 MB, requiere red
.venv/bin/python scripts/01_territory.py
.venv/bin/python scripts/02_topography.py  # ~3 min, 8 hilos de GDAL
.venv/bin/python scripts/03_infrastructure.py
.venv/bin/python scripts/04_soils.py       # descarga selectiva (~70 MB)

cd frontend && npm install && npm run build && cd ..
.venv/bin/uvicorn agrosv.api:app --app-dir backend --host 0.0.0.0 --port 8000
```

Abre `http://localhost:8000` para el mapa y `/docs` para Swagger.
En desarrollo, `cd frontend && npm run dev` sirve Vite en 5173 con proxy a 8000.

Cada script imprime sus comprobaciones y **termina con código ≠ 0 si alguna
falla**; no hay capas "aproximadas" que se publiquen en silencio.

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
CRS y transformaciones, valores raster ausentes, contrato de endpoints y
umbrales de rendimiento. Las pruebas se **omiten** si falta un artefacto, nunca
pasan en falso.

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
