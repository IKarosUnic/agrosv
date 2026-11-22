# SOIL_DATA_INVENTORY — AGROSV Fase 3

**Fecha de consulta:** 2026-11-22 · **Método:** sondeo HTTP propio
(`scripts/06_probe_phase3_sources.py`, resultados en
`research/raw/phase3/probes_20261122_r3.json`) y lectura de documentación
institucional. **No** se declara medido lo que es predicción ni viceversa.

---

## 1. Resumen ejecutivo

| Fuente | Tipo de dato | Escala / resolución | Acceso | Estado |
|---|---|---|---|---|
| **CENTA — Mapa Digital de Suelos** | Medición de laboratorio + interpolación | ~11.000 muestras; escala declarada por CENTA | Visor público; descarga no verificada | **PENDING_VALIDATION** |
| **MAG — mapa temático de suelos (PDF)** | Cartografía derivada | No declarada | PDF descargable | **VERIFIED** (documento) |
| **SoilGrids 2.0 (ISRIC) — WebDAV** | Predicción global (machine learning) | 250 m, 6 profundidades | Descarga directa | **VERIFIED** |
| **SoilGrids 2.0 — REST API** | Ibídem | 250 m | API | **PENDING_VALIDATION** (devuelve `null`) |
| **ISRIC WoSIS** | Perfiles medidos | Puntual | Catálogo/consulta | **DOCUMENTED** |
| **FAO HWSD v2** | Armonización global | ~1 km | Descarga | **UNAVAILABLE** (404 en la ruta documentada) |
| **UES / publicaciones científicas** | Estudios locales | Variable | Según publicación | **PENDING_VALIDATION** |

**Regla de oro:** SoilGrids y CENTA **no son intercambiables**. SoilGrids es una
predicción a 250 m (~6,25 ha/píxel); CENTA es medición de suelo con muestras
georreferenciadas. AGROSV nunca debe fusionarlas en una sola capa ni promediar
una con otra.

---

## 2. Cobertura de variables requeridas

Leyenda: **SÍ** = disponible; **PARCIAL** = derivable o solo en algunas
profundidades; **NO** = no existe en la fuente; **?** = no verificable sin acceso.

| Variable | SoilGrids 2.0 | CENTA (declarado) | MAG (PDF) | Observación |
|---|---|---|---|---|
| Arena (%) | SÍ (`sand`, g/kg ÷10) | SÍ (textura) | Mapa de textura | — |
| Limo (%) | SÍ (`silt`) | SÍ | Mapa de textura | — |
| Arcilla (%) | SÍ (`clay`) | SÍ | Mapa de textura | Ya procesado en Fase 1 (0–30 cm) |
| Textura (clase) | PARCIAL (derivada de las 3 fracciones) | SÍ | SÍ | Clasificación USDA calculable |
| Profundidad efectiva | **NO** | SÍ | SÍ | Vacío crítico para AquaCrop |
| pH | SÍ (`phh2o`, ÷10) | SÍ (acidez) | SÍ | Fase 1 ya publica 0–30 cm |
| Materia orgánica | PARCIAL (`soc` → MO ≈ SOC × 1,724) | SÍ | ? | La conversión debe declararse |
| Carbono orgánico | SÍ (`soc`, dg/kg ÷10) | ? | ? | — |
| Nitrógeno total | SÍ (`nitrogen`, cg/kg ÷100) | ? | ? | No equivale a N disponible |
| Fósforo (P) | **NO** | SÍ | SÍ | SoilGrids no publica P |
| Potasio (K) | **NO** | SÍ | SÍ | — |
| Calcio (Ca) | **NO** | SÍ | SÍ | — |
| Magnesio (Mg) | **NO** | SÍ | SÍ | — |
| Micronutrientes (Cu, Zn, Fe, Mn) | **NO** | SÍ | SÍ | Solo CENTA los declara |
| CIC | SÍ (`cec`, mmol(c)/kg ÷10) | ? | ? | pH 7 |
| Retención de agua | **NO en la versión actual** | ? | ? | Ver §4, hallazgo correctivo |
| Drenaje (clase) | **NO** | ? | SÍ (limitantes) | — |
| Salinidad (CE) | **NO** | ? | ? | No hay CE en SoilGrids |
| Pedregosidad | PARCIAL (`cfvo`, fragmentos >2 mm) | ? | ? | No es pedregosidad superficial |
| Compactación | **NO** | **NO** | **NO** | Requiere medición de campo |
| Susceptibilidad a erosión | **NO** | SÍ (erosión/degradación) | SÍ | MARN publica además RUSLE 2015 |
| Densidad aparente | SÍ (`bdod`) | ? | ? | Necesaria para stock de C |

