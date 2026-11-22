# PHASE_3_FINAL_REPORT — AGROSV

**Fecha:** 2026-11-22 · **Alcance:** expansión nacional de datos (Fase 3).
**Estado:** inventario, verificación y muestras completados; integración de
datos nacionales restringidos **no** realizada (requiere convenios).

---

## 1. Resumen ejecutivo

Se ejecutaron **118 sondas HTTP** sobre fuentes nacionales e internacionales
(85 VERIFIED, 14 DOCUMENTED, 11 UNAVAILABLE, 7 RESTRICTED, 1 PENDING_VALIDATION),
se descargaron y validaron **9 muestras mínimas** y se
produjeron **18 documentos** de inventario, calidad, licencias, arquitectura e
interoperabilidad.

El resultado principal no es una colección de datasets: es un **mapa verificado de
qué existe, cómo se consigue y qué no se puede usar todavía**. Tres hallazgos
cambian decisiones de diseño:

1. **SoilGrids ya no publica las propiedades hidráulicas** (`wv0033`/`wv1500`)
   que el registro anterior daba por disponibles para AquaCrop; su API REST
   devuelve `null`. El balance hídrico necesita pedotransferencia declarada o
   datos CENTA.
2. **La capa administrativa de Fase 1 (272 polígonos) no coincide con los 262
   distritos oficiales ni con los 44 municipios de 2023.** Sin tabla de
   correspondencia, cualquier unión con el censo es incorrecta.
3. **Los portales nacionales no ofrecen descarga abierta verificada**: CENTA
   responde 403 y su Hub devuelve 0 ítems; el CNR vende sus productos y su página
   de descargas solo contiene documentos administrativos; el MARN está caído
   (503/522); *El Salvador Maps* tiene certificado TLS inválido.

---

## 2. Trabajo realizado

| Actividad | Resultado | Evidencia |
|---|---|---|
| Inspección del repositorio | Fase 1 y 2 reutilizadas; sin duplicar capas | `README.md`, `docs/PHASE_2_IMPLEMENTATION_REPORT.md` |
| Sondas de fuentes | 118 URLs, 85 VERIFIED | `research/raw/phase3/probes_20261122_r3.json` |
| Muestras descargadas | 9, con hash y validación | `data/manifests/phase3_samples.json` |
| Scripts reproducibles | Sondeo y muestreo | `scripts/06_…py`, `scripts/07_…py` |
| Documentos | 18 entregables | `docs/data_expansion/` |
| Correcciones al registro | 8 afirmaciones previas corregidas | `DATA_SOURCE_REGISTRY.md` §5 |

### 2.1 Muestras validadas

| Muestra | Validación |
|---|---|
| NASA POWER (2019–2025, 3 variables) | JSON, 2.557 días |
| Open-Meteo (ET₀ FAO-56, 2019–2025) | JSON, ET₀ presente |
| Banco Mundial (superficie agrícola SLV) | JSON de indicador |
| GBIF (300 ocurrencias SV) | JSON con coordenadas |
| SoilGrids REST (punto) | **`mean: null`** — defecto documentado |
| CHIRPS v3 (1 día global) | `rasterio`: EPSG:4326, 7200×2400, 0,05°, float32 |
| Sentinel-2 STAC + COG | Item `S2B_15PZR_20250227_0_L2A`; lectura por rango 206 |
| Nemotron (3 filas) | JSON sintético |
| geoBoundaries ADM0 | GeoJSON nacional |

---

## 3. Entregables

| Documento | Contenido |
|---|---|
| `NATIONAL_GEODATA_INVENTORY.md` | División territorial, catastro, topografía, geología, cobertura |
| `SOIL_DATA_INVENTORY.md` | CENTA, SoilGrids, variables, comparación nacional/global |
| `HYDROLOGICAL_DATA_INVENTORY.md` | Aguas superficiales, subterráneas, calidad, infraestructura |
| `CLIMATE_DATA_INVENTORY.md` | Fuentes, variables, almanaque agroclimático |
| `AGRICULTURAL_KNOWLEDGE_DATABASE.md` | Catálogo de cultivos, producción, sistemas, vacíos |
| `CROP_PARAMETERS_CATALOG.md` | Esquema y parámetros por cultivo (REF/NAC/GAP) |
| `CENSUS_AND_SOCIOECONOMIC_DATA.md` | CPV 2024, CAP 2025, 2007, desagregaciones |
| `PHYTOSANITARY_DATA_INVENTORY.md` | Plagas, vigilancia, biodiversidad, áreas protegidas |
| `AGRICULTURAL_ECONOMIC_DATA.md` | Precios, costos, comercio, comercialización |
| `SATELLITE_DATA_INVENTORY.md` | S2, S1, Landsat, MODIS, cobertura, acceso COG |
| `NEMOTRON_PERSONAS_INTEGRATION.md` | Hechos verificados, arquetipos, metodología multiagente |
| `DATA_SOURCE_REGISTRY.md` | Registro maestro con estados y evidencia |
| `DATA_QUALITY_REPORT.md` | Validación de muestras y 12 defectos |
| `DATA_LICENSE_AND_ACCESS_REPORT.md` | Licencias, restricciones, decisiones |
| `DATA_STORAGE_ARCHITECTURE.md` | Estructura, nombres, manifiestos, tamaños |
| `GEOSPATIAL_INTEROPERABILITY.md` | CRS, IDs, unidades, metadatos, estándares OGC |
| `DATA_GAPS_AND_LIMITATIONS.md` | 30 vacíos priorizados y 10 afirmaciones prohibidas |
| `PHASE_3_FINAL_REPORT.md` | Este documento |

