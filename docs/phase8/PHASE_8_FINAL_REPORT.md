# AGROSV Fase 8 — Reporte Final

**Fecha:** 2026-11-22 · **Versión:** 8.0.0 · **Paquete:** `backend/agrosv/economics/` · **Router API:** `/api/economics`

---

## 1. Resumen ejecutivo

Se implementaron los **7 subsistemas interoperables (42 motores)** de inteligencia económica, producción, costos, mercados, rentabilidad, cadena de valor, economía de hogares e integración de Fase 8 en `backend/agrosv/economics/`, junto con la integración real de datos de El Salvador (`wfp_food_prices_slv.csv`, `wfp_markets_slv.csv`, `osm_markets_slv.json`, `cap_2025_public_aggregates.json` y el corpus agrícola real de `nvidia/Nemotron-Personas-El-Salvador`).

## 2. Inventario por estado de implementación (§19)

### Motores completamente implementados (operativos de forma determinista y sin datos inventados)

- **Subsistema B (7/7):** `AgriculturalCostEngine`, `InputCostEngine`, `LaborCostEngine`, `IrrigationCostEngine`, `MachineryAndEquipmentCostEngine`, `PostHarvestCostEngine`, `ProductionBudgetEngine`.
- **Subsistema D (7/7):** `AgriculturalProfitabilityEngine`, `RevenueAnalysisEngine`, `BreakEvenAnalysisEngine`, `GrossMarginEngine`, `NetMarginEngine`, `AgriculturalInvestmentAnalysisEngine`, `AgriculturalEconomicRiskEngine`.
- **Subsistema F (5/5, reutilizando Fase 6/Nemotron):** `AgriculturalHouseholdEconomyEngine`, `AgriculturalResourceAllocationEngine`, `AgriculturalLivelihoodEngine`, `AgriculturalTechnologyEconomicsEngine`, `AgriculturalEconomicBehaviorEngine`.
- **Subsistema G (5/5):** `AgriculturalEconomicIntegrationEngine`, `AgriculturalEconomicScenarioEngine` (15 escenarios), `AgriculturalDecisionSupportEngine`, `AgriculturalEconomicAnalysisEngine`, `AgriculturalEconomicReportingEngine`.
- **Subsistema A y C con datos integrados:** `ProductionSystemEngine`, `CropYieldAnalysisEngine`, `AgriculturalProductivityEngine`, `AgriculturalMarketEngine`, `AgriculturalPriceEngine`, `PriceHistoryEngine`, `MarketComparisonEngine`, `MarketOpportunityEngine`, `AgriculturalLogisticsEngine`, `MarketAccessEngine`, `StorageAndPostHarvestEngine`, `AgriculturalDistributionEngine`.

### Motores parcialmente implementados (lógica completa; cobertura de datos externos parcial)

- `AgriculturalProductionEngine`: integración multi-escala funcional; a escala municipal/parcelaria requiere datos aportados por el llamador.
- `HarvestEstimationEngine`: conecta calendario, fenología y balance hídrico FAO-56; sin modelo varietal calibrado de biomasa.
- `ProductionStatisticsEngine`: integra agregados preliminares públicos CAP 2025 (`maize`, `beans`, `rice`, ganado) y `wb_agri_land_share_slv.json`; sin series tabulares del MAG ni FAOSTAT.
- `MarketSupplyDemandEngine`: calcula disponibilidad aparente cuando el llamador aporta importaciones/exportaciones; comercio exterior del BCR no está ingerido automáticamente.
- `AgriculturalSupplyChainEngine`: estructura completa de etapas; vínculos comerciales reales no están tabulados nacionalmente y se declaran `hypothetical`.
- `AgriculturalValueChainEngine`: calcula brecha mayorista-minorista con datos reales WFP; carece de series sistemáticas de precio en finca (*farm-gate*).

### Motores no implementados

- **Ninguno** (los 42 motores requeridos están implementados, registrados en `agrosv.economics.list_engines()`, documentados y cubiertos por pruebas).

## 3. Conjuntos de datos reales integrados vs evaluados

### Integrados localmente (`data/standardized/economics/` y `data/samples/phase3/nemotron_rows/`)

