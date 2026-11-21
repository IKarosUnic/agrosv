# DATA_PIPELINE.md — AGROSV

**Versión:** 1.0 · **Fecha:** 2026-11-21
**Principio:** `data/raw/` es inmutable y sagrado. Todo lo demás se puede reconstruir con un comando.

---

## 1. Estructura de directorios

```
agrosv/
├── data/
│   ├── raw/                     # INMUTABLE — nunca se edita, nunca se sobrescribe
│   │   ├── nemotron/<sha>/      # 3 parquet + README original
│   │   ├── copdem30/N13_W090/
│   │   ├── soilgrids/<version>/
│   │   ├── chirps3/v3.0/rnl/<año>/
│   │   ├── era5/<dataset>/<año>/
│   │   ├── osm/<fecha_extraccion>/
│   │   └── national/bcr_cap2025/   # PDF originales
│   ├── interim/                 # intermedios descartables
│   ├── processed/               # reconstruible por script, con .provenance.json
│   └── metadata/
│       ├── registry.yaml        # fuente única de verdad de fuentes
│       └── manifests/           # un manifiesto por ejecución de ingesta
├── src/agrosv/
│   ├── contracts/  ingest/  geo/  climate/  agronomy/
│   ├── economics/  agents/  api/  storage/
├── db/migrations/
├── tests/
│   ├── golden/  contract/  architecture/
└── research/probe_sources.sh
```

**Regla de oro del `raw`:** el ingestor escribe **una sola vez**. Si el archivo ya existe y el hash coincide, no hace nada. Si el hash difiere, **falla** y exige intervención: nunca reemplaza silenciosamente un dato de origen.

---

## 2. Flujo por etapas

```
┌─────────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌───────────┐
│ ADQUISICIÓN │──▶│VALIDACIÓN│──▶│NORMALIZ. │──▶│  ALMACÉN │──▶│  DERIVADOS │
│  (fetch)    │   │(gate)    │   │(transform)│  │(raw→proc)│   │ (modelos)  │
└─────────────┘   └──────────┘   └──────────┘   └──────────┘   └───────────┘
      │                │               │              │               │
   manifiesto      rechazo o        CRS único      PostGIS         simulación
   + sha256        cuarentena      EPSG:4326/        + COG          + procedencia
                                   32616           + Zarr
```

Cada etapa es **idempotente y reanudable**. Un fallo en la etapa 4 no obliga a re-descargar la etapa 1.

---

## 3. Etapa 1 — Adquisición

### 3.1 Contrato de cada ingestor

```python
def fetch(source_id: str, params: dict) -> Manifest
```

Todo ingestor debe:

1. Resolver la URL desde `registry.yaml` (nunca hardcodeada).
2. Enviar `User-Agent` identificable con contacto.
3. Respetar `robots.txt` y los límites de tasa de la fuente.
4. Reintentar con backoff exponencial (3 intentos, 2/4/8 s) **solo** en 5xx y timeouts.
5. **No reintentar** en 401/403/404: esos son fallos de configuración, no de red.
6. Calcular `sha256` del contenido.
7. Escribir en `raw/` de forma atómica (`*.tmp` → `os.replace`).
8. Emitir un `Manifest` con: `source_id`, `url`, `retrieved_at`, `http_status`, `bytes`, `sha256`, `source_version`, `product_variant`, `license`.

### 3.2 Particularidades por fuente (derivadas de la verificación real)

