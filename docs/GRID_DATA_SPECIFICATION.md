# Especificación de datos en grilla — AGROSV

**Versión:** 1.0 · **Fecha:** 2026-11-21
**Aplica a:** clima (CHIRPS, AgERA5, ERA5), suelos (SoilGrids), topografía
derivada y cualquier futura variable rasterizada.

Regla fundacional: **no se combinan fuentes de distinta resolución sin
conservar la resolución original**. Un producto agregado es una capa nueva,
declarada como derivada, nunca un reemplazo silencioso.

---

## 1. Identificador de celda

Cada celda de cada grilla tiene un identificador estable e independiente de la
fuente:

```
{grid_id}:{row}:{col}
```

- `grid_id` describe **la grilla**, no la variable: `chirps3-005`, `agera5-01`,
  `era5-025`, `soilgrids-250-igh`, `agrosv-utm16-30`.
- `row`/`col` son índices enteros en el orden de la grilla de origen (fila 0 =
  norte).
- El identificador **no** codifica la fecha: una celda es una geometría; el
  valor pertenece a una observación.

Registro de grillas (`grid_registry`):

| grid_id | CRS | Resolución | Origen | Ancla | Tamaño |
|---|---|---|---|---|---|
| `chirps3-005` | EPSG:4326 | 0,05° | CHIRPS v3 | −180, 60 | 7.200 × 2.400 |
| `agera5-01` | EPSG:4326 | 0,1° | AgERA5 | −180, 90 | 3.600 × 1.800 |
| `era5-025` | EPSG:4326 | 0,25° | ERA5 | −180, 90 | 1.440 × 720 |
| `soilgrids-250-igh` | Goode Homolosine | 250 m | SoilGrids 2.0 | VRT maestro | 159.246 × 58.034 |
| `agrosv-utm16-30` | EPSG:32616 | 30 m | AGROSV (topografía) | 155.000 E / 1.600.000 N | 9.217 × 5.516 |

---

## 2. Registro de observaciones (modelo lógico)

Toda celda-fecha-variable se describe con la misma estructura, sea NetCDF,
Zarr o COG:

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `cell_id` | text | sí | `{grid_id}:{row}:{col}` |
| `grid_id` | text | sí | grilla de origen |
| `lon`, `lat` | float | sí | centroide de la celda en EPSG:4326 |
| `x`, `y` | float | no | centroide en el CRS nativo de la grilla |
| `source_id` | text | sí | p. ej. `chirps3`, `agera5` |
| `variable` | text | sí | `precip`, `t2m`, `rh`, `rs`, `wind10`, `et0`, … |
| `unit` | text | sí | `mm`, `°C`, `%`, `W/m²`, `m/s`, `mm/día` |
| `date` | date | sí | fecha del dato (día local para AgERA5) |
| `value` | float | sí | valor; `NULL` si falta |
| `quality` | smallint | sí | 0 = faltante, 1 = preliminar, 2 = final, 3 = validado |
| `uncertainty` | float | no | desviación o intervalo, en la unidad de `value` |
| `native_resolution` | text | sí | «0,05°», «250 m», «30 m» |
| `derived_from` | text[] | no | `source_id` de las entradas si es derivado |
| `provenance_id` | text | sí | enlace al manifiesto |
| `ingested_at` | timestamptz | sí | fecha de carga |

**Nunca** se guarda un valor agregado sin `native_resolution` y
`derived_from`: es lo que impide presentar un promedio de 0,25° como si fuera
de 5 km.

---

## 3. Formatos: evaluación y decisión

| Formato | Ventaja | Límite | Uso en AGROSV |
|---|---|---|---|
| **NetCDF (CF-1.8)** | estándar científico, metadatos ricos, multidim | lectura por ventana irregular limitada; requiere xarray | **formato de archivo** de series diarias por variable/año |
| **Zarr** | chunks, lectura paralela, ideal en la nube | ecosistema más joven; no todos los SIG lo abren | **cubos de análisis** (clima histórico multi-variable) |
| **COG** | un archivo, overviews, lectura por rango, GDAL nativo | una banda por archivo o multibanda sin CF | **capas servidas al mapa** y rásteres estáticos (DEM, suelos) |

Decisión:

1. **Ingesta**: se conserva el archivo original de la fuente (NetCDF/GeoTIFF) en
   `data/raw/`, inmutable.
2. **Almacén de análisis**: Zarr chunked `(time, y, x)` con chunks de 1×256×256
   para clima diario; un grupo por variable y por grilla.
3. **Servicio**: COG por variable-mes para el mapa; el API lee por ventana.
4. **Nunca** se republica un NetCDF como si fuera un COG ni al revés.

---

## 4. Preservación de resolución

