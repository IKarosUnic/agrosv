# MODULE J — Hydrological Simulation

**Versión:** 2.0 · **Fecha:** 2026-11-22 · **Estado:** **núcleo D8 implementado y probado** (`backend/agrosv/science/hydrology.py`); balance hídrico, SWAT+, recarga y demanda agrícola siguen **no implementados**.

Delimitación de cuencas, balance hídrico y demanda agrícola. El módulo responde
«¿cuánta agua hay, cuándo y con qué confiabilidad?», no «¿hay un río cerca?».

---

## 1. Fuentes

| Insumo | Fuente | Resolución | Estado |
|---|---|---|---|
| DEM | Copernicus GLO-30 (Fase 1) | 30 m | **VERIFIED** |
| Subcuencas oficiales | PNGIRH 2017 (Pfafstetter > 10 km², DEM 1:25.000) | — | **PENDING_VALIDATION** |
| Subcuencas (servicio) | FeatureServer regional (tercero) | — | **VERIFIED** |
| Precipitación | CHIRPS v3 0,05° | diaria | **VERIFIED** |
| Temperatura / ET₀ | AgERA5 0,1° | diaria | **RESTRICTED** |
| Uso del suelo | OSM + ESA WorldCover (a validar) | vectorial / 10 m | parcial |
| Suelos | SoilGrids / CENTA | 250 m / no disp. | predicción / **PENDING** |
| Agua superficial | OSM `waterway`, `water` | vectorial | **VERIFIED** |
| Calidad del agua | MARN | — | **UNAVAILABLE** |

---

## 2. Componentes

| Componente | Método | Salida |
|---|---|---|
| Delimitación de cuencas | D8 o D-infinity sobre DEM corregido (fill sinks) | polígonos de cuenca |
| Red de drenaje | acumulación de flujo con umbral de área | líneas con orden de Strahler |
| Escorrentía | número de curva (SCS-CN) o SWAT+ | mm/día |
| Infiltración | CN + propiedades del suelo | mm/día |
| Balance hídrico | P − ET − Q − ΔS | mm/mes |
| Recarga potencial | balance en la zona no saturada | mm/año |
| Demanda agrícola | ETc por cultivo (Module C) | m³/ha |
| Riesgo de inundación | acumulación + pendiente + lluvia extrema | índice, no mapa oficial |
| Erosión | RUSLE (R·K·LS·C·P) | t/ha/año |

**Modelo externo evaluado:** SWAT+ rev. 62.0.1, **LGPL-2.1**, sin registro;
requiere DEM proyectado sin vacíos, suelos, uso del suelo, clima diario y punto
de salida; QSWAT+ exige QGIS + TauDEM. Se adopta **solo** para cuencas piloto,
no para el país completo en Fase 2.

**Alternativa propia:** D8 + SCS-CN es suficiente para un primer balance y no
requiere dependencias externas; se usa para validar antes de escalar a SWAT+.

---

## 3. Regla crítica sobre disponibilidad de agua

> La proximidad a un río **no** implica disponibilidad legal ni técnica.

El motor distingue:

| Concepto | Qué significa | Fuente |
|---|---|---|
| Agua física | caudal o almacenamiento estimado | modelo |
| Agua accesible | pendiente, distancia, infraestructura | DEM + OSM |
| Agua autorizada | concesión o permiso | **no disponible** |
| Agua comprometida | otros usos | **no disponible** |

Ningún resultado se etiqueta «agua disponible para riego» sin las dos últimas.
Se usa «agua físicamente presente» y «demanda estimada».

---

## 4. Modelo de datos