| Fuente | Particularidad que el ingestor **debe** manejar |
|---|---|
| **Nemotron** | Anclar al `sha` `68f6a21c…`. Descargar los 3 shards. Guardar el `README.md` original junto a los datos: es la evidencia de licencia y limitaciones. |
| **Copernicus DEM** | Vía AWS S3 (`copernicus-dem-30m`), **no CDSE** (view service restringido desde 28-jul-2026). Nomenclatura de tile `Copernicus_DSM_COG_10_N{lat}_W{lon}_DEM`. Verificar que el tile exista: GLO-30 tiene exclusiones por país. |
| **SoilGrids** | Vía WebDAV `files.isric.org`, **no REST** (devuelve `null`). Descargar VRT + teselas, o mejor: recortar por bbox al vuelo y guardar solo el recorte. Aplicar el factor de conversión de unidad de la tabla del registro. |
| **CHIRPS** | Un archivo por día. `product_variant` (`rnl`/`sat`) es **obligatorio** y no intercambiable. 16.436 peticiones para 1981–2025: paralelizar con límite de concurrencia (≤4) y reanudar por año. |
| **ERA5/CDS** | Requiere token del usuario. Cola asíncrona: `cdsapi` puede tardar minutos. Guardar el `request_id` para reanudar. |
| **Open-Meteo** | Es transporte, no archivo. Guardar siempre la respuesta cruda junto a los parámetros exactos de la petición. Límite 600/min, 5.000/h, 10.000/día. |
| **OSM/Geofabrik** | Extracción semanal. Guardar la fecha de extracción: el `.pbf` cambia cada día. |
| **Sentinel-2** | **No descargar escenas.** Indexar vía STAC y guardar solo la lista de `item_id` + `href`. Los píxeles se leen por ventana en el momento del cálculo. |
| **MAG/BCR** | PDF. Descarga directa; la extracción de tablas es un paso humano-asistido, no automático silencioso. |

---

## 4. Etapa 2 — Validación (puerta de calidad)

Ningún dato entra a `processed/` sin pasar estas comprobaciones. Un fallo **bloquea**; no se "arregla" el dato para que pase.

### 4.1 Validaciones comunes

| Control | Regla | Acción si falla |
|---|---|---|
| Integridad | `sha256` coincide con el manifiesto | Abortar |
| Tipo de contenido | Magic bytes coherentes con el formato esperado | Cuarentena |
| Completitud | Ningún tile/día/fila faltante en el rango solicitado | Reportar hueco; **no** interpolar por defecto |
| CRS | Declarado y reconocible; si falta, deducir y registrar | Abortar si ambiguo |
| Rango físico | Valores dentro de límites físicos por variable | Cuarentena + reporte |
| Nulos | Proporción de nulos dentro de umbral por fuente | Reporte; nunca rellenar en silencio |
| Licencia | `license` presente y no vacía en el manifiesto | Abortar |

### 4.2 Validaciones específicas

| Variable | Regla física | Nota |
|---|---|---|
| Elevación (Copernicus DEM) | −10 m ≤ z ≤ 3.000 m en El Salvador | Punto más alto ~2.730 m (El Pital) |
| Precipitación diaria (CHIRPS) | 0 ≤ p ≤ 500 mm | > 500 mm/día es implausible en SV |
| Precipitación anual (agregado) | 1.200 ≤ a ≤ 3.200 mm | Fuera de rango → revisar |
| Temperatura (ERA5-Land) | 5 °C ≤ T ≤ 45 °C | |
| ET0 | 0 ≤ ET0 ≤ 15 mm/día | |
| pH (SoilGrids) | 3,0 ≤ pH ≤ 9,5 tras ÷10 | El factor de escala es la causa #1 de error |
| Arcilla+limo+arena | |Σ − 100| ≤ 5 % tras ÷10 | Si no, inconsistencia de textura |
| Profundidad de suelo | 0–5 … 100–200 cm | 6 intervalos exactos |
| Ocupación (Nemotron) | ∈ 119 clases CIIU conocidas | Rechazar clases nuevas sin revisión |
| `area` (Nemotron) | ∈ {urbano, rural} | |

### 4.3 Validación cruzada entre fuentes

Tres contrastes que detectan errores que ninguna validación individual ve:

