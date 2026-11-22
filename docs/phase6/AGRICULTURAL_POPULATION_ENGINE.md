# AgriculturalPopulationEngine

**Fase 6 · Subsistema B · Estado: implementado; población sintética, no representativa**

Código: `backend/agrosv/social/population.py`
API: `GET /api/social/archetypes`, `POST /api/social/population`

## Propósito

Construir poblaciones agrícolas configurables para experimentos. Los
arquetipos son **tipos de simulación**, no una descripción de la distribución
real de productores salvadoreños.

## Arquetipos (10)

| Arquetipo | Sistema | Cultivo principal | Superficie (ha) |
|---|---|---|---|
| `subsistence_maize` | secano de subsistencia | maíz | 0,2–1,5 |
| `smallholder_basic_grains` | secano pequeño productor | maíz | 1–5 |
| `bean_producer` | secano pequeño productor | frijol | 0,3–3 |
| `coffee_smallholder` | agroforestería | café | 0,5–6 |
| `vegetable_producer` | horticultura con riego | tomate | 0,2–3 |
| `fruit_producer` | frutales | mango | 0,5–8 |
| `mixed_crop` | diversificado | maíz | 0,5–4 |
| `urban_farmer` | urbano de pequeño espacio | lechuga | 0,005–0,10 |
| `cooperative_member` | cooperativa | café | 0,5–5 |
| `commercial_technified` | comercial tecnificado | caña | 10–200 |

Cada arquetipo define rangos de superficie, probabilidad de riego, capital,
acceso a crédito y mercado, mano de obra familiar y contratada, tenencia,
aversión al riesgo, acceso a información, experiencia, alfabetización digital,
cooperativismo e ingreso extrapredial. Todos son `SCENARIO`.

## Generación

* `numpy.random.default_rng(seed)` (PCG64).
* Sorteo de arquetipo con pesos explícitos; por defecto, equiprobables.
* Variables sorteadas de forma **independiente** dentro de cada rango; no hay
  correlaciones empíricas.
* Departamento elegido uniformemente entre los 14; no representa la
  distribución real.
* ID estable: `AGSV-<arquetipo>-<índice>`.
* Cada agente es un registro `SYNTHETIC_AGRICULTURAL_STATE` con método,
  supuestos, procedencia y `validation_status = not_validated`.

## Reproducibilidad

Misma semilla + misma versión de NumPy + mismos arquetipos ⇒ mismos valores.
La respuesta incluye `seed`, conteos, rango y media de superficie de **la
muestra**, y un bloque `representativeness` con `representative: false`.

## Límites

* No se puede inferir ninguna prevalencia poblacional.
* No hay calibración contra el CAP 2025 ni el CPV 2024.
* El tamaño máximo por llamada es 100.000; no se generan millones por defecto.
* La asignación geográfica es uniforme y artificial.

## Costo medido

5.000 agentes: 2,58 s de mediana y 11,5 MB de pico (`benchmark_phase6.json`).
