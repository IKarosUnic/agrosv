# AgriculturalEconomicIntegrationEngine

**Módulo:** `backend/agrosv/economics/integration.py`
**Endpoint:** `POST /api/economics/integrate`
**Versión:** 8.0.0

## Propósito

Integra en una consulta territorial-productiva-económica las Fases 5 (territorio), 6 (aptitud, calendario, Nemotron), 7 (riesgo) y 8 (costos, precios WFP, logística, rentabilidad, punto de equilibrio).

## Implementación verificada

Respeta clases de evidencia por bloque y evita rellenar costos o rendimientos ausentes.

## Limitaciones y reglas de gobernanza

- Precios mayoristas WFP se etiquetan explícitamente como referencia de plaza, nunca como precio en finca.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
