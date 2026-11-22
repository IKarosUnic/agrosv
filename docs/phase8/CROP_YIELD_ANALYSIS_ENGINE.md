# CropYieldAnalysisEngine

**Módulo:** `backend/agrosv/economics/production.py`
**Endpoint:** `POST /api/economics/production/yield`
**Versión:** 8.0.0

## Propósito

Normalización de rendimientos (`t/ha`, `qq/mz`) y estadística descriptiva (media, desviación, CV) separada por clase de evidencia.

## Implementación verificada

Distingue `official_observed`, `survey_based`, `experimental`, `model_estimated` y `synthetic_scenario`.

## Limitaciones y reglas de gobernanza

- Nunca combina rendimientos experimentales o sintéticos como estadística nacional.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
