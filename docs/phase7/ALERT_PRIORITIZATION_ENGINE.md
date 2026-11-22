# AlertPrioritizationEngine — prioridad con motivo

**Módulo:** `backend/agrosv/monitoring/alerts.py`
**Endpoint:** `POST /api/monitoring/alerts/prioritize`
**Versión:** 7.0.0

## Puntuación

| Componente | Peso | Escala |
|---|---|---|
| severidad | 0,35 | low 0,25 → very_high 1,0 |
| exposición | 0,15 | log10(área_km² + 1) normalizado 0–4 |
| sensibilidad del cultivo | 0,15 | aportada; 0,5 por defecto |
| confianza | 0,15 | none 0 / low 0,3 / medium 0,6 / moderate 0,8 / high 1 |
| calidad de evidencia | 0,10 | low 0,3 / moderate 0,6 / high 1 |
| urgencia temporal | 0,10 | ≤7 d 1,0; ≤14 d 0,6; resto 0,3 |

La puntuación no es una probabilidad y los pesos son una decisión
metodológica.

## Regla de protección

Un evento **VERIFIED con severidad ≥ 0,75** se ordena antes que cualquier señal
algorítmica, aunque su puntuación sea menor. La respuesta expone
`verified_high_severity` y `reasons` para cada alerta.

Cada entrada devuelve componentes, puntuación, motivos y posición. Se informa
si algún componente quedó sin dato.

## Limitaciones

1. La exposición requiere área verificada; si falta, se renormaliza.
2. La calidad de evidencia es una evaluación del llamador.
3. La prioridad no sustituye la verificación ni la decisión de campo.

## Validación

Prueba: una alerta verificada de severidad alta se ordena por delante de una
alerta algorítmica `very_high` con confianza baja.
