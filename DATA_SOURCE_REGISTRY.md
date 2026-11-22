# DATA_SOURCE_REGISTRY.md — AGROSV

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Método:** sondeo HTTP directo desde el entorno de trabajo, más lectura de documentación oficial.

> **Ampliación Fase 3 (2026-11-22):** este registro se complementa con
> [`docs/data_expansion/DATA_SOURCE_REGISTRY.md`](docs/data_expansion/DATA_SOURCE_REGISTRY.md),
> que añade 103 sondas nuevas, fuentes internacionales de relieve, hidrología y
> cobertura, y corrige afirmaciones que ya no se sostienen (SoilGrids
> `wv0033`/`wv1500`, ruta de Geofabrik, estado de los portales nacionales).
> Las filas de este archivo no se eliminan: las correcciones están señaladas en
> la sección §5 del registro de Fase 3.

---

## 1. Definición de estados

| Estado | Significado operativo |
|---|---|
| **VERIFIED** | Se ejecutó una petición real y se obtuvo contenido válido y utilizable. Se registra código HTTP, tamaño y naturaleza del contenido. |
| **DOCUMENTED** | Documentación oficial localizada y leída; no se probó acceso funcional a los datos. |
| **RESTRICTED** | El acceso existe pero requiere credenciales, registro, aceptación de licencia o permisos institucionales. |
| **UNAVAILABLE** | No se logró acceder por ningún medio probado. |
| **PENDING_VALIDATION** | Información insuficiente o contradicción entre documentación y comportamiento observado. |

**VERIFIED no significa "apto para producción".** Significa "el canal responde hoy". La idoneidad científica se evalúa por separado (§5).

---

## 2. Tabla maestra

| ID | Fuente | Cobertura SV | Resolución | Formato | Acceso | Licencia | Coste | Estado |
|---|---|---|---|---|---|---|---|---|
| `nemotron-sv` | Nemotron-Personas-El-Salvador (NVIDIA) | Nacional (14 dept., 44 mun.) | Persona sintética | Parquet | HF Hub API + Datasets Server | CC BY 4.0 | $0 | **VERIFIED** |
| `copdem30` | Copernicus DEM GLO-30 | Global | 30 m | COG GeoTIFF | AWS S3 abierto | Copernicus DEM (atribución obligatoria) | $0 | **VERIFIED** |
| `copdem90` | Copernicus DEM GLO-90 | Global | 90 m | COG GeoTIFF | AWS S3 abierto | Ibídem | $0 | **VERIFIED** |
| `soilgrids-rest` | SoilGrids 2.0 REST API | Global | 250 m | GeoJSON | `rest.isric.org` | CC BY 4.0 | $0 | **PENDING_VALIDATION** |
| `soilgrids-files` | SoilGrids 2.0 WebDAV | Global | 250 m | COG GeoTIFF + VRT | `files.isric.org` | CC BY 4.0 | $0 | **VERIFIED** |
| `chirps3` | CHIRPS v3 (UCSB CHC) | Global 60N–60S | 0,05° (~5,5 km) | GeoTIFF/BIL/NetCDF/COG | HTTP directo | Dominio público (verificar aviso) | $0 | **VERIFIED** |
| `era5-cds` | ERA5 / ERA5-Land (C3S) | Global | 0,25° / 0,1° | GRIB/NetCDF/Zarr | API CDS (`cdsapi`) | CC BY 4.0 | $0 | **RESTRICTED** |
| `open-meteo` | Open-Meteo (ERA5/ERA5-Land/IFS) | Global | 0,25° / 0,1° / 9 km | JSON | REST, sin clave | CC BY 4.0 (API) | $0 no comercial | **VERIFIED** |
| `google-weather` | Google Weather API | SV cubierto | Modelo Google | JSON | REST con clave | Google Maps Platform ToS | Por llamada | **RESTRICTED** (contractual) |
| `osm-geofabrik` | OpenStreetMap — extracto SV | Nacional | Vectorial | `.osm.pbf` | Descarga HTTP | ODbL 1.0 | $0 | **VERIFIED** |
| `osm-overpass` | Overpass API | Nacional | Vectorial | JSON | POST/GET | ODbL 1.0 | $0 (uso justo) | **VERIFIED** (con reserva) |
| `s2-l2a-stac` | Sentinel-2 L2A (Earth Search + AWS COG) | Global | 10/20/60 m | COG GeoTIFF | STAC + S3 abierto | Copernicus (CC BY 3.0 IGO modificada) | $0 | **VERIFIED** |
| `s2-cdse` | Sentinel Hub / CDSE | Global | 10 m | API de proceso | OAuth2 | Copernicus | $0 con cuenta | **RESTRICTED** |
| `geoboundaries` | geoBoundaries SLV ADM1/ADM2 | Nacional | Límites administrativos | GeoJSON/SHP | API REST | CC BY-SA 2.0 | $0 | **VERIFIED** |
| `bcr-cap2025` | V Censo Agropecuario y I de Pesca 2025 (BCR) | Nacional + 14 dept. | Dept./municipio | PDF + ArcGIS Hub | Portal web | **No declarada** | $0 | **VERIFIED** (acceso) / **RESTRICTED** (redistribución) |
| `mag-anuario` | Anuario de Estadísticas Agropecuarias (MAG/DGEA) | Nacional + 14 dept. | Dept./municipio | PDF | HTTP directo | No declarada | $0 | **VERIFIED** |
| `mag-costos` | Informe anual de costos de producción (MAG) | Nacional | Cultivo | PDF | HTTP | No declarada | $0 | **VERIFIED** |
| `centa-suelos` | Mapeo Digital de Suelos (CENTA) | Nacional | ~1:50.000 declarado | ArcGIS Hub | Portal web | No declarada | $0 | **PENDING_VALIDATION** |
| `wb-soils-sv` | Soil in El Salvador (Banco Mundial) | Nacional | Clasificación | Shapefile/Feature Service | Data Catalog | CC BY 4.0 | $0 | **DOCUMENTED** |
| `aquacrop` | FAO AquaCrop 7.3 | Modelo | — | Python + Fortran | GitHub / FAO | **Licencia propia FAO: «All rights reserved», uso no comercial previa solicitud** (ver §8.1) | $0 | **VERIFIED** |
| `dssat` | DSSAT CSM 4.8.6 | Modelo | — | Fortran + ejecutables | GitHub | BSD-3-Clause | $0 | **DOCUMENTED** |