- Cada capa declara `native_resolution` y `effective_resolution`. Si se
  remuestrea (p. ej. AgERA5 0,1° → rejilla de 1 km para el visor), la capa
  resultante es **derivada**, lleva `derived_from` y en la UI muestra la
  resolución efectiva más gruesa de sus insumos.
- Prohibido: promediar CHIRPS (0,05°) y AgERA5 (0,1°) en una única «precipitación
  AGROSV» sin declarar que el resultado es 0,1°.
- Comparaciones entre resoluciones se hacen por **agregación a la más gruesa**,
  nunca por interpolación a la más fina para «igualar».

---

## 5. Consultas requeridas

| Consulta | Entrada | Salida |
|---|---|---|
| Por coordenada | `lat`, `lon`, `variable`, `date_from`, `date_to` | serie de la celda que contiene el punto, con `native_resolution` |
| Por parcela | geometría (`Polygon`) | media ponderada por área de celdas intersectadas + n celdas + % de cobertura |
| Por municipio | `adm1_code` / código municipal | agregado por municipio, declarando la resolución de origen |
| Por departamento | `adm1_code` (ISO 3166-2:SV) | agregado departamental |
| Por región agrícola | `region_code` | agregado; `PENDING_VALIDATION` hasta tener límites MAG |

Reglas de agregación espacial:

- **Precipitación**: media ponderada por área (no suma).
- **Temperatura**: media ponderada; mínimas/máximas se agregan por extremos, no
  por promedio de promedios.
- **Eventos extremos**: se agregan por umbral y conteo (días > 50 mm), no por
  promedio.
- Toda respuesta incluye `cells_used`, `coverage_pct` y
  `native_resolution`; si `coverage_pct < 0.8`, la respuesta se marca
  `partial: true`.

---

## 6. Particionado y nombres

```
data/processed/climate/
  chirps3/
    precip/
      year=2024/
        chirps3_precip_2024.zarr/        # análisis
        chirps3_precip_2024-01.tif       # COG para el mapa
  agera5/
    t2m/  rh/  rs/  wind10/  et0/
  derived/
    spi3/  spei3/  water_balance/
```

- Un directorio por `grid_id` y variable; nunca se mezclan grillas.
- Los derivados viven en `derived/` y siempre declaran sus insumos.
- Nombres en minúsculas, sin acentos, con la fecha en ISO 8601.

---

## 7. Calidad e incertidumbre

| Nivel | Significado |
|---|---|
| 0 | faltante (no se interpola para publicar) |
| 1 | preliminar de la fuente (CHIRPS preliminar, CAP preliminar) |
| 2 | final de la fuente |
| 3 | validado por AGROSV contra observación independiente |

- La incertidumbre se propaga: un índice calculado sobre dos fuentes toma la
  mayor de las incertidumbres declaradas y lo indica.
- Los faltantes **no se rellenan** con climatología para publicar mapas: se
  muestran como vacío y se informa el porcentaje.

---

## 8. Contrato mínimo de la API de grillas (diseño, no implementado)

```
GET /api/grid/cells?lat=&lon=&variable=&from=&to=
GET /api/grid/aggregate?level=department&code=SV-SS&variable=precip&from=&to=
GET /api/grid/aggregate?geometry=<GeoJSON>&variable=precip&from=&to=
GET /api/grid/registry
```

Toda respuesta:

```json
{
  "variable": "precip",
  "unit": "mm",
  "grid_id": "chirps3-005",
  "native_resolution": "0.05 deg",
  "source_id": "chirps3",
  "quality": 2,
  "provenance_id": "chirps3@2026-11-21T00:00:00Z",
  "partial": false,
  "cells_used": 12,
  "coverage_pct": 1.0
}
```

---

## 9. Pruebas exigidas antes de publicar una grilla

1. Identificadores únicos (`cell_id` + `date` + `variable`).
2. Sin valores fuera de rango físico (precipitación ≥ 0; humedad 0–100 %;
   temperatura −5…45 °C para SV).
3. Cobertura declarada = cobertura medida.
4. Suma de celdas intersectadas ≈ área del polígono (± 2 % en la proyección
   equal-area).
5. Series sin duplicados de fecha ni huecos silenciosos.
6. Reproyección ida y vuelta < 1 m en coordenadas.
7. Toda capa tiene manifiesto y `native_resolution`.

---

## 10. Lo que esta especificación no resuelve

- No define el modelo de datos de **pronóstico** (Google Weather): no es una
  grilla y sus términos prohíben almacenarlo como si lo fuera. Ver
  `WEATHER_CLIMATE_ENGINE.md`.
- No fija la grilla común definitiva: cada fuente conserva la suya. Una grilla
  nacional de 1 km sería un **producto derivado** futuro, con su propio ADR.
- No incluye asimilación de datos ni reanálisis propio.
