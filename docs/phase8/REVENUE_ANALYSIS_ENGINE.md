# RevenueAnalysisEngine

**Módulo:** `backend/agrosv/economics/profitability.py`
**Endpoint:** `POST /api/economics/revenue`
**Versión:** 8.0.0

## Propósito

Calcula ingresos brutos y netos bajo múltiples canales de venta, factores de calidad, mermas poscosecha y costos de transporte/comercialización.

## Implementación verificada

Exige que las participaciones de canales sumen 1.0.

## Limitaciones y reglas de gobernanza

- Nunca asume que el 100% de lo cosechado se vende al precio máximo.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
