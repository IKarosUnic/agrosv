# AgriculturalAlertEngine — alertas estructuradas

**Módulo:** `backend/agrosv/monitoring/alerts.py`
**Endpoints:** `POST/GET /api/monitoring/alerts`, `POST /api/monitoring/alerts/expire`
**Versión:** 7.0.0

## Contenido obligatorio

Cada alerta incluye: identificador único (`ALR-<huella>`), categoría, ámbito
geográfico con escala, cultivo (si se conoce), `detected_at`, periodo de
observación, datasets de origen, método de detección, nivel de riesgo,
evidencia, clase de evidencia, confianza, incertidumbre, verificación
recomendada, fecha de expiración/revisión, estado, versión del modelo e
historial.

Se rechaza una alerta sin evidencia o sin datasets de origen: no se crea vacía.

## Categorías

Sequía, lluvia excesiva, exposición a inundación, calor extremo, anomalía de
vegetación, estrés hídrico, riesgo de plaga, riesgo de enfermedad, degradación
del suelo y “se requiere monitoreo”.

## Identidad y duplicados

La huella es SHA-256 de `categoría + ámbito + cultivo + periodo`. Si existe una
alerta activa con la misma huella, se devuelve la existente con
`duplicate: true` y el motivo. Las alertas DISMISSED/EXPIRED no bloquean una
nueva.

## Ciclo de vida

```
DETECTED → PRELIMINARY | NEEDS_VERIFICATION | DISMISSED | EXPIRED
PRELIMINARY → NEEDS_VERIFICATION | VERIFIED | DISMISSED | EXPIRED
NEEDS_VERIFICATION → VERIFIED | DISMISSED | EXPIRED
VERIFIED → EXPIRED
DISMISSED / EXPIRED → (terminal)
```

- Una transición no permitida lanza `MonitoringError`.
- **VERIFIED exige verificación suficiente**: un verificador fuerte confirmado o
  dos verificadores débiles de tipo distinto con confianza ≥ 0,5.
- La alerta original se conserva en `original`; los cambios solo actualizan
  `status`, `updated_at` e `history`.

## Desde un riesgo

`from_risk(risk_value, ...)` crea alerta solo si el riesgo ≥ 0,25; el nivel se
asigna por umbrales 0,35 / 0,50 / 0,75.

## Expiración

`expire(on=...)` marca EXPIRED las alertas no terminales cuya fecha de revisión
ya pasó y registra el evento. No borra nada.

## Limitaciones

1. Las alertas viven en memoria del proceso.
2. El umbral 0,25 es operativo, no oficial.
3. Una alerta no es un diagnóstico ni una pérdida confirmada.
