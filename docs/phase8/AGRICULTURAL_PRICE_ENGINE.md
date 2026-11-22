# AgriculturalPriceEngine

**Módulo:** `backend/agrosv/economics/markets.py`
**Endpoint:** `GET /api/economics/prices`
**Versión:** 8.0.0

## Propósito

Consulta y normalización de 7,864 registros reales de `wfp_food_prices_slv.csv` (2005-01-15 a 2026-10-15, `Wholesale` y `Retail`).

## Implementación verificada

Normaliza `45 KG`, `46 KG`, `Libra` y `50 Pounds` a `USD/kg`, `USD/qq (46 kg)` y `USD/t`, separando `price_type`.

## Limitaciones y reglas de gobernanza

- Cubre 6 productos básicos WFP; cultivos ausentes devuelven `available: false` sin inventar precios.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
