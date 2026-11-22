# Pipeline automatizado y monitoreo

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/pipeline.py` · Salida: `data/manifests/monitoring.json` · Pruebas: `tests/test_data_pipeline.py`

## 1. Alcance

Sin servicios de pago, sin daemon y sin scraping no autorizado. El pipeline:

- detecta datasets desactualizados;
- detecta cambios de cobertura y versiones nuevas;
- encola revalidaciones;
- registra errores;
- genera un informe reproducible;
- reutiliza `agrosv.science.orchestrator` (dependencias, reintentos, estado en
  disco) en lugar de crear un segundo motor.

## 2. Ejecución local

```bash
# monitoreo e informe
.venv/Scripts/python.exe -m agrosv.data.pipeline --monitor

# ruta explícita
.venv/Scripts/python.exe -m agrosv.data.pipeline --monitor \
    --out data/manifests/monitoring.json

# construcción completa (catálogo, calidad, base, ráster, linaje, monitoreo)
.venv/Scripts/python.exe scripts/08_build_phase4_integration.py --rebuild
```

`python -m agrosv.data.pipeline` requiere `backend/` en `PYTHONPATH`; el script
de construcción lo inserta. No hay tarea programada incluida: la ejecución es
manual o la puede lanzar el usuario con el programador del sistema. Esto evita
depender de un servicio externo.

## 3. Vigencia

`FRESHNESS_DAYS` es una **política de operación**, no una propiedad del dato:

| Dominio | Días |
|---|---|
| ECONOMY | 45 |
| CLIMATE | 60 |
| PHYTOSANITARY | 30 |
| HYDROLOGY | 365 |
| BIODIVERSITY | 365 |
| AGRICULTURE | 400 |
| TERRITORY | 730 |
| SOILS | 1825 |

`freshness(record)` usa `download_date` y, si falta, `publication_date`. Sin
ninguna fecha → `UNKNOWN`. Solo se evalúa en estados activos (`DOWNLOADED`,
`PARSED`, `VALIDATED`, `INTEGRATED`): un dataset `RESTRICTED` o `UNAVAILABLE` no
«envejece» porque no se usa.

Resultado actual: **11 frescos, 0 STALE, 0 UNKNOWN, 11 no evaluados**. Ninguno
requiere revalidación por antigüedad.

## 4. Cambio de cobertura

`detect_coverage_change(anterior, actual, threshold_pct=5)` compara métricas
numéricas (celdas, área, recuento) y devuelve los cambios con delta y porcentaje.
Un cambio no es un error: se registra para revisar si la fuente cambió de versión
o de método. No se dispara una revalidación automática por un 6 % de diferencia
sin revisión humana.

## 5. Versión nueva

`detect_new_version(manifiesto_previo, sonda)` compara sha256, ETag y tamaño:

- sin manifiesto previo → primera versión, `changed: true`;
- hash distinto, ETag distinto o tamaño distinto → `changed: true` y
  `requires_revalidation: true`, con la lista de motivos;
- todo igual → `changed: false`.

La descarga en sí usa el ledger de `ingest.py`: si el contenido es idéntico, no
se vuelve a copiar.

## 6. Cola de revalidación

`revalidation_queue(catalog)` reúne:

- datasets activos con vigencia `STALE` o `UNKNOWN`;
- artefactos declarados que ya no existen en disco;
- datasets sin historial de evidencia;
- cambios de versión detectados por la sonda.

Cada entrada incluye `dataset_id`, `state` y `reasons`. La cola actual está vacía
en el informe (`stale_or_unknown: []`, `missing_artifacts: {}`).

## 7. Errores

`ingest_log.jsonl` guarda fallos de importación/descarga. `monitoring_report()`
incluye los últimos errores (`limit` configurable) y no los convierte en cero.
`write_monitoring()` conserva la versión anterior como
`monitoring.previous.json` antes de sobrescribir: el histórico no se pierde.

La prueba `test_monitoreo_escribe_y_conserva_anterior` verifica ese
comportamiento.

## 8. Informe de monitoreo

Estructura real (resumida):

```json
{
  "ok": true,
  "generated_at": "2026-11-22T04:19:54Z",
  "catalog": {"count": 22, "by_state": {...}, "integrated": [7]},
  "audit": {"checked": 22, "ok": true, "transitions": 71},
  "store": {"observations": 20456, "occurrences": 300, "territories": 287,
            "assets": 22, "quality_reports": 10, "rtree": true},
  "freshness": {"fresh": 11, "stale_or_unknown": [],
                "not_evaluated": [11 ids], "policy_days": {...}},
  "missing_artifacts": {},
  "quality": {"reports": 10, "failing": [], "latest_by_dataset": {...}},
  "revalidation_queue": [],
  "errors": [],
  "observations_by_dataset": {"nasa_power_point": 7671,
                              "open_meteo_point": 12785},
  "note": "solo se evalúa vigencia en estados activos: un dataset RESTRICTED o UNAVAILABLE no envejece"
}
```

`ok` es verdadero solo si se cumplen las reglas; no es un adorno.

## 9. Plan orquestado

`monitoring_plan()` construye tareas (`monitoring_report`, escritura del
informe) con `Task`/`run_plan` del orquestador de Fase 2 y guarda estado en
`manifests/monitoring_state.json`. Reintentos y dependencias son los del motor
existente.

## 10. Límites

- No hay programador (cron/Task Scheduler) incluido: el usuario decide cuándo
  ejecutar. Un daemon permanente no es necesario para esta fase.
- Las sondas de versión son manuales o se ejecutan con un cliente autorizado; no
  se hace scraping de portales.
- Los umbrales de vigencia son decisiones revisables; un DEM antiguo puede seguir
  siendo válido y un precio de 40 días ya no describe el mercado.
- La detección de cambio de cobertura compara métricas declaradas, no imágenes
  ni contenidos completos.
- El monitoreo no corrige datos: solo informa y encola.