---

## 3. SoilGrids 2.0 — estado real verificado

### 3.1 WebDAV (vía recomendada)

```
GET https://files.isric.org/soilgrids/latest/data/            → 200, 6.709 B (listado)
GET .../phh2o/phh2o_0-5cm_mean.vrt                            → 200/206, 3.524.139 B (VRT)
GET .../clay/clay_0-5cm_mean.vrt                              → 206 (cabecera leída)
```

El listado de `latest/data/` devuelve **15 entradas** y solo estas variables:
`bdod, cec, cfvo, clay, landmask, nitrogen, ocd, ocs, phh2o, sand, silt, soc,
wrb` (+ `checksum.sha256.txt`, `README.md`).

**Hallazgo correctivo (afecta a la documentación previa de AGROSV):** el
registro anterior afirmaba que `wv0010`, `wv0033` y `wv1500` (agua volumétrica a
10/33/1500 kPa) estaban disponibles y eran «directamente utilizables por
AquaCrop». **No están en la versión `latest`**: `wv0033/` y `wv1500/` devuelven
HTTP 404 y no aparecen en el listado. Consecuencia:

- La capacidad de campo y el punto de marchitez **deben derivarse por
  pedotransferencia** (p. ej. Saxton & Rawls) a partir de arena/limo/arcilla y
  densidad aparente, declarando el método.
- Alternativa preferible: usar las propiedades hidráulicas que CENTA o un
  laboratorio nacional midan, cuando exista acceso.
- No se debe citar `wv0033` como dato de SoilGrids hasta que reappeared en el
  servicio; si se usa una versión anterior archivada, hay que registrar la fecha
  y el hash del archivo.

Profundidades estándar GlobalSoilMap: **0–5, 5–15, 15–30, 30–60, 60–100,
100–200 cm**. AGROSV Fase 1 agregó 0–30 cm para sus seis rásteres; ese agregado
es un **derivado AGROSV**, no un producto de ISRIC.

### 3.2 REST API — no utilizable

```
GET https://rest.isric.org/soilgrids/v2.0/properties/query?lon=-89.2&lat=13.7
    &property=phh2o&depth=0-5cm&value=mean
→ 200 {"...","values":{"mean":null}}
```

Muestra guardada: `data/samples/phase3/soilgrids_rest_point/` (357 B, sha256
`0c456e2042b3…`). Responde 200 con `mean: null`: un pipeline que no valide
nulos produciría una capa vacía «exitosa». **Prohibido usar esta API como
fuente.**

### 3.3 Incertidumbre

SoilGrids publica intervalos Q0.05/Q0.5/Q0.95 y una capa de incertidumbre por
propiedad. AGROSV debe arrastrar `uncertainty` cuando use el valor medio y no
presentar el mapa como verdad de campo. En El Salvador, con relieve volcánico y
500–2.700 m de altitud en distancias cortas, el error de un modelo global de
250 m es estructuralmente mayor que en llanuras.

---

## 4. CENTA — la fuente nacional decisiva

**Qué declara publicar** (página oficial `centa.gob.sv/mapa-digital-de-suelos`,
publicada 2026-06-05; y portal
`portal-de-mapas-digitales-del-centa-centa.hub.arcgis.com`):

- textura (arena, limo, arcilla), profundidad efectiva, materia orgánica, pH;
- nutrientes: potasio, fósforo, magnesio, calcio, cobre, zinc, hierro, manganeso;
- erosión y degradación; información climática, de relieve y potencial de cultivos;
- una capa específica para las **cordilleras cafetaleras**.

El portal se describe como «Buscar, Visualizar, **Descargar** Crear».

**Evidencia del sondeo (2026-11-22):**

| Prueba | Resultado |
|---|---|
| `centa.gob.sv/mapa-digital-de-suelos` | **403** (bloqueo a clientes no navegador) |
| `centa.gob.sv/` | **403** |
| Portal Hub (HTML) | **200** |
| `…hub.arcgis.com/api/search/v1/collections/all/items?limit=50` | **200 con `numberMatched: 0`** |
| `…/collections/dataset/items?limit=50` y `?q=*` | **200 con 0 elementos** |

