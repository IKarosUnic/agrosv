# Arquitectura de datos ráster

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/raster.py` · Catálogo: `data/metadata/raster_catalog.json` · Pruebas: `tests/test_raster_temporal.py`, `tests/test_phase4_performance.py`

## 1. Reglas

1. La **resolución nativa** y la **resolución efectiva** se declaran por separado.
2. No se aumenta la resolución de una fuente: un ráster de 250 m no se convierte
   en «30 m» por remuestreo. `plan_reproject()` lanza `ResolutionInflationError`
   si se pide una resolución más fina que la nativa.
3. Todo remuestreo se registra con método, resolución de origen y destino, y se
   marca `degraded: true`.
4. El producto original se conserva. Los derivados van a `processed/` o
   `derived/`, nunca sobrescriben `raw/`.
5. Los rásteres grandes se procesan por **ventanas o bloques**; no se cargan
   completos en RAM.

## 2. Catálogo real (13 rásteres)

| Dataset | Variable | CRS | Resolución | dtype | NoData |
|---|---|---|---|---|---|
| copdem30 | `dem30_wgs84` | EPSG:4326 | 0,000277…° (30 m) | float32 | −32768 |
| copdem30 | `slope_deg` | EPSG:32616 | 30 m | int16 | −32768 |
| copdem30 | `aspect_deg` | EPSG:32616 | 30 m | uint16 | 65535 |
| copdem30 | `hillshade` | EPSG:32616 | 30 m | uint8 | 0 |
| copdem30 | `relief_class` | EPSG:32616 | 30 m | uint8 | 255 |
| soilgrids_2 | phh2o 0–30 cm | EPSG:32616 | 250 m | int16 | −32768 |
| soilgrids_2 | soc 0–30 cm | EPSG:32616 | 250 m | int16 | −32768 |
| soilgrids_2 | nitrogen 0–30 cm | EPSG:32616 | 250 m | int16 | −32768 |
| soilgrids_2 | clay 0–30 cm | EPSG:32616 | 250 m | int16 | −32768 |
| soilgrids_2 | sand 0–30 cm | EPSG:32616 | 250 m | int16 | −32768 |
| soilgrids_2 | silt 0–30 cm | EPSG:32616 | 250 m | int16 | −32768 |
| chirps3 | precipitación global (muestra) | EPSG:4326 | 0,05° (~5,5 km) | float32 | **None** |
| chirps3 | precipitación recortada SV | EPSG:4326 | 0,05° | float32 | **None** |

Datos de tamaño: DEM 91 MB; los seis SoilGrids suman ~1 MB; la muestra CHIRPS
global 14 MB. El catálogo guarda ruta, bytes, CRS, resolución, dtype, nodata,
bounds y una recomendación de contenedor.

## 3. Resolución nativa vs efectiva

`RasterProfile.as_dict()` describe la fuente con estos campos (ejemplo SoilGrids):

```json
{
  "driver": "GTiff",
  "crs": "EPSG:32616",
  "res": [250.0, 250.0],
  "dtype": "int16",
  "nodata": -32768.0,
  "nodata_declared": true,
  "pixel_area_m2": 62500.0,
  "tiled": true,
  "block_shape": [512, 512],
  "overviews": [2, 4, 8],
  "cog_heuristic": true,
  "cog_notes": []
}
```

La resolución nativa es `res`; no se convierte en una cadena «efectiva» hasta
que existe una operación de remuestreo. `ResampleOperation` declara entonces
`native_resolution`, `effective_resolution`, `degraded`, `method`, `source_res`
y `target_res`. Ejemplo real de CHIRPS a 6 km:

```json
{
  "native_resolution": "0.05",
  "effective_resolution": "6000 (remuestreado desde 0.05)",
  "degraded": true,
  "method": "average",
  "rule": "un producto remuestreado nunca declara la resolución nativa de la fuente"
}
```

Un derivado nunca hereda la etiqueta de nativo.

## 4. NoData

- Se lee de la cabecera. Si es `None`, no se asume 0.
- `undeclared_nodata_candidates()` escanea una muestra y reporta centinelas
  sospechosos (`-9999`, `-32768`, etc.) **sin** reescribir la cabecera.
- Caso real: CHIRPS declara `nodata=None` y contiene valores `-9999`. El catálogo
  lo marca con `nodata_candidates` y el informe de calidad lo advierte. No se
  convierte silenciosamente: el recorte conserva el valor y la advertencia.
- Un cero puede ser un dato válido (día sin lluvia). `check_missing_vs_zero()` y
  el motor de calidad los distinguen.

## 5. Procesamiento por bloques

- `iter_blocks(path)` recorre ventanas alineadas con los bloques internos del
  archivo; devuelve `(window, array)` y nunca la matriz completa.
- `read_window(path, bounds)` lee solo la intersección geográfica.
- `window_stats()` calcula mínimo, máximo, media y nº de celdas válidas de una
  ventana.
- `safe_block(size)` elige un tamaño de bloque teselado válido (múltiplo de 16,
  ≤512) para no generar GeoTIFF inválidos en recortes pequeños.

Pruebas de rendimiento: una ventana de ~6×6 km del DEM se lee en <2 s y ocupa
mucho menos que el archivo; una ventana de CHIRPS no materializa el mundo
(`test_bloques_de_chirps_no_cargan_el_mundo`). Los umbrales son holgados: buscan
detectar un cambio de orden de magnitud, no un benchmark fino.

## 6. Reproyección y remuestreo

`plan_reproject(path, target_crs, target_res=None, method=None, reason=...)`:

- calcula resolución de origen y destino;
- rechaza `target_res` más fina que la nativa;
- exige método declarado (`nearest`, `bilinear`, `cubic`, `average`, `mode`, …)
  cuando hay remuestreo;
- devuelve un `ResampleOperation` con `degraded`, `reason`, `method`, `factor`;
- `reproject_to_file()` ejecuta el plan y escribe un archivo nuevo.

`clip_to_file()` recorta por extensión y declara `resampling: "none"`. Es la
operación usada con CHIRPS: se conserva la resolución y no se interpola.

## 7. Rejillas compatibles

`assert_same_grid([...])` compara CRS, transform, ancho, alto y resolución.
Devuelve `{ok, problems}`. Es requisito antes de combinar dos rásteres píxel a
píxel; dos capas «en 4326» pueden tener rejillas distintas.

## 8. Contenedores

`choose_container(temporal, variables, access)`:

| Caso | Recomendación |
|---|---|
| una variable, acceso por ventana | COG (GeoTIFF teselado con overviews) |
| serie temporal, muchas variables, acceso paralelo | Zarr |
| serie temporal, muchas variables, acceso secuencial | NetCDF |

Es una **decisión documentada**, no una conversión automática. El catálogo
registra la recomendación por ráster. En Fase 4 los archivos siguen en GeoTIFF:
convertirlos sin necesidad duplicaría almacenamiento y añadiría una dependencia
no instalada (Zarr/NetCDF).

## 9. COG

`cog_heuristic` se calcula por heurística: driver GTiff, teselado, overviews y
tamaño de bloque.
No se afirma «COG válido» sin validación con `rio cogeo` u otra herramienta
específica; el catálogo dice `cog_heuristic`. CHIRPS es una franja sin overviews:
no es COG y se declara así.

## 10. Limitaciones

- No se ha calculado incertidumbre por píxel para ningún ráster.
- Pendiente, aspecto y relieve se derivaron en EPSG:32616 a 30 m; siguen siendo
  derivados de un DEM de 30 m, no mediciones de campo.
- SoilGrids es una **predicción** global a 250 m; el archivo local está en la
  rejilla UTM 16N de Fase 1 y no cubre necesariamente todo el país.
- La muestra CHIRPS es de un día; no constituye una serie climática nacional.
- La conversión a COG/Zarr queda recomendada, no ejecutada.
