# HYDROLOGICAL_DATA_INVENTORY — AGROSV Fase 3

**Fecha de consulta:** 2026-11-22 · **Evidencia:** `research/raw/phase3/probes_20261122_r3.json`.
**Regla transversal:** proximidad a un río, lago o pozo **no** implica derecho de
uso, caudal disponible ni viabilidad técnica de extracción.

---

## 1. Estado de las fuentes

| ID | Fuente | Contenido | Acceso observado | Estado |
|---|---|---|---|---|
| `snet_hidrologia_ver` | MARN/SNET — hidrología | Atlas hidrológico, red hídrica | 200 (33.552 B) | **VERIFIED** (portal) |
| `snet_hidrologia` | MARN/SNET — atlas | Página histórica del atlas | 200 (360 B, redirección/JS) | **DOCUMENTED** |
| `marn_geoportal` | Geoportal MARN | Servicios REST | **522** | **UNAVAILABLE** |
| `marn_home` | MARN | Portal institucional | **503** (2 intentos) | **UNAVAILABLE** |
| `rmgir_subcuencas` | RMGIR (tercero) | Subcuencas de El Salvador | **404** en la ruta documentada | **UNAVAILABLE** |
| `anda_home` | ANDA | Agua potable y saneamiento | **403** (bloqueo a no navegador) | **RESTRICTED** |
| `hydrosheds` / `hydrobasins` / `hydroatlas` | WWF/USGS | Red hídrica, cuencas, atributos | 200 | **VERIFIED** (portal) |
| `fao_aquastat` | FAO | Estadísticas de agua por país | 200 | **VERIFIED** |
| `fao_gmia` | FAO | Superficie regada | 200 | **VERIFIED** |
| `jrc_global_surface_water` | JRC | Agua superficial 1984–2021 | 200 | **VERIFIED** |
| `whymap` | BGR/UNESCO | Acuíferos transfronterizos | 200 | **VERIFIED** |
| `wri_aqueduct` | WRI | Estrés hídrico, riesgo | 200 | **VERIFIED** |

**Ningún servicio nacional de datos hidrológicos crudos (aforos, niveles
freáticos) respondió con datos descargables en esta ronda.** El atlas del SNET es
documento/visor; el geoportal del MARN está caído (522).

---

## 2. Aguas superficiales

| Elemento | Fuente disponible | Formato | Limitación |
|---|---|---|---|
| Ríos y quebradas | OSM (extracto nacional), SNET atlas | Vectorial / PDF | OSM es colaborativo: topología y nombres incompletos fuera de rutas principales |
| Lagos, lagunas, embalses | OSM; JRC Global Surface Water | Vectorial / ráster 30 m | JRC detecta agua, no distingue uso ni calidad |
| Cuencas y subcuencas | HydroBASINS (niveles 1–12) | Shapefile/GeoPackage | Unidades globales; no coinciden con la delimitación oficial del PNGIRH 2017 |
| Subcuencas nacionales | PNGIRH 2017 (Pfafstetter, >10 km²), DEM 1:25.000 | Informe PDF; geodatabase no verificada | Es la unidad oficial de referencia; requiere solicitud |
| Divisorias y red de drenaje | Derivables del DEM 30 m (motor de hidrología de Fase 2) | Ráster/vector | Sin calibrar; el DEM es un DSM (incluye vegetación/edificios) |
| Humedales | No hay capa nacional verificada | — | Vacío; OSM tiene cobertura parcial |
| Historial de inundaciones | MARN — mapa preliminar de susceptibilidad; perfil de riesgo 2014 | PDF/visor | No es capa GIS; requiere vectorización etiquetada |

**Escala de trabajo:** el motor de hidrología de AGROSV (`backend/agrosv/science/hydrology.py`)
ya calcula priority-flood, D8, acumulación, cuenca aguas arriba y factor LS sobre
el DEM de 30 m. Es reproducible y **no está calibrado**: no hay aforos para
ajustar el coeficiente de escorrentía ni el tiempo de concentración.

---

## 3. Aguas subterráneas

| Necesidad | Estado | Nota |
|---|---|---|
| Mapa de acuíferos nacional | **DOCUMENTED** (MARN/SNET; WHYMAP solo transfronterizo) | Sin geodatabase verificada |
| Zonas de recarga | **No verificada** | Requiere MARN o estudio hidrogeológico |
| Inventario de pozos | **No verificado** | ANDA/MARN; datos posiblemente restringidos por seguridad |
| Niveles freáticos históricos | **No disponible públicamente** | Sin serie descargable identificada |
| Profundidad del agua | **No disponible** | — |
| Calidad química del agua subterránea | **No disponible** | — |

**Consecuencia:** AGROSV no puede modelar agua subterránea en Fase 3. Cualquier
afirmación sobre disponibilidad de pozo debe limitarse a «existe un punto de
agua a X km según OSM», nunca a «hay agua extraíble».

---

## 4. Disponibilidad y calidad

