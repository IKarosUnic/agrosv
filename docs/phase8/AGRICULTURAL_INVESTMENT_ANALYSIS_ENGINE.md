# AgriculturalInvestmentAnalysisEngine

**Módulo:** `backend/agrosv/economics/profitability.py`
**Endpoint:** `POST /api/economics/investment`
**Versión:** 8.0.0

## Propósito

Evalúa inversiones agrícolas mediante periodo de recuperación (`payback_years`), VAN (`npv`) y TIR (`irr` por bisección).

## Implementación verificada

Exige `discount_rate_justification` cuando se solicita VAN.

## Limitaciones y reglas de gobernanza

- No inventa condiciones de financiamiento bancario ni garantiza retornos (`returns_guaranteed: false`).
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
