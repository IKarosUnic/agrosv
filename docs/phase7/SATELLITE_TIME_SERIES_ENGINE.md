# SatelliteTimeSeriesEngine — series temporales y línea base

**Módulo:** `backend/agrosv/monitoring/timeseries.py`
**Endpoints:** `POST /api/monitoring/timeseries`, `POST /api/monitoring/timeseries/anomaly`
**Versión:** 7.0.0

## Operaciones

| Método | Qué hace | Qué no hace |
|---|---|---|
| `build` | valida fechas, excluye nubes > umbral y valores ausentes | no interpola |
| `gaps` | intervalos > 1,5× el esperado | no rellena |
| `rolling` | media/mín/máx móvil con `min_periods` | no suaviza para “completar” |
| `seasonal_baseline` | ventana de día del año en **otros años** | no compara estaciones distintas |
| `anomaly` | z robusto (mediana/MAD) | no atribuye causa |
| `trajectory` | OLS descriptiva | no pronostica |
| `compare` | diferencia de medianas | no es prueba de significancia |

## Línea base estacional

`seasonal_baseline(target_date, window_days=15, min_years=3, min_obs=6)`:

- selecciona observaciones dentro de ±15 días del día del año objetivo;
- excluye el año objetivo por defecto;
- exige ≥ 3 años y ≥ 6 observaciones; si no, `InsufficientRecordError`;
- devuelve mediana, MAD escalado (×1,4826), P10, P90, años y valores.

La distancia de día del año es circular (365/366), de modo que diciembre y
enero quedan próximos. Limitación: una ventana de 15 días puede mezclar etapas
fenológicas.

## Anomalía

```
z = (valor − mediana_línea_base) / MAD
```

Si MAD = 0, el resultado es `None` con nota: una anomalía infinita no es
información. Dirección `below_baseline`/`above_baseline` solo con z finito.

## Huecos

`gaps(expected_interval_days=10)` informa intervalos y observaciones faltantes
estimadas. La respuesta incluye `interpolated: false` y la advertencia de que
una nube persistente puede ocultar una parcela sana. **Una observación ausente
no se interpreta como deterioro.**

## Tendencia

OLS sobre días ordinales; devuelve pendiente por día y por 30 días, R², periodo
y la etiqueta “tendencia descriptiva; no es pronóstico ni atribución causal”.
No elimina estacionalidad: para eso están las anomalías estacionales.

## Validación

Las pruebas verifican exclusión por nubosidad y valor ausente, detección de un
hueco de 45 días, rechazo de línea base con menos de 3 años, coincidencia del z
robusto con el cálculo manual, pendiente positiva en serie creciente y
comparación descriptiva.
