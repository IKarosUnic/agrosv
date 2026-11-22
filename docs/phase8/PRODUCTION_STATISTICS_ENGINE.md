# ProductionStatisticsEngine

**Módulo:** `backend/agrosv/economics/production.py`
**Endpoint:** `GET /api/economics/production/statistics`
**Versión:** 8.0.0

## Propósito

Estadísticas oficiales integradas de BCR CAP 2025 (agregados públicos preliminares) y Banco Mundial (`wb_agri_land_share_slv.json`).

## Implementación verificada

Entrega cobertura nacional y participaciones departamentales seleccionadas (`maize`, `beans`, `rice`) con trazabilidad completa.

## Limitaciones y reglas de gobernanza

- Rechaza inferir estadísticas municipales o parcelarias desde totales nacionales.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
