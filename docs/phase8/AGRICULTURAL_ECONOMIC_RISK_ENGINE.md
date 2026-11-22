# AgriculturalEconomicRiskEngine

**Módulo:** `backend/agrosv/economics/profitability.py`
**Endpoint:** `POST /api/economics/risk`
**Versión:** 8.0.0

## Propósito

Modela exposición financiera ante 11 factores (precios, rendimiento, sequía, inundación, plagas, transporte, almacenamiento, crédito) e integra `AgriculturalRiskEngine` de Fase 7.

## Implementación verificada

Calcula impacto multiplicativo sobre ingresos, costos y margen bajo choques declarados.

## Limitaciones y reglas de gobernanza

- Distingue exposición modelada de pérdida financiera real (`is_actual_financial_loss: false`).
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
