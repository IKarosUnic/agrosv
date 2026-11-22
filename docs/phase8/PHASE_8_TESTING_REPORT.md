# Reporte de pruebas de Fase 8

**Archivo de pruebas:** `tests/test_phase8_economics.py`
**Pruebas complementarias Nemotron + Saltbor:** `tests/test_phase6_nemotron_saltbor.py`
**Script de benchmark:** `scripts/16_phase8_benchmark.py` (`docs/phase8/benchmark_phase8.json`)

## 1. Cobertura de pruebas automatizadas

- **Subsistema A (Producción):** estadísticas CAP 2025 y rechazo de inferencia municipal, normalización y CV de rendimientos separados por clase de evidencia, sistemas productivos, productividad física/económica, estimación de cosecha y perfil productivo multi-escala.
- **Subsistema B (Costos):** agregación multi-unidad, presupuestos `reference`/`scenario`/`observed`, caducidad de precios de insumos y regla fitosanitaria de plaguicidas, mano de obra pagada vs familiar, riego, depreciación de maquinaria y costos poscosecha.
- **Subsistema C (Mercados y Precios):** catálogo real WFP + OSM, consulta y normalización de `wfp_food_prices_slv.csv`, análisis histórico y estacional, comparación neta de mercados, oportunidades potenciales y balance oferta-disponibilidad.
- **Subsistema D (Rentabilidad):** ingresos multi-canal, margen bruto, margen neto escalonado, punto de equilibrio, payback/VAN/TIR y exposición económica conectada a Fase 7.
- **Subsistema E (Cadena y Logística):** mapa de cadena (`hypothetical` vs `evidenced`), distancia vial OSM real en `EPSG:32616`, acceso práctico, almacenamiento, distribución y participación en cadena de valor con datos WFP.
- **Subsistema F (Economía de Hogares):** reutilización de `generate_from_nemotron` y `AgriculturalHouseholdEngine`, asignación multi-objetivo de recursos, medios de vida, economía de adopción tecnológica y comportamiento MAUT sintético.
- **Subsistema G (Integración y API):** integración completa Fases 5+6+7+8, ejecución de los **15 escenarios económicos**, matriz de compensaciones (`decision-support`), análisis comparativo nacional, reportes estructurados y endpoints `/api/economics/*` preservando compatibilidad con fases anteriores.

## 2. Ejecución sin conexión (*offline*)

Todas las pruebas de `tests/test_phase8_economics.py` y el benchmark `scripts/16_phase8_benchmark.py` se ejecutan 100% **sin acceso a internet** utilizando los archivos descargados localmente en `data/standardized/economics/` y `data/samples/phase3/nemotron_rows/`.

## 3. Mediciones de rendimiento (`docs/phase8/benchmark_phase8.json`)

| Operación | Media (ms) | p95 (ms) |
|---|---:|---:|
| `production_statistics` | 1.018 | 1.409 |
| `cost_aggregation` | 0.137 | 0.200 |
| `wfp_price_query` | 10.927 | 193.838 |
| `wfp_price_history` | 26.174 | 30.460 |
| `profitability_and_breakeven` | 0.088 | 0.095 |
| `osm_logistics` | 33.875 | 77.570 |
| `nemotron_household_econ` | 34.762 | 41.924 |
| `all_15_scenarios` (lote completo) | 3.403 | 4.414 |
| `integrated_phase5_6_7_8` | 335.685 | 489.875 |
| `api_get_prices` | 34.832 | 373.606 |
| `api_post_scenario` | 9.421 | 13.127 |

- **Memoria pico (`tracemalloc`):** `24.06 MB`.
- **Almacenamiento Fase 8 (`data/standardized/economics/`):** `1.009 MB` (`1,058,229` bytes).
- **Corpus agrícola Nemotron:** `3.065 MB` (`3,214,323` bytes).
