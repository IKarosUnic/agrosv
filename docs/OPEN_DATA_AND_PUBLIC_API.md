# Open Data and Public API

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Define qué datos de AGROSV son públicos, bajo qué licencia, en qué formato y con
qué límites. Un dato restringido **no** se publica «porque está en el servidor».

---

## 1. Clasificación de publicación

| Clase | Qué incluye | Acceso | Licencia de salida |
|---|---|---|---|
| **Público abierto** | límites, relieve, hidrografía OSM, vías, cobertura derivada | sin auth | CC BY 4.0 (derivados propios) |
| **Público agregado** | censos por departamento/municipio, aptitud por celda | sin auth | CC BY 4.0 con cita |
| **Restringido por fuente** | WorldClim, GAEZ, AgERA5, SoilGrids derivados | sin redistribución del original | solo resultados, no archivos |
| **Privado** | parcelas, reportes comunitarios, datos personales | propietario | no se publica |
| **No disponible** | datos de terceros sin licencia | — | no se sirve |

Regla: la API nunca sirve un archivo de una fuente que prohíbe redistribución.
Sirve **resultados derivados** con atribución y método.

---

## 2. Endpoints públicos (diseño)

```
GET /api/v1/meta                          versión, fuentes, fecha de datos
GET /api/v1/territory/departments
GET /api/v1/territory/municipalities?dept=
GET /api/v1/terrain/elevation?lat=&lon=
GET /api/v1/terrain/hillshade/{z}/{x}/{y}.png
GET /api/v1/hydro/waterways?bbox=
GET /api/v1/roads?bbox=&class=
GET /api/v1/soils?lat=&lon=
GET /api/v1/climate/normals?lat=&lon=&period=
GET /api/v1/alerts?level=department&status=vigente
GET /api/v1/aptitude?crop=maiz&bbox=
GET /api/experiments/{id}/export          (solo públicos)
```

Los endpoints existentes de Fase 1 (`/api/health`, `/api/territory`, teselas,
`/api/point`) **se conservan**; `/api/v1` es una capa de versión, no un reemplazo
inmediato.

---

## 3. Formatos

| Tipo | Formato | Nota |
|---|---|---|
| Vectorial | GeoJSON (RFC 7946) | EPSG:4326 |
| Raster | COG (GeoTIFF) | tiles y descarga |
| Series | CSV + JSON | unidades explícitas |
| Clima | NetCDF / Zarr (cuando aplique) | chunking por mes |
| Metadatos | JSON-LD con `prov` | procedencia |

Cada respuesta incluye cabeceras:

```
X-AGROSV-Version: 2.0
X-AGROSV-Data-Date: 2026-11-01
X-AGROSV-Provenance: <provenance_id>
X-AGROSV-License: CC-BY-4.0 | derived-only | private
```

---

## 4. Límites y uso aceptable

| Límite | Valor propuesto |
|---|---|
| Peticiones/min por IP | 60 |
| Tamaño de `bbox` | ≤ 0,5° × 0,5° |
| Registros por página | ≤ 1.000 |
| Descarga raster | tiles o COG por escena, no país completo |
| Reintentos | backoff exponencial |

Sin SLA en Fase 2. No se promete disponibilidad 24/7.

---

## 5. Paquetes offline

Para conectividad limitada:

```
agrosv-package-<dept>-<version>.zip
  metadata.json        (versión, fecha, licencias, hashes)
  territory.geojson
  terrain_hillshade.tif
  climate_normals.csv
  soils_summary.csv
  README.md
```

Límite propuesto: ≤ 500 MB por departamento. Se genera por lote, se versiona y
se publica con hash. No incluye datos privados ni fuentes no redistribuibles.

---

## 6. Versionado y compatibilidad

- `v1` estable; cambios incompatibles ⇒ `v2` con solapamiento ≥ 6 meses.
- Campos nuevos son aditivos; no se renombran sin deprecación.
- Cada dataset tiene `dataset_version` y fecha de corte.

---

## 7. Validación

| Prueba | Criterio |
|---|---|
| Licencia | ninguna respuesta viola la licencia de la fuente |
| Cabeceras | 100 % de respuestas con versión, fecha y procedencia |
| Límites | rate limit y tamaño de bbox efectivos |
| Formato | GeoJSON válido; COG legible por GDAL |
| Reproducibilidad | mismo `dataset_version` ⇒ mismo hash |
| Privacidad | ningún endpoint público devuelve parcelas o personas |

---

## 8. Limitaciones

1. Muchas fuentes son no comerciales: la API pública no puede ser un espejo.
2. El rate limit es una protección, no una garantía de servicio.
3. Los paquetes offline quedan desactualizados; llevan fecha y versión.
4. La API no sustituye los portales oficiales (MAG, MARN, CNR).

---

## 9. Dependencias y prioridad

Depende de: Data Provenance Engine, versionado, Module A/C para derivados.

**Prioridad:** media-alta. Publicar lo que ya existe (territorio, relieve,
hidrografía) es barato y da valor inmediato; el resto llega con cada módulo.
