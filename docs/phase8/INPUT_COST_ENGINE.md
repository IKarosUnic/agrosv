# InputCostEngine

**Módulo:** `backend/agrosv/economics/costs.py`
**Endpoint:** `POST /api/economics/costs/inputs`
**Versión:** 8.0.0

## Propósito

Registro y valoración de 11 categorías de insumos con marca, empaque, vendedor, ubicación, fecha y tipo de precio.

## Implementación verificada

Marca precios antiguos (`> 90 días` o `historical`) con advertencia explícita y exige `crop_id`, `target_organism` y `registration_status` en plaguicidas.

## Limitaciones y reglas de gobernanza

- No publica cotizaciones actuales inventadas de agroservicios.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
