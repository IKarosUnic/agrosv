# Modelo de incertidumbre y confianza

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/confidence.py` · Pruebas: `tests/test_quality_confidence.py`

## 1. Por qué no hay un índice único

Un «índice de confianza» de 0 a 100 mezcla errores de naturaleza distinta y
esconde cuál domina. AGROSV separa seis componentes y **solo** calcula un
compuesto si el modelo declara método, valores y pesos. Sin esa declaración, el
resultado es una etiqueta cualitativa con sus motivos.

```
measurement      error de instrumento, muestreo y laboratorio
model            error estructural/paramétrico del modelo
spatial          soporte espacial, agregación, desplazamiento de píxel
temporal         fecha de observación, agregación, desfase
classification   error de clase (cobertura, suelo, cultivo)
provenance       fiabilidad de la fuente y de su cadena de custodia
```

Omitir un componente no lo elimina: `UncertaintyModel.__post_init__` falla si
falta alguno.

## 2. Declaración de un componente

`ComponentStatement` exige:

- si `quantified=True`: método no vacío y al menos un valor
  (`standard_uncertainty`, `relative_uncertainty` o `interval`);
- si `quantified=False`: un motivo explícito (`not_quantified_reason`).

No se acepta «cuantificado: sí» sin número ni «no cuantificado» sin explicación.

## 3. Etiqueta cualitativa

`ConfidencePolicy` fija umbrales **del proyecto**, documentados:

| Etiqueta | Condición |
|---|---|
| `alta` | todos los componentes cuantificados y compuesto relativo ≤ 0,10 |
| `media` | compuesto relativo ≤ 0,30 |
| `baja` | compuesto > 0,30, ausente o componentes sin cuantificar |

Los umbrales no son una propiedad del dato ni sirven para comparar fuentes de
distinta naturaleza. `confidence_label()` devuelve además
`unquantified_components`, `relative_uncertainty` (o `null`) y el motivo.

## 4. Compuesto explícito

`composite(weights=..., aggregation="rss")` exige:

1. pesos declarados para **todos** los componentes que se usan;
2. que los pesos sumen 1 (tolerancia 1e-6);
3. que ningún componente esté sin cuantificar;
4. una metodología no vacía.

Si falta cualquiera, lanza `UncertaintyError`. No hay valores por defecto.

```json
{
  "dataset_id": "ejemplo",
  "variable": "precipitation",
  "unit": "mm",
  "aggregation": "rss",
  "weights": {"measurement": 0.4, "model": 0.1, "spatial": 0.2,
              "temporal": 0.1, "classification": 0.1, "provenance": 0.1},
  "relative_uncertainty": 0.049,
  "confidence": "alta",
  "methodology": "propagación de cuadratura declarada",
  "limits": [
    "el compuesto supone independencia entre componentes; con correlación debe declararse",
    "un intervalo compuesto no es una distribución completa"
  ]
}
```

La agregación `rss` (raíz de la suma de cuadrados) supone independencia. Si hay
correlación, debe declararse y no usarse `rss`. `aggregation="linear"` existe
para escenarios conservadores declarados.

## 5. Resolución ≠ precisión

`assert_resolution_is_not_accuracy(claim)`:

- si hay `resolution` y no `accuracy` → error;
- si hay `accuracy` sin `accuracy_method` → error;
- si ambos existen → devuelve la regla:
  `"resolución ≠ precisión; jerarquía nacional ≠ superioridad científica"`.

Un DEM de 30 m no tiene exactitud de 30 m; SoilGrids a 250 m no tiene error de
250 m; un mapa nacional no es superior a uno global por ser nacional. La
resolución describe el espaciado de la rejilla, no el error.

## 6. Procedencia

`provenance_penalty(source_class)` es una plantilla, no una medición. El valor
cuantificado debe venir de auditar la cadena de custodia (quién produjo el dato,
con qué protocolo, si hubo control de calidad independiente). Una fuente
«oficial» sin documentación no recibe automáticamente menor incertidumbre.

## 7. Estado en Fase 4

- `unquantified_template()` se usa al registrar un dataset nuevo: los seis
  componentes quedan sin cuantificar con su motivo.
- **Ningún dataset de Fase 4 tiene hoy un compuesto numérico de incertidumbre
  publicado.** El catálogo declara una descripción cualitativa de la
  incertidumbre (p. ej. «reanálisis MERRA-2, error de representación espacial no
  cuantificado en El Salvador»), que es honesta pero no es una medición.
- No se ha inventado un número para llenar la ficha. Cuantificar exige datos de
  referencia o repeticiones que aún no están disponibles.

## 8. Límites

- El compuesto no modela correlación entre componentes salvo que se declare.
- Los umbrales 0,10/0,30 son decisiones de publicación, no leyes.
- La etiqueta `alta` no significa «apto para cualquier decisión»: depende del uso.
- `compare_source_uncertainty()` compara modelos declarados, no ordena fuentes
  por país ni por resolución.
