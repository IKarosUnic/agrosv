# AgriculturalSupplyChainEngine

**Módulo:** `backend/agrosv/economics/supply_chain.py`
**Endpoint:** `POST /api/economics/supply-chain`
**Versión:** 8.0.0

## Propósito

Mapea relaciones entre proveedores, productores, acopio, cooperativas, procesadores, mayoristas, minoristas, exportadores y consumidores.

## Implementación verificada

Exige evidencia documental para vínculos marcados `evidenced`; los demás quedan explícitamente como `hypothetical`.

## Limitaciones y reglas de gobernanza

- No afirma relaciones comerciales reales sin respaldo.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
