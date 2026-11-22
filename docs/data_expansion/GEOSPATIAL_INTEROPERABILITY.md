# GEOSPATIAL_INTEROPERABILITY — AGROSV Fase 3

**Fecha:** 2026-11-22 · **Objetivo:** que cualquier capa pueda cruzarse con otra
sin perder resolución, procedencia ni significado.

---

## 1. Sistemas de referencia

| Uso | CRS | Motivo |
|---|---|---|
| **Almacenamiento y API** | **EPSG:4326** (WGS 84, grados) | Estándar de intercambio; compatible con GeoJSON y STAC |
| Análisis nacional | **EPSG:32615 / 32616** (UTM 15N / 16N) | Distancias y áreas en metros |
| Áreas y pendientes | UTM del huso correspondiente | Evitar distorsión de grados |
| Rásteres globales | EPSG:4326 en origen | No reproyectar sin declararlo |
| Altitud | EGM2008 (Copernicus DEM) | No mezclar con altitud elipsoidal |

**Regla:** la capa publicada conserva el CRS de origen en el manifiesto y se
reproyecta solo en la salida. Nunca se sobrescribe el original.

El Salvador se divide entre los husos 15N (mayoría) y 16N (extremo este). Una
reproyección nacional única a 15N introduce error creciente hacia el este; para
áreas, usar el huso local.

---

## 2. Rejillas y resoluciones

| Rejilla | Resolución | Uso | No usar para |
|---|---|---|---|
| CHIRPS | 0,05° (~5,5 km) | Precipitación acumulada pentadal/mensual | Eventos diarios locales |
| AgERA5 | 0,1° (~11 km) | ET₀ y balance hídrico | Gradientes topográficos |
| SoilGrids | 250 m | Prior de suelo | Propiedad de parcela |
| Copernicus DEM | 30 m | Pendiente, hidrología | Microrelieve |
| Sentinel-2 | 10/20/60 m | Índices de vegetación | Identificación de cultivo sin campo |
| Catastro/ortofoto | ≤ 1 m (si se obtiene) | Parcela | Series temporales (no hay) |

**Prohibición:** remuestrear una capa de 250 m a 10 m y presentarla como
«suelo a 10 m». El remuestreo se documenta como interpolación, no como precisión.

---

## 3. Identificadores territoriales

```
SV                    país (ISO 3166-1 alpha-2)
SV-AH                 departamento (ISO 3166-2)
SV-AH-01              municipio (44, reforma 2023) — esquema propuesto
SV-AH-01-03           distrito (262) — esquema propuesto
```

| Campo | Obligatorio | Nota |
|---|---|---|
| `territory_id` | Sí | Esquema AGROSV estable |
| `source_gid` | Sí | Identificador original de la fuente |
| `name_official` | Sí | Nombre según la fuente |
| `valid_from` / `valid_to` | Sí | La reforma 2023 exige vigencias |
| `level` | Sí | country / department / municipality / district |
| `official` | Sí | `true` solo si la fuente es oficial |

**Tabla de correspondencia obligatoria** (`data/metadata/territory_crosswalk.csv`):
`district_id`, `district_name`, `municipality_2023`, `department`, `source`,
`valid_from`. Sin ella no se une ningún tabulado a una geometría.

---

## 4. Tiempo

| Concepto | Formato | Ejemplo |
|---|---|---|
| Fecha | ISO 8601 | `2026-11-22` |
| Fecha-hora | ISO 8601 con zona | `2026-11-22T03:10:00Z` |
| Año agrícola | `AAAA-AAAA` (mayo–abril) | `2024-2025` |
| Pentada CHIRPS | `AAAA-PNN` | `2026-P03` |
| Campaña | `primera` / `postrera` / `apante` | — |
| Vigencia territorial | `valid_from` / `valid_to` | `2023-05-01` / — |

**Regla:** una serie que cruce el 2023 (reforma territorial) debe declarar el
cambio de unidad geográfica; no se compara «municipio 2023» con «municipio 2019»
sin tabla de correspondencia.

