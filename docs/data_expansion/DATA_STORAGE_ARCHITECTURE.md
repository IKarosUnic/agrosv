# DATA_STORAGE_ARCHITECTURE — AGROSV Fase 3

**Fecha:** 2026-11-22 · **Principio:** datos crudos inmutables, derivados
reproducibles, manifiestos verificables y Git solo para lo que debe versionarse.

---

## 1. Estructura propuesta (adaptada a la existente)

```
data/
├── raw/                     # descargas originales, inmutables, NO versionadas
│   ├── territorial/         # CNR, geoBoundaries, OSM
│   ├── topography/          # Copernicus DEM, SRTM/NASADEM
│   ├── geology/             # MARN, CNR
│   ├── landcover/           # WorldCover, Dynamic World, MAG (PDF)
│   ├── soils/               # SoilGrids, CENTA (cuando exista)
│   ├── hydrology/           # HydroSHEDS, JRC GSW, SNET
│   ├── climate/             # CHIRPS, AgERA5, POWER
│   ├── satellite/           # STAC + COG por AOI
│   ├── crops/               # fichas, variedades
│   ├── production/          # CAP 2025, anuarios
│   ├── census/              # CPV 2024, CAP 2025
│   ├── phytosanitary/       # IPPC, OIRSA, GBIF
│   └── economic/            # precios, costos, comercio
├── interim/                 # temporales de escritura (NO versionado)
├── processed/               # capas listas para API (versionadas si < umbral)
├── derived/                 # resultados de modelo (índices, cuencas, aptitud)
├── metadata/                # catálogos, tablas de correspondencia, esquemas
├── samples/                 # muestras mínimas validadas (Fase 3)
│   └── phase3/<source_id>/
└── manifests/               # un manifiesto por lote o por muestra
```

Coincide con lo ya usado en Fase 1 (`data/processed`, `*.provenance.json`) y
añade las carpetas que faltaban. **No se renombra nada existente.**

---

## 2. Política de versionado

| Ruta | ¿Git? | Motivo |
|---|---|---|
| `data/raw/**` | **No** | Voluminoso y regenerable; se reconstruye con scripts |
| `data/interim/**` | **No** | Temporal |
| `data/processed/**` | **Sí, si < 25 MB por archivo** | Es el entregable verificable |
| `data/derived/**` | **Sí, si es pequeño y reproducible** | Resultado científico |
| `data/samples/phase3/**` | **JSON sí; ráster > 5 MB no** | Evidencia ligera; el hash queda en el manifiesto |
| `data/metadata/**` | **Sí** | Catálogos y correspondencias |
| `data/manifests/**` | **Sí** | Trazabilidad |

Reglas añadidas a `.gitignore`:

```
data/samples/**/*.tif
data/samples/**/*.pbf
data/samples/**/*.zip
```

(`data/raw/` y `data/interim/` ya estaban ignorados.)

---

## 3. Convención de nombres

```
{source_id}_{variable}_{resolucion}_{extension}_{fecha}_{version}.{ext}

Ejemplos:
chirps3_precip_0p05deg_sv_2026-01-15_v3.0.tif
copdem30_elev_30m_sv_2011-2015_v1.tif
soilgrids_clay_250m_sv_0-30cm_v2.0.tif
mag_precios_maiz_2023-12_la-tiendona.pdf
```

- `source_id` en minúsculas, sin espacios, igual que en el registro.
- Resolución como `0p05deg`, `250m`, `30m`, `1km`.
- Fecha en ISO 8601 (`AAAA-MM-DD`) o intervalo.
- Versión de la fuente, no de AGROSV; la versión AGROSV va en el manifiesto.
- Sin acentos ni `ñ` en nombres de archivo; sin espacios.

---

## 4. Manifiesto obligatorio

