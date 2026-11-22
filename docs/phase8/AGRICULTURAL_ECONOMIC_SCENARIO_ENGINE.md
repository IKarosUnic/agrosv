# AgriculturalEconomicScenarioEngine

**Módulo:** `backend/agrosv/economics/integration.py`
**Endpoint:** `POST /api/economics/scenarios/run`
**Versión:** 8.0.0

## Propósito

Ejecuta los 15 escenarios económicos configurables (alza de fertilizantes/semillas/combustible, caídas de rendimiento/precio, sequía, lluvia excesiva, plagas, riego, diversificación, agricultura protegida, almacenamiento, canal alternativo, disrupción vial).

## Implementación verificada

Preserva línea base, entradas, parámetros modificados, versiones, fecha, delta y limitaciones.

## Limitaciones y reglas de gobernanza

- Escenarios son simulaciones condicionales (`is_prediction: false`).
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
