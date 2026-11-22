# PriceHistoryEngine

**Módulo:** `backend/agrosv/economics/markets.py`
**Endpoint:** `GET /api/economics/prices/history`
**Versión:** 8.0.0

## Propósito

Estadística descriptiva de series históricas reales (media, desviación, CV, tendencia lineal, índice estacional mensual y choques `|z| >= 2`).

## Implementación verificada

Opera sobre las series WFP integradas o series aportadas por el usuario.

## Limitaciones y reglas de gobernanza

- No extrapola series cortas como pronóstico de largo plazo ni afirma causalidad.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
