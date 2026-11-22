# BreakEvenAnalysisEngine

**Módulo:** `backend/agrosv/economics/profitability.py`
**Endpoint:** `POST /api/economics/break-even`
**Versión:** 8.0.0

## Propósito

Calcula precio de equilibrio (`USD/t` y `USD/qq`), rendimiento de equilibrio (`t/ha` y `qq/mz`), volumen mínimo, área de equilibrio y sensibilidad de costos (`-10%` a `+25%`).

## Implementación verificada

Expone explícitamente todas las fórmulas utilizadas.

## Limitaciones y reglas de gobernanza

- Asume costos fijos constantes en el rango evaluado.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