---

## 3. Evidencia de verificación (sondeos ejecutados 2026-11-21)

Reproducible con `research/probe_sources.sh`.

### 3.1 Nemotron-Personas-El-Salvador — **VERIFIED**

```
GET https://huggingface.co/api/datasets/nvidia/Nemotron-Personas-El-Salvador   → HTTP 200, 3.731 B
GET .../parquet                                                               → HTTP 200, 3 shards
GET https://datasets-server.huggingface.co/size?dataset=nvidia%2F...          → HTTP 200
GET https://datasets-server.huggingface.co/statistics?dataset=nvidia%2F...    → HTTP 200, 15.479 B
```

Metadatos confirmados del propio servicio:

| Campo | Valor |
|---|---|
| `id` | `nvidia/Nemotron-Personas-El-Salvador` |
| `sha` (versión inmutable) | `68f6a21c17973d6a34ac6354d50a31c1fbcec14f` |
| `lastModified` | 2026-06-05 |
| `gated` | `false` — sin solicitud de acceso |
| `license` | `cc-by-4.0` |
| Filas / columnas | **148.000 / 25** |
| Tamaño parquet | 568.403.131 B (542 MiB) · en memoria 1.166.555.900 B (1,09 GiB) |
| Shards | `default/train/0.parquet`, `1.parquet`, `2.parquet` |
| Idioma | `es` (español salvadoreño) |
| Tags | `synthetic`, `sovereign-ai`, `el-salvador` |

**Linaje declarado por el editor:** generado con NeMo Data Designer (NVIDIA), modelo gráfico probabilístico propietario + `openai/gpt-oss-120b` (Apache-2.0). Anclado en el **VII Censo de Población y VI de Vivienda 2024** (BCR/ONEC, 6.029.976 personas) y en la **EHPM 2024** para la estructura ocupacional. Las ocupaciones son clases **CIIU Rev.4** (119 tipos) sobre 8 categorías de empleo censales.

**Distribuciones verificadas (calculadas sobre las estadísticas oficiales del Datasets Server, no estimadas):**

| Variable | Distribución observada |
|---|---|
| `area` | urbano 109.063 (73,69 %) · rural 38.937 (26,31 %) |
| `sex` | femenino 79.632 (53,81 %) · masculino 68.368 (46,19 %) |
| `age` | mín. 18 · máx. 100 · media 42,8 · mediana 40 |
| `department` | 14 valores; San Salvador 39.603 (26,76 %) … Cabañas 3.474 (2,35 %) |
| `municipality` | **44 valores** (coincide con la reforma territorial de 2023) |
| `country` | `El Salvador` en las 148.000 filas |
| `languages_spoken` | español 134.650 (90,98 %) · español e inglés 12.770 (8,63 %) |

**Perfiles con ocupación agrícola primaria** (CIIU sección A, división 01) — suma calculada por AGROSV sobre las frecuencias oficiales:

| Clase CIIU | Registros | % del total |
|---|---:|---:|
| Cultivo de cereales (excepto arroz), legumbres y semillas oleaginosas | 9.324 | 6,30 % |
| Cultivo de plantas con las que se preparan bebidas (café, cacao, té) | 1.950 | 1,32 % |
| Otras actividades agropecuarias | 1.806 | 1,22 % |
| Cultivo de productos agrícolas combinado con cría de animales (explotación mixta) | 1.532 | 1,03 % |
| Cultivo de hortalizas y melones, raíces y tubérculos | 966 | 0,65 % |
| Cría de ganado bovino y búfalos | 859 | 0,58 % |
| Cría de aves de corral | 851 | 0,57 % |
| Cultivo de caña de azúcar | 669 | 0,45 % |
| **Total división 01** | **17.957** | **12,13 %** |

Agroindustria asociada (no agrícola primaria): elaboración de azúcar 328, almidones 502, molinería 268, lácteos 693, cacao y chocolate 166.

**Consecuencia para AGROSV:** el conjunto de agentes agrícolas sintéticos disponible es de **~17.957 perfiles** (12,13 %). Es suficiente para simulación por departamento, **no** para representar los 401.101 productores de maíz del censo. La diferencia entre 17.957 y 401.101 no es un error: son universos distintos (población ocupada vs. unidades productivas, que incluyen productores de patio y familiares no remunerados). Debe declararse siempre.

