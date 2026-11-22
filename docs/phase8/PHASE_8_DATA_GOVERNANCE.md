# Gobernanza de datos económicos (Fase 8)

**Módulo:** `backend/agrosv/economics/governance.py`

## 1. Estados de ciclo de vida

`DISCOVERED`, `ACCESS_PENDING`, `DOWNLOADED`, `PARSED`, `VALIDATED`, `INTEGRATED`, `RESTRICTED`, `UNAVAILABLE`, `REJECTED`.

## 2. Clases de evidencia económica

- `observed_transaction`: transacción documentada real.
- `producer_reported`: dato reportado por productor.
- `official_statistic`: estadística oficial publicada (BCR CAP 2025, WFP/HDX, Banco Mundial).
- `institutional_reference`: presupuesto o parámetro técnico de referencia.
- `commercial_quotation`: cotización comercial fechada de insumo o equipo.
- `model_estimate`: cálculo determinista de motores de Fase 8.
- `synthetic_scenario`: simulación condicional / hogares sintéticos Nemotron.
- `hypothetical_assumption`: supuesto explícito sin dato de campo.

## 3. Reglas obligatorias aplicadas en código

1. `make_economic_record()` exige `product_or_activity`, `geography`, `observation_date`, `reference_period`, `currency`, `unit`, `source`, `methodology`, `verification_status`, `evidence_class` y `license`.
2. `InputCostEngine` marca precios antiguos (`> 90 días` o `historical`) y rechaza plaguicidas sin cultivo, organismo objetivo y estatus de registro.
3. `AgriculturalCostEngine` y `AgriculturalPriceEngine` rechazan mezclar monedas incompatibles o comparar precios de unidades distintas sin normalización.
4. `ProductionStatisticsEngine` rechaza desagregar totales nacionales a nivel municipal o parcelario.
5. Los archivos históricos (`wfp_food_prices_slv.csv`) se mantienen intactos y nunca se sobrescriben.
