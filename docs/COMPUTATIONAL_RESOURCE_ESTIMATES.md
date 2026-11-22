# Computational Resource Estimates

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** **estimación calculada, no medida**.

Todas las cifras se derivan de la superficie nacional y de la resolución nativa
de cada producto. **No** son benchmarks: ningún módulo de Fase 2 se ha ejecutado
a escala nacional. Se marcan como `calc` (derivadas) o `est` (supuestos).

---

## 1. Base de cálculo

| Dato | Valor | Fuente |
|---|---|---|
| Superficie nacional | 20.966,4 km² | Fase 1 (dissolve ADM1) |
| DEM 1″ | 9.159 × 5.311 = **48,6 Mpx** | Fase 1 |
| DEM 30 m métrico | 9.217 × 5.516 = **50,8 Mpx** | Fase 1 |
| Píxeles a 10 m | 209,7 Mpx | calc |
| Píxeles a 20 m | 52,4 Mpx | calc |
| Píxeles a 30 m | 23,3 Mpx | calc |
| Píxeles a 250 m | 0,34 Mpx | calc |
| Celdas 0,05° (~5,6 km) | ≈ 679 | calc |
| Celdas 0,1° (~11,1 km) | ≈ 170 | calc |
| Celdas 0,25° (~27,8 km) | ≈ 27 | calc |
| Celdas 0,5° (~55,6 km) | ≈ 7 | calc |

Fórmula: `celdas = 20.966,4 km² / (lado_celda_km)²`.
A 0,1° el lado es ≈ 11,1 km y la celda ≈ 123 km².

---

## 2. Volumen por producto (una fecha nacional)

Supone `uint16` para reflectancia e índices, `float32` para SAR y variables
continuas, sin compresión.

| Producto | Resolución | Bandas | Bytes/px | Tamaño/fecha |
|---|---|---|---|---|
| Sentinel-2 L2A | 10 m | 10 | 2 | **4,19 GB** |
| Sentinel-2 L2A | 20 m | 10 | 2 | 1,05 GB |
| Sentinel-1 GRD | 10 m | 2 (VV+VH) | 4 | **1,68 GB** |
| Landsat 8/9 C2 | 30 m | 7 | 2 | 0,33 GB |
| MODIS MOD13Q1 | 250 m | 2 | 2 | **1,3 MB** |
| NDVI derivado | 10 m | 1 | 2 | 0,42 GB |
| AgERA5 (1 variable) | 0,1° | 1 | 4 | 0,25 MB/año |
| CHIRPS diario | 0,05° | 1 | 4 | 1,0 MB/año |
| SoilGrids (7 prof. × 3 prop.) | 250 m | 21 | 4 | **28 MB** |

**Lectura clave:** el coste no está en el clima (megas), está en las imágenes
ópticas y radar (gigas por fecha).

---

## 3. Escenarios de almacenamiento anual

`est`: se asume 40 fechas útiles de S2 al año (nubosidad), 40 de S1 y 23 de
Landsat; se archiva **NDVI/NDMI + máscara de nubes**, no la reflectancia
completa, salvo para escenas piloto.

| Escenario | Qué guarda | Año 1 | Año 5 |
|---|---|---|---|
| **A. Mínimo** (índices) | NDVI/NDMI 10 m + máscaras | 40 × 0,42 GB = **17 GB** | 85 GB |
| **B. Radar** | S1 VV/VH a 20 m | 40 × 0,42 GB = **17 GB** | 85 GB |
| **C. Completo** | S2 reflectancia + S1 + Landsat | 4,19×40 + 1,68×40 + 0,33×23 = **242 GB** | 1,2 TB |
| **D. Clima y suelo** | CHIRPS, AgERA5, SoilGrids | **< 1 GB** | < 1 GB |

Recomendación: escenario **A + D** para el país completo; **C** solo en 2–3
áreas piloto (p. ej. un departamento ≈ 1/14 del volumen).

Con compresión COG + deflate (≈ 2:1 en índices) los volúmenes bajan a la mitad;
no se asume en la tabla.

---

## 4. Cómputo por operación

`est`: se asume una máquina de 8 núcleos, 32 GB RAM, sin GPU, y procesamiento
por ventanas de 512 × 512 con `rasterio`/`dask`.