**Limitaciones declaradas por el editor** (leídas del dataset card, no inferidas):
- Subrepresentación de identidades indígenas (Náhuat-Pipil, Lenca, Kakawira) y afrodescendientes.
- Supuestos de rol de género heredados del LLM narrativo.
- Español salvadoreño aproximado por el modelo generativo, no extraído de un corpus autorizado.
- Religión no modelada.
- **Independencia asumida:** ocupación independiente del nivel educativo, dado departamento, edad y sexo.
- Sin campos de nombre individual (mitigación de reidentificación).
- Solo adultos 18–100 años.
- **Sin campos de:** tamaño de finca, tenencia, ingreso, acceso a agua, crédito, superficie sembrada, activos.

### 3.2 Copernicus DEM GLO-30 — **VERIFIED**

```
GET https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N13_00_W090_00_DEM/...tif
→ HTTP 200, 22.877.925 B, COG válido (cabecera GDAL_STRUCTURAL_METADATA)
```

Tile completo descargado y validado por cabecera. Bucket `copernicus-dem-30m`, región `eu-central-1`, sin credenciales, sin límite de tasa declarado.

**Advertencia crítica:** desde el **28 de julio de 2026** el *view service* de Copernicus DEM 30 m en CDSE está restringido a categorías de usuario CCM registradas. **Usar la vía AWS, no CDSE.** Además, GLO-30 no cubre la totalidad de algunos países (lista pública de exclusiones); El Salvador sí está cubierto según la convención de tiles, pero debe comprobarse tile por tile al ingerir.

### 3.3 SoilGrids — **VERIFIED** (WebDAV) / **PENDING_VALIDATION** (REST)

```
GET https://rest.isric.org/soilgrids/v2.0/properties/query?lon=-89.2&lat=13.7&property=phh2o&depth=0-5cm&value=mean
→ HTTP 200  ...  "values": { "mean": null }
```

**Hallazgo:** la API REST responde 200 pero devuelve **`null` en todos los valores** para un punto en El Salvador (13,7 N, 89,2 O). La propia documentación de ISRIC advierte que el servicio REST v2.0 está **temporalmente suspendido** por problemas técnicos. No se debe construir un pipeline sobre esta API.

```
GET https://files.isric.org/soilgrids/latest/data/phh2o/phh2o_0-5cm_mean.vrt     → HTTP 200, 3.524.139 B
GET https://files.isric.org/soilgrids/latest/data/phh2o/                        → HTTP 200, listado WebDAV
```

El WebDAV sí funciona: expone las 11 propiedades × 6 profundidades × 5 estadísticos (Q0.05, Q0.5, Q0.95, mean, uncertainty) como VRT + teselas COG. **Vía recomendada: WebDAV, no REST.**

Propiedades y conversiones (documentación oficial ISRIC):

| Código | Propiedad | Unidad mapeada | Factor | Unidad convencional |
|---|---|---|---|---|
| `bdod` | Densidad aparente | cg/cm³ | ÷100 | kg/dm³ |
| `cec` | CIC (pH 7) | mmol(c)/kg | ÷10 | cmol(c)/kg |
| `cfvo` | Fragmentos gruesos | cm³/dm³ | ÷10 | % vol |
| `clay` | Arcilla | g/kg | ÷10 | % |
| `sand` | Arena | g/kg | ÷10 | % |
| `silt` | Limo | g/kg | ÷10 | % |
| `nitrogen` | Nitrógeno total | cg/kg | ÷100 | g/kg |
| `phh2o` | pH en agua | pH×10 | ÷10 | pH |
| `soc` | Carbono orgánico | dg/kg | ÷10 | g/kg |
| `wv0010` / `wv0033` / `wv1500` | Agua vol. a 10/33/1500 kPa | 10⁻³ cm³/cm³ | ÷10 | % |

Profundidades estándar GlobalSoilMap: **0–5, 5–15, 15–30, 30–60, 60–100, 100–200 cm**. Las variables `wv0033` (capacidad de campo) y `wv1500` (punto de marchitez) son **directamente utilizables por AquaCrop** — esto evita derivar las propiedades hidráulicas por pedotransferencia.

**Limitación de uso:** 250 m ≈ 6,25 ha por píxel. No es un dato de parcela.

### 3.4 CHIRPS v3 — **VERIFIED**

```
GET https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/readme.txt      → HTTP 200, 6.481 B
GET https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/               → HTTP 200 (final/, prelim/)
GET .../daily/final/rnl/2025/  → chirps-v3.0.rnl.2025.12.27.tif … 12.31.tif
```

Estructura confirmada: `daily/{final,prelim}/{rnl,sat}/<año>/chirps-v3.0.<tipo>.<año>.<mes>.<día>.tif`, desde **1981** hasta presente.

**Dos productos diarios** (no son intercambiables):
- `rnl` — pentadas desagregadas con **ERA5**. 1981–presente.
- `sat` — pentadas desagregadas con **IMERG Late V07**. 1998–presente.

**Advertencia científica decisiva:** CHIRPS se calcula nativamente a escala **pentadal y mensual**. Los valores diarios son una *desagregación temporal* de un total pentadal; la resolución de 0,05° de los productos diarios **no implica información real a 0,05°** (el propio readme lo advierte: ERA5 es 0,25° e IMERG 0,1°, remuestreados). Cualquier análisis de eventos extremos diarios o de sequías intra-mensuales debe hacerse con eso declarado, o directamente a escala pentadal.

CHIRPS v2 dejará de producirse **después de diciembre de 2026**. AGROSV debe nacer en v3.

### 3.5 ERA5 / ERA5-Land — **RESTRICTED**

```
GET https://cds.climate.copernicus.eu/api/retrieve/v1/processes   → HTTP 200 (catálogo público)
GET https://identity.dataspace.copernicus.eu/auth/realms/CDSE/... → HTTP 405 (endpoint existe, requiere POST/OAuth)
```