1. **`wfp_food_prices_slv.csv`** (WFP/HDX, `CC BY-IGO`): **7,864** observaciones reales (`2005-01-15` a `2026-10-15`), `Wholesale` y `Retail`, 14 mercados departamentales + promedio nacional, 6 productos (`Beans (red)`, `Beans (silk red)`, `Maize (white)`, `Rice`, `Sorghum`, `Wheat flour`).
2. **`wfp_markets_slv.csv`** (WFP/HDX, `CC BY-IGO`): **71** mercados georreferenciados en El Salvador.
3. **`osm_markets_slv.json`** (OSM `ODbL 1.0`, extraído de `infrastructure.gpkg`): **39** puntos `mercado` + acceso a red vial nacional OSM.
4. **`cap_2025_public_aggregates.json`** (BCR V Censo Agropecuario 2025, entregas públicas preliminares): agregados nacionales y participaciones departamentales seleccionadas.
5. **`wb_agri_land_share_slv.json`** (World Bank, `CC BY 4.0`): superficie agrícola nacional (`1961–2024`).
6. **`nemotron_agricultural_corpus.json`** (`nvidia/Nemotron-Personas-El-Salvador`, `CC BY 4.0`): **363** filas reales con ocupación agrícola cubriendo los **14 departamentos**.

### Evaluados y NO integrados

- **MAG (costos, guía de insumos, anuarios):** PDFs maquetados sin tabla abierta automatizable (`2022-23` retornó 404).
- **CENTA (boletines técnicos):** HTTP 403 a clientes automatizados.
- **FAOSTAT:** API HTTP 521 / bulk HTTP 403.
- **World Bank WDI (consulta en vivo adicional):** timeout (>15–25 s) el 2026-11-22.
- **BCR Comercio Exterior / FAO GIEWS / AMIS / CEPAL / IICA / IFAD / USDA / UN Comtrade:** catalogados en `SOURCE_REGISTRY` (`ACCESS_PENDING` / `DISCOVERED`), sin descarga tabular integrada.

## 4. Cobertura y metodologías

- **Cobertura geográfica y temporal:** precios reales 2005–2026 en 14 cabeceras departamentales; mercados OSM y red vial en todo El Salvador; estadísticas nacionales CAP 2025 (2024–2025).
- **Cobertura de costos de insumos:** motor completo con 11 categorías y control de vigencia; sin serie nacional de precios actuales de agroservicios (deben aportarse con fecha y fuente).
- **Metodologías económicas:** conversiones explícitas (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`), depreciación lineal, margen bruto vs margen neto escalonado (caja/contable/económico), punto de equilibrio, payback/VAN/TIR, exposición multiplicativa conectada a Fase 7 y matriz de compensaciones.
- **Componentes de hogar reutilizados:** `NemotronDatasetClient`, `AgriculturalPopulationEngine.generate_from_nemotron`, `AgriculturalHouseholdEngine`, `TechnologyAdoptionEngine` y `FarmerBehaviorEngine` (Fase 6), manteniendo `synthetic: true` separado de estadísticas reales.
- **Escenarios económicos probados:** los 15 escenarios de §10.2 ejecutados deterministamente contra línea base (`is_prediction: false`).

## 5. Validación, rendimiento y limitaciones

- **Validación empírica lograda:** integridad y normalización de series reales WFP, mercados WFP/OSM, agregados CAP 2025 y perfiles Nemotron.
- **Validación empírica pendiente:** contraste contra encuestas de costos de finca, precios recibidos en finca (*farm-gate*), mermas poscosecha medidas en campo y microdatos del CAP 2025 (restringidos por ley).
- **Rendimiento medido (`benchmark_phase8.json`):** estadísticas `1.02 ms`, costos `0.14 ms`, consulta WFP `10.93 ms`, historia de precios `26.17 ms`, rentabilidad+equilibrio `0.09 ms`, logística OSM `33.88 ms`, lote de 15 escenarios `3.40 ms`, integración completa Fases 5–8 `335.69 ms`, memoria pico `24.06 MB`, almacenamiento económico `1.009 MB`.
- **Limitaciones principales:** ausencia de series tabulares de precios de insumos, salarios municipales y precios en finca; cobertura WFP limitada a 6 productos básicos; sin motor de ruteo vial con tiempos reales de viaje.

## 6. Prioridades recomendadas para Fase 9

1. **Extracción auditada de tablas de costos e insumos del MAG** (con número de página y revisión humana) hacia CSV versionados.
2. **Módulo de ingesta de comercio exterior BCR (partidas SAC)** para completar balances de oferta y demanda.
3. **Encuesta o piloto de precios en finca (*farm-gate*) y mermas poscosecha** en 2–3 cadenas prioritarias (maíz, frijol, café, hortalizas).
4. **Ruteo real sobre la red vial OSM (`roads`)** con velocidades por clase de vía para tiempos de viaje verificables.
5. **Interfaz web interactiva** sobre `/api/economics/*` y `/api/social/saltbor/*` para simulación y análisis de escenarios.
