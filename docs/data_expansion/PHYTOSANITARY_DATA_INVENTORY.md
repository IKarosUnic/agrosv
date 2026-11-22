# PHYTOSANITARY_DATA_INVENTORY — AGROSV Fase 3

**Fecha:** 2026-11-22 · **Evidencia:** sondas propias + GBIF.
**Regla:** una observación confirmada, un riesgo modelado y un reporte no
verificado son **tres cosas distintas** y se etiquetan por separado.

---

## 1. Fuentes

| ID | Fuente | Contenido | Acceso observado | Estado |
|---|---|---|---|---|
| `ippc_sv` | IPPC — perfil de El Salvador | Estatus fitosanitario, reportes de plagas | 200 (82.958 B) | **VERIFIED** (portal) |
| `oirsa_uris` | OIRSA — alertas regionales | Plagas cuarentenarias, alertas | 200 (372 B, aplicación JS) | **DOCUMENTED** |
| `isc_cafe` | ISC — Instituto Salvadoreño del Café | Roya, broca, boletines | **403** | **RESTRICTED** |
| `mag_centa` | MAG/CENTA — vigilancia fitosanitaria | Monitoreo, alertas nacionales | Sin dataset abierto verificado | **PENDING_VALIDATION** |
| `eppo_gd` | EPPO Global Database | Distribución de plagas | 200 | **VERIFIED** (portal) |
| `cabi_cpc` | CABI Crop Protection Compendium | Fichas de plagas y enfermedades | **403** (suscripción) | **RESTRICTED** |
| `gbif_api` | GBIF | Ocurrencias de especies | 200 | **VERIFIED** (muestra descargada) |
| `protectedplanet_sv` | UNEP-WCMC | Áreas protegidas | 200 | **VERIFIED** (portal) |
| `wdpa_api` | Protected Planet API | WDPA | **401** (requiere token) | **RESTRICTED** |
| `gfw_hansen` | Global Forest Watch | Cobertura forestal, alertas | 200 | **VERIFIED** |
| `marn_areas` | MARN | Áreas naturales protegidas | Documentado | **DOCUMENTED** |

**Ningún sistema nacional de vigilancia fitosanitaria publica datos crudos
descargables.** IPPC muestra el perfil del país; OIRSA publica alertas en una
aplicación web; el ISC bloquea el acceso automatizado.

---

## 2. Evidencia GBIF (biodiversidad)

```
GET https://api.gbif.org/v1/occurrence/search?country=SV&limit=300&hasCoordinate=true
→ 200, 2.125.141 B (300 registros)
count total con coordenadas: 1.240.548
```

Muestra: `data/samples/phase3/gbif_sv/` (sha256 `c2bf4264b01d…`).

**Advertencia:** 1,24 millones de registros no significan 1,24 millones de
observaciones independientes; incluyen registros de museo, observaciones
ciudadanas y duplicados entre publicadores. Cada registro trae su propia licencia
(CC0, CC BY, CC BY-NC), por lo que **no se puede relicenciar el conjunto en
bloque**.

---

## 3. Plagas y enfermedades por cultivo (referencia)

| Cultivo | Plaga principal | Enfermedad principal | Fuente de confirmación |
|---|---|---|---|
| Maíz | Gusano cogollero (*Spodoptera frugiperda*) | Mancha de asfalto (*Phyllachora maydis* complex) | Literatura; MAG/CENTA (boletines) |
| Frijol | Mosca blanca (*Bemisia tabaci*) | Mosaico dorado del frijol (BGMV) | Literatura; MAG/CENTA |
| Café | Broca (*Hypothenemus hampei*) | Roya (*Hemileia vastatrix*) | ISC (403, boletines no descargables) |
| Caña | Taladrador (*Diatraea* spp.) | — | Literatura |
| Arroz | — | Añublo bacteriano | Literatura |
| Hortalizas | Trips, ácaros, minadores | Tizón, mildiu | MAG/CENTA |

**Estas asociaciones son referencia agronómica, no un registro de brotes.** Para
declarar un brote se necesita fecha, lugar, superficie afectada y fuente oficial.

---

## 4. Vigilancia y riesgo

| Componente | Disponibilidad | Comentario |
|---|---|---|
| Brotes documentados con fecha y lugar | **No hay dataset abierto** | Solo notas de prensa y boletines PDF |
| Distribución geográfica de plagas | Parcial (EPPO/CABI, por país) | No por municipio |
| Condiciones de riesgo (clima favorable) | Modelable con clima + fenología | Es **riesgo modelado**, no observación |
| Especies invasoras | GBIF / EPPO | Registros dispersos |
| Polinizadores | GBIF (parcial) | Sin monitoreo nacional |
| Áreas protegidas | WDPA / MARN | Verificar límites y categorías |
| Cobertura forestal | GFW/Hansen 30 m | Cobertura de árboles, no bosque primario |
| Corredores ecológicos | MARN (documentado) | Sin capa GIS verificada |

---

## 5. Separación obligatoria de capas

| Etiqueta | Qué significa | Ejemplo |
|---|---|---|
| `OBSERVED` | Registro con fecha, lugar y fuente | Trampa de broca en finca X, 2025-08 |
| `REPORTED` | Reporte institucional o de prensa sin verificación independiente | «Se detectó roya en la zona» |
| `MODELLED` | Índice de riesgo calculado por AGROSV | Riesgo de roya por humedad y temperatura |
| `SUITABILITY` | Aptitud climática del patógeno | Zonas térmicamente favorables |

Nunca se presenta `MODELLED` como `OBSERVED`.

---

## 6. Vacíos críticos

| Vacío | Consecuencia | Prioridad |
|---|---|---|
| Red nacional de trampeo con datos abiertos | Sin línea base de brotes | **Alta** |
| Boletines del ISC accesibles por API | Roya/broca no automatizables | **Alta** |
| Registro de aplicaciones de plaguicidas | Sin exposición ni resistencia | Media |
| Distribución municipal de plagas | Sin análisis territorial | Media |
| Lista de variedades resistentes | Sin recomendación varietal | Media |

---

## 7. Ruta de integración

1. **GBIF** como contexto de biodiversidad, con licencia por registro y sin
   relicenciar en bloque.
2. **Solicitud al MAG/CENTA** de los datos de vigilancia (trampeo, alertas) con
   acuerdo de uso.
3. **Modelo de riesgo** solo después de tener clima validado y fenología; se
   publica como `MODELLED`.
4. **No publicar** mapas de «plaga presente» derivados de modelos como si fueran
   detecciones.

---

## 8. Evidencia reproducible

- `research/raw/phase3/probes_20261122_r3.json`: `ippc_sv`, `oirsa_home`,
  `isc_cafe`, `eppo_gd`, `cabi_cpc`, `gbif_api`, `protectedplanet_sv`,
  `wdpa_api`, `gfw_hansen`.
- `data/samples/phase3/gbif_sv/sample.json` — 300 registros con sus licencias.
