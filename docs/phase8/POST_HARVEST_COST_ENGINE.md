# PostHarvestCostEngine

**Módulo:** `backend/agrosv/economics/costs.py`
**Endpoint:** `POST /api/economics/costs/post-harvest`
**Versión:** 8.0.0

## Propósito

Desglose de manejo, limpieza, clasificación, secado, procesamiento, empaque, almacenamiento, refrigeración, flete y mermas poscosecha.

## Implementación verificada

Separa pérdidas poscosecha de pérdidas en campo y exige `loss_fraction_source` cuando `post_harvest_loss_fraction > 0`.

## Limitaciones y reglas de gobernanza

- No aplica porcentajes genéricos de pérdida como medición salvadoreña.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