---

## 5. Unidades

| Magnitud | Unidad canónica | Conversión declarada |
|---|---|---|
| Superficie | hectárea (ha) | 1 mz = 0,6989 ha |
| Producción | tonelada (t) | 1 qq = 45,36 kg |
| Precipitación | mm | — |
| Temperatura | °C | — |
| Evapotranspiración | mm/día o mm/campaña | — |
| Caudal | m³/s | — |
| Concentración | mg/L | — |
| Precio | USD/unidad | Moneda USD |
| Pendiente | grados | — |

Cada respuesta de API incluye `units` explícito. No se devuelven números sin
unidad.

---

## 6. Formatos

| Formato | Uso | Ventaja |
|---|---|---|
| **GeoPackage** | Vectorial transaccional | Un archivo, sin shapefile frágil |
| **GeoJSON** | API y web | Legible, estándar |
| **COG (GeoTIFF)** | Ráster | Lectura por rango, sin descargar todo |
| **NetCDF / Zarr** | Clima multidimensional | Series temporales eficientes |
| **Parquet / GeoParquet** | Tablas y tablas geoespaciales | Compresión y tipos |
| **CSV** | Intercambio simple | Universal |
| **Shapefile** | Solo si la fuente lo exige | Limitaciones de campos y encoding |

**Nombre de campos:** `snake_case`, ASCII, ≤ 10 caracteres si el destino es
shapefile (documentar la abreviatura).

---

## 7. Metadatos

| Nivel | Estándar | Implementación |
|---|---|---|
| Catálogo | **DCAT** | Lista de datasets con licencia, cobertura y acceso |
| Ráster | **STAC 1.0** | Items con `bbox`, `datetime`, `assets`, `proj:epsg` |
| Vector | **ISO 19115 / 19139** o FGDC | Ficha por capa |
| Servicios | **OGC API – Features / Coverages**, WMS, WMTS | Publicación |
| Procedencia | W3C PROV + manifiesto AGROSV | `.provenance.json` |

Campos mínimos por capa: título, descripción, fuente, licencia, atribución,
CRS, resolución, cobertura, fecha, método, limitaciones, hash.

---

## 8. Contrato de cruce espacial

Para cruzar dos capas, AGROSV exige:

1. Mismo CRS de análisis (reproyectar a UTM local).
2. Declarar qué capa manda en la resolución (nunca «promediar resoluciones»).
3. `zonal_stats` con método explícito (media, mediana, moda, majority).
4. Registrar el porcentaje de píxeles válidos por polígono.
5. No extrapolar a polígonos con < 50 % de cobertura válida.
6. Guardar el resultado como `derived/`, con hash y receta.

**Ejemplo:** NDVI medio por municipio con Sentinel-2 10 m → se reporta también
el número de píxeles válidos y la fecha de la imagen. Un municipio nublado no
recibe un valor inventado: recibe `null`.

---

## 9. Compatibilidad con la arquitectura actual

| Elemento existente | Cómo se respeta |
|---|---|
| API Fase 1 (13 endpoints) | No se modifican; las capas nuevas entran por routers separados |
| `/api/v1` científica | Se reutiliza el contrato de procedencia y validación V0–V4 |
| `.provenance.json` | Se extiende con `effective_resolution` y `product_variant` |
| GeoPackage por licencia | Se mantiene: OSM separado, geoBoundaries separado |
| CRS de Fase 1 | Se conserva; las nuevas capas declaran su CRS de origen |

---

## 10. Estándares OGC considerados

| Estándar | Estado en AGROSV |
|---|---|
| OGC API – Features | Recomendado para capas vectoriales |
| OGC API – Coverages | Recomendado para ráster (evita WCS clásico) |
| STAC | Usado para satélite |
| WMS/WMTS | Solo para interoperar con visores institucionales |
| GeoPackage (OGC) | Formato vectorial por defecto |
| COG | Formato ráster por defecto |