| Variable | Fuente | Resolución | Estado |
|---|---|---|---|
| Precipitación | CHIRPS v3, AgERA5, IMERG, estaciones SNET | 0,05° / 0,1° / 0,1° / puntual | CHIRPS **VERIFIED**; AgERA5/IMERG con cuenta |
| Caudal (aforos) | SNET/MARN | Puntual | **No descargable verificado** |
| Escorrentía | Derivada de DEM + precipitación | 30 m / 0,05° | Modelo, no observación |
| Infiltración / recarga | No medida | — | Solo estimable con modelo calibrado (no disponible) |
| Evapotranspiración | AgERA5, Open-Meteo (ET₀ FAO-56) | 0,1° | Open-Meteo **VERIFIED** sin clave |
| Calidad (pH, CE, contaminantes) | No hay serie nacional abierta verificada | — | Vacío crítico |
| Estaciones hidrométricas | SNET (ubicación en atlas) | Puntual | Metadatos; series no verificadas |
| Sequías | MARN/SNET resúmenes climatológicos; CHIRPS SPI calculable | — | Índice calculable, no «sequía oficial» |

**Advertencia sobre SPI/sequía:** CHIRPS permite calcular SPI-3/SPI-6 con
metodología declarada, pero el resultado es un **índice AGROSV**, no un
dictamen oficial. El estado de sequía oficial lo declara el MARN.

---

## 5. Infraestructura hídrica

| Elemento | Fuente | Estado |
|---|---|---|
| Distritos de riego y canales | MAG (anuario, informes de riego); no hay capa GIS verificada | **DOCUMENTED** |
| Presas y embalses | OSM; CEL (hidroeléctricas) | Parcial |
| Captaciones y pozos agrícolas | Sin inventario abierto verificado | Vacío |
| Sistemas comunitarios de agua | ANDA (403); sin datos abiertos | **RESTRICTED** |
| Superficie regada | FAO GMIA (global, ~10 km); CAP 2025 declara riego por productor | **VERIFIED** (portal) / agregado censal |

La superficie regada del CAP 2025 es la referencia nacional; GMIA solo sirve
como contraste internacional y no debe publicarse como cifra de El Salvador.

---

## 6. Fuentes internacionales: qué aportan y qué no

| Fuente | Aporta | No aporta |
|---|---|---|
| HydroSHEDS / HydroBASINS | Red de drenaje global coherente, cuencas anidadas | Delimitación oficial salvadoreña; caudales |
| HydroATLAS | Atributos climáticos, topográficos, antropogénicos por cuenca | Mediciones locales |
| JRC Global Surface Water | Persistencia de agua 1984–2021, 30 m | Uso del agua, derechos, calidad |
| WHYMAP | Acuíferos transfronterizos | Pozos, niveles, recarga local |
| AQUASTAT | Agregados nacionales de agua y riego | Datos de cuenca o parcela |
| WRI Aqueduct | Estrés hídrico y riesgo de inundación | Caudal observado |
| GMIA | Superficie regada global | Riego real por parcela |

---

## 7. Ruta de integración recomendada

1. **Ahora (sin permisos):** publicar red hídrica OSM + HydroBASINS nivel 6–8
   como capas separadas, con nota de que no son la delimitación oficial; añadir
   JRC GSW como máscara de agua permanente (30 m).
2. **Ahora:** calcular acumulación y cuencas desde el DEM y compararlas con
   HydroBASINS para cuantificar la discrepancia (test de validación cruzada).
3. **Solicitud institucional:** PNGIRH 2017 (subcuencas oficiales) y series de
   aforos del SNET; sin ellos no hay calibración posible.
4. **Solicitud:** inventario de pozos y niveles (MARN/ANDA), con acuerdo de
   confidencialidad si aplica.
5. **No hacer:** presentar recarga, disponibilidad o «déficit hídrico» como
   resultados antes de tener caudales observados.

---

## 8. Evidencia

```
GET https://www.snet.gob.sv/ver/hidrologia/                     → 200, 33.552 B
GET https://www.snet.gob.sv/ver/meteorologia/                   → 200, 31.535 B
GET https://geoportal.marn.gob.sv/                              → 522
GET https://www.marn.gob.sv/                                    → 503
GET https://www.anda.gob.sv/                                    → 403
GET https://www.hydrosheds.org/products                         → 200, 47.988 B
GET https://www.hydrosheds.org/products/hydrobasins             → 200, 47.551 B
GET https://global-surface-water.appspot.com/download           → 200, 85.949 B
GET https://www.fao.org/aquastat/en/                            → 200, 280.634 B
GET https://www.whymap.org/whymap/EN/Home/whymap_node.html      → 200, 17.340 B
```

Ninguna de estas respuestas es un dataset hidrológico: son portales. La única
capa hidrológica realmente **descargada y validada** en esta fase es el ráster
CHIRPS de precipitación (ver `CLIMATE_DATA_INVENTORY.md`) y las capas OSM ya
procesadas en Fase 1.
