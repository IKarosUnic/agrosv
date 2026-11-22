# MarketSupplyDemandEngine

**Módulo:** `backend/agrosv/economics/markets.py`
**Endpoint:** `POST /api/economics/markets/supply-demand`
**Versión:** 8.0.0

## Propósito

Balance contable de disponibilidad aparente (`producción + importaciones - exportaciones + cambio_inventarios`).

## Implementación verificada

Reutiliza producción nacional de CAP 2025 cuando está disponible y declara componentes faltantes (`imports_t`, `exports_t`).

## Limitaciones y reglas de gobernanza

- No infiere demanda real desde precios incompletos.
- Todas las unidades y conversiones (`1 mz = 0.70 ha`, `1 qq = 46 kg`, `1 t = 1000 kg`) se declaran explícitamente.
- Ningún resultado calcula pronósticos de mercado ni inventa precios o estadísticas faltantes.
