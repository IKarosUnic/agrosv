# AgriculturalLogisticsEngine

**Módulo:** `backend/agrosv/economics/supply_chain.py`
**Endpoint:** `POST /api/economics/logistics`
**Versión:** 8.0.0

## Propósito

Mide distancia exacta en `EPSG:32616` a la vía OSM más cercana (`infrastructure.gpkg`) y distancia a plazas reales WFP/OSM.

## Implementación verificada

Valida coordenadas dentro de El Salvador mediante `TerritorialEngine.validate_coordinate`.

## Limitaciones y reglas de gobernanza

- No afirma tiempos reales de viaje sin motor de ruteo ni estado vial actual.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
