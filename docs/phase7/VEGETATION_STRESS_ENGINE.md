# VegetationStressEngine — indicadores de estrés

**Módulo:** `backend/agrosv/monitoring/crop_health.py`
**Endpoint:** `POST /api/monitoring/vegetation-stress`
**Versión:** 7.0.0

## Regla mínima

Se exigen **al menos dos indicadores** disponibles. Con uno solo el resultado es
`insufficient_evidence`: no se infiere estrés de una señal aislada.

Indicadores admitidos y umbral declarado:

| Indicador | Cuenta como negativo si |
|---|---|
| NDVI (z) | ≤ −1,5 |
| NDMI (z) | ≤ −1,5 |
| lluvia (z) | ≤ −1,5 |
| temperatura (z) | ≥ +1,5 |
| déficit de humedad del suelo | ≥ 0,5 |

## Salida

- `negative_count` / `available_count` y `share_negative`;
- estado `none_detected`, `possible` (share < 0,6) o `multiple_indicators`;
- `possible_causes`: componente hídrico (NDVI con NDMI/suelo/lluvia), térmico
  (temperatura con NDVI) o “causa no identificable”;
- `missing_evidence`: variables ausentes;
- `confidence` según número de indicadores (2 baja, 3 media, ≥4 moderada).

## Distinciones conservadas

- indicador observado ≠ inferencia ≠ causa;
- un indicador de estrés **no es un diagnóstico**;
- los indicadores no son independientes (NDVI y NDMI comparten atmósfera y
  geometría), lo que se declara como limitación;
- no se cuantifica pérdida de rendimiento.

## Validación

Pruebas: un solo indicador produce evidencia insuficiente; NDVI+NDMI+lluvia
negativos producen estrés posible con causa hídrica.
