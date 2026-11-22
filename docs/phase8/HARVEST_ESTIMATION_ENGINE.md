# HarvestEstimationEngine

**Módulo:** `backend/agrosv/economics/production.py`
**Endpoint:** `POST /api/economics/production/harvest`
**Versión:** 8.0.0

## Propósito

Ventanas esperadas de cosecha y producción condicionada reutilizando `AgriculturalCalendarEngine`, `CropPhenologyEngine` y `CropWaterNutrientEngine`.

## Implementación verificada

Ajusta opcionalmente `reference_yield_t_ha` mediante la razón `ETa/ETm` y registra contexto NDVI satelital sin afirmar medición directa de cosecha.

## Limitaciones y reglas de gobernanza

- Las ventanas esperadas no equivalen a fechas reales observadas ni a pronóstico varietal calibrado.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
