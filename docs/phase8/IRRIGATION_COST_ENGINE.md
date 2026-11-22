# IrrigationCostEngine

**Módulo:** `backend/agrosv/economics/costs.py`
**Endpoint:** `POST /api/economics/costs/irrigation`
**Versión:** 8.0.0

## Propósito

Cálculo de demanda bruta por eficiencia de sistema (`manual`, `surface`, `sprinkler`, `drip`), bombeo, tarifa, mantenimiento y depreciación.

## Implementación verificada

Integra demanda neta desde `CropWaterNutrientEngine` (Fase 6) cuando se aportan suelo y siembra.

## Limitaciones y reglas de gobernanza

- Proximidad a cauces de Fase 5 no implica acceso legal ni económico al agua (`water_access_verified` explícito).
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
