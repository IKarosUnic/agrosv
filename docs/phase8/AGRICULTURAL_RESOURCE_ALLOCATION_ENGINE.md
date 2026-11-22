# AgriculturalResourceAllocationEngine

**Módulo:** `backend/agrosv/economics/household_econ.py`
**Endpoint:** `POST /api/economics/household/allocation`
**Versión:** 8.0.0

## Propósito

Asigna tierra, mano de obra y presupuesto operativo del hogar sintético entre actividades bajo restricciones duras (riego, capital, trabajo).

## Implementación verificada

Soporta objetivos múltiples (`balanced_food_security_and_margin`, `food_security_first`, `profit_maximization`).

## Limitaciones y reglas de gobernanza

- Asignación heurística sintética (`profit_only_assumed: false`).
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