Datasets relevantes confirmados en el catálogo: `reanalysis-era5-single-levels` (1940–presente, CC-BY-4.0, DOI 10.24381/cds.adbb2d47), `reanalysis-era5-land` (1950–presente, DOI 10.24381/cds.e2161bac), `derived-era5-land-daily-statistics` (agregados diarios ya calculados, omiten variables acumuladas).

Requiere registro gratuito + token personal. **No se verificó con credenciales** (no se dispone de ellas y no se inventan). Coste $0, licencia CC-BY-4.0.

### 3.6 Open-Meteo — **VERIFIED**

```
GET https://archive-api.open-meteo.com/v1/archive?latitude=13.69&longitude=-89.22
    &start_date=2024-01-01&end_date=2024-01-05
    &daily=precipitation_sum,temperature_2m_max,et0_fao_evapotranspiration
→ HTTP 200  {"elevation":719.0, "daily_units":{"et0_fao_evapotranspiration":"mm"}, ...}

GET https://api.open-meteo.com/v1/forecast?latitude=13.69&longitude=-89.22
    &daily=precipitation_sum&forecast_days=3
→ HTTP 200  {"daily":{"time":["2026-11-21",...],"precipitation_sum":[0.80,2.80,2.50]}}
```

**Por qué es estratégicamente importante:** entrega ET0 FAO-56 ya calculada (`et0_fao_evapotranspiration`), que es exactamente la variable de forzamiento de AquaCrop. Sin clave, sin registro. Fuentes: ERA5 (1940–), ERA5-Land (1950–), ECMWF IFS 9 km (2017–).

**Restricción contractual, no técnica:** licencia CC BY 4.0, pero **solo uso no comercial** en el nivel gratuito (<10.000 llamadas/día). El uso comercial exige plan de pago. Si AGROSV se institucionaliza o comercializa, este es el primer costo real del proyecto.

### 3.7 Google Weather API — **RESTRICTED (contractual)**

Documentación verificada. Cobertura de El Salvador confirmada (4 servicios marcados). Endpoints: `currentConditions:lookup`, `forecast/hours:lookup` (240 h), `forecast/days:lookup` (10 días), `history/hours:lookup` (**solo 24 h de histórico**).

**Dos cláusulas lo descalifican como fuente principal de AGROSV:**

1. **§21.1 de los Service Specific Terms:** *"Customers may not use Google Maps Content retrieved from Weather API to recreate a Google service or product (e.g. use data retrieved from Weather API in a weather app or weather model whose primary purpose is to provide weather information)."* AGROSV es, en parte, un modelo agroclimático. Uso en conflicto.
2. **§21.2 Caching Permissions:** condición actual 1 h; pronóstico horario 1 h; pronóstico diario 24 h; histórico horario 240 h; *"today's forecast"* 30 días — **después debe eliminarse**. Es incompatible con un archivo climático histórico, que es el núcleo de AGROSV.

**Además:** el histórico es *"primarily modeled output"*, no observación. No sirve para validación.

**Veredicto:** usar únicamente como capa opcional de condiciones actuales en la interfaz, con caché volátil y atribución, nunca como archivo ni como insumo de modelo. El coste por llamada no se verificó (requiere cuenta de facturación); no se asume.

### 3.8 OpenStreetMap — **VERIFIED**

```
GET https://download.geofabrik.de/central-america/el-salvador-latest.osm.pbf
→ HTTP 200, 35.238.372 B (33,6 MiB), extracto completo con actualizaciones diarias

POST https://overpass-api.de/api/interpreter  (data=way["landuse"="farmland"](13.1,-90.2,14.5,-87.6);out count;)
→ HTTP 200, ways=1554
```

**Hallazgo crítico de cobertura:** en el bounding box nacional hay solo **1.554 ways con `landuse=farmland`**. El Salvador tiene ~293.000 mz de maíz (≈205.000 ha). OSM **no contiene** un mapa de cobertura agrícola utilizable. Sirve para: red vial rural, hidrografía, infraestructura, localidades — no para delimitación de cultivos.

**Reserva operativa:** la misma consulta Overpass devolvió **HTTP 502** ("server at capacity") en un intento previo. El endpoint público **no es apto para uso automatizado intensivo**; para ingesta por lotes usar el extracto Geofabrik local (osm2pgsql/osmium) o instancia Overpass propia.

Licencia **ODbL 1.0**: es *share-alike* sobre la base de datos derivada. Si AGROSV publica una base derivada de OSM, esa base debe licenciarse ODbL. Debe mantenerse OSM en un esquema separado para no contaminar el resto.

### 3.9 Sentinel-2 L2A — **VERIFIED**

```
POST https://earth-search.aws.element84.com/v1/search
  {"collections":["sentinel-2-l2a"],"bbox":[-89.35,13.6,-89.1,13.8],
   "datetime":"2025-01-01/2025-03-01","limit":2}
→ HTTP 200, 2 features. id=S2B_15PZR_20250227_0_L2A, datetime=2025-02-27T16:39:43Z
  assets: B04/B08 (red/nir), SCL, TCI → sentinel-cogs.s3.us-west-2.amazonaws.com/...

GET (range 0-1023) .../B04.tif → HTTP 206, 1024 B
```

Acceso funcional **sin credenciales** vía STAC público + COG en S3 (`us-west-2`), lectura por rango confirmada. Ventaja decisiva: permite leer solo la ventana del polígono, sin descargar escenas completas. Tile confirmado sobre El Salvador: **15PZR** (UTM 15N). El país cae en las zonas **15P** y **16P**.

