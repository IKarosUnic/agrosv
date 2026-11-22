# Estándar temporal

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/temporal.py` · Pruebas: `tests/test_raster_temporal.py`, `tests/test_data_api.py`

## 1. Base temporal

El Salvador usa **UTC−6 todo el año** (no aplica horario de verano). Cada
observación conserva:

- `time_utc` — instante normalizado;
- `time_local` — fecha/hora de referencia local;
- `period_start` y `period_end` — intervalo que representa el valor;
- `frequency` y `aggregation` — frecuencia y operación del período;
- `time_basis` — `UTC` o `local`, declarada por la fuente.

`to_utc("2024-05-01T00:00:00", time_basis="local")` devuelve `06:00Z`;
`to_local("2024-05-01T06:00:00Z")` devuelve `00:00`. `time_basis_report()`
publica `utc_offset_hours: -6` y `dst: false`.

No se infiere la base temporal a partir de la fuente: se declara. Una serie
diaria de NASA POWER viene desagregada de pentadas; Open-Meteo agrega ERA5/IFS.
Ambas se registran como `reanalysis`, con su método y limitación.

## 2. Clases de evidencia

`EvidenceClass`: `observation`, `reanalysis`, `forecast`,
`climate_projection`, `simulation`. Son categorías **no intercambiables**.

`assert_comparable([...])` prohíbe mezclar observación con pronóstico o
proyección en la misma serie. `TimeSeriesSpec` exige `uncertainty_note` cuando la
clase no es observacional: un pronóstico sin incertidumbre declarada no es
publicable.

Los datasets integrados de clima son reanálisis (`nasa_power_point`,
`open_meteo_point`); el catálogo lo dice y la API devuelve
`evidence_class: "reanalysis"` por fila. No se presentan como estaciones.

## 3. Frecuencia y agregación

`Frequency` distingue horaria, diaria, mensual, anual y eventos. `Aggregation`
distingue `sum`, `mean`, `max`, `min`, `instant`.

Regla: una precipitación diaria es `sum`; una temperatura diaria es `mean` o
`max`/`min` según la variable. El registro conserva ambos campos. Cambiar de
frecuencia sin declarar la agregación es un error, no una comodidad.

`validate_series()` detecta:

| Código | Significado |
|---|---|
| `fechas_invalidas` | fecha no parseable |
| `periodos_faltantes` | huecos en la secuencia esperada |
| `periodos_duplicados` | misma fecha dos veces |
| `frecuencia_inconsistente` | etiquetas que no corresponden a la frecuencia declarada |
| `centinela_como_dato` | −999, −9999 u otro centinela tratado como medición |
| `serie_vacia` | sin datos |

Un hueco no se rellena con cero ni con interpolación silenciosa. Se enumera.

## 4. Períodos y agregación

`aggregate_periods(times, values, spec, target)` agrega con la operación
declarada y devuelve por período: valor, nº de observaciones, `complete` y
`quality_flag`. Si el período no tiene todas las observaciones esperadas, se
marca `incomplete_period`. Ejemplo: cinco días de noviembre agregados a mes
producen un valor de 5 mm y `complete: false`.

Esto evita el error clásico de comparar un mes completo con otro incompleto sin
saberlo.

## 5. Temporadas agrícolas y año hidrológico

`season_of(date)` devuelve una referencia (`primera`, `postrera`, `apante`,
transición) y `season_calendar_report()` publica:

```json
{
  "status": "REFERENCE_ONLY",
  "limitation": "no es un calendario oficial; las fechas varían por zona y año"
}
```

**No se inventa** un calendario oficial del MAG. Las temporadas son una
referencia de consulta, no una regla de agregación. Cualquier modelo futuro debe
declarar qué calendario usa y su fuente.

`hydrological_year(date)` usa el año hidrológico **1 de mayo – 30 de abril**:

- `2025-03-15` → `HY2024/2025`
- `2025-05-01` → `HY2025/2026`

Es una convención documentada, no una verdad universal; se puede cambiar en un
solo lugar si el proyecto adopta otra.

## 6. Filtros temporales en la API

`GET /api/data/observations?start=2020-01-01&end=2020-12-31` filtra por
**fecha local de referencia** (`time_local`), con `end` inclusivo por día
calendario. Esto evita dos errores de borde:

- una observación del 1 de enero local (UTC−6) empieza el 31 de diciembre en UTC
  y desaparecería si se filtrara por `period_start` UTC;
- una observación del 1 de enero de 2021 local podría colarse si se filtrara por
  solapamiento de período.

La prueba de regresión exige exactamente **366** observaciones para 2020
(año bisiesto) en `nasa_power_point`/`precipitation`. Antes del arreglo devolvía
364; el defecto se detectó con la prueba, no en producción.

## 7. Volumen integrado

- `nasa_power_point`: 7.671 observaciones (precipitación, temperatura máx/mín y
  otras variables, 2019–2025).
- `open_meteo_point`: 12.785 observaciones.
- Total en la base: **20.456** observaciones.

Cada fila conserva dataset, versión, fuente, unidad, base temporal, frecuencia,
agregación, clase de evidencia y bandera de calidad.

## 8. Limitaciones

- No hay series de estaciones SNET/MARN: las observaciones locales no están
  integradas. La comparación NASA vs Open-Meteo es una **intercomparación de
  reanálisis**, no una validación contra mediciones.
- El calendario agrícola es una referencia, no el calendario oficial.
- Las series cubren puntos (13,70 N, 89,20 O y 13,67 N, 89,17 O), no el país.
- La serie CHIRPS integrada es un día recortado; no es una serie nacional.
- La zona horaria es fija UTC−6; si una fuente usa otra base, debe declararlo y
  se convierte al registrar, conservando la base original en el manifiesto.
