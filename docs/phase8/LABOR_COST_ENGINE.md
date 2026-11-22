# LaborCostEngine

**Módulo:** `backend/agrosv/economics/costs.py`
**Endpoint:** `POST /api/economics/costs/labor`
**Versión:** 8.0.0

## Propósito

Análisis de 10 actividades laborales en modalidades `daily`, `hourly`, `seasonal`, `family_unpaid` y `contract`.

## Implementación verificada

Separa costo remunerado en efectivo del costo imputado de mano de obra familiar no pagada y exige `wage_reference`.

## Limitaciones y reglas de gobernanza

- No asume jornales municipales no verificados.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
