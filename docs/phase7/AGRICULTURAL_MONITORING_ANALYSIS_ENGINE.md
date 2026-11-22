# AgriculturalMonitoringAnalysisEngine — análisis descriptivo

**Módulo:** `backend/agrosv/monitoring/integration.py`
**Endpoint:** `POST /api/monitoring/analysis`
**Versión:** 7.0.0

## Qué calcula

- **Descriptivo:** n, media, mediana, desviación, mínimo, máximo, P10/P90 y
  periodo.
- **Tendencia:** OLS con ≥ 5 observaciones (pendiente, R², periodo) mediante el
  motor de series temporales.
- **Alertas:** conteo, por categoría y por mes.
- **Verificación:** conteo por resultado (`confirmed`, `not_confirmed`,
  `inconclusive`).

## Separación explícita

`inference.causal_claim` es siempre `false`, con la nota de que la comparación y
la tendencia son descriptivas y no permiten afirmar que un factor ambiental
causó una anomalía.

## Limitaciones

1. n pequeño reduce la estabilidad de la tendencia.
2. La muestra no es un diseño experimental.
3. La frecuencia de alertas depende de umbrales configurados; no mide
   incidencia real.
4. No se calculan pruebas de significancia ni intervalos de confianza.
5. No se comparan áreas sin normalizar por superficie y periodo.

## Validación

Pruebas: seis observaciones crecientes producen tendencia positiva, el conteo
de alertas es correcto y `causal_claim` es `false`.
