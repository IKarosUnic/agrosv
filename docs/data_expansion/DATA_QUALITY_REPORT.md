# DATA_QUALITY_REPORT — AGROSV Fase 3

**Fecha:** 2026-11-22 · **Alcance:** validación de las muestras descargadas y de
los canales sondeados. No evalúa la calidad científica de datasets que no se
pudieron obtener.

---

## 1. Método

1. Sonda HTTP a 118 URLs (nacionales e internacionales) con User-Agent de
   navegador y `Range` para archivos grandes.
2. Descarga de **9 muestras mínimas** (punto, AOI, un día global, cabecera de
   COG, filas sintéticas) — nunca datasets nacionales completos.
3. Cálculo de `sha256`, tamaño y tipo de contenido.
4. Validación específica por formato: `rasterio` para GeoTIFF, `json.loads` para
   JSON, comprobación de claves para APIs.
5. Registro de defectos encontrados y su severidad.

Scripts: `scripts/06_probe_phase3_sources.py`,
`scripts/07_fetch_phase3_samples.py`.
Manifiesto: `data/manifests/phase3_samples.json`.

---

## 2. Muestras validadas

| Muestra | Bytes | sha256 (16) | Validación | Resultado |
|---|---:|---|---|---|
| `nasa_power_point` | 128.012 | `f0ff69a77369…` | JSON; `properties.parameter`; 2.557 días | **OK** |
| `open_meteo_point` | 92.997 | `9a6d9b1b1064…` | JSON; `et0_fao_evapotranspiration` presente | **OK** |
| `worldbank_slv` | 14.891 | `dbe04d5b44be…` | JSON; serie de indicador | **OK** |
| `gbif_sv` | 2.125.141 | `c2bf4264b01d…` | JSON; 300 registros con coordenadas | **OK** |
| `soilgrids_rest_point` | 357 | `0c456e2042b3…` | JSON válido pero `mean: null` | **DEFECTO** (documentado) |
| `chirps3_day` | 14.000.124 | `1769f6f4fffe…` | `rasterio`: EPSG:4326, 7200×2400, 0,05°, float32 | **OK** |
| `sentinel2_stac` | 42.425 | `049c3afc7efa…` | JSON STAC; item `S2B_15PZR_20250227_0_L2A`; COG 206/2.048 B | **OK** |
| `nemotron_rows` | 27.580 | `59ea5ead123c…` | JSON; 3 filas; sintético | **OK** |
| `geoboundaries_slv` | 321.639 | `c864925e93e1…` | GeoJSON ADM0 | **OK** |

**Integridad:** todos los archivos coinciden con el hash registrado en el
manifiesto. Ninguno se guardó parcialmente.

---

## 3. Defectos y hallazgos

| # | Defecto | Severidad | Evidencia | Estado |
|---|---|---|---|---|
| D-01 | SoilGrids REST responde 200 con `mean: null` para un punto de El Salvador | **Alta** (fallo silencioso) | 357 B, `soilgrids_phh2o_point.json` | Documentado; API vetada |
| D-02 | SoilGrids `latest` ya no publica `wv0033`/`wv1500` | **Alta** (rompe supuesto de AquaCrop) | 404 + listado de 15 directorios | Corregido; pedotransferencia |
| D-03 | Geofabrik cambió la ruta del extracto SV; PBF 404, SHP 200 | **Media** | 404 / 206 (88.096.457 B) | Ruta nueva documentada |
| D-04 | `elsalvadormaps.sv` con certificado TLS inválido | **Alta** (riesgo de seguridad) | `CERTIFICATE_VERIFY_FAILED` | No automatizable |
| D-05 | CENTA Hub anuncia descarga pero su API devuelve 0 ítems | **Alta** (bloquea suelos) | `numberMatched: 0` | PENDING_VALIDATION |
| D-06 | CNR «Descargas» no contiene datos geográficos | **Media** | 0 enlaces `.zip/.shp/.gpkg/.csv` | Documentado |
| D-07 | `marn.gob.sv` 503 y `geoportal.marn.gob.sv` 522 | **Alta** (sin hidrología oficial) | 2 intentos | UNAVAILABLE |
| D-08 | `one.gob.sv` no resuelve DNS | **Media** | `getaddrinfo failed` | UNAVAILABLE |
| D-09 | STAC de Earth Search rechaza `datetime` sin hora (HTTP 400) | **Baja** (era error del cliente) | `{"code":"BadRequest"}` | Corregido en el script |
| D-10 | CHIRPS no declara `nodata` en metadatos | **Media** (riesgo de tratar −9999 como dato) | `nodata: None` | Regla: enmascarar −9999 explícitamente |
| D-11 | ADM2 de Fase 1 tiene 272 polígonos y la división oficial 262 distritos | **Alta** (uniones incorrectas) | README de Fase 1 vs reforma 2023 | Requiere tabla de correspondencia |
| D-12 | Anuario MAG 2022-2023: URL indexada devuelve 404 | **Baja** | 404 | Usar edición 2021-2022 |

