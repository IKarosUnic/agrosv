# CropKnowledgeEngine

**Fase 6 · Subsistema A · Estado: implementado (software), sin calibración local**

Código: `backend/agrosv/agriculture/catalog.py`
Pruebas: `tests/test_phase6_agriculture.py` (catálogo y auditoría)
API: `GET /api/agriculture/crops`, `/crops/{id}`, `/search`, `/audit`

## Propósito

Mantener un catálogo agrícola extensible, priorizado para El Salvador, donde
**cada parámetro declara su procedencia** y los vacíos se publican como `null`
con estado `GAP`. No es una base de recomendaciones ni un modelo calibrado.

## Estados por parámetro

| Estado | Significado |
|---|---|
| `REF` | rango de referencia bibliográfico (FAO-56, AquaCrop, guías CENTA/MAG) |
| `NAC` | estadística nacional publicada (CAP 2025) |
| `GAP` | no existe dato; `value = null` |
| `MODEL_DERIVED` | derivado por AGROSV (se usa en fenología, no aquí) |
| `SCENARIO` | supuesto configurable de escenario |

## Cobertura real

22 fichas:

* **Granos básicos:** maíz, frijol, arroz, sorgo.
* **Hortalizas:** tomate, chile dulce, cebolla, pepino, repollo.
* **Frutales:** mango, aguacate, cítricos, papaya, coco, banano, plátano.
* **Comerciales/perennes:** café, caña de azúcar, cacao.
* **Agricultura urbana:** lechuga, rábano, cilantro (fichas deliberadamente
  vacías: no hay parámetros verificados).

Solo **5 cultivos** declaran los mínimos para un ciclo térmico (maíz, frijol,
arroz, sorgo, tomate): ciclo, temperatura base y ETc estacional. El resto no se
puede simular y el motor lo dice (`simulation_ready.ready = false`).

Único valor `NAC`: maíz, **2,4 t/ha**, derivado de superficie y producción del
CAP 2024–25. No hay rendimiento nacional por variedad ni por municipio.

## Campos de cada ficha

Taxonomía (nombre científico, familia, tipo, ciclo de vida, hábito), nombres
locales y sinónimos salvadoreños, ciclo, temperatura óptima y base, ETc
estacional, etapas críticas, pH, profundidad mínima, pendiente máxima, textura
y drenaje, remoción de N/P₂O₅/K₂O por tonelada, Kc (siempre `GAP`), meses de
siembra (`GAP`), rendimiento, plagas, enfermedades, fuentes, confianza,
sistemas de producción y lista de vacíos.

## Lo que el catálogo declara ausente

* Coeficientes genéticos por variedad.
* Kc local por etapa (los 22 cultivos en `GAP`).
* Calendario oficial de siembra.
* Rendimiento por zona, variedad o sistema.
* Umbrales económicos de plagas.
* Preferencia textural y salinidad por cultivo.

`GET /api/agriculture/audit` devuelve 22 cultivos, 5 simulables, 67 vacíos
declarados, 32 estados `GAP` entre ciclo y Kc, y 1 estadística nacional.

## Búsqueda y comparación

`find("MAÍZ")` normaliza acentos y mayúsculas y devuelve `maize`.
`compare()` conserva el estado de cada valor y advierte que comparar `REF` con
`NAC` no los hace equivalentes.

## Límites

El catálogo **no** sustituye un análisis de suelo, una guía de variedades ni
una recomendación de fertilización. Un valor `REF` no es una medición
salvadoreña y ninguno está validado en campo.
