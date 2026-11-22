# AgriculturalCostEngine

**Módulo:** `backend/agrosv/economics/costs.py`
**Endpoint:** `POST /api/economics/costs/aggregate`
**Versión:** 8.0.0

## Propósito

Agregador de costos separando `variable`/`fixed`, `direct`/`indirect` y `operating`/`investment`/`opportunity`.

## Implementación verificada

Normaliza costos por ciclo, `ha`, `mz` (`0.70 ha`), `kg`, `qq` (`46 kg`) y `t` (`1000 kg`), ordenando los principales impulsores de costo.

## Limitaciones y reglas de gobernanza

- Rechaza mezclar monedas distintas sin conversión explícita.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
