# AgriculturalEconomicAnalysisEngine

**Módulo:** `backend/agrosv/economics/integration.py`
**Endpoint:** `GET /api/economics/analysis`
**Versión:** 8.0.0

## Propósito

Resumen comparativo nacional de cultivos básicos combinando CAP 2025, series WFP mayorista/minorista y brecha de cadena de valor.

## Implementación verificada

Clasifica explícitamente qué salidas son estadísticas descriptivas vs métricas derivadas.

## Limitaciones y reglas de gobernanza

- Declara `causal_inference_claimed: false`.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