1. **CHIRPS vs. ERA5-Land** — correlación mensual por departamento. Si r < 0,6 en una zona, algo está mal alineado (típicamente offset de fecha o reproyección).
2. **SoilGrids vs. mapa de CENTA** — cuando esté disponible, comparar textura. Discrepancia grande en un departamento = revisar unidad o profundidad.
3. **DEM vs. pendiente derivada** — pendientes > 60° en zonas llanas indican artefacto del DEM o error de reproyección.

---

## 5. Etapa 3 — Normalización

### 5.1 Sistemas de referencia

- **Almacenamiento canónico:** `EPSG:4326` para geometrías (interoperabilidad).
- **Cálculo de áreas y distancias:** usar **área geodésica** (`pyproj.Geod.geometry_area_perimeter`) como método por defecto — es exacta y evita problemas de zona.
- **Proyecciones métricas de trabajo:** `EPSG:32616` (UTM 16N, 90°O–84°O) para rásteres y análisis de pendiente. **Atención:** el extremo occidental de El Salvador (≈ −90,13°) cae en **UTM 15N (`EPSG:32615`)**, porque la frontera entre zonas está en 90°O. Un pipeline que asuma 16N para todo el país reproyecta mal Ahuachapán y Ahuachapán Sur. Decidir por bbox: si `lon_min < -90.0`, usar 15N para ese bloque.
- **Nunca** calcular áreas en 4326 (grados no son metros).

### 5.2 Convenciones obligatorias

| Convención | Valor | Motivo |
|---|---|---|
| Unidad de precipitación | mm/día | Estándar agronómico |
| Unidad de ET0 | mm/día | Entrada directa de AquaCrop |
| Unidad de temperatura | °C | |
| Unidad de área | hectárea (ha) **y** manzana (mz) | 1 mz = 0,6989 ha — conversión explícita, nunca implícita |
| Unidad de producción | quintal (qq) y tonelada | 1 qq = 45,36 kg (maíz); declarar el cultivo |
| Fecha | ISO 8601, zona `America/El_Salvador` (UTC−6) | Sin horario de verano |
| Nombres de variable | snake_case, sin acentos | |
| Nombres de cultivo | `maiz`, `frijol`, `maicillo`, `arroz` | Sin tildes en claves; tildes solo en presentación |

**La manzana es la trampa principal.** Toda cifra de superficie del censo viene en mz; toda cifra de modelo agronómico sale en ha. La conversión tiene que ser una función única probada, no una multiplicación dispersa por el código.

### 5.3 Resolución efectiva

Ninguna capa puede declarar resolución mayor que la real. El campo `resolucion_efectiva` es obligatorio:

| Capa | `resolucion_nativa` | `resolucion_efectiva` |
|---|---|---|
| Copernicus DEM | 30 m | 30 m (DSM: incluye vegetación y edificios) |
| SoilGrids | 250 m | 250 m |
| CHIRPS diario | 0,05° | **pentadal** (desagregado) |
| CHIRPS mensual | 0,05° | 0,05° |
| ERA5 | 0,25° | 0,25° |
| ERA5-Land | 0,1° | 0,1° |
| Sentinel-2 | 10 m | 10 m (condicionado a nubosidad) |
| Censo agropecuario | departamental | departamental |

El validador rechaza cualquier registro donde `resolucion_efectiva` sea menor (más fina) que la nativa.

---

## 6. Etapa 4 — Almacenamiento

### 6.1 Reparto

| Tipo de dato | Almacén | Motivo |
|---|---|---|
| Tabular y vectorial | PostGIS | Joins espaciales, índices GiST, integridad |
| Ráster puntual (DEM, suelo recortado) | COG | Lectura por ventana, overviews, TiTiler |
| Cubo espacio-temporal (clima) | Zarr | Series multidimensionales, compresión por chunk |
| Serie puntual por unidad | PostGIS `climate_daily` | Consultas analíticas rápidas |
| Texto de agentes | PostGIS `agent` | Consistencia y joins |
| OSM | Esquema PostGIS **separado** | Aislamiento ODbL (§7) |

### 6.2 Regla de no duplicación

