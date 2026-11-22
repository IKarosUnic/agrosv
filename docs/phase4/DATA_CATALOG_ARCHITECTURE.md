# Arquitectura del catálogo nacional de datos

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/catalog.py` · Persistencia: `data/metadata/datasets.json` · Pruebas: `tests/test_data_catalog.py`

## 1. Qué resuelve

El catálogo es la **fuente única de verdad** sobre qué datos existen, de dónde
vienen, bajo qué licencia y —sobre todo— **qué se ha demostrado** sobre ellos. No
es una lista de descargas: es un registro de estados con evidencia auditable.

Regla de diseño: *importar no valida*. Un archivo en disco puede estar
`DOWNLOADED` durante meses; solo pasa a `VALIDATED` cuando un informe de calidad
aprobado, con al menos tres comprobaciones y un alcance declarado, lo respalda. Y
solo pasa a `INTEGRATED` cuando además existe una consulta verificable.

```
descubrir → conseguir acceso → descargar → parsear → validar → integrar
                    ↘ restringido / no disponible / rechazado
```

El estado **no es una medida de calidad científica**. `evidence_level` (V0–V4)
es independiente y se rige por el protocolo de validación de Fase 2. Un dataset
`INTEGRATED` puede seguir en V0: significa «consultable», no «científicamente
validado». El resumen del catálogo lo dice explícitamente.

## 2. Ficha de dataset

Cada registro (`DatasetRecord`, Pydantic) contiene los campos exigidos por §3:

| Grupo | Campos |
|---|---|
| Identidad | `dataset_id`, `name`, `description`, `domain` |
| Origen | `institution`, `source_url`, `publication_date`, `version` |
| Acceso | `license`, `redistribution_allowed`, `derived_use_allowed`, `usage_restrictions`, `download_date` |
| Cobertura | `geographic_coverage`, `temporal_coverage`, `crs`, `spatial_resolution`, `temporal_resolution` |
| Contenido | `variables`, `units`, `format`, `size` |
| Ciencia | `methodology`, `limitations`, `uncertainty` |
| Estado | `state`, `evidence_level`, `validation_scope`, `integration_scope` |
| Evidencia | `artifacts`, `transitions`, `updated_at` |

Los campos desconocidos son `None` y **no se rellenan por conveniencia**.
`missing_fields()` enumera lo que falta; ese listado viaja en la API y bloquea la
transición a `VALIDATED` cuando afecta a licencia, cobertura, resolución,
metodología, incertidumbre, limitaciones, variables, unidades o CRS.

Una variable física sin unidad declarada se reporta como `units[<variable>]`. Las
variables adimensionales (pH, NDVI) pueden declarar `""` porque su unidad
canónica es el vacío, no porque la unidad sea opcional.

### Ejemplo abreviado de ficha (`chirps3`)

```json
{
  "dataset_id": "chirps3",
  "name": "CHIRPS v3 — precipitación (muestra de un día)",
  "institution": "Climate Hazards Center, UC Santa Barbara",
  "source_url": "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/2026/chirps-v3.0.rnl.2026.01.15.tif",
  "publication_date": "2026-01-15 (fecha del dato)",
  "download_date": "2026-11-22",
  "version": "v3.0 (variante rnl)",
  "license": "Uso abierto con atribución (verificar aviso CHC)",
  "geographic_coverage": "global, recortado a El Salvador",
  "temporal_coverage": "1 día (2026-01-15)",
  "crs": "EPSG:4326",
  "spatial_resolution": "0,05° (~5,5 km)",
  "temporal_resolution": "diaria desagregada; nativa pentadal",
  "variables": ["precipitation"],
  "units": {"precipitation": "mm"},
  "format": "GeoTIFF (muestra) → GeoTIFF recortado",
  "state": "VALIDATED",
  "evidence_level": "V1",
  "validation_scope": "1 día global recortado a El Salvador; no es una serie integrada"
}
```

## 3. Máquina de estados

Transiciones permitidas (`ALLOWED_TRANSITIONS`):

| Desde | Hacia |
|---|---|
| DISCOVERED | ACCESS_PENDING, DOWNLOADED, RESTRICTED, UNAVAILABLE, REJECTED |
| ACCESS_PENDING | DOWNLOADED, RESTRICTED, UNAVAILABLE, REJECTED |
| DOWNLOADED | PARSED, REJECTED, UNAVAILABLE |
| PARSED | VALIDATED, REJECTED |
| VALIDATED | INTEGRATED, DOWNLOADED (degradación por revalidación), REJECTED |
| INTEGRATED | VALIDATED (degradación), REJECTED |
| RESTRICTED | ACCESS_PENDING, UNAVAILABLE, REJECTED |
| UNAVAILABLE | ACCESS_PENDING, DISCOVERED, REJECTED |
| REJECTED | — (terminal) |

No se puede saltar de `DISCOVERED` a `VALIDATED`. Tampoco se puede «arreglar» un
estado con un `PATCH`: `Catalog.patch()` rechaza el campo `state` y obliga a usar
`transition()` con evidencia.

## 4. Puertas de evidencia

Toda transición exige al menos una `Evidence` con `reference` verificable
(mínimo 3 caracteres) y fecha de captura. Tipos: `url_probe`, `file_hash`,
`parse_result`, `validation_report`, `integration_record`, `license_check`,
`institutional_response`, `manual_review`, `reconciliation`.

| Destino | Exigencia |
|---|---|
| DISCOVERED | evidencia no vacía (sonda de URL o revisión manual) |
| DOWNLOADED | `file_hash`, ≥1 artefacto existente en disco, `download_date` |
| PARSED | `parse_result` con `passed=true` y variables declaradas |
| VALIDATED | sin campos críticos faltantes; `validation_report` pasado; `checks_run ≥ 3`; sin informe `FAIL`; `validation_scope` |
| INTEGRATED | haber pasado por VALIDATED; `validation_scope`; `integration_scope`; `integration_record` con `queryable=true` |
| RESTRICTED | `license_check` |
| UNAVAILABLE / REJECTED | evidencia con `passed=false`; REJECTED exige limitación o motivo |

`Evidence.from_file()` calcula el sha256 del archivo y marca `passed=false` si no
existe. La evidencia no es decorativa: `Transition` valida que cada entrada tenga
referencia.

## 5. Estado actual del catálogo

Generado por `scripts/08_build_phase4_integration.py` (22 datasets, 71
transiciones, auditoría estructural OK):

| Estado | N |
|---|---|
| DISCOVERED | 1 |
| ACCESS_PENDING | 2 |
| DOWNLOADED | 1 |
| PARSED | 1 |
| VALIDATED | 2 |
| INTEGRATED | 7 |
| RESTRICTED | 4 |
| UNAVAILABLE | 3 |
| REJECTED | 1 |
| **Total** | **22** |

Por dominio: TERRITORY 5, CLIMATE 5, AGRICULTURE 4, SOILS 3, BIODIVERSITY 2,
HYDROLOGY 2, ECONOMY 1. No hay datasets de FITOSANIDAD: el catálogo no inventa
fuentes que la Fase 3 no pudo verificar.

Integrados: `copdem30`, `geoboundaries_adm1`, `osm_sv`, `soilgrids_2`,
`nasa_power_point`, `open_meteo_point`, `gbif_sv`.

## 6. Auditoría

`Catalog.audit()` comprueba, sin reevaluar ciencia:

- que cada transición registrada sea legal;
- que el estado actual sea alcanzable;
- que exista historial de evidencia;
- que los artefactos declarados existan;
- que no haya estados imposibles.

Salida real: `{"checked": 22, "ok": true, "problems": [], "transitions": 71}`.
La nota de la API es explícita: *auditoría estructural, no científica*.

## 7. Persistencia y API

`datasets.json` (112 KB) guarda `schema_version: 4`, fecha de generación y la
lista completa. `Catalog.load()` rechaza un esquema más nuevo que el código.
La API expone:

- `GET /api/data/catalog` — resumen, auditoría, filtros por dominio, estado,
  institución y redistribución.
- `GET /api/data/datasets/{dataset_id}` — ficha, artefactos, informes de calidad
  y `served` (solo `INTEGRATED` sirve observaciones).

## 8. Limitaciones declaradas

- El catálogo **no** contiene todos los metadatos de todos los productos: cuando
  la Fase 3 no pudo verificar CRS, variables o resolución, el campo queda nulo y
  aparece en `missing_fields`. Es una limitación visible, no un hueco disimulado.
- La auditoría verifica estructura, no veracidad: un `file_hash` prueba que el
  archivo es el registrado, no que la fuente haya medido bien.
- Los estados `RESTRICTED`, `UNAVAILABLE` y `REJECTED` documentan por qué no se
  usa un dataset; no son fallos del catálogo.