```sql
basin(
  basin_id TEXT PK, name TEXT, level TEXT,        -- 'cuenca'|'subcuenca'
  parent_id TEXT NULL, area_km2 NUMERIC,
  source_id TEXT, geometry GEOMETRY(MultiPolygon,4326)
);

flow_network(
  reach_id TEXT PK, basin_id TEXT, order INT,
  geometry GEOMETRY(LineString,4326), length_km NUMERIC
);

water_balance(
  cell_id TEXT, date DATE, precip_mm, et0_mm, et_actual_mm,
  runoff_mm, infiltration_mm, storage_change_mm,
  source_id TEXT, quality SMALLINT
);

erosion_risk(
  geometry, r_factor, k_factor, ls_factor, c_factor, p_factor,
  soil_loss_t_ha_year, class TEXT, method TEXT, source_id
);
```

---

## 5. Interfaz

```
GET  /api/hydro/basins?level=subcuenca&bbox=
GET  /api/hydro/flow?basin_id=
GET  /api/hydro/balance?basin_id=&from=&to=
GET  /api/hydro/demand?basin_id=&crop=maiz&area_ha=
GET  /api/hydro/erosion?basin_id=&from=&to=
POST /api/hydro/scenario                  (riego, cambio de uso)
```

Toda respuesta incluye `method`, `resolution`, `calibrated: false|true` y
`limitations`.

---

## 6. Validación

| Prueba | Criterio |
|---|---|
| Topología | la red es conexa; todos los tramos drenan a una salida |
| Áreas | ∑ subcuencas = área de la cuenca (± 2 %) |
| Balance | P = ET + Q + ΔS (± 10 % anual) |
| Física | escorrentía ≥ 0; ET ≤ ET₀; sin valores negativos de almacenamiento |
| DEM | sin sumideros tras el relleno; pendientes ≥ 0 |
| Erosión | RUSLE en rango 0–200 t/ha/año para SV; valores extremos revisados |

**Calibración:** sin aforos ni datos de caudal, el modelo **no está calibrado**.
Se declara en cada respuesta y no se presentan caudales como mediciones.

---

## 7. Limitaciones

1. Sin datos de caudal ni estaciones, no hay calibración hidrológica posible.
2. El DEM 30 m no resuelve cauces menores ni obras hidráulicas.
3. Las subcuencas oficiales no están verificadas como descargables.
4. SWAT+ agrega incertidumbre de suelos y uso del suelo; su calibración requiere
   series observadas.
5. El balance es climático, no operativo: no sirve para asignar agua.

---

## 8. Dependencias y prioridad

Depende de: DEM, CHIRPS, AgERA5, suelos, subcuencas. Habilita: Module F
(inundación, sequía), Module K (erosión), Module C (riego).

**Prioridad:** media. Primero delimitación y balance simple (sin SWAT+); SWAT+
solo cuando exista una cuenca piloto y datos para calibrar.

---

## 9. Implementado en este ciclo (2026-11-22)

`backend/agrosv/science/hydrology.py` implementa, con NumPy y `heapq` (sin
dependencias nuevas):

| Componente | Método | Verificación |
|---|---|---|
| Relleno de sumideros | priority-flood (Barnes et al., 2014) | pozo interior rellenado al borde; nunca se rellena una celda sin dato |
| Dirección de flujo | D8 (O'Callaghan & Mark, 1984) | ladera plana drena al este; el borde queda como salida |
| Acumulación | orden descendente de elevación | crece aguas abajo; conserva el área total |
| Cuenca | recorrido inverso D8 desde la salida | máscara = acumulación de la celda de salida (invariante probado en el DEM real) |
| Red de drenaje | umbral de área declarado | umbral inválido rechazado |
| Pendiente y LS | diferencias finitas + Wischmeier & Smith (1978) | positivo, monótono con pendiente y área aportante |

Expuesto en la API como `GET /api/v1/hydro/watershed` y `GET /api/v1/hydro/aoi`,
con etiqueta `derivado`, resolución 30 m, `truncated` cuando la cuenca toca el
borde de la ventana y la limitación explícita de que **no está calibrado**.

Lo que sigue sin existir: balance hídrico con ET real, escorrentía SCS-CN,
recarga, demanda agrícola, riesgo de inundación, SWAT+, y cualquier validación
contra aforos. La proximidad a un cauce sigue sin implicar agua disponible.
