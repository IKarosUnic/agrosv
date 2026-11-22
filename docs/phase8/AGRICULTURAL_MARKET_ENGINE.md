# AgriculturalMarketEngine

**Módulo:** `backend/agrosv/economics/markets.py`
**Endpoint:** `GET /api/economics/markets`
**Versión:** 8.0.0

## Propósito

Catálogo integrado de mercados reales de El Salvador: 71 plazas georreferenciadas WFP y 39 puntos `mercado` de OpenStreetMap.

## Implementación verificada

Filtra por departamento, fuente (`wfp_markets_slv`, `osm_markets_slv`) y nombre.

## Limitaciones y reglas de gobernanza

- No inventa compradores activos, centros de acopio privados ni volúmenes no documentados.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
