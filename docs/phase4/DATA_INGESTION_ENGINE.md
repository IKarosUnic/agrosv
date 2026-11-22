# Motor de ingestión de datos

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/ingest.py` · Pruebas: `tests/test_data_ingest.py`

## 1. Objetivo

Incorporar datos de forma **reproducible, verificable y reanudable**, sin volver
a descargar lo idéntico y sin cargar un ráster completo en memoria. El motor no
interpreta ciencia: identifica formato, calcula integridad, extrae metadatos,
deduplica y deja un manifiesto. La validación científica es otra etapa.

```
fuente local / URL autorizada
        │
        ▼
detect_format ──► integridad (tamaño, sha256, legibilidad)
        │
        ▼
almacén por contenido (raw/_objects/aa/bb/<sha256>)
        │
        ├── manifiesto JSON (metadatos + hashes)
        ├── registro en ingest_log.jsonl
        └── estado del lote (reanudación)
```

## 2. Formatos

`Format` cubre: GeoJSON, Shapefile, GeoPackage, GeoTIFF/COG, CSV, Parquet,
NetCDF, Zarr, JSON y servicios OGC. La detección combina extensión **y**
contenido:

| Formato | Cómo se reconoce | Metadatos extraídos |
|---|---|---|
| GeoJSON | JSON con `FeatureCollection`/`Feature` | nº features, tipos de geometría, CRS declarado |
| Shapefile | `.shp` + archivos auxiliares | capa, CRS, extensión |
| GeoPackage | cabecera SQLite `SQLite format 3` + tablas gpkg | capas, CRS, recuento |
| GeoTIFF/COG | cabecera TIFF vía rasterio | ancho, alto, bandas, dtype, CRS, transform, nodata, bounds |
| CSV | texto delimitado detectable | columnas, filas, delimitador |
| JSON | JSON válido sin claves geoespaciales | tipo, claves |
| Parquet | firma `PAR1` | limitado: sin pyarrow no hay esquema completo |
| NetCDF | firma HDF5/CDF | limitado: sin xarray no se listan variables |
| Zarr | directorio con `.zgroup`/`.zarray` | limitado: sin zarr no se inspecciona |
| OGC | URL de servicio | detectado, no rastreado automáticamente |

Una extensión incoherente no se «corrige» en silencio: `FormatDetection`
(`format`, `extension`, `matches_extension`) lo reporta. Un `.json` con CSV
dentro se registra como CSV y con `matches_extension=false`.

**Limitación real:** el entorno de Fase 4 no tiene `pyarrow`, `xarray` ni `zarr`.
Parquet, NetCDF y Zarr se detectan y se registran, pero su esquema profundo no se
extrae. No se finge lo contrario; está en `DATA_INTEGRATION_STATUS.md`.

## 3. Integridad

`IntegrityCheck` verifica: existencia, tamaño > 0, sha256, y legibilidad según
formato. `ingest_local()`:

1. detecta formato;
2. calcula sha256 y compara con `expected_sha256` si se proporcionó;
3. si el hash ya existe en el almacén, devuelve `DUPLICATE` **sin copiar** y
   escribe igualmente el manifiesto (la evidencia de la segunda importación no se
   pierde);
4. si es nuevo, copia a `raw/_objects/<aa>/<bb>/<sha256>` y escribe manifiesto.

Resultado (`IngestRecord`): `status` (`INGESTED`, `DUPLICATE`, `FAILED`),
`artifact_id`, `sha256`, `bytes`, `format`, `stored_path`, `manifest_path`,
`metadata`.

Un hash distinto del esperado lanza `IntegrityError` **antes** de copiar. Un
archivo vacío también. No se registra como «importado» lo que no pasó el control.

## 4. Deduplicación

El almacén es direccionado por contenido. Dos archivos con el mismo contenido y
distinto nombre producen un solo objeto. Prueba:
`test_segunda_ingesta_identica_no_duplica` verifica que el almacén contiene un
único blob y que el segundo registro es `DUPLICATE`.

Esto responde a la regla «no descargar nuevamente datasets idénticos»: la
identidad es el contenido, no la URL ni el nombre.

## 5. Descarga autorizada

`IngestEngine.download()` exige una lista explícita de hosts (`allow_hosts`).
Un host fuera de la lista lanza `HostNotAllowed` **antes** de tocar la red.

- Usa `GET` con streaming por bloques; no carga el archivo en RAM.
- Consulta `HEAD` para ETag/Content-Length cuando el cliente lo permite.
- Mantiene `data/manifests/download_ledger.json` con URL, ETag, tamaño, sha256 y
  fecha.
- Si el contenido descargado coincide con el del ledger, devuelve `SKIPPED` y no
  reescribe el archivo.
- No hay scraping: solo URLs declaradas y permitidas por la fuente.

## 6. Reanudación y lotes

`ingest_batch(items, job_name, resume=True)` procesa una lista de trabajos y
guarda el estado en `data/manifests/<job>_state.json`. Cada ítem tiene
`item_id`. Al reanudar:

- los ítems `ok` se omiten y se marcan `resumed: true`;
- los `failed` se reintentan;
- el lote se puede repetir sin duplicar objetos.

Prueba real: primer lote con un archivo válido y uno ausente → `ok=1`,
`failed=1`; se crea el archivo faltante; segundo lote → `all_ok`, y el ítem
bueno figura como reanudado.

## 7. Errores

`ingest_log.jsonl` es un registro append-only con `stage`, `error`, `path`,
`item_id` y fecha. `pipeline.monitoring_report()` lee los últimos errores y los
publica. Un fallo no se convierte en «0 observaciones»: queda escrito.

## 8. Rásteres sin cargar todo

La extracción de metadatos abre la cabecera con rasterio y lee únicamente
ventanas/bloques (`raster.iter_blocks`, `read_window`). El perfil incluye ancho,
alto, CRS, transform, nodata, resolución nativa, área de píxel y estimación de
tamaño. La prueba `test_raster_se_inspecciona_sin_cargarlo` verifica que un
GeoTIFF de prueba se registra por cabecera, sin leer la matriz completa.

## 9. Lo que este motor no hace

- No valida calidad científica (eso es `quality.py`).
- No reproyecta ni remuestrea (eso es `raster.py` / `geo.py`).
- No convierte unidades (eso es `units.py`).
- No descarga de portales que exigen autenticación interactiva ni evade
  restricciones: esos datasets quedan `RESTRICTED` o `ACCESS_PENDING`.
- No garantiza que un formato declarado sea el real más allá de la firma
  detectable; por eso el manifiesto conserva el formato detectado y la extensión.
