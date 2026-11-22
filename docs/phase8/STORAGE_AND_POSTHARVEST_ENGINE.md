# StorageAndPostHarvestEngine

**Módulo:** `backend/agrosv/economics/supply_chain.py`
**Endpoint:** `POST /api/economics/storage`
**Versión:** 8.0.0

## Propósito

Evalúa capacidad de almacenamiento, déficit, vida útil de referencia, riesgo por humedad observada, costo y merma.

## Implementación verificada

Incluye parámetros bibliográficos de humedad segura y perecibilidad para granos, café y hortalizas/frutas.

## Limitaciones y reglas de gobernanza

- No aplica tasas genéricas de pérdida si el usuario no aporta `loss_fraction` con fuente.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
