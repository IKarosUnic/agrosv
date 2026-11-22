# AgriculturalDecisionSupportEngine

**Módulo:** `backend/agrosv/economics/integration.py`
**Endpoint:** `POST /api/economics/decision-support`
**Versión:** 8.0.0

## Propósito

Genera matriz multi-criterio de compensaciones (`tradeoff_matrix`) comparando producción, costo, ingreso, margen, agua, exposición ambiental, trabajo, inversión, acceso a mercado y riesgo.

## Implementación verificada

Identifica destacados por criterio individual sin imponer una única recomendación sin respaldo.

## Limitaciones y reglas de gobernanza

- Declara `single_unsupported_recommendation_issued: false`.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