---

## 4. Criterios de aceptación

| Criterio | Estado | Evidencia |
|---|---|---|
| Investigación de fuentes nacionales | **Cumplido** | 50 IDs nacionales/regionales en el registro |
| Comparación con fuentes internacionales | **Cumplido** | Matrices en suelos, clima, hidrología, satélite |
| Registro de procedencia | **Cumplido** | Manifiestos con hash y fecha |
| Documentación de licencias | **Cumplido** | Informe de licencias + columna por fuente |
| Identificación de datos descargables | **Cumplido** | §2 del registro + §5 de geodatos |
| Validación de muestras | **Cumplido** | 9 muestras, 8 correctas, 1 defecto documentado |
| Documentación de resolución y cobertura | **Cumplido** | Por fuente, con `effective_resolution` |
| Identificación de vacíos | **Cumplido** | 30 vacíos priorizados |
| Diseño de almacenamiento | **Cumplido** | Estructura y política de versionado |
| Estandarización geoespacial | **Cumplido** | CRS, IDs, unidades, metadatos |
| Compatibilidad con la arquitectura actual | **Cumplido** | Sin modificar endpoints ni capas de Fase 1 |

---

## 5. Prioridades recomendadas

### P0 — ahora (sin permisos nuevos)

1. **Tabla de correspondencia territorial** 262 distritos ↔ 44 municipios ↔ 14
   departamentos, y reconciliación de la capa histórica de 272 polígonos.
2. **CHIRPS v3 pentadal + NASA POWER** como base climática operativa, con
   `effective_resolution` declarada.
3. **Serie NDVI 10 m por AOI piloto** con `sentinel-2-c1-l2a` y máscara SCL.
4. **Extracción auditada** de las tablas del CAP 2025 (3 entregas) a CSV.

### P1 — con solicitud institucional

5. CENTA: datos de suelos + licencia de derivados.
6. SNET/MARN: series de estaciones y aforos.
7. CNR: ficha técnica y licencia de *El Salvador Maps*; cotización de piloto.
8. BCR: tabulados municipales del CAP y microdatos del CPV con salvaguardas.

### P2 — después de P0/P1

9. Sentinel-1 para época lluviosa.
10. Modelo de riesgo fitosanitario (`MODELLED`, no observado).
11. Motor multiagente con dotaciones derivadas del censo.
12. Repositorio externo con DOI para datasets derivados publicables.

---

## 6. Primeros datasets a implementar

| Orden | Dataset | Fuente | Por qué |
|---|---|---|---|
| 1 | Precipitación pentadal SV | CHIRPS v3 | Gratis, validado, serie larga |
| 2 | Clima diario de punto | NASA POWER | Sin clave, cubre variables faltantes |
| 3 | Límites ADM1 + tabla distrital | geoBoundaries + BCR/CNR | Base de toda unión |
| 4 | Serie NDVI por AOI | Sentinel-2 c1-l2a | Monitoreo sin descargar escenas |
| 5 | Suelo 0–30 cm (ya existente) | SoilGrids | Reutilizar Fase 1, añadir incertidumbre |
| 6 | Producción departamental | CAP 2025 | Verdad de referencia |

---

## 7. Lo que no se hizo (y por qué)

| No realizado | Motivo |
|---|---|
| Descarga de datasets nacionales completos | Sin licencia ni acceso verificado |
| Integración de CENTA/CNR/MARN | Requiere convenio o compra |
| Extracción completa de PDF censales | Requiere revisión humana; se dejó el procedimiento |
| Implementación de modelos de cultivo | Sin parámetros locales calibrados |
| Descarga de AgERA5/ERA5/IMERG/Sentinel-1 | Requieren credenciales |
| Validación de CHIRPS contra estaciones | Sin series de estación |
| Simulador de productores | Diseñado, no implementado |

---

## 8. Riesgos abiertos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| CENTA/CNR no responden | Media | Alto | Piloto con datos abiertos; escalar por convenio |
| Licencias no comerciales limitan el producto | Media | Alto | Diseñar sustitución (DSSAT, ERA5) |
| Portal nacional cambia de URL | Alta | Medio | Sondas en cada fase (R-10) |
| Confusión entre predicción y medición | Media | **Muy alto** | Etiquetas en el dato, no solo en la UI |
| Series satelitales con corte (MODIS) | Alta | Medio | Aviso y migración planificada |

---

## 9. Conclusión

AGROSV tiene ahora un inventario nacional trazable y una lista explícita de lo
que falta. La fase se completó en su parte verificable: **se sabe qué existe, con
qué resolución, bajo qué licencia y con qué evidencia**. Lo que no se completó —
acceso a suelos medidos, hidrología observada y catastro — no es un fallo de
investigación: es una restricción institucional documentada, con la ruta de
solicitud definida y el impacto cuantificado en `DATA_GAPS_AND_LIMITATIONS.md`.

Ninguna cifra de este informe se inventó; las que no se pudieron verificar se
marcaron como `DOCUMENTED`, `RESTRICTED`, `UNAVAILABLE` o `PENDING_VALIDATION`.