Un dato vive **en un solo lugar**. `climate_daily` en PostGIS se genera desde Zarr, y existe un test que verifica que una muestra aleatoria de 1.000 puntos coincide. Nunca se escribe en ambos.

---

## 7. Aislamiento de licencias

La licencia ODbL de OSM es *share-alike* sobre bases de datos derivadas. Mezclar OSM con datos propietarios en el mismo esquema crearía ambigüedad legal sobre todo el conjunto.

```
Esquema `osm`            → ODbL 1.0. Derivados publicables solo bajo ODbL.
Esquema `agrosv_core`    → datos propios + fuentes CC-BY + licencias no declaradas (uso interno).
Esquema `external_restricted` → datos con licencia no declarada (BCR/CENTA) mientras no haya permiso.
```

Una vista puede unir esquemas para análisis interno. **La exportación pública se hace por esquema**, respetando cada licencia. Ninguna exportación puede mezclar `osm` con `agrosv_core` en un mismo archivo publicado.

---

## 8. Ejecución por lotes

```bash
# Ingesta idempotente; reanudable; nunca sobrescribe raw
agrosv ingest chirps3 --variant rnl --from 1981 --to 2025 --bbox sv

# Construcción de capas derivadas
agrosv build topography --source copdem30
agrosv build soil       --source soilgrids
agrosv build climate    --normals 1991-2020

# Simulación
agrosv sim paup --unit <uuid> --crop maiz --planting 2025-05-15 --seed 42

# Auditoría
agrosv audit provenance --sample 200
```

**Restricciones del CLI:** sin daemon; código de salida ≠ 0 en cualquier fallo de validación; `--dry-run` obligatorio en todo comando que escriba; log estructurado (JSON) a `logs/<comando>-<ts>.log`.

---

## 9. Manifiesto de ejecución (ejemplo real)

```json
{
  "run_id": "ingest-chirps3-20261121T173100Z",
  "command": "agrosv ingest chirps3 --variant rnl --from 2025 --to 2025 --bbox sv",
  "source_id": "chirps3",
  "source_version": "v3.0",
  "product_variant": "rnl",
  "files": [
    {
      "url": "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/2025/chirps-v3.0.rnl.2025.12.27.tif",
      "http_status": 200,
      "bytes": 0,
      "sha256": "<calculado en ejecución>"
    }
  ],
  "license": "public-domain-claimed",
  "attribution": "CHIRPS v3, Climate Hazards Center, UC Santa Barbara",
  "resolucion_nativa": "0.05 deg",
  "resolucion_efectiva": "pentadal",
  "transform": "clip(bbox=[-90.2,13.1,-87.6,14.5]) -> reproject(EPSG:32616)",
  "software": {"agrosv": "0.1.0", "rasterio": "1.3.x", "gdal": "3.8.x"},
  "seed": null,
  "retrieved_at": "2026-11-21T17:31:00Z"
}
```

Cada fila de `provenance` en la base de datos apunta a uno de estos manifiestos. Si el manifiesto no existe, la cifra no es publicable.

---

## 10. Modos de fallo conocidos y su tratamiento

| Fallo | Tratamiento correcto | Tratamiento **prohibido** |
|---|---|---|
| Hueco de días en CHIRPS | Registrar el hueco, marcar la serie como incompleta, reportar | Interpolar y presentar como completa |
| Tile DEM ausente | Fallar el build de esa zona, listar tiles faltantes | Rellenar con 0 o con SRTM sin declararlo |
| SoilGrids REST devuelve `null` | Usar WebDAV | Rellenar con la media global |
| Overpass 502 | Backoff; para volumen, usar extracto Geofabrik | Reintentar en bucle contra el endpoint público |
| PDF censal sin tabla extraíble | Extracción manual con doble verificación | OCR sin revisión humana |
| Divergencia MAG vs BCR | Publicar ambas con procedencia | Elegir la que "se vea mejor" |
| Dato sintético faltante (ingreso) | Dejar nulo y declararlo | Inventar con el LLM |
