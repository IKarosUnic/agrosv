# AgriculturalHouseholdEconomyEngine

**Módulo:** `backend/agrosv/economics/household_econ.py`
**Endpoint:** `POST /api/economics/household`
**Versión:** 8.0.0

## Propósito

Extiende `HOUSEHOLD_STATE` de Fase 6 (y perfiles reales agrícolas de Nemotron) con flujo neto agrícola, ingreso no agrícola, consumo y brecha de liquidez.

## Implementación verificada

Reutiliza `AgriculturalPopulationEngine.generate_from_nemotron` y `AgriculturalHouseholdEngine.compose` sin duplicar capas.

## Limitaciones y reglas de gobernanza

- Todos los registros llevan `synthetic: true` en capa `SIMULATION_HISTORY`.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