Alternativa oficial (Copernicus Data Space / Sentinel Hub) requiere OAuth2 → **RESTRICTED**, coste $0 con cuenta.

**Limitación:** ventana útil noviembre–abril. En estación lluviosa la revisita efectiva cae a semanas. Complementar con Sentinel-1 (SAR) es la solución estándar, pero queda fuera de Fase 1.

### 3.10 Límites administrativos — **VERIFIED**

```
GET https://www.geoboundaries.org/api/current/gbOpen/SLV/ADM1/
→ HTTP 200  {"boundaryID":"SLV-ADM1-98794003","boundaryYearRepresented":"2021",
             "boundaryLicense":"Creative Commons Attribution-ShareAlike 2.0",
             "boundarySource":"Open Street Map"}
```

**Atención:** la capa es de 2021 y **no refleja la reforma territorial de 2023** que redujo el país a 44 municipios — el mismo nivel que usa Nemotron. Hay que construir la tabla de correspondencia municipio 2023 ↔ distritos previos, o los agentes no podrán unirse espacialmente a la estadística.

### 3.11 Estadística agrícola nacional — **VERIFIED** (acceso) + **RESTRICTED** (licencia)

```
GET https://www.mag.gob.sv/                                                    → HTTP 200, 123.312 B
GET .../Anuario-de-Estadísticas-Agropecuarias-2021-2022.pdf                     → HTTP 200, 4.321.899 B
GET https://agropecuario.bcr.gob.sv/                                            → HTTP 200, 407.497 B
GET https://censo2024.bcr.gob.sv/.../Segunda_entrega_de_resultados_CAP_2025.pdf → HTTP 200, 11.794.421 B
```

**El BCR, no el MAG, es la fuente primaria de 2025.** El V Censo Agropecuario y I de Pesca 2025 (levantado 2 may – 26 jul 2025, día de referencia 2 de mayo 2025) publica por departamento. Cifras verificadas en las presentaciones oficiales:

| Indicador (may 2024 – abr 2025) | Valor |
|---|---|
| Maíz — superficie cosechada | 293.458 mz |
| Maíz — producción | ~10,9 millones qq (~493.403 t) |
| Maíz — productores | 401.101 |
| Maíz — semilla híbrida / criolla | 75,0 % / 19,7 % del área |
| Maíz — destino autoconsumo / venta | 49,5 % / 47,8 % |
| Frijol — producción | 996,2 mil qq (~45.189 t) |
| Frijol — productores | 214.738 |
| Frijol — destino autoconsumo / venta | 50,3 % / 48,8 % |
| Concentración maíz | Ahuachapán 12,3 % · Santa Ana 10,6 % · La Libertad 8,7 % · Usulután 8,2 % · Sonsonate 8,0 % |

El Anuario del MAG (DGEA) sigue siendo útil para series históricas y precios, pero su última edición publicada es 2021-2022.

**Formatos:** PDF, presentaciones y un ArcGIS Hub cuyo feed DCAT devolvió **0 datasets** desde el sondeo automatizado. **No hay API documentada de descarga.** La automatización viable es: (a) ingestión de PDF + extracción de tablas con verificación humana, o (b) solicitud formal de microdatos. El geoportal declara microdatos anonimizados del censo de población en `geoportal.bcr.gob.sv`; su acceso máquina-a-máquina está **PENDING_VALIDATION**.

**Licencia:** no se localizó licencia explícita de reutilización. Tratar como **RESTRICTED para redistribución**, VERIFIED para uso interno con atribución.

### 3.12 Suelos nacionales — **PENDING_VALIDATION**

CENTA opera el *Portal de Mapas Digitales* (ArcGIS Hub) con mapeo digital de suelos: textura, profundidad efectiva, pH, materia orgánica, nutrientes (K, P, Mg, Ca, Cu, Zn, Fe, Mn), erosión y degradación, y 19 mapas nacionales. Es la fuente **más importante después de SoilGrids**, porque es nacional y a escala declarada 1:50.000.

**Pero:** el feed DCAT del portal devolvió **0 datasets** y la API de búsqueda, 0 resultados. No se confirmó acceso máquina-a-máquina. **Requiere contacto institucional con CENTA.** No asumir que existe API.

Alternativa documentada: *Soil in El Salvador* del Banco Mundial (10 MB, shapefile, clasificación de suelos, CC BY 4.0, actualizado 2017) — descarga viable, resolución no declarada en la ficha.

### 3.13 Modelos agronómicos — **VERIFIED**

**AquaCrop 7.3** — licencia **propietaria de FAO**: el archivo `LICENSE` del repositorio dice «All rights reserved» y exige solicitud previa para uso no comercial. **No es BSD-3-Clause** (corrección de esta revisión, ver §8.1). © FAO / KU Leuven. Repositorios: `un-fao/fao-AquaCrop` y `KUL-RSDA/AquaCrop`. **Desde 7.3 existe implementación oficial en Python** (antes solo Fortran/Pascal). Novedades relevantes: *"automatic estimation of soil hydraulic properties from soil texture"* — elimina la dependencia de una pedotransferencia externa, y *"frequency analysis of simulation results"* — útil para P10/P50/P90.

**Consecuencia arquitectónica:** `AquaCrop-OSPy` (pip `aquacrop`), que era la opción estándar en Python, está basado en AquaCrop-OS v6. **Usar el código oficial 7.3 de FAO, no el fork de la Universidad de Manchester.** Se evita divergencia de modelo y se gana el cálculo de propiedades hidráulicas.

