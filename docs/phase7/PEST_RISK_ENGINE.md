# PestRiskEngine — idoneidad, exposición y riesgo

**Módulo:** `backend/agrosv/monitoring/pests.py`
**Endpoint:** `POST /api/monitoring/pest-risk`
**Versión:** 7.0.0

## Componentes separados

| Componente | Cómo se obtiene |
|---|---|
| presencia documentada | ámbito y calidad del registro; categórico |
| idoneidad ambiental | ventanas cuantitativas con fuente, o reglas del llamador |
| exposición del cultivo | 1 si el cultivo está en `affected_crops`, 0 si no |
| factor de etapa | tabla genérica de sensibilidad |
| daño potencial | texto de importancia económica |
| índice de riesgo | idoneidad × exposición × factor de etapa |

El índice **no** es una probabilidad de presencia ni una pérdida esperada.

## Reglas

`assess(pest_id, conditions, crop_id, stage, rules, rules_source)`:

- si no se pasan `rules`, se usan las ventanas del registro;
- si el registro no tiene ventanas → `environmental_suitability: null`,
  `risk_index: null` y `gap` con el motivo;
- cada ventana exige `variable`, `min`, `max` y `source`; si falta la fuente se
  lanza `MonitoringError` (“no se inventan umbrales”);
- `rules_source` es obligatorio si se aportan reglas;
- idoneidad = proporción ponderada de ventanas cumplidas (peso 1 por defecto);
- condiciones ausentes reducen la base y se declaran en `missing`.

## Salida

`presence_evidence`, `crop_exposure`, `environmental_suitability`,
`suitability_detail`, `stage_factor`, `potential_damage`, `risk_index`, `gap`,
método, supuestos, limitaciones e incertidumbre.

## Regla científica central

**La idoneidad ambiental no prueba la presencia de la plaga.** Una plaga
documentada en el país no está necesariamente en el cultivo consultado. El
motor lo declara en `note` y en las limitaciones, y no convierte la presencia
nacional en presencia municipal.

## Validación

Pruebas: registro sin ventana devuelve GAP; reglas explícitas producen
idoneidad 1 y riesgo 1; reglas sin fuente se rechazan; el ámbito regional no se
presenta como confirmación nacional.
