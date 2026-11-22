# CropLossRiskEngine — impacto potencial vs pérdida observada

**Módulo:** `backend/agrosv/monitoring/risks.py`
**Endpoint:** `POST /api/monitoring/crop-loss`
**Versión:** 7.0.0

## Tres campos que no se suman

| Campo | Origen |
|---|---|
| `potential_impact` | combinación ponderada de peligros × etapa |
| `observed_damage.fraction` | solo si el llamador aporta una medición de campo |
| `modeled_loss.fraction` | solo si se aportan rendimiento potencial y esperado |

`is_actual_yield_loss` es siempre `false`.

## Pesos de peligro declarados

sequía 0,25; calor 0,20; inundación 0,15; plaga 0,15; enfermedad 0,15;
lluvia excesiva 0,05; degradación del suelo 0,05. Se renormaliza si falta
alguno y se informa.

## Etapa y manejo

```
impacto = peligro_ponderado × (0,4 + 0,6·sensibilidad_etapa)
```

`management_factor` opcional multiplica el resultado; se declara. Sin etapa, la
sensibilidad es 0,5.

## Pérdida modelada

Si se aportan rendimientos:

```
fracción = 1 − esperado / potencial
```

Se etiqueta “pérdida modelada, no observada”. No se usa una salida de
simulación como pérdida real.

## Limitaciones

1. Los pesos son metodológicos y no están calibrados.
2. La etapa fenológica debe estar verificada.
3. No es una pérdida de rendimiento observada.
4. No incorpora precios ni ingresos (eso pertenece a Fase 8).

## Validación

Pruebas: con sequía 0,8 y calor 0,6 en floración, el impacto potencial existe,
el daño observado es `None` y la pérdida modelada es 0,4 con rendimientos 5 y 3
t/ha.
