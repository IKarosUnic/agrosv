# NetMarginEngine

**Módulo:** `backend/agrosv/economics/profitability.py`
**Endpoint:** `POST /api/economics/net-margin`
**Versión:** 8.0.0

## Propósito

Separa `cash_operating_result`, `accounting_excluding_financing`, `accounting_net_result` y `economic_result_with_family_labor`.

## Implementación verificada

Emite advertencia explícita cuando `cost_model_complete=False`.

## Limitaciones y reglas de gobernanza

- Evita presentar modelos de costos incompletos como utilidad neta integral.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
