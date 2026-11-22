# CROP_PARAMETERS_CATALOG — AGROSV Fase 3

**Fecha:** 2026-11-22 · **Estado:** catálogo de **estructura + valores de
referencia**. Ningún parámetro de este documento está calibrado para variedades
salvadoreñas.

---

## 0. Advertencia científica

Los valores marcados **REF** son rangos agronómicos de referencia
(FAO, *Irrigation and Drainage Paper 56*; base de cultivos de AquaCrop; guías
técnicas de CENTA/MAG cuando se indiquen). **No** son mediciones locales, **no**
están validados contra rendimiento observado en El Salvador y **no** deben
publicarse como «requerimiento de agua del cultivo en El Salvador».

Estados usados:

| Código | Significado |
|---|---|
| **REF** | Rango de referencia bibliográfica; pendiente de validación local |
| **NAC** | Dato nacional publicado y verificado (censo/anuario) |
| **GAP** | No existe dato; requiere medición o solicitud institucional |

---

## 1. Esquema obligatorio por cultivo

```
crop_id                  slug estable
scientific_name          binomial con autor
local_names              nombres en español salvadoreño
varieties[]              nombre, fuente, ciclo, adaptación, estado (REF/NAC/GAP)
climate.adaptation       zonas altitudinales y térmicas
climate.temp_opt         óptima (°C)
climate.temp_limits      mínima/máxima tolerate
water.etc_season_mm      evapotranspiración estacional
water.critical_stages    etapas sensibles al déficit
water.rainfed_suitability
soil.texture_pref        clases USDA
soil.ph_range
soil.depth_min_cm        profundidad efectiva mínima
soil.slope_max_pct
soil.drainage
cycle.days_total
cycle.stages[]           etapa, duración, Kc, requerimiento
nutrition.n_uptake       extracción por tonelada
nutrition.p_k_removal
management.practices[]
pests[]                  plaga, agente, época, fuente
diseases[]
yield.national_avg       NAC (fuente censal)
yield.potential_rainfed  modelo, no observación
harvest.conditions
sources[]                cada valor con su cita
uncertainty               rango o cualitativo
```

**Regla:** un campo vacío se publica como `null` + `GAP`, nunca con un valor
«razonable» inventado.

---

## 2. Fichas de prioridad 1

### 2.1 Maíz — *Zea mays* L.

| Parámetro | Valor | Estado |
|---|---|---|
| Nombres locales | maíz, milpa (sistema) | — |
| Superficie cosechada 2024-25 | 293.458 mz (~205.000 ha) | **NAC** (CAP 2025) |
| Producción 2024-25 | ~10,9 millones qq (~493.403 t) | **NAC** |
| Productores | 401.101 | **NAC** |
| Semilla híbrida / criolla | 75,0 % / 19,7 % del área | **NAC** |
| Destino autoconsumo / venta | 49,5 % / 47,8 % | **NAC** |
| Ciclo | 90–140 días según variedad y altitud | **REF** |
| Etapas | siembra–emergencia, V, floración, llenado, madurez | **REF** |
| ET estacional | 500–800 mm | **REF** |
| Etapas críticas | floración y llenado de grano | **REF** |
| Profundidad radicular efectiva | 60–100 cm (hasta 120 en suelo profundo) | **REF** |
| pH | 5,5–7,5 (óptimo 6,0–7,0) | **REF** |
| Pendiente máxima | ≤ 15 % sin obras de conservación | **REF** |
| T óptima | 24–30 °C | **REF** |
| Plagas | gusano cogollero (*Spodoptera frugiperda*), barrenador, pulgón | **REF** |
| Enfermedades | mancha de asfalto, roya, pudriciones de mazorca | **REF** |
| Rendimiento nacional | derivado de CAP: ~2,4 t/ha | **NAC** (calculado) |
| Variedades locales | **GAP** — no hay catálogo público con coeficientes | — |

### 2.2 Frijol — *Phaseolus vulgaris* L.

| Parámetro | Valor | Estado |
|---|---|---|
| Superficie / producción | 996,2 mil qq (~45.189 t) | **NAC** |
| Productores | 214.738 | **NAC** |
| Destino autoconsumo / venta | 50,3 % / 48,8 % | **NAC** |
| Ciclo | 65–90 días (según hábito y altura) | **REF** |
| ET estacional | 300–500 mm | **REF** |
| Etapas críticas | floración y formación de vaina | **REF** |
| Profundidad radicular | 40–60 cm | **REF** |
| pH | 6,0–7,5 | **REF** |
| Pendiente máxima | ≤ 15 % | **REF** |
| T óptima | 18–24 °C | **REF** |
| Plagas | mosca blanca (*Bemisia tabaci*), lorito verde, ácaros | **REF** |
| Enfermedades | mosaico dorado, antracnosis, mustia hilachosa | **REF** |
| Variedades locales | **GAP** | — |

### 2.3 Café — *Coffea arabica* L.

