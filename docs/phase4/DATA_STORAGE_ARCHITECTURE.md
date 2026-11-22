# Arquitectura de almacenamiento

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/storage.py`, `backend/agrosv/data/store.py` · Pruebas: `tests/test_lineage_storage.py`

## 1. Zonas

La estructura existente no se renombró. Se añadieron `staging/` y `validated/`
con un significado explícito:

```
data/
  raw/         descargas originales, inmutables        (no Git)
  staging/     escritura temporal, nunca entregable   (no Git)
  validated/   normalizado + aprobado por calidad      (Git con límite)
  processed/   capas listas para API                   (Git con límite)
  derived/     resultados de modelo pequeños           (Git con límite)
  metadata/    catálogo, correspondencias, contratos   (Git, ≤5 MB)
  manifests/   linaje, monitoreo, estado de lotes      (Git, ≤5 MB)
  samples/     evidencia ligera de Fase 3              (Git, ≤5 MB)
```

`DataLayout` centraliza todas las rutas; ningún otro módulo escribe
`data/...` a mano. `ensure_layout()` solo crea directorios ausentes: no borra ni
mueve nada.

## 2. Política Git (ejecutable)

| Zona | ¿Git? | Límite por archivo | Motivo |
|---|---|---|---|
| raw | no | — | descargas voluminosas y regenerables |
| staging | no | — | escritura temporal |
| validated | sí | 25 MB | datos normalizados aprobados |
| processed | sí | 25 MB | capas de API |
| derived | sí | 10 MB | resultados reproducibles |
| metadata | sí | 5 MB | catálogo y contratos |
| manifests | sí | 5 MB | trazabilidad |
| samples | sí | 5 MB | evidencia ligera |

`git_tracking_decision(path)` devuelve `{track, zone, bytes, limit, reason}`; no
un booleano. Un archivo de 26 MB en `validated/` se rechaza con el motivo
«excede el límite… versione solo su manifiesto».

Además, `.gitignore` excluye:

```
data/raw/*                     (regla existente)
data/samples/**/*.tif          (regla existente)
data/validated/*.sqlite        (Fase 4)
data/validated/*.sqlite-wal
data/validated/*.sqlite-shm
data/validated/**/*.tif
```

La base SQLite y los rásteres derivados son **regenerables**: su receta y hash
quedan en `manifests/`. Versionar 9,6 MB de base en cada cambio sería ruido, no
trazabilidad.

## 3. Qué va en base de datos y qué en archivos

| Contenido | Dónde | Por qué |
|---|---|---|
| catálogo de datasets | JSON + tabla `datasets` | lectura humana y consulta |
| observaciones normalizadas | SQLite `observations` | filtros por dataset, variable, tiempo, bbox |
| ocurrencias biológicas | SQLite `occurrences` | filtros por bbox/taxón |
| territorios e índices | SQLite `territories` | jerarquía y búsqueda |
| artefactos y hashes | SQLite `assets` + manifiestos | auditoría |
| informes de calidad | SQLite `quality_reports` + JSON | consulta y archivo |
| DEM, pendiente, suelo | GeoTIFF en `processed/` | operaciones por ventana |
| CHIRPS recortado | GeoTIFF en `validated/` | ráster pequeño derivado |
| GeoPackage administrativo | `processed/` | capas vectoriales completas |
| linaje y monitoreo | JSON en `manifests/` | pequeños, versionables |

La base **no** guarda rásteres ni capas vectoriales completas: solo metadatos,
índices y series. Los binarios viven en `data/` y se referencian por ruta y hash.

## 4. Evaluación de alternativas

| Tecnología | Para qué sirve | Decisión en Fase 4 |
|---|---|---|
| PostgreSQL + PostGIS | consultas espaciales concurrentes, índices GiST | no ahora: añade un servicio sin demanda; ruta de migración documentada |
| SQLite | consulta local por clave, series y metadatos | **elegido** para la capa de consulta |
| GeoPackage | capas vectoriales completas portables | **usado** para límites administrativos y OSM |
| Parquet | analítica columnar de tablas grandes | no adoptado: sin `pyarrow` en el entorno; evaluar al crecer |
| COG | ráster por ventana con overviews | **recomendado** para los GeoTIFF; no se convirtieron aún |
| NetCDF | series multidimensionales secuenciales | no adoptado: no hay series multidimensionales integradas |
| Zarr | series multidimensionales en chunks paralelos | no adoptado: misma razón; recomendación registrada |

La elección se hizo con el volumen real (20.456 observaciones, 287 territorios),
no con un supuesto de escala futura.

## 5. SQLite: decisión y esquema

Se eligió SQLite, no PostgreSQL/PostGIS, porque:

- el volumen integrado es de decenas de miles de filas (20.456 observaciones);
- el proyecto se ejecuta local, sin servicio que administrar;
- el esquema es SQL explícito y las geometrías se guardan como GeoJSON, lo que
  permite migrar a PostGIS sin reescribir la capa de consulta;
- los rásteres no se benefician de PostGIS en esta fase.

Tablas: `meta`, `datasets`, `observations`, `occurrences`, `territories`,
`assets`, `quality_reports` y, cuando el módulo R-tree está disponible,
`observations_rtree` para consultas por caja.

Índices: `(dataset_id, variable, time_utc)`, `territory_id`,
`(longitude, latitude)`, nivel territorial, dataset de activos e informes.

Estado real (`DataStore.summary()`):

```json
{
  "exists": true,
  "schema_version": 4,
  "datasets": 22,
  "observations": 20456,
  "occurrences": 300,
  "territories": 287,
  "assets": 22,
  "quality_reports": 10,
  "rtree": true
}
```

Tamaño del archivo: 9,59 MB. Catálogo JSON: 112 KB. Catálogo ráster: 20 KB.
Linaje: 8 KB. Monitoreo: 3,6 KB.

## 6. Deduplicación e incrementalidad

- `store_object()` guarda un blob por sha256 en `raw/_objects/aa/bb/<hash>`.
  Importar dos veces el mismo contenido no duplica el archivo.
- `promote()` copia de `staging/` a `validated/`; si el destino tiene el mismo
  hash, no duplica; si tiene otro, falla y exige versión nueva.
- Las consultas usan `LIMIT/OFFSET` y filtros; no se materializa la tabla entera.
- Los rásteres se procesan por bloques/ventanas; el almacenamiento derivado es
  por región, no una copia nacional completa.
- La base se reconstruye con `scripts/08_build_phase4_integration.py --rebuild`
  desde los artefactos normalizados.

## 7. Migración futura

Si el volumen o la concurrencia lo exigen:

1. crear el esquema equivalente en PostgreSQL/PostGIS;
2. cargar `observations`, `occurrences`, `territories` y `assets` (los tipos son
   estándar);
3. convertir `geometry_geojson` a `geometry(..., 4326)`;
4. mantener los rásteres en COG y las capas en GeoPackage.

No se implementó porque añadiría un servicio sin demanda actual. La decisión está
documentada, no oculta.

## 8. Límites

- SQLite no soporta escritura concurrente intensiva; la API es de lectura.
- La base contiene solo la última ejecución de informes de calidad; el historial
  completo queda en `metadata/quality_reports/` (incluidos informes antiguos).
- `data/raw/` no se versiona; en un clon nuevo hay que volver a descargar o
  copiar los crudos. Los manifiestos permiten verificar que lo copiado es lo
  correcto.
- El límite de 25 MB por archivo es una política del proyecto, no una restricción
  técnica de Git; se revisa si cambia la naturaleza de los datos.
