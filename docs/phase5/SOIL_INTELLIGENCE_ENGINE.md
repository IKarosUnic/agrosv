# SoilEngine — propiedades del suelo y limitaciones declaradas

**Fase 5 · versión 5.0.0 · estado: implementado (una sola profundidad)**
Código: `backend/agrosv/engines/soil.py` · API: `/api/engines/soil`, `/api/engines/soil/profile`

## 1. Fuente y clase de dato

| Campo | Valor |
|---|---|
| Dataset | SoilGrids 2.0 (ISRIC — World Soil Information) |
| Clase de evidencia | `modeled_prediction` (machine learning global) |
| Resolución | 250 m (soporte de la predicción) |
| Profundidad | **0–30 cm únicamente** |
| CRS | EPSG:32616 (reproyectado desde Interrupted Goode Homolosine) |
| Licencia | CC BY 4.0 |
| Cobertura | tierra firme de El Salvador, 97,4 % de celdas con dato |

**No es una medición de laboratorio.** El Mapa Digital de Suelos del CENTA está en el
catálogo como `RESTRICTED` (sin acceso ni licencia verificados) y no se usa. No se
presenta una predicción global como equivalente a una muestra nacional.

## 2. Variables disponibles

| Variable | Unidad | Archivo | Escala declarada |
|---|---|---|---|
| `clay` | % | `clay_0-30cm.tif` | 0,1 |
| `sand` | % | `sand_0-30cm.tif` | 0,1 |
| `silt` | % | `silt_0-30cm.tif` | 0,1 |
| `ph` | — (pH en H₂O) | `phh2o_0-30cm.tif` | 0,1 |
| `soil_organic_carbon` | g kg⁻¹ | `soc_0-30cm.tif` | 0,1 |
| `soil_nitrogen` | g kg⁻¹ | `nitrogen_0-30cm.tif` | 0,01 |

El valor se obtiene multiplicando el entero almacenado por la escala del propio
archivo. `nodata` (−32768) y celdas enmascaradas devuelven `null` con el motivo; no se
imputa el valor de una celda vecina.

La media 0–30 cm se construyó en Fase 1 con pesos **5/30, 10/30 y 15/30** a partir de
las capas 0–5, 5–15 y 15–30 cm.

## 3. Clase textural USDA

`usda_texture_class(sand, silt, clay)` implementa el triángulo textural USDA-NRCS en
orden de especificidad. Si las fracciones no suman 100 ± 5 o ninguna regla aplica,
devuelve `sin_clasificar` en vez de forzar una clase.

**Corrección aplicada en Fase 5.** La versión inicial clasificaba arcilla 20–27 % con
limo ≥ 28 % como «franco arcilloso». El franco arcilloso exige arcilla ≥ 27 %; con
20–27 % la clase USDA es franca. El caso `(arena 50, limo 30, arcilla 20)` devolvía
`franco arcilloso` y ahora devuelve `franco`. La prueba paramétrica del triángulo
(textura arenosa, franca, limosa, arcillosa y sus intermedios) cubre 12 combinaciones.

Advertencia publicada: el redondeo del ráster (±0,05 %) puede mover una celda de clase
cerca de una frontera.

## 4. Materia orgánica

Solo se calcula con un factor documentado:

```
MO (%) = SOC (g/kg) × 1,724 / 10
```

`1,724` es el factor de Van Bemmelen; el rango publicado habitual es 1,7–2,0, de modo
que el valor cambia ±8 %. La respuesta lo etiqueta `derivado`, no `medido`, e incluye
`factor`, `factor_range` y la nota de conversión.

## 5. Modelo de perfil

`profile_model()` declara los intervalos normalizados y su disponibilidad real:

| Intervalo | Rol | Estado |
|---|---|---|
| 0–30 cm | integrado (media ponderada) | **disponible** |
| 0–5 cm | estándar SoilGrids | no disponible |
| 5–15 cm | estándar SoilGrids | no disponible |
| 15–30 cm | estándar SoilGrids | no disponible |
| 30–60 cm | estándar SoilGrids | no disponible |
| 60–100 cm | estándar SoilGrids | no disponible |
| 100–200 cm | estándar SoilGrids | no disponible |

