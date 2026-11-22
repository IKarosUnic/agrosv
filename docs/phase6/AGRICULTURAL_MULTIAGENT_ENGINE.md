# AgriculturalMultiAgentEngine

**Fase 6 · Subsistema B · Estado: implementado; difusión reproducible en red sintética**

Código: `backend/agrosv/social/multiagent.py`
API: `POST /api/social/multiagent`

## Red

* Anillo: cada agente se conecta con el anterior y el siguiente.
* Un lazo aleatorio adicional por agente, sorteado con semilla.
* Grado medio ≈ 3.
* La red no representa vínculos reales, parentesco, vecindad ni organizaciones.

## Difusión

Cada paso, para agentes no adoptantes y factibles:

```
peer = media(propensión de vecinos)
Δ    = 0,30 × acceso_a_información × (peer − propensión)
       + 0,05 si el agente es cooperativista
propensión ← clip(propensión + Δ, 0, 1)
```

Adopción cuando `propensión ≥ umbral` (0,55 por defecto) y la tecnología es
factible según `TechnologyAdoptionEngine`.

La propensión puede bajar si los vecinos tienen menor propensión: no se impone
monotonicidad artificial.

## Choque común

Opcional. Aplica al capital de productores de secano:

```
capital ← capital × (1 − 0,3 × severidad)
```

## Salida

Historial por paso (adoptantes, fracción, propensión media), agregado por
arquetipo, IDs adoptantes, descripción de red, `seed`,
`reproducible: true`, `deterministic_given_seed: true` y
`is_national_forecast: false`.

Un registro `SIMULATION_HISTORY` guarda el resultado con supuestos y método.

## Reproducibilidad

Misma población, misma semilla y mismos pasos ⇒ mismo historial. Las pruebas lo
verifican ejecutando dos veces la misma simulación.

## Límites

No hay mercado, precios, instituciones endógenas, competencia por recursos,
formación de coaliciones ni des-adopción. No predice tasas nacionales de
adopción ni valida teoría de difusión.
