# AgriculturalResilienceEngine

**Fase 6 · Subsistema B · Estado: implementado; índices de escenario sin validación**

Código: `backend/agrosv/social/resilience.py`
API: `GET /api/social/shocks`, `POST /api/social/resilience`

## Choques (8)

| Choque | Severidad | Dimensión |
|---|---|---|
| sequía | 0,60 | agua |
| lluvia excesiva | 0,50 | agua |
| inundación | 0,80 | agua |
| estrés térmico | 0,50 | calor |
| brote de plaga | 0,55 | biótico |
| alza de insumos | 0,40 | costo |
| caída de precio | 0,50 | ingreso |
| interrupción de suministro | 0,40 | logística |

Los multiplicadores son supuestos declarados, no coeficientes estimados.

## Exposición

Suma acotada de: secano (0,25), monocultivo (0,15), capital < 1.000 (0,15),
acceso a mercado < 0,3 (0,10), crédito < 0,2 (0,10).

## Capacidad de adaptación

Suma acotada de: colchón de capital (0,25 × log₁₀(capital+1)/5), crédito
(0,20), riego (0,20), diversificación (0,15 × cultivos/4), información (0,10),
cooperativa (0,10).

## Impacto

```
impacto = severidad × (0,5 + 0,5 × exposición) × (1 − 0,7 × capacidad)
```

Clases: `bajo` < 0,20; `moderado` < 0,40; `alto` < 0,65; `severo` ≥ 0,65.

## Opciones de afrontamiento

Se habilitan solo si el recurso existe: ahorros, crédito, riego
complementario, diversificación, trabajo extrapredial, apoyo cooperativo,
reducción de insumos y ajuste de siembra (para choques hídricos).

`production_loss_fraction_scenario = impacto × factor_de_pérdida × 2` es una
cota de escenario, no una pérdida esperada.

## Comparación por arquetipo

`compare()` agrega impacto medio por arquetipo con la misma semilla. Sirve para
explorar diferencias internas, no para clasificar comunidades reales.

## Límites

No hay datos de pérdidas, recuperación, seguros ni ayuda institucional. El
índice no tiene validación empírica y no debe presentarse como medición oficial
de vulnerabilidad.
