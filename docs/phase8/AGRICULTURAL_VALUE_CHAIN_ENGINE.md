# AgriculturalValueChainEngine

**Módulo:** `backend/agrosv/economics/supply_chain.py`
**Endpoint:** `POST /api/economics/value-chain`
**Versión:** 8.0.0

## Propósito

Calcula participación del productor/mayorista en precio minorista y brecha mayorista-minorista usando series reales WFP.

## Implementación verificada

Normaliza precios a `USD/t` y consulta WFP cuando no se provee mayorista o minorista.

## Limitaciones y reglas de gobernanza

- Prohíbe inferir explotación o poder de mercado solo a partir de diferencias de precios (`market_power_inferred: false`).
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
