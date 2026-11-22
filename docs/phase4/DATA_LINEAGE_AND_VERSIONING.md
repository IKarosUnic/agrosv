# Linaje y versionado

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/lineage.py` · Grafo: `data/manifests/lineage.json` · Pruebas: `tests/test_lineage_storage.py`

## 1. Objetivo

Responder «¿de dónde salió este mapa?» sin depender de la memoria de quien lo
produjo. Cada producto derivado tiene:

- dataset de origen y versión;
- archivos de entrada y salida con sha256;
- pasos ordenados (herramienta, versión, parámetros);
- fecha de ejecución, `run_id` reproducible;
- estado de validación;
- manifiesto verificable.

Sin registro, un derivado **no es publicable**: `assert_traceable()` lanza
`UntraceableArtifact`.

## 2. Manifiesto de ejecución

`record_derivation()` reutiliza `agrosv.science.reproducibility.build_manifest`
(fase 2). El `run_id` es un hash de 16 hex de:

```
nombre + parámetros + seed + [(ruta, sha256) de cada entrada]
```

Misma receta e insumos → mismo `run_id`. Cambiar un parámetro, una entrada o el
seed produce otro. El manifiesto se escribe en
`data/manifests/derivations/<run_id>.json`.

La prueba `test_manifiesto_de_ejecucion_es_reproducible` registra dos veces la
misma derivación y exige el mismo `run_id`.

## 3. Grafo

- **Nodo** = sha256 de un artefacto.
- **Arista** = derivación registrada (`outputs ← inputs`).
- `LineageGraph.add()` es idempotente por `run_id`.
- Se detectan ciclos (`_assert_acyclic`), salvo una copia idéntica
  entrada=salida, que no es un ciclo sino una derivación sin cambio de contenido.
- `explain(artifact)` devuelve la cadena, los pasos y las entradas raíz.
- `datasets_for(artifact)` devuelve los datasets implicados.
- `verify()` recalcula hashes y `run_id` de todos los manifiestos.

Estado real: **5 derivaciones, 5 salidas, 4 entradas raíz, 0 sin validar**.
`verify()` → `{"checked": 5, "verified": 5, "ok": true}`.

Derivaciones registradas:

| Dataset | Derivación | Entrada → salida |
|---|---|---|
| chirps3 | `chirps3_recorte_sv` | GeoTIFF global → recorte SV sin remuestreo |
| nasa_power_point | `nasa_power_point_normalizacion` | JSON POWER → CSV normalizado |
| open_meteo_point | `open_meteo_point_normalizacion` | JSON Open-Meteo → CSV |
| gbif_sv | `gbif_sv_normalizacion` | JSON GBIF → CSV de ocurrencias |
| agrosv_data_store | `carga_base_consulta` | 3 CSV → SQLite |

## 4. Bases de datos: hash lógico

El sha256 de un archivo SQLite cambia con WAL, checkpoints y reorganización de
páginas aunque el contenido sea idéntico. Hashear bytes del archivo haría que la
verificación fallara tras una simple consulta.

Solución: para `.sqlite`, `.sqlite3` y `.db`, `logical_database_digest()` hashea
el esquema y las filas ordenadas de cada tabla, y el registro declara
`"digest": "sqlite-logical"`. El manifiesto de ejecución excluye la base del
hash físico y la declara en `params.database_outputs`. Los CSV, GeoJSON, TIFF y
demás archivos siguen verificándose byte a byte.

Esto es una **excepción declarada**, no una relajación silenciosa: el tipo de
hash viaja en el registro y en el manifiesto. La prueba de alteración modifica un
CSV y exige que `verify()` falle.

## 5. Verificación e integridad

`verify()` comprueba:

- que cada entrada y salida exista;
- que su hash coincida (físico o lógico según `digest`);
- que `run_id` corresponda al contenido del manifiesto;
- que no haya manifiestos ausentes.

Un archivo alterado produce `"hash distinto en <ruta>"`. Un manifiesto alterado
produce un `run_id` que no coincide. No se corrige automáticamente: se reporta.

## 6. Versionado

- El nombre del artefacto incluye fuente, variable, resolución, fecha y versión
  (`chirps3_precipitation_0p05deg_2026-01-15_v3.0.tif`).
- `promote()` no sobrescribe: si el destino existe con otro contenido, lanza
  `FileExistsError` y exige incrementar la versión.
- Si el contenido es idéntico, devuelve `duplicate: true` sin duplicar el
  archivo.
- Los datasets tienen `version` en el catálogo; los derivados declaran
  `version: "AGROSV-4.0"` en el paso.
- El grafo conserva derivaciones anteriores: no se reescribe la historia.

## 7. Reconstrucción

Para reconstruir un producto:

1. `LineageGraph.explain(path)` → derivaciones y entradas raíz;
2. abrir cada manifiesto (`manifest_path`) → parámetros, seed, versiones;
3. verificar hashes de las entradas;
4. volver a ejecutar los pasos con la misma versión de herramienta.

`reconstructable` es verdadero solo si todas las derivaciones de la cadena tienen
manifiesto. Si falta uno, `assert_traceable()` falla.

## 8. Límites

- No se versiona el entorno completo (solo versiones de software declaradas y
  huella de entorno del manifiesto de Fase 2).
- Las entradas SQLite se hashean físicamente; hoy no hay bases como entrada de
  una derivación. Si se añaden, habrá que extender el mismo criterio lógico.
- La reconstrucción automática de un paso no está implementada: el manifiesto
  permite rehacerlo, no lo rehace solo.
- Los derivados de la base (`agrosv_data_store`) dependen de tres CSV; si uno se
  regenera con otro contenido, el `run_id` cambia y la cadena anterior queda como
  histórica, no como equivalente.
