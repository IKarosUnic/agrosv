# HeatAndClimateRiskEngine — calor y déficit de lluvia

**Módulo:** `backend/agrosv/monitoring/risks.py`
**Endpoint:** `POST /api/monitoring/heat-risk`
**Versión:** 7.0.0

## Observado

- exposición sobre un umbral declarado con fuente (días, racha, ola ≥ 3 días,
  grados-día de exceso);
- fracción de días sobre el umbral;
- cociente P/ET0 del periodo y clase de déficit (< 0,75);
- cultivo y etapa con sensibilidad genérica.

El riesgo observado combina exposición y déficit con pesos iguales y se clasifica
con la escala operativa AGROSV.

## Pronóstico separado

Si se aporta `forecast`, se valida y se devuelve en un bloque aparte:

- proveedor, emisión, vigencia, horizonte, incertidumbre, valores y estado;
- `evidence_class: forecast`;
- `mixed_with_observed: false`.

El pronóstico **no** se suma al riesgo observado. No se emite una afirmación
determinista sobre el futuro.

## Validación del pronóstico

Se exigen todos los campos: `provider`, `issued_at`, `valid_from`, `valid_to`,
`horizon_days`, `uncertainty` y `values`. Fechas ISO y horizonte ≥ 0. Un
pronóstico incompleto se rechaza.

## Limitaciones

1. El umbral debe venir de una fuente explícita.
2. La temperatura del aire no es la del dosel.
3. ENSO y variabilidad climática no se evalúan sin datos.
4. La clase de riesgo no está validada contra pérdidas.

## Validación

Pruebas: el pronóstico queda separado (`mixed_with_observed: false`), con
horizonte 3 y clase `forecast`; un pronóstico incompleto lanza
`MonitoringError`.
