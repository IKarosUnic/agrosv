# GrossMarginEngine

**Módulo:** `backend/agrosv/economics/profitability.py`
**Endpoint:** `POST /api/economics/gross-margin`
**Versión:** 8.0.0

## Propósito

Calcula `gross_margin = gross_revenue - sum(variable_costs)` por ciclo y por hectárea.

## Implementación verificada

Lista explícitamente costos variables incluidos y costos excluidos (`fixed_costs`, `depreciation`, `family_unpaid_labor`, `financing`).

## Limitaciones y reglas de gobernanza

- Declara `is_net_profit: false`.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
