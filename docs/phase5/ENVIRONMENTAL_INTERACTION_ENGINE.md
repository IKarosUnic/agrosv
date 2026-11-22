# EnvironmentalInteractionEngine — perfil ambiental integrado

**Fase 5 · versión 5.0.0 · estado: implementado, sin índice compuesto**
Código: `backend/agrosv/engines/environmental.py` · API: `/api/engines/environmental`

## 1. Propósito

Une los cuatro motores anteriores en un **perfil ambiental documentado** de un punto.
No puntúa: muestra relaciones, restricciones y ausencias, cada una con su regla y su
clase de evidencia.

## 2. Composición

| Bloque | Origen | Tolerancia a fallos |
|---|---|---|
| `identification` | TerritorialEngine | si falla, el bloque queda `null` y se registra el error |
| `terrain` | Terrain Analysis | ídem |
| `soil` | SoilEngine | ídem |
| `hydrology` | HydrologyEngine (superficial, cuenca, balance, subterránea) | cada subcomponente por separado |
| `climate` | ClimateEngine | ídem |
| `environmental_constraints` | reglas de interacción | solo si están los insumos |
| `data_coverage` | disponibilidad real por componente | — |
| `uncertainty` | clase y confianza por componente | — |
| `component_errors` | errores capturados, con tipo y mensaje | — |
| `processing_history` | pasos con herramienta y parámetros | — |

Un componente ausente no invalida el perfil: se marca `available: false` con el motivo
y el resto se devuelve igual. Ningún componente se rellena con un valor por defecto.

## 3. Reglas de interacción

Cada regla cruza dos dominios, declara su umbral y su consecuencia. No hay pesos ni
puntuación agregada.

| Código | Dominios | Condición | Consecuencia |
|---|---|---|---|
| `erosion_pendiente_textura` | terreno + suelo | pendiente ≥ 25° y arcilla < 35 % | alta susceptibilidad a erosión hídrica con suelo desnudo |
| `erosion_pendiente` | terreno | 12° ≤ pendiente < 25° | relieve pronunciado: limita mecanización y aumenta riesgo |
| `infiltracion_baja_arcilla` | suelo + terreno | arcilla ≥ 35 % y pendiente < 5° | drenaje lento y riesgo de encharcamiento |
| `deficit_hidrico` | clima + hidrología | P anual < ET0 | déficit climático anual; no cuantifica riego |
| `aridez` | clima | P/ET0 < 0,5 | condición semiárida del período |
| `racha_seca_prolongada` | clima + hidrología | racha seca máxima ≥ 20 días | exposición a veranillos |
| `suelo_superficial_limitado` | suelo | profundidad efectiva < 50 cm | menor reservorio de agua y nutrientes |
| `sin_dato_de_profundidad` | suelo | profundidad no disponible | se declara la ausencia, no se asume un valor |
| `cobertura_hidrica_incompleta` | hidrología | sin cauce mapeado | ausencia en OSM ≠ ausencia de agua |

Las dos últimas son **reglas de ausencia**: se ejecutan aunque el insumo sea `null`
(`allow_missing: true`). Sin ese indicador el filtro general las descartaría y la
ausencia nunca se publicaría; se corrigió en Fase 5.

Cada hallazgo incluye `inputs`, `rule`, `implication`, `evidence_class:
derived_from_rule`, `declares_absence` y `validated: false`.

`suelo_superficial_limitado` no puede dispararse mientras no exista profundidad de
suelo; se mantiene declarada para cuando el dato exista.

## 4. Sin índice compuesto

`composite_indicator()` lanza `CompositeIndicatorError`:

> no se implementa un índice ambiental compuesto: no hay variables objetivo, pesos
> validados ni datos de referencia con los que verificarlo.

No se suman pendiente, pH y lluvia porque no hay pesos validados ni una variable
objetivo; un índice así ocultaría las reglas y las ausencias. Si en el futuro se
implementa, §7 exige fórmula, variables, pesos, limitaciones y validación.

## 5. Incertidumbre

Por componente:

| Componente | Clase | Confianza | Componentes de incertidumbre |
|---|---|---|---|
| terreno | `modeled_prediction` | baja | vertical, horizontal, modelo (DSM) |
| suelo | `modeled_prediction` | baja | modelo, soporte 250 m, sin medición |
| clima | `reanalysis` | baja | modelo, celda, serie corta, sin estación |
| hidrología | `simulation` | baja | D8/Budyko sin calibrar, ventana finita |

Agregado:

```json
"aggregate": {
  "quantified": false,
  "reason": "no hay datos de referencia para cuantificar ningún componente"
}
```

No se publica un número de incertidumbre agregado. La confianza «baja» es una
declaración cualitativa, no un intervalo.

## 6. Cobertura

`data_coverage` informa por componente: disponible, resolución, extensión, profundidad
y nota. Ejemplos:

- suelo: 0–30 cm, 250 m, «predicción, no medición»;
- agua subterránea: `available: false`, «sin capa ni series»;
- cuenca: `truncated` según el borde de la ventana;
- clima: «puntos: 2; representatividad no evaluada».

## 7. Ejemplo real

Punto `(-89.2, 13.7)`, ventana 3 km. Restricciones encontradas:

```
racha_seca_prolongada        (numérica, no ausencia)
sin_dato_de_profundidad      (declara ausencia)
```

El perfil no incluye `deficit_hidrico` porque P media (2.219 mm) supera ET0
(1.618 mm) en el punto de reanálisis, ni `erosion_pendiente` porque la pendiente es
2,67°. Estas ausencias de hallazgo son resultados de las reglas, no omisiones.

## 8. Caché

El perfil se cachea con clave:

```
sha256(motor + versión + parámetros + huella de cada artefacto fuente)
```

La huella incluye ruta, tamaño y `mtime_ns`; si un ráster o la base se regenera, la
clave cambia y el resultado viejo no se reutiliza. Medición: primera llamada 0,182 s,
segunda 0,0014 s (≈130×), con `hit: true`. `use_cache=False` desactiva la lectura del
caché pero mantiene la clave declarada.

## 9. Límites

1. No es una validación científica: integra resultados con sus límites.
2. El clima es de dos puntos de reanálisis, no del lugar.
3. El suelo es una predicción global de 0–30 cm.
4. Faltan agua subterránea, profundidad de suelo, AWC y estaciones.
5. Las reglas son generales y no están validadas con rendimientos locales.
6. No hay agregación areal: el perfil es de un punto.

## 10. Pruebas

`tests/test_engines_integration.py` (36) cubre cuatro regiones, ausencia de puntuación,
procedencia, incertidumbre, unidades, reglas de ausencia, rechazo del índice compuesto,
API y rendimiento. No existe una prueba de «verdad» del perfil: no hay referencia
independiente con la que compararlo.