**DSSAT CSM 4.8.6** — open source **BSD-3-Clause** desde diciembre de 2019 (`DSSAT/dssat-csm-os`). Técnicamente accesible, pero **no viable en Fase 1**: requiere coeficientes genéticos de cultivar calibrados con ensayos locales, que no están disponibles abiertamente para variedades salvadoreñas. Postergar a Fase 3 con datos de CENTA.

---

## 4. Costes reales

| Concepto | Coste | Nota |
|---|---|---|
| Todas las fuentes de datos núcleo | **$0** | sin suscripción obligatoria |
| Open-Meteo, uso no comercial | **$0** | <10.000 llamadas/día |
| Open-Meteo, uso comercial | **De pago** | plan mensual fijo; precio no verificado — no se asume |
| CDS ERA5 | **$0** | registro gratuito, cuota de cola |
| CDSE / Sentinel Hub | **$0** con cuenta | cuotas de proceso |
| Google Weather API | **Por llamada** | precio por 1.000 no verificado; además restringido por ToS (§3.7) |
| Almacenamiento local | **$0** | ver estimación en `SYSTEM_ARCHITECTURE.md` §7 |
| **Único coste técnico real** | **Horas de ingeniería** | no hay barrera económica de entrada |

---

## 5. Idoneidad científica por fuente (independiente del estado de acceso)

| Fuente | Sirve para | **No** sirve para |
|---|---|---|
| Sentinel-2 10 m | NDVI/NDWI, fenología, cambios de cobertura, monitoreo de parcela | identificación de cultivo sin verdad de campo; estación lluviosa |
| Copernicus DEM 30 m | pendiente, orientación, escorrentía, corrección por altitud | microrelieve; es un **DSM** (superficie), no un DTM — incluye vegetación y edificios |
| SoilGrids 250 m | prior de paisaje, propiedades hidráulicas para AquaCrop | propiedad de una parcela |
| CENTA 1:50.000 | suelos nacionales, mayor detalle que SoilGrids | aún no verificado para descarga |
| CHIRPS 0,05° | precipitación acumulada pentadal/mensual/anual, SPI | eventos diarios extremos; gradientes topográficos |
| ERA5-Land 0,1° | ET0, temperatura, humedad de suelo, series largas | relieve complejo sin corrección |
| Open-Meteo | prototipado rápido, ET0 lista para AquaCrop | archivo permanente propio (dependencia de tercero) |
| Google Weather | condiciones actuales en UI | archivo histórico, modelo, validación |
| OSM | vialidad rural, ríos, infraestructura, localidades | delimitación de cultivos |
| Nemotron | heterogeneidad de respuestas, simulación de agentes | evidencia estadística; dotaciones económicas; ubicación fina |
| Censo Agropecuario 2025 | verdad de referencia agregada, estructura productiva | trayectoria por parcela |

---

## 6. Reglas de procedencia obligatorias

Cada activo de datos ingerido debe registrar, sin excepción:

```yaml
source_id: chirps3
source_url: https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/2025/chirps-v3.0.rnl.2025.03.15.tif
retrieved_at: 2026-11-21T17:31:00Z
source_version: v3.0
product_variant: rnl            # rnl | sat  ← nunca omitir
license: public-domain-claimed  # verificar aviso oficial
attribution_text: "CHIRPS v3, Climate Hazards Center, UC Santa Barbara"
native_resolution: 0.05 deg
effective_resolution: pentadal  # ← resolución real del dato, no la de la rejilla
transform: clip(bbox=[-90.2,13.1,-87.6,14.5]) -> reproject(EPSG:32616)
sha256: <hash del archivo o del resultado>
```

El campo `effective_resolution` es obligatorio y distinto de `native_resolution`. Es el mecanismo que impide que AGROSV publique precisión falsa.

---

## 7. Ampliación 2026-11-21 — fuentes nacionales, censales y climáticas

Este bloque **añade** fuentes al registro; no modifica los estados de §2. La
evidencia ampliada y las condiciones de acceso están en
[`docs/NATIONAL_DATA_INTEGRATION.md`](docs/NATIONAL_DATA_INTEGRATION.md).
Sondas ejecutadas el 2026-11-21 desde este entorno.

