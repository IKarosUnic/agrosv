# AgriculturalProductivityEngine

**Módulo:** `backend/agrosv/economics/production.py`
**Endpoint:** `POST /api/economics/production/productivity`
**Versión:** 8.0.0

## Propósito

Indicadores físicos (`t/ha`, `qq/mz`, `kg/jornal`, `kg/m³`, `kg/USD`, `kg/MJ`) y razón beneficio/costo.

## Implementación verificada

Separa explícitamente productividad física de rentabilidad financiera.

## Limitaciones y reglas de gobernanza

- Indicadores sin datos de entrada quedan como `null`.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
