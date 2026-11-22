# CropHealthMonitoringEngine — estado interpretativo del cultivo

**Módulo:** `backend/agrosv/monitoring/crop_health.py`
**Endpoint:** `POST /api/monitoring/crop-health`
**Versión:** 7.0.0

## Qué produce

Un **estado enumerado**, no una puntuación de salud:

| Estado | Regla |
|---|---|
| `insufficient_evidence` | < 3 observaciones, < 3 años de línea base, etapa desconocida o NDVI ausente |
| `unusual_vegetation_decline` | z ≤ −3,0 |
| `possible_vegetation_stress` | z ≤ −2,0 y sensibilidad de etapa ≥ 0,6 |
| `monitoring_recommended` | z ≤ −1,0 |
| `normal_observed` | z > −1,0 |

La anomalía es el z robusto de NDVI frente a la línea base estacional (motor de
series temporales).

## Sensibilidad por etapa

Tabla **genérica y declarada**: emergencia 0,4; vegetativo 0,6; floración 1,0;
llenado de grano 0,9; madurez 0,3. No es específica de variedad ni de cultivo:
el catálogo de Fase 6 no publica coeficientes por etapa para todos los cultivos.

## Evidencia y confianza

- `observed_indicators`: z de NDVI, NDMI, lluvia y temperatura; n y años.
- `inference`: etiqueta de inferencia, separada del indicador.
- `possible_causes`: solo si hay indicadores concordantes (p. ej. NDVI y NDMI
  bajos → posible componente hídrico).
- `confidence`: baja con un solo indicador, media con dos, moderada con tres.
- `missing_evidence` enumera lo que falta.

Una anomalía de NDVI se interpreta **relativa a la etapa**; no se crea un
índice universal de salud.

## Perfil de cultivo

`profile(crop_id)` devuelve nombre científico, ciclo, etapas críticas del
catálogo de Fase 6 y la tabla de sensibilidad, con la nota de que la tabla es
genérica.

## Limitaciones

1. NDVI satura en dosel denso y se mezcla con suelo desnudo.
2. Una nube residual puede producir una anomalía negativa.
3. La etapa debe provenir de fecha de siembra o de campo.
4. El estado es interpretativo: no es diagnóstico agronómico.

## Validación

Pruebas: evidencia insuficiente, estrés posible en floración con dos
indicadores y confianza media, y error para cultivo desconocido.
