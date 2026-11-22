# MachineryAndEquipmentCostEngine

**Módulo:** `backend/agrosv/economics/costs.py`
**Endpoint:** `POST /api/economics/costs/machinery`
**Versión:** 8.0.0

## Propósito

Comparación entre propiedad (depreciación lineal, combustible, operador, mantenimiento, financiamiento), alquiler y uso compartido.

## Implementación verificada

Fórmula de depreciación: `(compra - rescate) / vida_útil_horas`.

## Limitaciones y reglas de gobernanza

- Declara explícitamente la barrera de acceso a maquinaria propia para pequeños productores.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