```json
{
  "artifact_id": "chirps3_precip_0p05deg_sv_2026-01-15_v3.0",
  "source_id": "chirps3",
  "source_url": "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/2026/chirps-v3.0.rnl.2026.01.15.tif",
  "retrieved_at": "2026-11-22T03:10:00Z",
  "source_version": "v3.0",
  "product_variant": "rnl",
  "license": "open-with-attribution (verificar aviso CHC)",
  "attribution_text": "CHIRPS v3, Climate Hazards Center, UC Santa Barbara",
  "native_resolution": "0.05 deg",
  "effective_resolution": "pentadal",
  "crs": "EPSG:4326",
  "transform": "clip(bbox=[-90.2,13.1,-87.6,14.5])",
  "sha256": "1769f6f4fffe…",
  "bytes": 14000124,
  "qa": {"nodata_declared": false, "mask_applied": "-9999", "nulls": null},
  "status": "VERIFIED"
}
```

`effective_resolution` es obligatorio y distinto de `native_resolution`: impide
publicar precisión falsa.

---

## 5. Tamaños y necesidades de almacenamiento

| Activo | Tamaño observado / estimado | Nota |
|---|---|---|
| Capas procesadas Fase 1 | ~150 MB | Ya versionadas |
| Crudos Fase 1 | ~420 MB | Regenerables |
| Muestra CHIRPS diaria global | **14,0 MB/día** | ~5,1 GB/año sin recortar |
| CHIRPS recortado a SV | ~50–200 KB/día | El recorte es la diferencia entre viable y no viable |
| Copernicus DEM 30 m (tiles SV) | ~23 MB por tile; ~200 MB el país | Ya procesado |
| OSM shapefiles SV | **88,1 MB** | PBF no disponible hoy |
| Nemotron parquet completo | **542 MB** | No se descarga; solo estadísticas y filas |
| SoilGrids por propiedad × profundidad (SV) | < 1 MB recortado | WebDAV + recorte |
| Serie NDVI 10 m por AOI | ~4 MB por banda y fecha | Archivar índices, no reflectancia |
| Muestras Fase 3 | **2,9 MB** (sin CHIRPS) + 14 MB CHIRPS | Ver manifiesto |

**Conclusión:** el país completo en índices decenales es manejable en disco
local; el país completo en reflectancia multiespectral **no**. La arquitectura
debe archivar índices y metadatos, no escenas.

---

## 6. Almacenamiento externo

| Opción | Uso propuesto | Condición |
|---|---|---|
| Disco local del proyecto | Desarrollo, capas procesadas pequeñas | Ninguna |
| Almacenamiento en bloque del usuario | Crudos y series climáticas | Propiedad del usuario |
| Zenodo / OSF | Publicación de datasets derivados con DOI | Licencia compatible |
| S3/R2 compatible | Servir COG y teselas | Coste operativo; no obligatorio |
| Git LFS | **No recomendado** para rásteres de decenas de MB | Duplica el repositorio |

**Regla:** si un dataset no puede publicarse por licencia, no se sube a un
servicio público aunque sea técnicamente posible.

---

## 7. Ciclo de vida

1. **Ingesta:** descarga a `raw/<tema>/`, hash, manifiesto.
2. **Validación:** CRS, resolución, nulos, extensión, duplicados.
3. **Transformación:** recorte, reproyección, agregación; se registra el comando.
4. **Publicación:** `processed/` o `derived/` + `.provenance.json`.
5. **Caducidad:** cada fuente tiene fecha de verificación; al vencer, se repite
   la sonda (R-10).
6. **Retención:** los crudos se conservan mientras la licencia lo permita; si no,
   se conserva solo el manifiesto y la receta de descarga.

---

## 8. Qué no se guarda

- Escenas Sentinel completas.
- Series globales sin recortar (CHIRPS, ERA5) más allá de la muestra.
- Parquet completo de Nemotron.
- Duplicados de capas ya procesadas.
- PDF institucionales redistribuibles solo si la licencia lo permite; en caso
  contrario, solo URL + hash + fecha.
