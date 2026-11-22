# CropMonitoringTimelineEngine — línea temporal

**Módulo:** `backend/agrosv/monitoring/integration.py`
**Endpoint:** `POST /api/monitoring/timeline`
**Versión:** 7.0.0

## Tipos de evento

`planting`, `growth_stage`, `satellite_observation`, `climate_event`,
`anomaly`, `risk_change`, `alert`, `field_verification`, `harvest`,
`management`.

Cada evento declara fecha ISO, tipo, descripción, valor/unidad opcionales,
clase de evidencia, fuente y procedencia.

## Orden y procedencia

- ordena por fecha y asigna `sequence`;
- valida el tipo y la clase de evidencia (una clase inventada se rechaza);
- detecta posibles duplicados por `(fecha, tipo, fuente)` y los informa en
  `duplicates_suspected`, sin borrarlos;
- calcula `period` de la línea;
- si se aporta `expected_interval_days`, informa `missing_periods` cuando el
  hueco supera 1,5× el intervalo.

## Regla de no relleno

`interpolated: false`. **No se inventan eventos** para completar un periodo. Un
hueco es un hueco, no una siembra ni una cosecha supuesta.

## Limitaciones

1. La fecha de un evento no prueba que el proceso ocurriera ese día.
2. Eventos de fuentes distintas pueden solaparse.
3. No se resuelve conflicto entre eventos: se muestran ambos.
4. La siembra y la cosecha requieren registro de campo o fuente documentada.

## Validación

Pruebas: orden correcto, duplicado informado, hueco detectado y rechazo de tipo
desconocido.
