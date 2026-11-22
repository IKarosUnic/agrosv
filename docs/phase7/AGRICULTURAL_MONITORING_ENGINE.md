# AgriculturalMonitoringEngine — capa integrada

**Módulo:** `backend/agrosv/monitoring/integration.py`
**Endpoint:** `POST /api/monitoring/status`
**Versión:** 7.0.0

## Función

Reúne capas ya calculadas para un punto y declara cuáles están disponibles:

- índice satelital;
- anomalías;
- riesgos;
- resumen de alertas;
- soporte de escala (si se aporta resolución);
- contexto territorial/suelo de Fase 5 (opcional).

## Contrato

Cada capa es `{available, value, evidence_class}` o
`{available: false, value: null, reason}`. El motor **no calcula** capas
ausentes ni las sustituye por un valor por defecto.

`missing_layers` enumera lo que falta. `available_layers`/`total_layers` da una
cuenta explícita, no una puntuación.

## Escala

Si se aporta `resolution_m`, se ejecuta `scale_support(resolution_m, scale)` y se
declara si la resolución sostiene la escala solicitada (nacional,
departamental, municipal, zona agrícola, finca, parcela).

## Reglas

1. Coordenada fuera de El Salvador → `MonitoringError` (HTTP 400).
2. Escala no admitida → `UnsupportedScaleError`.
3. No se promedia entre observación y modelo.
4. No se crea un índice compuesto de monitorización.

## Limitaciones

1. Depende de que el llamador aporte las capas; no orquesta cálculos pesados.
2. El contexto de Fase 5 puede no estar disponible y se declara.
3. La agregación no resuelve desacuerdos entre capas: los muestra.
