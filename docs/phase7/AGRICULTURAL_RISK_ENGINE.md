# AgriculturalRiskEngine — marco de riesgo transparente

**Módulo:** `backend/agrosv/monitoring/risks.py`
**Endpoint:** `POST /api/monitoring/risk`
**Versión:** 7.0.0

## Fórmula

```
riesgo = peligro × exposición × vulnerabilidad
```

Cada factor se normaliza a [0, 1] por el llamador. Si falta un factor y
`require_all=True` (por defecto), `risk_value` es `None` con `missing`: no se
imputa.

## Escala operativa AGROSV

| Riesgo | Clase |
|---|---|
| < 0,10 | negligible |
| < 0,25 | low |
| < 0,50 | moderate |
| < 0,75 | high |
| ≥ 0,75 | very_high |

La escala es **operativa y no oficial**. No está validada contra daños
observados.

## Integración de sub-riesgos

`integrate(indicators, weights, require_all=False)` aplica una media ponderada
declarada. Si falta un indicador, renormaliza y lo informa (`missing`,
`renormalized`). No se combinan escalas incompatibles: los pesos son una
decisión metodológica, no un resultado.

## Supuestos y límites

1. Los tres factores se multiplican como independientes; la correlación no se
   modela.
2. Un riesgo alto no es un evento confirmado.
3. Las clases no son una clasificación oficial.
4. No se agrega un índice nacional ni municipal sin datos de exposición
   verificados.

## Validación

Pruebas: producto 0,8 × 0,5 × 0,5 = 0,2 con clase `low`; factor ausente produce
`None` y `missing == ["exposure"]`.
