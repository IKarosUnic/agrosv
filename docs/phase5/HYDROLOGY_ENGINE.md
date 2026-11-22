# HydrologyEngine — agua superficial, cuenca derivada y balance climático

**Fase 5 · versión 5.0.0 · estado: implementado parcialmente (sin agua subterránea ni caudales)**
Código: `backend/agrosv/engines/hydrology.py` · API: `/api/engines/hydrology`

## 1. Tres bloques que no son el mismo dato

| Bloque | Qué es | Clase de evidencia |
|---|---|---|
| A. Agua superficial mapeada | cauces y cuerpos de agua de OpenStreetMap, con distancia | observado (cobertura incompleta) |
| B. Cuenca derivada del DEM | D8 sobre una ventana métrica | simulación |
| C. Balance hídrico climático | P y ET0 de reanálisis, escorrentía Budyko–Fu | reanálisis + simulación |

Mezclarlos sería un error: un cauce mapeado no implica caudal, una cuenca derivada no
es una cuenca oficial y un balance P−ET0 no es agua infiltrada ni recarga.

## 2. Agua superficial (OSM)

`surface_water(lon, lat, max_km=10)`:

- lee las capas `waterways` y `water_bodies` del GeoPackage de infraestructura;
- usa el índice espacial para obtener candidatos y mide solo esas geometrías;
- transforma el punto y la geometría a EPSG:32616 y calcula distancia euclídea en metros;
- devuelve el cauce y el cuerpo de agua más cercanos, y el más cercano de ambos;
- declara `within_max_distance` según el radio solicitado.

Advertencias que viajan con la respuesta:

- un cauce mapeado no implica caudal permanente ni agua disponible;
- la ausencia en OSM no implica ausencia en el terreno;
- la proximidad a un cauce no dice nada sobre agua subterránea.

La cobertura de OSM es incompleta y de precisión heterogénea; no es cartografía oficial
de cauces. No hay aforos ni régimen de caudal.

## 3. Cuenca derivada del DEM

`dem_window_metric(lon, lat, size_m, res_m=30)`:

1. valida `5 ≤ size_m ≤ 60.000` y rechaza una ventana menor que dos celdas (no se puede
   remuestrear 10 m desde un DEM de 30 m);
2. transforma el centro a EPSG:32616 y define una rejilla métrica de 30 m;
3. reproyecta **la ventana**, no el país, con remuestreo bilineal declarado;
4. informa `nodata_share` y el número de celdas válidas.

`watershed_from_point(lon, lat, size_m=8000)` aplica el núcleo de Fase 2:

- **priority-flood** (Barnes et al., 2014) para rellenar depresiones;
- **D8** (O'Callaghan & Mark, 1984) para dirección de flujo;
- acumulación de flujo;
- recorrido inverso para la cuenca aguas arriba de la celda consultada;
- área = celdas de la cuenca × 900 m²;
- `truncated: true` si la cuenca toca el borde de la ventana;
- diagnóstico de celdas válidas, acumulación máxima y celdas planas.

El ráster nativo de 1 arcosegundo se reproyecta a 30 m: es un remuestreo declarado, no
resolución nueva. El DEM no resuelve obras hidráulicas ni cauces menores; en zonas
planas el orden de flujo D8 es arbitrario y se informa.

**No es una cuenca oficial.** No hay delimitación oficial (MARN/HydroSHEDS) en el
repositorio. Si el área toca el borde, la cuenca está truncada y el resultado lo dice.

## 4. Balance hídrico climático

`water_balance(lon, lat)` usa la serie anual de precipitación y ET0 del punto climático
más cercano:

```
déficit = P − ET0
índice de aridez = P / ET0
escorrentía = Budyko–Fu(P, ET0, ω)
```

Budyko–Fu:

```
E/P = 1 + φ − (1 + φ^ω)^(1/ω),   φ = ET0/P
Q = P · (1 − E/P)
```

Parámetros y supuestos:

- **ω = 2,0** es una elección documentada, **no calibrada** en El Salvador;
- sensibilidad con **ω = 1,5 y ω = 3,0**; mayor ω implica más evaporación y menos
  escorrentía, de modo que ω = 3,0 da la cota inferior y ω = 1,5 la superior;
- estado estacionario anual: no hay cambio de almacenamiento;
- P y ET0 provienen de productos distintos (NASA POWER y Open-Meteo);
- ningún parámetro se calibró con aforos.

El rango entre productos y sensibilidades **no es un intervalo de confianza**: no hay
estaciones de referencia.

### Lo que el balance no es

- no es un caudal ni un volumen aprovechable;
- no es recarga de acuífero;
- no separa escorrentía, infiltración y caudal base;
- no incorpora extracciones, riego ni regulación;
- no incorpora humedad del suelo ni capacidad de agua disponible (no existen).

## 5. Agua subterránea: interfaz sin datos

`groundwater_availability()` devuelve `available: false` y enumera:

| Variable | Estado | Requisito |
|---|---|---|
| Acuíferos | `NO_SOURCE` | shapefile MARN/ANDA con licencia |
| Niveles piezométricos | `NO_SOURCE` | red de pozos con datum |
| Recarga | `BLOCKED_BY_MISSING_INPUT` | modelo calibrado o trazadores |
| Calidad del agua | `NO_SOURCE` | laboratorio con método y fecha |
| Derechos de agua | `NO_SOURCE` | registro administrativo |

No se infiere un acuífero, un nivel ni una recarga a partir de la proximidad de un río
o de la geología superficial. La ausencia es una propiedad del repositorio, no un
resultado del motor.

## 6. Potencial ≠ acceso

Toda respuesta hidrológica incluye:

```json
"rule": "potencial hidrológico ≠ acceso legal ni operativo al agua"
```

y una lista de lo no calculado: caudal, recarga, almacenamiento de suelo, agua
autorizada. AGROSV no convierte una condición física en un derecho de uso.

## 7. Ejemplo real

Punto `(-89.2, 13.7)`, ventana de 4 km:

```
cuenca aguas arriba        0,0018 km² (2 celdas) · truncated=false
ventana                    133 × 133 celdas · 30 m · EPSG:32616
método                     priority-flood + D8 + recorrido inverso
```

Balance climático anual medio:

```
P      2.219,1 mm
ET0    1.617,9 mm
P−ET0    601,2 mm
P/ET0      1,372
Budyko   1.128,4 mm  (rango 857,2–1.446,2 mm para ω 3,0–1,5)
```

## 8. Rendimiento

| Operación | Mediana (5 repeticiones) |
|---|---|
| `watershed` (3 km) | 0,032 s |
| `profile` (3 km, sin caché) | 0,037 s |

La ventana de 3 km son 100 × 100 celdas (~80 KB en float64); no se carga el DEM nacional.

## 9. Planificado, no implementado

- Delimitación oficial de cuencas y subcuencas.
- Caudales: requieren aforos y curvas de gasto.
- Recarga: requiere acuífero, niveles y parámetros hidráulicos.
- Humedad del suelo y capacidad de agua disponible: bloqueadas por falta de densidad
  aparente y curva de retención.
- Balance mensual/serie: la serie climática existe, pero un balance mensual exigiría
  almacenamiento de suelo que no existe; publicarlo sería un supuesto disfrazado.

## 10. Pruebas

`tests/test_engines_hydrology.py` (10): validación de ventana, rejilla métrica,
distancia real y advertencias, ausencia de agua subterránea, invariantes de cuenca,
límites físicos de Budyko, coherencia del balance y separación potencial/acceso.
`tests/test_engines_integration.py` añade áreas dentro de la ventana, caché y API.
