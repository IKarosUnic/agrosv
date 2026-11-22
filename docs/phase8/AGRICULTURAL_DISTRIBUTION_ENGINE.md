# AgriculturalDistributionEngine

**Módulo:** `backend/agrosv/economics/supply_chain.py`
**Endpoint:** `POST /api/economics/distribution`
**Versión:** 8.0.0

## Propósito

Evalúa rutas y asignación de volumen manteniendo `physical_routing` separado de `economic_assumptions`.

## Implementación verificada

Deriva rutas candidatas desde mercados reales o desde rutas aportadas.

## Limitaciones y reglas de gobernanza

- Sin grafo vial completo con restricciones de carga ni pendientes.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