Es decir: el portal anuncia descarga, pero **su API de catálogo no expone
ningún ítem** a un cliente automatizado. Puede ser (a) un portal con contenido
no publicado al catálogo público, (b) un visor embebido de otro tenant, o (c)
una restricción de compartición. **No se puede concluir que los datos sean
descargables.**

**Requisito para integrar (bloqueante):** solicitud formal a CENTA con:

1. servicio ArcGIS REST o geodatabase del Mapa Digital de Suelos;
2. ficha técnica: escala real, fecha de muestreo, método analítico, densidad de
   muestras por departamento;
3. licencia escrita de uso y de publicación de derivados (AGROSV publica
   agregados y capas derivadas, no los datos crudos si la licencia no lo permite);
4. identificador de parcela/muestra para poder auditar.

**No se asume** que la escala 1:50.000 citada en documentación secundaria sea la
escala efectiva de publicación; debe constar en la ficha.

---

## 5. Otras fuentes nacionales

| Fuente | Evidencia | Uso | Limitación |
|---|---|---|---|
| MAG — *Mapas temáticos… suelos* (`/wp-content/uploads/2021/06/suelos.pdf`, 1.324.595 B) | **200, application/pdf** | Referencia cartográfica, contexto | Es un PDF: no es capa GIS; vectorizarlo exige etiquetarlo como derivado AGROSV |
| MAG — Anuario de Estadísticas Agropecuarias 2021-2022 | **200, 4.321.899 B** | Capítulo de uso del suelo y mapas temáticos | Extracción manual con referencia de página |
| MARN — susceptibilidad a erosión (RUSLE 2015) | Documentado en `NATIONAL_DATA_INTEGRATION.md` | Riesgo de erosión | PDF/visor; escala y método deben declararse |
| UES y publicaciones regionales | No sondeado de forma sistemática | Validación local, perfiles | Requiere búsqueda bibliográfica por cultivo/zona |

---

## 6. Comparación nacional vs global

| Criterio | CENTA | SoilGrids |
|---|---|---|
| Naturaleza | Medición + interpolación nacional | Predicción global ML |
| Unidad mínima | Muestra georreferenciada | Píxel 250 m |
| Variables | Textura, nutrientes, profundidad, erosión | Físicas y C/N/pH/CIC; sin P, K, Ca, Mg, micronutrientes |
| Aptitud AGROSV | Fertilidad, aptitud de cultivos, calibración | Prior de paisaje, relleno de vacíos, modelos hidrológicos |
| Riesgo | Licencia y acceso | Falsa precisión si se usa a escala de parcela |

**Uso combinado admisible:** SoilGrids como prior y para zonas sin cobertura
CENTA; CENTA como referencia cuando exista. Se documenta la discrepancia, no se
promedia.

---

## 7. Lo que falta y bloquea modelos

| Vacío | Impacto | Mitigación |
|---|---|---|
| Profundidad efectiva nacional | AquaCrop/DSSAT no pueden limitar la zona radicular | Pedir a CENTA; mientras tanto usar valor conservador declarado |
| P, K, Ca, Mg, micronutrientes | Fertilización y aptitud no calculables con SoilGrids | CENTA o análisis de laboratorio; no estimar con modelos no validados |
| CE / salinidad | Riego y suelos costeros | Medición; no hay fuente global utilizable verificada aquí |
| Compactación | Manejo y erosión | Solo medición de campo |
| Propiedades hidráulicas | Balance hídrico | Pedotransferencia declarada (Saxton-Rawls) o medición |
| Validación espacial de SoilGrids en SV | Error desconocido | Muestreo propio o convenio con CENTA/UES |

---

## 8. Evidencia reproducible

```bash
.venv/Scripts/python.exe scripts/06_probe_phase3_sources.py r3
.venv/Scripts/python.exe scripts/07_fetch_phase3_samples.py
```

- `research/raw/phase3/probes_20261122_r3.json` — sondas `soilgrids_rest`,
  `soilgrids_webdav_phh2o`, `soilgrids_clay_0_5`, `centa_*`, `fao_hwsd_v2`.
- `data/samples/phase3/soilgrids_rest_point/sample.json` — evidencia del `null`.
- `data/samples/phase3/soilgrids_rest_point/soilgrids_phh2o_point.json` — 357 B.

**Advertencia de caducidad:** los estados `VERIFIED` de este documento caducan;
deben repetirse antes de cada fase (regla R-10 del registro maestro).
