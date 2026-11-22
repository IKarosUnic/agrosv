# FarmerBehaviorEngine

**Fase 6 · Subsistema B · Estado: implementado; reglas explícitas, no teoría psicológica**

Código: `backend/agrosv/social/behavior.py`
API: `POST /api/social/behavior`

## Decisión MAUT

Cada opción se puntúa con cinco pesos normalizados derivados de atributos
sintéticos:

```
return      = 1,0 − 0,5 × aversión_al_riesgo
risk        = 0,2 + 0,6 × aversión_al_riesgo
capital     = 0,3 + 0,4 × (1 − capacidad_de_capital)
information = 0,2 + 0,3 × acceso_a_información
experience  = 0,1 + 0,2 × min(experiencia/30, 1)
```

`capacidad_de_capital = min(capital/20.000, 1)`. Los pesos se normalizan a suma 1
y se publican en la respuesta.

Puntuación:

```
score = w_return × retorno_normalizado
      + w_risk × (1 − riesgo)
      + w_capital × holgura_de_capital
      + w_info × acceso × intensidad_de_información
      + w_experiencia × experiencia_normalizada
```

## Restricciones duras

Se excluye una opción si:

* `capital_required > capital`;
* `suitability_class == "N"` (restricción científica);
* `water_required_mm > agua_disponible` del escenario;
* `labor_required_days > días de trabajo`.

Ningún peso puede compensar una restricción dura. Si no queda ninguna opción,
`decision = null` y `decision_status = "no_feasible_option"`.

## Inspección

La respuesta incluye pesos, ranking completo, opciones excluidas con razones,
supuestos y `reproducible: true`. No hay aleatoriedad en la decisión.

## Aprendizaje

`learn(success, source, magnitude)`:

* ajusta `info_access` en ±0,5 × magnitud (acotado a [0,1]);
* incrementa experiencia en 1 si hubo éxito (máximo 60);
* actualiza confianza por fuente (extensión, pares, mercado) en ±magnitud.

Es una regla declarada, no un modelo cognitivo validado.

## Límites

No se modelan emociones, aversión a la ambigüedad, sesgos cognitivos,
aprendizaje social complejo ni heterogeneidad no observada. Los pesos son una
convención AGROSV y no están calibrados con productores salvadoreños.
