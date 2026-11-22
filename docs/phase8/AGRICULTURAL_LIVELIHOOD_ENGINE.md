# AgriculturalLivelihoodEngine

**Módulo:** `backend/agrosv/economics/household_econ.py`
**Endpoint:** `POST /api/economics/household/livelihoods`
**Versión:** 8.0.0

## Propósito

Analiza estrategias diversificadas (cultivos, pecuario, empleo agrícola/no agrícola, microempresa, remesas) separando ingreso agrícola del total.

## Implementación verificada

Conserva proporciones sintéticas de Fase 6 cuando no se aportan montos monetarios.

## Limitaciones y reglas de gobernanza

- Registro estrictamente sintético.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