Cada intervalo ausente lleva su motivo: la capa no se descargó y no se interpola entre
profundidades. `profile_at_depth(lon, lat, top_cm, bottom_cm)` responde una consulta
por intervalo: devuelve propiedades solo para 0–30 cm y, para cualquier otro
intervalo, `available: false` con el intervalo disponible más cercano. No se reparte
la media ponderada entre subintervalos.

## 6. Reglas de limitación

No hay puntuación ni índice de aptitud. Cada regla produce un hallazgo con variable,
umbral, consecuencia y evidencia:

| Código | Variable | Condición | Consecuencia declarada |
|---|---|---|---|
| `acidez_fuerte` | pH | < 5,5 | posible limitación de P y toxicidad de Al |
| `acidez_moderada` | pH | 5,5–6,0 | puede requerir encalado según cultivo |
| `alcalinidad` | pH | > 7,8 | menor disponibilidad de micronutrientes |
| `arcilla_alta` | arcilla | ≥ 35 % | compactación, laboreo dificultoso, drenaje lento |
| `arena_alta` | arena | ≥ 70 % | baja retención de agua y nutrientes |
| `carbono_organico_bajo` | SOC | < 10 g kg⁻¹ | menor estructura y fertilidad potencial |
| `ph_fuera_de_rango` | pH | < 3,5 o > 10,0 | revisar: posible artefacto |

Cada hallazgo incluye `evidence_class: modeled_prediction`, `confidence: baja` y la
advertencia de que una regla sobre una predicción global no es un diagnóstico de campo
ni una recomendación.

## 7. Comparación entre fuentes

`compare_sources()` devuelve:

- `available_sources`: SoilGrids 2.0, con las variables que sí tienen valor;
- `unavailable_sources`: CENTA, `RESTRICTED`, con el motivo;
- `conflicts: []` y `comparison_possible: false`.

No se pueden detectar conflictos entre una predicción global y una fuente nacional
inaccesible. La lista vacía es una consecuencia declarada de la ausencia, no una
afirmación de que las fuentes coinciden.

## 8. Variables declaradas ausentes

`governance.UNAVAILABLE` documenta, con motivo y requisito:

| Variable | Estado | Por qué |
|---|---|---|
| Perfiles por horizonte | `NOT_DOWNLOADED` | solo se descargó la agregación 0–30 cm |
| Profundidad efectiva | `NO_SOURCE` | ninguna fuente integrada la mide |
| Densidad aparente | `NOT_DOWNLOADED` | SoilGrids `bdod` no descargado |
| Fragmentos gruesos | `NOT_DOWNLOADED` | SoilGrids `cfvo` no descargado |
| CEC | `NOT_DOWNLOADED` | no se estima por pedotransferencia |
| Agua disponible (AWC) | `BLOCKED_BY_MISSING_INPUT` | falta densidad aparente y curva de retención |
| Salinidad (CE) | `NO_SOURCE` | sin análisis de laboratorio |
| Mapa nacional de suelos | `RESTRICTED_SOURCE` | CENTA sin licencia verificada |
| Drenaje, unidades de suelo | `RESTRICTED_SOURCE` | dependen del mapa nacional |

## 9. Ejemplo real

Punto `(-88.6, 13.4)`:

```
arcilla 33,3 % · limo 31,9 % · arena 34,8 % · pH 6,0
SOC 22,6 g/kg · N total 1,83 g/kg
clase textural: arcilla franca
materia orgánica derivada: 3,9 % (factor 1,724)
limitaciones: ninguna regla disparada
```

## 10. Límites

1. Predicción, no medición; sin error por celda en este repositorio.
2. Una sola profundidad integrada.
3. Sin CEC, densidad aparente, fragmentos gruesos, AWC ni salinidad.
4. Sin comparación posible con la fuente nacional.
5. Las reglas no están validadas con rendimientos ni análisis locales.
6. El soporte de 250 m no es precisión de 250 m.

## 11. Pruebas

`tests/test_engines_soil.py` (22 pruebas): 12 combinaciones texturales, suma
incoherente, materia orgánica, intervalos del perfil, reglas sin puntuación,
NoData real, unidades/procedencia/resolución y declaración de ausencias.
`tests/test_engines_integration.py` añade la consulta por profundidad y la coherencia
de unidades en el perfil ambiental.
