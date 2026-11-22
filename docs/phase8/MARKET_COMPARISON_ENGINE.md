# MarketComparisonEngine

**Módulo:** `backend/agrosv/economics/markets.py`
**Endpoint:** `POST /api/economics/markets/compare`
**Versión:** 8.0.0

## Propósito

Compara plazas reales WFP o alternativas del usuario descontando distancia, transporte, transacción y almacenamiento.

## Implementación verificada

Distingue `gross_price_per_t` de `net_producer_price_per_t`.

## Limitaciones y reglas de gobernanza

- Distancia estimada `geodésica × 1.3` cuando no hay ruteo real; precio de plaza no garantiza compra en finca.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
