# ThermalStressEngine — exposición térmica

**Módulo:** `backend/agrosv/monitoring/crop_health.py`
**Endpoint:** `POST /api/monitoring/thermal-stress`
**Versión:** 7.0.0

## Cálculo

`heat_exposure(tmax_c, threshold_c, threshold_source)`:

- días sobre el umbral;
- racha máxima consecutiva;
- `heat_wave_3d`: racha ≥ 3 días;
- grados-día de exceso: Σ max(0, Tmax − umbral).

**El umbral y su fuente son obligatorios.** Sin fuente se lanza
`MonitoringError`: no se inventa un umbral agronómico.

## Salida de evaluación

- estado `heat_wave_detected`, `isolated_heat_days` o `no_heat_exposure`;
- sensibilidad de la etapa (tabla genérica);
- `sensitive_stage`: sensibilidad ≥ 0,6;
- confianza media con ≥ 7 días de registro, baja con menos;
- GDD si se aportan Tmin y Tbase (`accumulate` de Fase 6).

## Temperatura del aire vs LST

`land_surface_temperature` se informa con `used_for_stress: false`. La LST de
satélite **no** se sustituye por temperatura de dosel sin metodología validada.
La temperatura del aire de un punto tampoco representa toda la parcela.

## Limitaciones

1. El umbral no está calibrado para variedades salvadoreñas.
2. No se modela aclimatación ni el efecto de la humedad del aire.
3. La exposición no cuantifica daño ni pérdida.
4. No hay datos de temperatura de dosel en el repositorio.

## Validación

Pruebas: ola de calor de 7 días detectada, LST presente pero no usada y rechazo
de umbral sin fuente.
