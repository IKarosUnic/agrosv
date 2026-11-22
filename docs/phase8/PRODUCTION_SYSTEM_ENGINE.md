# ProductionSystemEngine

**Módulo:** `backend/agrosv/economics/production.py`
**Endpoint:** `GET /api/economics/production/systems`
**Versión:** 8.0.0

## Propósito

Catálogo y perfilado de 12 sistemas productivos salvadoreños (secano, riego, familiar, subsistencia, comercial, agroforestal, protegido, urbano, milpa, diversificado).

## Implementación verificada

Convierte superficie entre hectáreas y manzanas (`1 mz = 0.70 ha`) y conserva como `null` los atributos de manejo no aportados.

## Limitaciones y reglas de gobernanza

- No estandariza fincas heterogéneas bajo un modelo único.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
