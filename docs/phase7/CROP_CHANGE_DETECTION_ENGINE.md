# CropChangeDetectionEngine — cambio entre observaciones

**Módulo:** `backend/agrosv/monitoring/change.py`
**Endpoint:** `POST /api/monitoring/change`
**Versión:** 7.0.0

## Método

Compara dos índices sobre la **misma rejilla** con un umbral explícito:

```
delta = after − before
cambio = |delta| ≥ threshold
```

Clasificación por mediana del delta:

| Mediana | Señal |
|---|---|
| abs < threshold | `no_change_detected` |
| ≤ −2·threshold | `strong_decline` |
| ≤ −threshold | `decline` |
| ≥ 2·threshold | `strong_increase` |
| ≥ threshold | `increase` |

Se informan píxeles válidos, cambiados, fracción de descenso/ascenso, mediana y
P10/P90 del delta.

## Comparabilidad

El motor **rechaza** comparar sensores distintos o resoluciones distintas si el
llamador no declara `harmonized=True`. Una diferencia de bandas, atmósfera o
resolución no es un cambio agrícola.

## Procesos posibles, no atribución

Un descenso devuelve una lista de procesos posibles: cosecha/retiro,
senescencia, estrés hídrico o térmico, disturbio. Un ascenso: establecimiento,
recuperación por lluvia, crecimiento de maleza. `attribution` siempre es `None`.

## Incertidumbre

`confidence` depende de la fracción de píxeles válidos (<0,5 baja; <0,8 media;
resto moderada). Un umbral mayor reduce falsos positivos y también sensibilidad.

`timeseries_summary` resume deltas sucesivos: pasos negativos, racha negativa
más larga y `persistent_decline` (≥ 2 pasos). Persistencia no es causa.

## Limitaciones

1. Nubes residuales y sombras producen deltas espurios.
2. La fenología normal explica parte del cambio estacional.
3. Dos fechas no bastan para distinguir cosecha de estrés.
4. No se aplica corrección atmosférica ni de BRDF.
5. No sustituye la verificación de campo.

## Validación

Pruebas: declive fuerte con 9/9 píxeles, rechazo de sensores distintos sin
armonización, umbral no positivo rechazado y compatibilidad con la misma rejilla.
