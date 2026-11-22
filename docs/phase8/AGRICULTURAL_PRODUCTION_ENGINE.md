# AgriculturalProductionEngine

**Módulo:** `backend/agrosv/economics/production.py`
**Endpoint:** `POST /api/economics/production`
**Versión:** 8.0.0

## Propósito

Integración productiva multi-escala (national, departmental, municipal, agricultural_zone, parcel).

## Implementación verificada

Integra `ProductionSystemEngine`, `CropSuitabilityEngine` (Fase 6), `HarvestEstimationEngine` y `ProductionStatisticsEngine`.

## Limitaciones y reglas de gobernanza

- No extrapola estadísticas nacionales a parcelas ni inventa rendimientos cuando faltan mediciones.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
