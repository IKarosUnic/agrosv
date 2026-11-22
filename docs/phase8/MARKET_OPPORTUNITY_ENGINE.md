# MarketOpportunityEngine

**Módulo:** `backend/agrosv/economics/markets.py`
**Endpoint:** `POST /api/economics/markets/opportunities`
**Versión:** 8.0.0

## Propósito

Clasifica oportunidades potenciales combinando comparación neta de mercados e índice estacional histórico WFP del mes de cosecha.

## Implementación verificada

Etiqueta cada salida como `potential_opportunity_not_guaranteed` (`guaranteed_buyer: false`).

## Limitaciones y reglas de gobernanza

- No constituye contrato comercial ni comprador confirmado.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
