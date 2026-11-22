# AgriculturalTechnologyEconomicsEngine

**Módulo:** `backend/agrosv/economics/household_econ.py`
**Endpoint:** `POST /api/economics/household/technology`
**Versión:** 8.0.0

## Propósito

Reutiliza `TechnologyAdoptionEngine` (Fase 6) y evalúa inversión, mantenimiento, brecha de capital y payback.

## Implementación verificada

Respeta barreras duras de agua, superficie y conocimiento de Fase 6.

## Limitaciones y reglas de gobernanza

- Declara `automatic_profit_improvement_assumed: false`.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
