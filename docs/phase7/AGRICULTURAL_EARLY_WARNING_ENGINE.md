# AgriculturalEarlyWarningEngine — aviso temprano

**Módulo:** `backend/agrosv/monitoring/alerts.py`
**Endpoint:** `POST /api/monitoring/early-warning`
**Versión:** 7.0.0

## Tres tipos que no se mezclan

| Tipo | Método | Clase de evidencia |
|---|---|---|
| pronóstico | `forecast_warning` | `forecast` |
| observación | `observation_warning` | `observed`/`satellite_derived` |
| institución | `official_warning` | `official_notice` |

## Pronóstico

`forecast_warning(forecast, crop_id, threshold_c, threshold_source, stage)`:

- valida el bloque de pronóstico (proveedor, emisión, vigencia, horizonte,
  incertidumbre, valores);
- exige umbral y fuente;
- calcula días sobre umbral en el horizonte;
- devuelve `possible_heat_warning` o `no_warning`;
- **`deterministic: false`** y un enunciado probabilístico (“posible
  exposición…”), nunca una afirmación sobre el futuro;
- conserva `lead_time_days`, incertidumbre y proveedor.

## Observación

`observation_warning(category, observed_value, threshold, threshold_source,
geographic_scope, evidence)` compara un valor observado con un umbral declarado.
`deterministic: true` porque describe el presente/pasado, no el futuro.

## Institución

`official_warning(institution, notice_id, statement, valid_from)` reproduce el
comunicado con su identificador. AGROSV no lo reclasifica ni lo convierte en
propio.

## Limitaciones

1. No hay proveedor de pronóstico integrado; el bloque se aporta y se valida.
2. No se generan probabilidades propias a partir de un pronóstico externo.
3. Un aviso por pronóstico no es una observación ni una alerta verificada.