| ID | Fuente | Cobertura | Resolución | Formato | Acceso | Licencia | Coste | Estado |
|---|---|---|---|---|---|---|---|---|
| `cnr-igcn` | Catálogo de servicios del IGCN (CNR) | Nacional | 1:1.000–1:500.000 | Productos digitales/impresos | Compra | No declarada | $3,50–$299,45 | **RESTRICTED** |
| `cnr-elsalvadormaps` | *El Salvador Maps* (CNR) | Nacional (20.742,5 km²) | hasta 10 cm (declarado) | Visor/plataforma | Consulta; sin descarga masiva documentada | No declarada | Desconocido | **DOCUMENTED** |
| `cnr-ortho` | Ortofoto y fotografía aérea | Nacional | hasta 10 cm (declarado) | Imagen | Compra, «desde $29» | No declarada | Pago | **RESTRICTED** |
| `cnr-lidar` | LiDAR / MDT / MDS / 3D | Nacional | no publicada | Nube de puntos/raster | Sin ficha pública | No declarada | Desconocido | **DOCUMENTED** |
| `mag-anuarios` | Anuarios de Estadísticas Agropecuarias 2018-19…2022-23 | Nacional/dept./mun. | — | PDF | HTTP directo | No declarada | $0 | **VERIFIED** |
| `mag-precios` | Precios diarios/semanales/mensuales | Nacional/plazas | — | PDF | HTTP directo | No declarada | $0 | **VERIFIED** |
| `mag-costos` | Costos de producción 2019-20…2022-23 | Por cultivo | — | PDF | HTTP directo | No declarada | $0 | **VERIFIED** |
| `mag-mapas` | Mapas temáticos (granos, frutales, hortalizas, suelos) | Nacional | no declarada | PDF (no GIS) | HTTP directo | No declarada | $0 | **DOCUMENTED** |
| `mag-censo-2007` | IV Censo Agropecuario 2007-08 | Nacional/dept./mun. | — | PDF | HTTP directo | No declarada | $0 | **VERIFIED** |
| `centa-mds` | Mapa Digital de Suelos (CENTA) | Nacional | no publicada | Visor ArcGIS | Consulta; descarga no verificada | No declarada | $0 | **PENDING_VALIDATION** |
| `bcr-cpv2024` | VII Censo de Población y VI de Vivienda 2024 | Nacional→distrito | — | CSV/SPSS + XLSX/PDF | Descarga pública | No declarada (datos abiertos) | $0 | **VERIFIED** |
| `bcr-cap2025` | V Censo Agropecuario y I de Pesca 2025 | Nacional/dept. | — | PDF/PPT + dashboards | Portal web | No declarada; sin microdatos | $0 | **VERIFIED** (agregados) |
| `marn-snet` | Atlas hidrológico, amenazas, geología (SNET/MARN) | Nacional | 1:50.000 (deslizamientos) | PDF/visor | HTTP directo | No declarada | $0 | **DOCUMENTED** |
| `marn-geoportal` | Geoportal MARN (REST) | Nacional | — | Servicios REST | — | No declarada | $0 | **UNAVAILABLE** (HTTP 522) |
| `subcuencas-rmgir` | Subcuencas El Salvador (FeatureServer regional) | Nacional | — | GeoJSON/REST | REST público | No declarada | $0 | **VERIFIED** (tercero) |
| `agera5` | AgERA5 (C3S) | Global | 0,1° diario | NetCDF/Zarr | CDS con cuenta y API key | CC BY 4.0 | $0 | **RESTRICTED** |
| `chirps3-v3` | CHIRPS v3 | Global 60N–60S | 0,05° | GeoTIFF/NetCDF/BIL/COG | HTTP directo | CC BY 4.0 / dominio público | $0 | **VERIFIED** |
| `s2-stac-cdse` | Sentinel-2 L2A vía STAC CDSE | Global | 10/20/60 m | COG | STAC público | Copernicus (atribución) | $0 | **VERIFIED** |

### 7.1 Evidencia de las sondas nuevas

```
https://www.cnr.gob.sv/                                         → 200
https://www.cnr.gob.sv/servicios/.../detalle-de-servicios-.../  → 200
https://elsalvadormaps.sv/                                     → 000 (sin respuesta)
https://geoportal.bcr.gob.sv/                                  → 200
https://poblacion.bcr.gob.sv/pages/teg-base-de-datos-y-tabulados → 200
https://agropecuario.bcr.gob.sv/pages/documentacion-cap-ter    → 200
https://agropecuario.bcr.gob.sv/pages/preguntasrespuestas-cap  → 200
https://www.mag.gob.sv/servicios/estadisticas-agropecuarias    → 200
https://www.mag.gob.sv/mapas-tematicos-.../                    → 200
https://www.centa.gob.sv/mapa-digital-de-suelos                → 403 (bloqueo a cliente no navegador)
https://geoportal.marn.gob.sv/                                 → 522
https://www.snet.gob.sv/Hidrologia/atlas.htm                   → 200
https://www.snet.gob.sv/ver/geologia/amenaza+deslizamientos    → 200
https://cds.climate.copernicus.eu/datasets/sis-agrometeorological-indicators → 200
https://data.chc.ucsb.edu/products/CHIRPS/v3.0/                → 200
https://rmgir.proyectomesoamerica.org/.../Sub_Cuencas_El_Salvador/FeatureServer?f=json → 200
https://stac.dataspace.copernicus.eu/v1/                       → 200
https://developers.google.com/maps/documentation/weather       → 200
```

### 7.2 Reglas nuevas que se suman a §6

- **R-7** Ninguna fuente nacional entra sin licencia escrita o, en su defecto,
  sin autorización institucional documentada.
- **R-8** Los PDF institucionales no se tratan como datos: se extraen tablas con
  referencia de página y revisión humana.
- **R-9** Toda fuente nueva declara `layer_type` (observación, amenaza,
  susceptibilidad, predicción o administrativo).
- **R-10** `VERIFIED` caduca: el sondeo se repite antes de cada fase y el
  resultado se registra con fecha.

---

## 8. Ampliación Fase 2 (2026-11-21) — observación, modelos y escenarios

Tabla de fuentes incorporadas en el diseño de Fase 2. Estados según §1.

### 8.1 Corrección de registro: AquaCrop

La revisión de esta fase **corrige** el registro de Fase 0. El archivo `LICENSE`
del repositorio oficial de FAO AquaCrop 7.3 declara «All rights reserved» y
exige solicitud previa para uso no comercial. **No es BSD-3-Clause.** Consecuencia:

- AquaCrop puede usarse para análisis interno y resultados propios con cita.
- No se redistribuye el código ni se ofrece como servicio sin autorización.
- El modelo alternativo con licencia permisiva es DSSAT (BSD-3, con registro).

