# Especificación de la API de datos

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/api.py` · Pruebas: `tests/test_data_api.py` · Prefijo: `/api/data`

Solo se documentan endpoints **implementados y probados**. No hay rutas de
demostración con datos inventados.

## 1. Convenciones

- Respuestas JSON; errores con `detail` en español.
- Encabezados en todas las respuestas:
  - `X-AGROSV-Version: 4.0.0`
  - `X-AGROSV-Data-Date: <UTC>`
  - `X-AGROSV-License` en la ficha de dataset (transliterado a ASCII porque los
    encabezados HTTP son latin-1).
- `limit` con máximo 5.000 en series; por defecto 500.
- `bbox` = `oeste,sur,este,norte` en EPSG:4326. Se valida orden y rango; un
  error devuelve **400**.
- Fechas ISO 8601 (`YYYY-MM-DD` o con hora). En observaciones, `end` es
  inclusivo por día calendario y el filtro usa la fecha **local** de referencia.

## 2. Catálogo

### `GET /api/data/catalog`

| Parámetro | Tipo | Descripción |
|---|---|---|
| `domain` | str | TERRITORY, SOILS, HYDROLOGY, CLIMATE, AGRICULTURE, ECONOMY, PHYTOSANITARY, BIODIVERSITY |
| `state` | str | uno de los nueve estados; valor inválido → 400 |
| `institution` | str | coincidencia por institución |
| `redistributable` | bool | filtra por `redistribution_allowed` |
| `include_transitions` | bool | incluye el historial de evidencia |

Devuelve `summary`, `audit`, `filters`, `count`, `datasets`, `states` y una nota
que separa estado de calidad científica. Si el catálogo no existe → **503** con
la instrucción de construcción.

### `GET /api/data/datasets/{dataset_id}`

Ficha completa, artefactos (`assets`), últimos informes de calidad y
`served: true` solo si el estado es `INTEGRATED`. Dataset desconocido → **404**.

### `GET /api/data/datasets/{dataset_id}/lineage`

Derivaciones registradas del dataset. Si no tiene productos derivados devuelve
`derivations: []` con una nota; no inventa una cadena. Sin grafo → **503**.

## 3. Territorio

### `GET /api/data/territories`

| Parámetro | Descripción |
|---|---|
| `level` | country, department, municipality_2023, municipality_historic, district, basin, subbasin, microbasin, protected_area, agricultural_unit, parcel |
| `parent_id` | filtra hijos de un territorio |
| `limit` / `offset` | paginación |

Un nivel sin capa verificada devuelve `total: 0` y la nota «no se sintetizan
límites»; **no** es un 404.

### `GET /api/data/territory/{territory_id}`

Unidad territorial, geometría y `children`. Desconocido → **404**. Sin base →
**503**.

Ejemplo real: `GET /api/data/territory/SV` → país con 14 departamentos.

## 4. Observaciones

### `GET /api/data/observations`

| Parámetro | Descripción |
|---|---|
| `dataset_id` | obligatorio para evitar mezclar fuentes; si el estado no es INTEGRATED → **409** |
| `variable` | p. ej. `precipitation`, `temperature` |
| `bbox` | caja geográfica |
| `territory_id` | unidad territorial asignada |
| `start`, `end` | período, fecha local inclusiva |
| `limit`, `offset` | paginación |

Cada fila conserva `dataset_id`, `dataset_version`, `source_id`, `variable`,
`unit`, `value`, `time_utc`, `time_local`, `period_start`, `period_end`,
`frequency`, `aggregation`, `evidence_class`, `latitude`, `longitude`,
`cell_support`, `territory_id`, `quality_flag`.

Ejemplo:

```bash
curl "http://127.0.0.1:8000/api/data/observations?dataset_id=nasa_power_point&variable=precipitation&start=2020-01-01&end=2020-12-31&limit=5"
```

```json
{
  "count": 5, "total": 366, "limit": 5, "offset": 0,
  "rows": [{
    "dataset_id": "nasa_power_point", "variable": "precipitation",
    "unit": "mm", "value": 0.01,
    "time_utc": "2020-01-01T06:00:00Z", "time_local": "2020-01-01",
    "period_start": "2020-01-01T06:00:00Z",
    "period_end": "2020-01-02T06:00:00Z",
    "frequency": "daily", "aggregation": "sum",
    "evidence_class": "reanalysis", "latitude": 13.7, "longitude": -89.2,
    "quality_flag": "ok"
  }]
}
```

`total` es el total del filtro, no el tamaño de página. Un dataset no integrado
(`chirps3`) devuelve 409: sus metadatos son públicos, sus observaciones no se
sirven porque no están integradas.

## 5. Ocurrencias

### `GET /api/data/occurrences`

`bbox`, `taxon`, `dataset_id`, `limit`, `offset`. Devuelve 300 registros de
GBIF; el registro fuera del *bounding box* terrestre se conserva con
`quality_flag: "outside_land_bbox"`. La nota recuerda que el sesgo de muestreo no
se corrige agregando.

## 6. Ráster

### `GET /api/data/raster/metadata`

`zone` opcional (`samples`, `processed`, `validated`). Devuelve 13 perfiles con
CRS, resolución nativa/efectiva, dtype, nodata, bounds, bytes, heurística COG y
recomendación de contenedor. Sin catálogo ráster → **503**.

## 7. Calidad

### `GET /api/data/quality/reports`

`status` (`PASS`, `PASS_WITH_WARNINGS`, `FAIL`) y `limit`. Devuelve resúmenes
ordenados por `created_at` descendente. Si la base no existe, lee los JSON del
directorio como respaldo, pero aplica la misma regla de vigencia que la base:
por dataset y artefacto solo cuenta el informe más reciente, de modo que un
`FAIL` ya superado no se publica (un `FAIL` vigente sí se publica). Nota:
«PASS no significa dato correcto».

### `GET /api/data/quality/reports/{dataset_id}`

Informes completos del dataset (hasta 20). Sin informes → **404**.

## 8. Dominios y almacenamiento

### `GET /api/data/domains`

Sin parámetros: los ocho contratos A–H con campos, unidades, clave natural,
niveles territoriales y qué está preparado / no implementado.
Con `?code=B` o `?code=SOILS`: contrato y `table_contract`.

Dominio inexistente → **404**.

### `GET /api/data/storage`

Zonas, política Git, existencia y conteos de la base. No expone rutas absolutas
de secretos ni contenido de archivos.

## 9. Códigos de error

| Código | Cuándo |
|---|---|
| 400 | bbox inválido, estado de catálogo inválido, parámetro mal formado |
| 404 | dataset, territorio, dominio o informe inexistente |
| 409 | dataset no INTEGRATED del que se piden observaciones |
| 503 | catálogo, base, grafo de linaje o catálogo ráster no construidos |

## 10. Cobertura de pruebas

`tests/test_data_api.py` verifica: catálogo y filtros, ficha y 404, 409 en
observaciones, filtros por variable/periodo/bbox, bbox inválido, territorios y
nivel sin capa, ocurrencias, metadatos ráster, informes y 404, dominios A–H,
almacenamiento y linaje. Total: 13 pruebas de API dentro de las 109 nuevas.

**No implementado:** autenticación, cuotas, paginación por cursor, consultas por
cuenca (no hay capa), descarga de rásteres por ventana y endpoints de escritura.
La API es de solo lectura.