---

## 4. Calidad por tipo de fuente

| Tipo | Fortaleza | Debilidad sistemática | Uso recomendado |
|---|---|---|---|
| **Estadística nacional (BCR/MAG)** | Verdad oficial, cobertura nacional | PDF maquetado, sin API, sin licencia | Verdad de referencia; extracción manual auditada |
| **Geoportal nacional (CNR/MARN/CENTA)** | Producto de mayor resolución | Disponibilidad intermitente, sin descarga abierta | Solicitud institucional, no pipeline |
| **Reanálisis global (ERA5/AgERA5)** | Consistente, serie larga | Resolución 0,1°; sesgo topográfico | Forzamiento de modelos, con corrección declarada |
| **Satélite (Sentinel-2)** | 10 m, acceso abierto | Nubes; requiere verdad de campo | Índices y fenología, no identificación de cultivo |
| **Predicción global de suelo (SoilGrids)** | Cobertura completa | 250 m; error en relieve; sin nutrientes | Prior de paisaje |
| **Censos** | Representatividad | Agregación, secreto estadístico | Denominadores y estructura |
| **Sintético (Nemotron)** | Heterogeneidad y lenguaje | No representativo; sin dotaciones | Simulación exploratoria |

---

## 5. Pruebas que **no** se pudieron ejecutar

| Prueba | Motivo |
|---|---|
| Validación de CHIRPS contra estaciones SNET | No hay series de estación descargables |
| Validación de SoilGrids contra perfiles CENTA | Sin acceso a CENTA |
| Extracción y control de totales del CAP 2025 | Requiere parseo de PDF y revisión humana; fuera del alcance de esta fase |
| Descarga de AgERA5/ERA5/IMERG | Requiere credenciales que no se poseen |
| Descarga de Sentinel-1 | Requiere OAuth2 CDSE |
| Validación de licencia de HydroSHEDS | EULA no leído en esta fase |

Se declaran como pendientes, **no** como superadas.

---

## 6. Reglas de calidad derivadas

1. **Validar nulos antes de aceptar un 200.** Un HTTP 200 con `null` es un fallo.
2. **Verificar el CRS y la resolución real** del ráster, no la del metadato.
3. **Enmascarar `nodata`** aunque la fuente no lo declare.
4. **Fijar y verificar rutas de descarga** en cada ejecución (Geofabrik cambió).
5. **No usar certificados inválidos** en pipelines; si un sitio los tiene, se
   excluye y se reporta.
6. **Comparar agregados** con el censo antes de publicar cualquier modelo.
7. **Registrar hash** de cada archivo y de la versión del dataset remoto.

---

## 7. Veredicto

Las muestras descargadas son **íntegras y utilizables** para prototipar
clima, geometría administrativa y lectura de COG. La base nacional de suelos,
hidrología y catastro **no está disponible** por canales abiertos verificados, y
tres portales institucionales presentaron fallos técnicos el día de la consulta.
Ninguna conclusión de este informe debe leerse como evaluación de la calidad
científica de CENTA, CNR o MARN: evalúa **el acceso**, no la institución.
