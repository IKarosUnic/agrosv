# AgriculturalProfitabilityEngine

**Módulo:** `backend/agrosv/economics/profitability.py`
**Endpoint:** `POST /api/economics/profitability`
**Versión:** 8.0.0

## Propósito

Calcula ingreso bruto, ingreso neto tras comercialización, margen bruto, margen operativo neto, beneficio económico tras mano de obra familiar y ROI.

## Implementación verificada

Integra `RevenueAnalysisEngine` para descontar mermas poscosecha y costos de venta.

## Limitaciones y reglas de gobernanza

- Distingue resultado operativo contable de estimación económica; no equivale a contabilidad auditada.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