| Operación | Entrada | Coste estimado | Nota |
|---|---|---|---|
| Índice NDVI nacional 10 m | 2 bandas × 210 Mpx | 2–5 min, ~4 GB RAM | streaming por ventanas |
| Serie de 40 fechas NDVI | 40 mosaicos | 2–3 h | paralelizable por ventana |
| Clasificación supervisada (RF, 50 árboles) | 23 Mpx × 10 bandas | 10–30 min | memoria > 8 GB si no hay chunking |
| Detección de cambios (2 fechas) | 2 × 1 banda | 1–2 min | umbral simple |
| Simulación de cultivo por celda | 1 punto, 1 ciclo | < 1 s (AquaCrop/DSSAT) | — |
| Simulación 170 celdas × 5 fechas de siembra | 850 corridas | 5–15 min | paralelizable |
| Delimitación de cuencas D8 nacional | DEM 48,6 Mpx | 3–8 min, ~4 GB | requiere relleno previo |
| SWAT+ cuenca piloto | 1 subcuenca | horas a días | calibración aparte |
| Balance hídrico 170 celdas × 365 d | ~62.000 filas | segundos | tabla, no raster |
| RUSLE nacional 30 m | 5 factores × 23 Mpx | 2–5 min | — |

**Cuello de botella real:** descarga y almacenamiento de imágenes, no el cálculo.

---

## 5. Límites de las fuentes (cuotas)

| Fuente | Límite | Consecuencia |
|---|---|---|
| Copernicus Data Space | 12 TB / 30 días | suficiente para NDVI nacional |
| Earthdata (GPM, MODIS) | por sesión, no por volumen | requiere cuenta |
| CDS (ERA5/AgERA5) | cola por usuario | pedidos grandes tardan horas/días |
| USGS (Landsat) | por sesión | requiere cuenta |
| WorldClim/GAEZ | descarga manual | no automatizable a escala fina |

---

## 6. Requisitos por módulo

| Módulo | CPU | RAM | Disco | GPU |
|---|---|---|---|---|
| A Satélite | 8 núcleos | 16–32 GB | 100 GB–1 TB | no |
| B Fitosanitario | 2–4 | 4–8 GB | < 5 GB | no |
| C Simulación | 4–8 | 4–8 GB | < 1 GB | no |
| D Parcelas | 2 | 4 GB | < 10 GB | no |
| E Economía | 1–2 | 2 GB | < 1 GB | no |
| F Alertas | 2–4 | 4 GB | < 10 GB | no |
| G Urbano | 2 | 4 GB | < 5 GB | no |
| H Gemelo digital | 4 | 8 GB | proporcional a parcelas | no |
| I Cambio climático | 8–16 | 32 GB | 50–200 GB | no |
| J Hidrología | 4–8 | 16 GB | < 20 GB | no |
| K Biodiversidad | 4 | 8 GB | < 10 GB | no |
| L Comunidad | 2 | 4 GB | según fotos | no |
| M Experimentos | 4–8 | 8–16 GB | < 10 GB | no |

**Ningún módulo requiere GPU.** Un LLM local (Nemotron vía Ollama) sí, pero es
opcional y no se usa para cálculos científicos.

---

## 7. Comparación de arquitecturas de datos

| Opción | Ventaja | Límite | Veredicto |
|---|---|---|---|
| Archivos COG + GeoParquet | sin servidor, reproducible | concurrencia baja | **sí**, para lotes |
| SQLite + SpatiaLite | simple, portable | escritura concurrente | **sí**, para parcelas pequeñas |
| PostgreSQL + PostGIS | concurrencia, consultas | operación | **cuando** haya escritura multiusuario |
| Zarr | series multidimensionales | ecosistema | **sí**, para clima |

No se introduce PostGIS en Fase 2: no hay carga multiusuario que lo justifique.

---

## 8. Incertidumbre de estas cifras

1. Son cálculos geométricos y supuestos de bandas, **no mediciones**.
2. La nubosidad real cambia el nº de fechas útiles (40/año es un supuesto).
3. El tiempo depende del disco y de la red; no se mide aquí.
4. La compresión puede reducir el volumen a la mitad o menos.
5. Cualquier cifra publicada debe reemplazarse por un benchmark real cuando
   exista.

---

## 9. Dependencias y prioridad

Depende de: superficie nacional y DEM (Fase 1), resoluciones nativas declaradas
en `DATA_SOURCE_REGISTRY.md`, cuotas de CDSE/Earthdata/CDS. No depende de código
nuevo: es un documento de planificación.

**Prioridad:** transversal. Debe revisarse antes de aprobar cualquier módulo P2+
(Module A, I, J), y sustituirse por mediciones reales en cuanto exista el primer
lote ejecutado a escala nacional.

**Qué no hace:** no mide rendimiento real, no fija precios de infraestructura y
no incluye el coste de personal ni de gestión institucional.
