# TerritorialEngine — identificación y contexto territorial

**Fase 5 · versión 5.0.0 · estado: implementado**
Código: `backend/agrosv/engines/territorial.py` · API: `/api/engines/territorial`, `/api/engines/territory/*`

## 1. Qué responde

«¿Dónde está este punto, a qué unidad administrativa pertenece y qué se sabe de su
territorio?» con tres bloques separados, porque no son la misma clase de dato:

| Bloque | Contenido | Clase de evidencia |
|---|---|---|
| Identificación | país, departamento (ADM1), municipio histórico (ADM2) | observado (límites derivados de OSM) |
| Caracterización física | elevación, pendiente, aspecto, TRI, TPI, clase de relieve | predicción modelada (DSM) |
| Asociación hidrográfica | cuenca local derivada del DEM, cauce mapeado más cercano | simulación + observado (OSM) |

## 2. Modos de consulta

### 2.1 Por coordenadas

`TerritorialEngine.profile(lon, lat, radius_cells=2, size_m=6000)`

EPSG:4326, longitud y latitud en grados decimales. Antes de leer cualquier ráster:

- se rechaza una coordenada no numérica, no finita o fuera de rango;
- se rechaza un punto fuera del rectángulo nacional `SV_BOUNDS`
  (`-90.1790975, 12.976046, -87.6351394, 14.4510488`) con `CoverageError` → HTTP 400;
- un punto dentro del rectángulo pero fuera de todo departamento se declara
  `inside_land: false` (aguas territoriales): no hay suelo ni DEM que consultar y
  el perfil falla en lugar de devolver ceros.

La contención se resuelve con geometría exacta (`shapely.Point` contra ADM1/ADM2),
no por distancia al centroide ni por nombre.

### 2.2 Por identificador oficial

`TerritorialEngine.profile_by_territory(query, level=None)`

Acepta `territory_id` (`SV-ADM1-AH`), código fuente (`SV-AH`) o nombre normalizado
(`ahuachapan`). El nombre es solo un atributo de búsqueda; la clave es el
identificador. Si hay ambigüedad se devuelven los candidatos y **no se elige uno**.

El perfil se evalúa en `representative_point()` del polígono, un punto interior
garantizado. La respuesta lo declara:

```json
"point_rule": "punto interior representativo (representative_point): el perfil
describe ese punto, no un promedio areal del territorio"
```

No se implementa agregación areal (media de todas las celdas del polígono): exigiría
ponderar por área y declarar la resolución efectiva de cada capa, y no es lo que
promete el endpoint.

### 2.3 Intersección y contención espacial

`territories_in_bbox(west, south, east, north, level=None)` y
`GET /api/engines/territory/intersect`.

- consulta el índice espacial de cada capa con predicado `intersects`;
- informa `contains_query_bbox` para saber si una unidad contiene el rectángulo
  completo;
- devuelve el área de la unidad en EPSG:6933 (calculada en Fase 1);
- rechaza extensiones invertidas, no finitas o fuera de rango geográfico.

Un rectángulo no es una parcela ni una cuenca; la respuesta lo dice.

## 3. Niveles administrativos

| Nivel | Presente | Oficial | Fuente |
|---|---|---|---|
| `country` (ADM0) | sí | sí | disolución de ADM1 (el ADM0 del proveedor incluye ~4.373 km² de aguas) |
| `department` (ADM1) | 14 | sí | geoBoundaries gbOpen |
| `municipality_historic` (ADM2) | 272 | **no** | división anterior a la reforma de 2023 |
| `municipality_2023` (44) | **no** | — | sin capa ni tabla de correspondencia verificada |
| `district` (262) | **no** | — | sin capa |
| `basin` / `subbasin` | **no** | — | la cuenca del motor es una derivación D8, no un límite oficial |
| `protected_area` / `parcel` | **no** | — | sin datos verificados |

`coverage()` enumera los niveles ausentes con su motivo. Los niveles ausentes no se
sintetizan por nombre, interpolación ni proximidad.

## 4. Respuesta

Toda respuesta usa la envoltura de `governance.envelope`:

```
engine, engine_version, generated_at, query, result,
sources[] (ficha §8), coverage, limitations[], processing_history[],
conventions (CRS, unidades, NoData)
```

`result` contiene `location`, `terrain`, `hydrological_association`,
`department_context` (solo si existe con su fuente) y `layer_resolution`.

## 5. Ejemplo real (San Salvador, 2025)

Consulta `(-89.2, 13.7)`, radio 2 celdas:

```
país          El Salvador (SV, oficial, 20.966,364 km²)
departamento  San Salvador (SV-SS, oficial, 900,394 km²)
municipio     San Salvador (ADM2 histórico, official=false, 55,866 km²)
elevación     676,82 m
pendiente     2,67° (4,66 %)
aspecto       139,8° SE
clase         suave (2–5°)
TRI           3,60 m
TPI           0,73 m → ladera
cuenca local  0,0018 km² (2 celdas), truncated=false
```

Una cuenca de dos celdas no es un error: el punto cae sobre una divisoria local y el
algoritmo D8 solo encuentra dos celdas aguas arriba. El resultado lo declara con su
método y su ventana; no se completa con una cuenca «plausible».

## 6. Límites de la implementación

1. No hay límites municipales 2023, distritos, cuencas oficiales, áreas protegidas ni
   parcelas.
2. ADM2 es histórico y `official: false`.
3. La exactitud posicional de los límites no está verificada; geoBoundaries deriva de
   OSM y puede diferir del límite legal.
4. Un límite administrativo no coincide con una cuenca ni con un acuífero.
5. El perfil por identificador describe un punto interior, no el territorio completo.
6. La resolución del DEM (30 m) no es su exactitud posicional.

## 7. Verificación

- `tests/test_engines_territorial.py` (19 pruebas): cobertura, rechazo de coordenadas,
  contención, búsqueda por nombre y código, cuenca truncada, gobernanza.
- `tests/test_engines_integration.py` (36 pruebas): perfil por identificador,
  intersección/contención, océano dentro del bbox, API y errores 400/404/409.
- Área nacional derivada 20.966,364 km² frente a 21.041 km² de referencia: −0,35 %
  (dentro de la tolerancia declarada de ±3 %).
