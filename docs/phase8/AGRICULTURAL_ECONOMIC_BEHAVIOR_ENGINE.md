# AgriculturalEconomicBehaviorEngine

**Módulo:** `backend/agrosv/economics/household_econ.py`
**Endpoint:** `POST /api/economics/household/behavior`
**Versión:** 8.0.0

## Propósito

Reutiliza `FarmerBehaviorEngine` (MAUT + restricciones duras de Fase 6) en 9 dominios de decisión económica.

## Implementación verificada

Registra cada decisión sintética con trazabilidad.

## Limitaciones y reglas de gobernanza

- Declara `represents_observed_farmer_behavior: false`.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
