# MarketAccessEngine

**Módulo:** `backend/agrosv/economics/supply_chain.py`
**Endpoint:** `POST /api/economics/market-access`
**Versión:** 8.0.0

## Propósito

Evalúa accesibilidad práctica considerando distancia vial OSM, flete sobre valor bruto, estacionalidad vial, volumen mínimo y calidad.

## Implementación verificada

Separa `geographic_proximity_index` de `practical_economic_access`.

## Limitaciones y reglas de gobernanza

- Proximidad geográfica no garantiza viabilidad comercial.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