| Parámetro | Valor | Estado |
|---|---|---|
| Zonas | cordilleras cafetaleras; 500–1.500 m | **REF** |
| Ciclo a primera cosecha | 3–4 años | **REF** |
| ET estacional | 1.000–1.800 mm | **REF** |
| T óptima | 18–24 °C | **REF** |
| pH | 5,0–6,5 | **REF** |
| Profundidad radicular | 60–90 cm | **REF** |
| Pendiente | apto en laderas con sombra y conservación | **REF** |
| Plagas | broca (*Hypothenemus hampei*) | **REF** |
| Enfermedades | roya (*Hemileia vastatrix*), ojo de gallo, antracnosis | **REF** |
| Superficie/producción | CAP 2025 (2.ª entrega) | **NAC** |
| Suelos de cordilleras | capa específica CENTA | **PENDING** |

### 2.4 Caña de azúcar — *Saccharum officinarum* L.

| Parámetro | Valor | Estado |
|---|---|---|
| Ciclo | 12–18 meses (plantilla), rebrotes anuales | **REF** |
| ET estacional | 1.200–1.800 mm | **REF** |
| T óptima | 24–32 °C | **REF** |
| pH | 5,5–8,0 | **REF** |
| Profundidad radicular | 80–150 cm | **REF** |
| Pendiente | ≤ 12 % mecanizable | **REF** |
| Riego | complementario en verano | **REF** |
| Superficie/producción | CAP 2025 | **NAC** |
| Plagas | taladrador del tallo (*Diatraea* spp.), salivazo | **REF** |

---

## 3. Fichas compactas (prioridad 2)

| Cultivo | Ciclo (d) | ET (mm) | pH | Prof. rad. (cm) | T ópt. (°C) | Nota nacional |
|---|---|---|---|---|---|---|
| Arroz | 100–140 | 450–700 (riego; +percolación) | 5,0–7,0 | 30–50 | 22–32 | CAP 2025; importación dominante |
| Sorgo / maicillo | 90–120 | 450–650 | 5,5–7,5 | 60–100 | 25–32 | Tolerante a sequía; canícula |
| Mango | perenne | 700–1.200 | 5,5–7,5 | 100–200 | 24–30 | Mapas temáticos MAG |
| Aguacate | perenne | 1.000–1.500 | 5,5–7,0 | 60–120 | 20–28 | Requiere drenaje |
| Cítricos | perenne | 900–1.200 | 5,5–7,0 | 60–120 | 23–30 | — |
| Papaya | 270–360 | 1.200–1.500 | 5,5–7,0 | 40–60 | 22–30 | Sensible a anegamiento |
| Tomate | 90–120 | 400–600 | 5,5–7,0 | 40–60 | 20–27 | Hortaliza de mayor valor |
| Chile dulce | 90–120 | 400–600 | 5,5–7,0 | 40–60 | 20–28 | — |
| Cebolla | 100–140 | 350–550 | 6,0–7,0 | 25–40 | 15–25 | — |
| Pepino | 55–75 | 400–600 | 5,5–7,0 | 30–50 | 20–30 | — |
| Repollo | 80–120 | 350–500 | 6,0–7,5 | 30–50 | 15–22 | — |
| Cacao | perenne | 1.200–1.800 | 5,5–7,0 | 60–100 | 22–30 | Agroforestería |
| Coco | perenne | 1.200–2.000 | 5,5–8,0 | 60–100 | 25–32 | Zonas costeras |

Todos los valores de esta tabla son **REF**; ninguna celda es **NAC**.

---

## 4. Requerimientos nutricionales (REF)

| Cultivo | N (kg/t producto) | P₂O₅ (kg/t) | K₂O (kg/t) | Nota |
|---|---|---|---|---|
| Maíz (grano) | 20–30 | 8–12 | 15–25 | Depende de rendimiento y MO |
| Frijol (grano) | 30–40 | 10–15 | 20–30 | Fijación simbiótica reduce N |
| Arroz | 15–25 | 6–10 | 12–20 | — |
| Sorgo | 20–30 | 8–12 | 15–25 | — |
| Café (grano oro) | 30–40 | 8–12 | 30–40 | Por tonelada de café oro |
| Caña | 1,5–2,5 | 0,8–1,2 | 2,0–3,0 | Por tonelada de caña |
| Tomate | 3,0–4,0 | 1,0–1,5 | 4,0–6,0 | Por tonelada de fruto |

**Estos valores no sustituyen un análisis de suelo.** Publicar una recomendación
de fertilización sin análisis y sin calibrar es un riesgo agronómico y ambiental.

---

## 5. Qué falta para que el catálogo sea científico

| Requisito | Estado |
|---|---|
| Coeficientes genéticos (DSSAT) por variedad salvadoreña | **GAP** — bloqueante |
| Kc local por etapa | **GAP** — usar Kc de AquaCrop como REF |
| Duración real de etapas por zona y fecha de siembra | **GAP** |
| Rendimiento observado por variedad y zona | **GAP** |
| Umbrales económicos de plagas | **GAP** |
| Validación de ET contra lisímetro o balance de campo | **GAP** |

Mientras estos vacíos existan, el motor de simulación debe devolver
`"calibrated": false` y un rango, nunca un número único.

---

## 6. Cómo se poblará el catálogo

1. Cargar los parámetros que ya trae AquaCrop 7.3 para maíz y frijol seco como
   **REF**, con la versión del modelo.
2. Extraer de los PDF del MAG/CENTA las variedades recomendadas y sus ciclos
   (con página).
3. Solicitar a CENTA los coeficientes de variedades liberadas.
4. Contrastar rendimiento simulado vs CAP 2025 departamental; si el error > 30 %,
   no se publica el resultado absoluto.
