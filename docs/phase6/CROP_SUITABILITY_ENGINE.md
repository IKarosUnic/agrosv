# CropSuitabilityEngine

**Fase 6 · Subsistema A · Estado: implementado; reglas AGROSV sin validación**

Código: `backend/agrosv/agriculture/suitability.py`
Pruebas: ventana de crecimiento, NoData, sistemas de producción, fuentes
API: `GET /api/agriculture/suitability?crop_id=&lat=&lon=&system=`

## Marco

Clasificación por factores limitantes inspirada en la evaluación de tierras y
la zonificación agroecológica de FAO. **No es el algoritmo de PyAEZ** ni usa
sus tablas de decisión: es una reimplementación AGROSV con umbrales publicados.

| Clase | Regla |
|---|---|
| S1 | ninguna limitación moderada o severa |
| S2 | una limitación moderada |
| S3 | dos o más moderadas |
| N | al menos una severa |
| `not_evaluated` | falta al menos un factor crítico |

## Factores

| Factor | Cálculo | Umbral | Crítico |
|---|---|---|---|
| temperatura | media de la ventana de 5 meses | óptimo del catálogo; margen ±3 °C | sí |
| agua (secano) | P de la ventana / ETc medio | ≥1,0 / 0,7 / 0,5 | sí |
| pH | pH 0–30 cm | rango del cultivo; margen ±0,5 | sí |
| pendiente | pendiente del DEM | máximo del cultivo; ×1,5 | sí si hay umbral |
| profundidad | no disponible | — | no |
| salinidad | no disponible | — | no |
| textura | clase USDA | preferencia del catálogo (`GAP`) | no |
| nutrientes | no hay análisis de suelo | — | no |

La **ventana de crecimiento** son los 5 meses consecutivos con mayor
precipitación (circular, admite cruce de año). Es una convención AGROSV, no un
calendario de manejo.

## Comportamiento con datos faltantes

En San Salvador (`13.69, -89.19`) SoilGrids devuelve NoData en pH (máscara
urbana/agua). El resultado es `not_evaluated`, `critical_missing = ["ph"]` y
una limitación explícita. **No se degrada a S3 ni se rellena el pH.**

Para café en `13.85, -89.45` hay pH y pendiente: la clase observada en la
verificación es S3. Ese valor depende de los umbrales y del punto; no es una
conclusión agronómica.

## Sistemas de producción

* `rainfed`: usa precipitación frente a ETc.
* `irrigated`: el agua no limita **solo si** el llamador declara
  `irrigation_available=true`; no existe capa de acceso a riego.
* `urban` y `periurban`: el agua, el espacio y la luz no están en AGROSV; el
  resultado es `not_evaluated` con los factores ausentes.

## Entradas de Fase 5

`TerrainEngine.terrain_metrics` (elevación, pendiente), `SoilEngine.sample`
(pH, textura 0–30 cm) y `ClimateEngine.monthly_climatology` (P, ET0, Tmax,
Tmin). Toda respuesta incluye las fichas de `copdem30`, `soilgrids_2`,
`open_meteo_point`, `crop_parameters_catalog` y `fao_aez`.

## Límites

No hay validación contra rendimientos observados, no hay datos de salinidad,
profundidad, CEC ni agua disponible, y el clima es de un punto de reanálisis
(2019–2025). Una clase de aptitud **no** es una recomendación de siembra.