### 8.2 Observación satelital

| id | Fuente | Variables | Resolución | Acceso | Licencia | Estado |
|---|---|---|---|---|---|---|
| `s2_l2a` | Sentinel-2 L2A (ESA/Copernicus) | 13 bandas, SCL | 10/20/60 m, 5 d | CDSE (cuota 12 TB/30 d) | Copernicus abierta | **VERIFIED** |
| `s1_grd` | Sentinel-1 IW GRD | VV/VH | 10 m spacing, 6–12 d | CDSE | Copernicus abierta | **VERIFIED** |
| `landsat_c2` | Landsat 8/9 Collection 2 | 7 bandas + QA | 30 m, 16 d | USGS (login) | Dominio público | **VERIFIED** |
| `mod13q1` | MODIS MOD13Q1 | NDVI/EVI 16 d | 250 m | Earthdata (login) | Abierta | **VERIFIED** (Terra cesa 2026-12-01) |
| `vj113a1` | VIIRS VJ113A1 (Suomi NPP) | NDVI/EVI | 250 m | Earthdata | Abierta | **PENDING_VALIDATION** |
| `gpm_imerg` | GPM IMERG Early/Final | precipitación | 0,1°, 30 min | Earthdata | Abierta | **RESTRICTED** (login) |
| `smap` | SMAP L4 | humedad del suelo | 9 km, 3 h | Earthdata | Abierta | **DOCUMENTED** |

MODIS Terra (MOD13Q1) cesa el **2026-12-01**: el pipeline debe migrar a
VJ113A1/VJ213A1 sin concatenar series sin aviso (P-13).

### 8.3 Clima y escenarios

| id | Fuente | Variables | Resolución | Acceso | Licencia | Estado |
|---|---|---|---|---|---|---|
| `chirps_v3` | CHIRPS v3 (UCSB/CHC) | precipitación diaria | 0,05° | descarga directa | CC BY 4.0 | **VERIFIED** |
| `agera5` | AgERA5 (Copernicus C3S) | T, precip, ET₀, radiación | 0,1° diaria | CDS (cuenta) | CC BY 4.0 | **RESTRICTED** |
| `era5` | ERA5 | reanálisis horario | 0,25° | CDS | CC BY 4.0 | **RESTRICTED** |
| `noaa_cpc` | NOAA CPC | precipitación/temperatura diaria | 0,5° | descarga directa | Abierta, sin registro | **VERIFIED** |
| `cmip6` | CMIP6 (ESGF) | GCM, SSP126/245/370/585 | ~100–200 km | ESGF/Metagrid | Términos CMIP6 | **DOCUMENTED** |
| `worldclim_21` | WorldClim 2.1 | 19 bioclimáticas + futuro | 30″ (~1 km) | descarga directa | **No comercial, sin redistribución** | **DOCUMENTED** |
| `gaez_v4` | GAEZ v4 (FAO/IIASA) | aptitud y rendimiento potencial | 5′; 30″ selectivo | REST/WCS + TIFF | **No comercial, atribución** | **DOCUMENTED** |

### 8.4 Modelos de simulación

| id | Modelo | Uso | Licencia | Requisito | Estado |
|---|---|---|---|---|---|
| `aquacrop` | AquaCrop 7.3 (FAO) | balance hídrico, biomasa | **Propietaria FAO, no comercial** | solicitud | **VERIFIED** |
| `dssat` | DSSAT 4.8.6 | fenología, N, rendimiento | BSD-3 | registro | **VERIFIED** |
| `apsim` | APSIM Next Gen | evaluación comparativa | Uso general 3 años no comercial | registro | **DOCUMENTED** |
| `swatplus` | SWAT+ 62.0.1 | hidrología de cuenca | LGPL-2.1 | QGIS + TauDEM | **DOCUMENTED** |

### 8.5 Fitosanidad y economía

| id | Fuente | Contenido | Acceso | Estado |
|---|---|---|---|---|
| `ippc_sv` | IPPC — El Salvador | reportes de plagas | portal público | **VERIFIED** (0 pest reports) |
| `oirsa_uris` | OIRSA URIS | alertas regionales | portal | **DOCUMENTED** |
| `isc_boletines` | ISC (café) | boletines roya/broca | PDF | **DOCUMENTED** |
| `mag_precios` | MAG — informes de precios | mayorista/consumidor | PDF | **VERIFIED** |
| `mag_costos` | MAG — costos de producción | por cultivo, 2019-20…2022-23 | PDF | **VERIFIED** |
| `mag_insumos` | MAG — guía de insumos | semillas, fertilizantes | PDF | **VERIFIED** |
| `bcr_cap` | BCR — CAP 2025 | producción y destino | PDF/PPT | **VERIFIED** (agregados) |

Ninguna de las fuentes MAG/BCR declara licencia de reutilización: se usan con
atribución y **no** se redistribuyen sus PDF (§6, R-7).

### 8.6 Restricciones que condicionan el producto

1. Licencias no comerciales (AquaCrop, WorldClim, GAEZ) impiden ofrecer AGROSV
   como servicio comercial sin autorización.
2. La cuota CDSE (12 TB/30 d) obliga a archivar índices, no reflectancia.
3. Los servicios con login (Earthdata, CDS, USGS) requieren cuentas: la
   reproducibilidad pública exige archivar la versión usada.
4. `VERIFIED` caduca (R-10): todo sondeo se repite antes de cada fase.
