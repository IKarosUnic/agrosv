# ProductionBudgetEngine

**Módulo:** `backend/agrosv/economics/costs.py`
**Endpoint:** `POST /api/economics/budgets`
**Versión:** 8.0.0

## Propósito

Generación de presupuestos `observed`, `reference` y `scenario` con ID estable, costos unitarios y estructura de rubros.

## Implementación verificada

Etiqueta cada presupuesto según su clase de evidencia (`observed_transaction`, `institutional_reference`, `synthetic_scenario`).

## Limitaciones y reglas de gobernanza

- Prohíbe mezclar presupuestos observados con escenarios hipotéticos sin etiquetado.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
