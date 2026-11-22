# TechnologyAdoptionEngine

**Fase 6 · Subsistema B · Estado: implementado; índice de propensión, no probabilidad**

Código: `backend/agrosv/social/adoption.py`
API: `GET /api/social/technologies`, `POST /api/social/adoption`

## Tecnologías (9)

Riego por goteo, semilla mejorada, análisis de suelo, sensores agrícolas,
asesoría digital, mecanización, agricultura protegida, servicios de información
climática y conservación de suelo.

Cada una declara: clase de capital (`low`, `medium`, `high`), conocimiento
requerido, necesidad de agua, superficie mínima, carga de mantenimiento,
alfabetización digital, acceso a mercado y barreras.

**No se publican precios de equipos**: no hay fuente verificada.

## Evaluación

Barreras duras (propensión = 0, `decision = not_feasible`):

* clase de capital insuficiente;
* tecnología que requiere riego y agente de secano;
* superficie menor que el mínimo.

Barreras blandas (reducen propensión): conocimiento, mantenimiento,
alfabetización digital y mercado.

```
penalización = media(severidad de barreras blandas)
propensión   = max(0, 1 − 0,7 × penalización)
```

Decisión: `consider_adoption` si propensión ≥ umbral (0,55 por defecto), si no
`not_now`.

## Qué significa

La propensión es un **índice ordenado** de compatibilidad entre dotaciones y
requisitos. No es una probabilidad, no es una tasa nacional y no predice
adopción real.

## Límites

No se modelan subsidios, extensión, crédito, redes de pares, precio del equipo,
curva de aprendizaje ni des-adopción. Los umbrales de clase de capital
(1.000 y 10.000 USD) son supuestos AGROSV.
