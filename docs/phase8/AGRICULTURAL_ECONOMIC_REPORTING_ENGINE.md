# AgriculturalEconomicReportingEngine

**Módulo:** `backend/agrosv/economics/integration.py`
**Endpoint:** `POST /api/economics/report`
**Versión:** 8.0.0

## Propósito

Emite informes económicos estructurados por cultivo, finca, municipio, zona, sistema, mercado o escenario con fuentes, metodología, fechas, unidades e incertidumbre.

## Implementación verificada

Asigna identificador estable `RPT-*` y metadatos completos de gobernanza.

## Limitaciones y reglas de gobernanza

- Sujeto a la cobertura real de fuentes declaradas.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
